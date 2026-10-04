"""Nominal envelope screen for the Split-C1 prototype, not fit qualification."""
from pathlib import Path
import argparse,copy,json,math,unittest
R=Path(__file__).resolve().parents[2]
CONTRACT=R/'hardware/thin18-compact/split-c1-prototype-enclosure.json'

def require(test,message):
    if not test:raise ValueError(message)

def screen(c,metadata=None):
    require(c['schema']=='panda-split-c1-prototype-enclosure-v1','Wrong enclosure target')
    w,h,t=c['outer_dimensions_mm'];cx,cy=c['outer_center_core_xy_mm'];wall=c['wall_thickness_mm']
    require(all(math.isfinite(v) and v>0 for v in [w,h,t,wall]),'Invalid dimensions')
    require(abs(c['front_top_z_mm']-c['rear_bottom_z_mm']-t)<1e-8,'Thickness does not equal actual planes')
    require(c['physical_fit_verified'] is False and c['manufacturing_release'] is False,'Unproven physical release')
    require(c['meets_7mm_product_target'] is False and t>c['product_target_thickness_mm'],'Do not advertise this prototype as the 7mm product')
    p=c['panel'];pw,ph,pt=p['nominal_body_mm'];wx,wy=p['window_mm'];aw,ah=p['active_area_nominal_mm']
    require(pw+2*.3 <= w-2*wall and ph+2*.3 <= h-2*wall,'Panel pocket exceeds cavity')
    require(aw<=wx<pw and ah<=wy<ph,'Window clips nominal active area or loses panel support')
    require(p['body_bottom_z_mm']-p['gasket_thickness_mm']>=c['critical_nominal_checks']['core_max_front_component_z_mm']+.5,'Panel/gasket intersects component budget')
    require(p['body_bottom_z_mm']+max(pt,p['thickness_budget_mm'])<=p['lip_bottom_z_mm'],'Panel thickness budget intersects front lip')
    require(p['lip_bottom_z_mm']<c['front_top_z_mm'],'Front lip has no thickness')
    b=c['battery_envelope'];x0,y0,x1,y1=b['core_xyxy_mm'];bw,bh,bt=b['nominal_maximum_pack_mm']
    require([x1-x0,y1-y0]==[bw,bh],'Pack XY dimensions differ')
    require(cx-w/2+wall <= min(0,x0) and cx+w/2-wall >= max(96,x1),'Core/pack X exceeds cavity')
    require(cy-h/2+wall <= min(0,y0) and cy+h/2-wall >= max(68,y1),'Core/pack Y exceeds cavity')
    dx0,dy0,dx1,dy1=c['critical_nominal_checks']['display_world_xyxy_mm']
    require(x1<=dx0 or x0>=dx1 or y1<=dy0 or y0>=dy1,'Pack overlaps Display PCB XY')
    rear_clear=b['bottom_z_mm']-(c['rear_bottom_z_mm']+c['rear_floor_thickness_mm'])
    require(rear_clear+1e-8>=b['rear_swelling_and_insulation_allowance_mm'],'No reserved rear pack allowance')
    require(b['bottom_z_mm']+bt<=-1.8,'Pack exceeds preliminary Core backside component clearance')
    if metadata:
        require(metadata['boards']['Core-C1']['dimensions_mm']==[96,68],'Not the current Core board')
        require(metadata['boards']['Display-C1']['dimensions_mm']==[45,36],'Not the current Display board')
        refs={f['ref']:f for f in metadata['boards']['Core-C1']['components']}
        for row in c['buttons']:
            require(refs[row['ref']]['xy']==row['center_core_xy_mm'],'Switch opening no longer follows native PCB')
            require(refs[row['ref']]['mpn']==row['mpn'],'Switch identity changed')
        require(refs['J201']['xy']==c['ports']['J201']['center_core_xy_mm'],'USB opening datum changed')
        require(refs['J501']['xy']==c['ports']['J501']['socket_center_core_xy_mm'],'microSD datum changed')
    return {'nominal_envelope_screen_passed':True,'outer_dimensions_mm':[w,h,t],
            'panel_over_component_clearance_mm':p['body_bottom_z_mm']-p['gasket_thickness_mm']-c['critical_nominal_checks']['core_max_front_component_z_mm'],
            'pack_to_display_xy_gap_mm':dx0-x1,'pack_rear_allowance_mm':round(rear_clear,6),
            'product_target_met':False,'exact_3d_collision_analysis_passed':False,'physical_fit_verified':False,'manufacturing_release':False}

class Tests(unittest.TestCase):
    def setUp(self):self.c=json.loads(CONTRACT.read_text())
    def test_nominal(self):self.assertTrue(screen(self.c)['nominal_envelope_screen_passed'])
    def bad(self,key,value):
        c=copy.deepcopy(self.c);node=c
        for k in key[:-1]:node=node[k]
        node[key[-1]]=value
        with self.assertRaises(ValueError):screen(c)
    def test_false_release(self):self.bad(['physical_fit_verified'],True)
    def test_false_7mm_claim(self):self.bad(['meets_7mm_product_target'],True)
    def test_wrong_thickness(self):self.bad(['outer_dimensions_mm'],[112,75,7])
    def test_panel_collision(self):self.bad(['panel','body_bottom_z_mm'],7)
    def test_panel_lip_collision(self):self.bad(['panel','thickness_budget_mm'],4)
    def test_clipped_active_area(self):self.bad(['panel','window_mm'],[90,52])
    def test_pack_overlap(self):self.bad(['battery_envelope','core_xyxy_mm'],[30,11,66,65])
    def test_missing_swelling_clearance(self):self.bad(['battery_envelope','bottom_z_mm'],-9)
    def test_pack_too_high(self):self.bad(['battery_envelope','nominal_maximum_pack_mm'],[36,54,9])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--test',action='store_true');p.add_argument('--metadata',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.test:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));raise SystemExit(0 if result.wasSuccessful() else 1)
    result=screen(json.loads(CONTRACT.read_text()),json.loads(a.metadata.read_text()) if a.metadata else None)
    if a.output:
        out=a.output.resolve();require(not out.is_relative_to(R) or out.is_relative_to(R/'.work'),'Generated report must remain outside source');out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
