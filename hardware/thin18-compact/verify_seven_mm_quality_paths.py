#!/usr/bin/env python3
"""Connected-path checks for quality routing; not impedance, delay or thermal proof."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'tools'))
from signal_path_geometry import SignalPathGraph, require


def inspect(geometry):
    graphs={};terminal={}
    for r in geometry['items']:
        if r['type']=='pad' and r.get('pad'):
            terminal.setdefault((r['ref'],r['pad']),set()).add(r['net'])
    def endpoints(net,ref=None):
        return sorted(k for k,v in terminal.items() if v=={net} and (ref is None or k[0]==ref))
    def path(net,a,b):
        if net not in graphs:graphs[net]=SignalPathGraph(geometry,net)
        return graphs[net].path(a,b)
    def series(net_a,net_b):
        candidates=[]
        for a in endpoints(net_a):
            if not a[0].startswith('R'):continue
            for b in endpoints(net_b):
                if a[0]==b[0]:candidates.append((a,b))
        require(len(candidates)==1,'Missing/ambiguous series link '+net_a)
        return candidates[0]
    sd=[]
    for signal in ['CLK','CMD','D0','D1','D2','D3']:
        net='SDMMC_'+signal;card=net+'_CARD';a,b=series(net,card)
        host=endpoints(net,'U501');port=endpoints(card,'J501');require(len(host)==len(port)==1,'Missing SD endpoint')
        parts=[path(net,host[0],a),path(card,b,port[0])]
        sd.append({'signal':signal,'planar_mm':sum(p['planar_path_length_mm'] for p in parts),'vias':sum(p['vias_on_path'] for p in parts),'layers':sorted({l for p in parts for l in p['signal_layers_used']})})
    clk=next(x['planar_mm'] for x in sd if x['signal']=='CLK')
    for row in sd:
        row['relative_to_clk_mm']=round(row['planar_mm']-clk,6)
        row['single_surface_no_via']=row['layers']==['F.Cu'] and row['vias']==0
    usb=[]
    for signal,hostpin,portpin,clamp in [('DP','26','A6','1'),('DM','25','A7','2')]:
        net='USB_'+signal;a,b=series(net+'_MCU',net)
        hm=path(net+'_MCU',('U501',hostpin),a)
        branch=path(net,b,('D201',clamp));full=path(net,b,('J201',portpin))
        usb.append({'signal':signal,'mcu_to_clamp_planar_mm':hm['planar_path_length_mm']+branch['planar_path_length_mm'],
                    'mcu_to_port_planar_mm':hm['planar_path_length_mm']+full['planar_path_length_mm'],
                    'signal_vias_mcu_to_port':hm['vias_on_path']+full['vias_on_path'],
                    'layers':sorted(set(hm['signal_layers_used'])|set(full['signal_layers_used']))})
    skew=abs(usb[0]['mcu_to_port_planar_mm']-usb[1]['mcu_to_port_planar_mm'])
    clamp_skew=abs(usb[0]['mcu_to_clamp_planar_mm']-usb[1]['mcu_to_clamp_planar_mm'])
    battery=path('BAT_CELL_N',('J301','2'),('U907','2'))
    return {'schema':'panda-seven-mm-path-review-v1','source_pcb_sha256':geometry['pcb_sha256'],
            'sd':sd,'sd_matching_and_surface_passed':all(r['single_surface_no_via'] and abs(r['relative_to_clk_mm'])<=1.27 for r in sd),
            'usb':usb,'usb_complete_board_planar_skew_mm':round(skew,6),'usb_mcu_to_clamp_planar_skew_mm':round(clamp_skew,6),
            'usb_complete_board_planar_skew_passed':skew<=.5,'usb_signal_via_count_matched':usb[0]['signal_vias_mcu_to_port']==usb[1]['signal_vias_mcu_to_port'],
            'battery_return':{k:v for k,v in battery.items() if k not in ['path_edges']},
            'scope':'Measured connected PCB centrelines. Package/resistor-body/via delay, impedance, coupling, load current and maximum-temperature rise are not qualified.',
            'impedance_qualified':False,'mechanical_qualified':False,'manufacturing_release':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('geometry',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    result=inspect(json.loads(a.geometry.read_text()))
    if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='battery_return'},indent=2))
    return 0 if result['sd_matching_and_surface_passed'] and result['usb_complete_board_planar_skew_passed'] and result['usb_signal_via_count_matched'] else 2
if __name__=='__main__':raise SystemExit(main())
