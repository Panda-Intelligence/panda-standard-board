#!/usr/bin/env python3
"""Native connected-path checks for BOTH reversible USB orientations and RF supply.

A matched A-side alone is insufficient. These are planar centreline/transition
checks, not a controlled-impedance, electromagnetic or thermal certification.
"""
from pathlib import Path
import argparse,json,sys,unittest,copy,math
sys.path.insert(0,str(Path(__file__).resolve().parent/'tools'))
from signal_path_geometry import SignalPathGraph
from verify_seven_mm_quality_paths import inspect as quality_inspect


def require(value,message):
    if not value:raise ValueError(message)


def evaluate_usb(rows):
    expected={('DP','A6'),('DP','B6'),('DM','A7'),('DM','B7')}
    require(len(rows)==4 and {(r['signal'],r['pin']) for r in rows}==expected,'Both reversible contact pairs are required')
    indexed={(r['signal'],r['pin']):r for r in rows};out=[]
    for orientation,dp,dm in [('A','A6','A7'),('B','B6','B7')]:
        p,m=indexed[('DP',dp)],indexed[('DM',dm)]
        require(all(isinstance(x['planar_mm'],(int,float)) and not isinstance(x['planar_mm'],bool) and math.isfinite(x['planar_mm']) and x['planar_mm']>0 for x in [p,m]),'Invalid path lengths')
        require(all(isinstance(x['vias'],int) and not isinstance(x['vias'],bool) and x['vias']>=0 for x in [p,m]),'Invalid physical via count')
        skew=abs(p['planar_mm']-m['planar_mm'])
        out.append({'orientation':orientation,'skew_mm':round(skew,6),'planar_skew_passed':skew<=.5,'via_count_matched':p['vias']==m['vias'],'DP_mm':p['planar_mm'],'DM_mm':m['planar_mm'],'signal_vias_each':p['vias'] if p['vias']==m['vias'] else None})
    return out


def inspect(geometry):
    base=quality_inspect(geometry);usb=[];graphs={}
    def path(net,a,b):
        if net not in graphs:graphs[net]=SignalPathGraph(geometry,net)
        return graphs[net].path(a,b)
    for signal,pin,resistor,ports in [('DP','26','R529',['A6','B6']),('DM','25','R530',['A7','B7'])]:
        host=path('USB_'+signal+'_MCU',('U501',pin),(resistor,'2'))
        for port in ports:
            tail=path('USB_'+signal,(resistor,'1'),('J201',port))
            usb.append({'signal':signal,'pin':port,'planar_mm':round(host['planar_path_length_mm']+tail['planar_path_length_mm'],6),'vias':host['vias_on_path']+tail['vias_on_path']})
    rf=[]
    for target in ['2','3']:
        p=path('3V3_RF',('C525','1'),('U501',target))
        rf.append({'from':['C525','1'],'to':['U501',target],'planar_mm':p['planar_path_length_mm'],'vias':p['vias_on_path'],'widths_mm':p['trace_widths_on_path_mm'],'review_limit_mm':5.0,'review_passed':p['planar_path_length_mm']<=5 and min(p['trace_widths_on_path_mm'])>=.508-1e-6})
    orientations=evaluate_usb(usb)
    return {'schema':'panda-seven-mm-product-paths-v1','source_pcb_sha256':geometry['pcb_sha256'],'reversible_usb_contacts':usb,'usb_orientations':orientations,'sd':base['sd'],'sd_matching_and_surface_passed':base['sd_matching_and_surface_passed'],'rf_bulk_supply_paths':rf,'all_path_checks_passed':base['sd_matching_and_surface_passed'] and all(r['planar_skew_passed'] and r['via_count_matched'] for r in orientations) and all(r['review_passed'] for r in rf),'impedance_or_thermal_qualified':False,'manufacturer_maximum_envelopes_qualified':False,'manufacturing_release':False,'scope':'Actual connected PCB centrelines in both USB orientations; no package/via-delay or EM certification.'}


class USBTests(unittest.TestCase):
    def setUp(self):self.rows=[{'signal':s,'pin':p,'planar_mm':x,'vias':2} for s,p,x in [('DP','A6',44.097236),('DP','B6',44.097236),('DM','A7',44.335534),('DM','B7',44.335534)]]
    def test_both_pass(self):self.assertTrue(all(r['planar_skew_passed'] and r['via_count_matched'] for r in evaluate_usb(self.rows)))
    def test_old_A_only_false_positive(self):
        r=copy.deepcopy(self.rows);r[0]['planar_mm']=r[2]['planar_mm']=44.224491;r[1]['planar_mm']=43.141698;r[3]['planar_mm']=45.224491
        v=evaluate_usb(r);self.assertTrue(v[0]['planar_skew_passed']);self.assertFalse(v[1]['planar_skew_passed'])
    def test_missing_reverse(self):
        with self.assertRaises(ValueError):evaluate_usb(self.rows[:2])
    def test_duplicate_contact(self):
        with self.assertRaises(ValueError):evaluate_usb(self.rows[:3]+[self.rows[2]])
    def test_via_asymmetry(self):
        r=copy.deepcopy(self.rows);r[3]['vias']=6;self.assertFalse(evaluate_usb(r)[1]['via_count_matched'])
    def test_unbounded_skew(self):
        r=copy.deepcopy(self.rows);r[0]['planar_mm']+=1;self.assertFalse(evaluate_usb(r)[0]['planar_skew_passed'])
    def test_nonfinite_length(self):
        r=copy.deepcopy(self.rows);r[0]['planar_mm']=float('inf')
        with self.assertRaises(ValueError):evaluate_usb(r)
    def test_bool_length(self):
        r=copy.deepcopy(self.rows);r[0]['planar_mm']=True
        with self.assertRaises(ValueError):evaluate_usb(r)
    def test_negative_vias(self):
        r=copy.deepcopy(self.rows);r[0]['vias']=-1
        with self.assertRaises(ValueError):evaluate_usb(r)
    def test_invalid_length(self):
        r=copy.deepcopy(self.rows);r[0]['planar_mm']=-1
        with self.assertRaises(ValueError):evaluate_usb(r)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('geometry',type=Path,nargs='?');p.add_argument('--output',type=Path);p.add_argument('--test',action='store_true');a=p.parse_args()
    if a.test:return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(USBTests)).wasSuccessful() else 1
    require(a.geometry is not None,'Native geometry input required');r=inspect(json.loads(a.geometry.read_text()))
    if a.output:a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2));return 0 if r['all_path_checks_passed'] else 2
if __name__=='__main__':raise SystemExit(main())
