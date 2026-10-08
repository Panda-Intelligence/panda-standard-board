#!/usr/bin/env python3
"""Read-only prototype review: electrical connection completion is not release.

Measures saved native copper and thermal vias. Gross net copper length is NOT
reported as endpoint delay or differential skew. Known guideline gaps and missing
manufacturing/stack evidence fail closed instead of reusing the old Split-C1 ZIP.
"""
from pathlib import Path
import argparse,hashlib,json
from seven_mm_native_evidence import verify_native_clean
from _split_c1_common import ROOT

ESP_LAYOUT='https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html'
CHARGER_LAYOUT='https://www.sg-micro.com/rect/assets/58a4fe4d-da1d-49a3-b312-5664211d9016/SGM41513_SGM41513A_SGM41513D.pdf'


def inspect_copper(pcb):
    import pcbnew as P
    b=P.LoadBoard(str(pcb));nets={}
    for t in b.GetTracks():
        net=str(t.GetNetname());r=nets.setdefault(net,{'via_count':0,'segment_count':0,'gross_copper_length_mm':0.,'widths_mm':set(),'layers':set()})
        if isinstance(t,P.PCB_VIA):r['via_count']+=1
        else:
            r['segment_count']+=1;r['gross_copper_length_mm']+=P.ToMM(t.GetLength());r['widths_mm'].add(round(P.ToMM(t.GetWidth()),6));r['layers'].add(b.GetLayerName(t.GetLayer()))
    for r in nets.values():r['gross_copper_length_mm']=round(r['gross_copper_length_mm'],6);r['widths_mm']=sorted(r['widths_mm']);r['layers']=sorted(r['layers'])
    thermal={}
    for ref,pin in [('U501','57'),('U901','25')]:
        f=b.FindFootprintByReference(ref)
        if f is None:continue
        pad=next((p for p in f.Pads() if p.GetNumber()==pin),None)
        if pad is None:raise ValueError('Missing thermal pad '+ref+'.'+pin)
        shape=P.SHAPE_POLY_SET();pad.TransformShapeToPolygon(shape,P.F_Cu,0,P.FromMM(.001),P.ERROR_INSIDE)
        vias=[v for v in b.GetTracks() if isinstance(v,P.PCB_VIA) and str(v.GetNetname())=='GND' and shape.Contains(v.GetPosition())]
        thermal[ref]={'pad':pin,'ground_vias_in_exposed_pad':len(vias),'positions_mm':[[round(P.ToMM(v.GetPosition().x),6),round(P.ToMM(v.GetPosition().y),6)] for v in vias]}
    return {'nets':nets,'thermal_pads':thermal}


def evaluate(core,layout):
    n=core['nets'];t=core['thermal_pads'];issues=[]
    def issue(code,status,message,measured=None,source=None):
        issues.append({'id':code,'status':status,'message':message,'measured':measured,'source':source})
    # These are conservative release-review tests from Espressif's guidance,
    # not claims that a narrower trace is necessarily unsafe at every current.
    for net,width in [('3V3_AON',.635),('3V3_RF',.508)]:
        actual=n.get(net,{}).get('widths_mm',[])
        if not actual or max(actual)<width:
            issue('POWER_WIDTH_'+net,'BLOCKED','No routed trunk meets the supplier-recommended width; review current path, necks and copper areas before fabrication.',{'observed_widths_mm':actual,'recommended_main_width_mm':width},ESP_LAYOUT)
        else:issue('POWER_WIDTH_'+net,'OPEN','A wide segment alone does not verify the entire current path or power-plane necks.',{'observed_widths_mm':actual},ESP_LAYOUT)
    count=t.get('U501',{}).get('ground_vias_in_exposed_pad',0)
    if count<9:issue('MCU_GROUND_VIAS','BLOCKED','ESP32-S3 exposed-pad grounding remains below the nine-via recommendation.',{'actual':count,'recommended_minimum':9},ESP_LAYOUT)
    switch=n.get('SGM41513_SW',{})
    if switch.get('via_count',0) or switch.get('gross_copper_length_mm',0)>10:
        issue('CHARGER_SWITCH_LOOP','OPEN','Review the charger switching loop against the shortest/wide same-layer guidance; no current/loop-area acceptance inferred from DRC.',switch,CHARGER_LAYOUT)
    usb={k:n.get(k,{}) for k in ['USB_DP','USB_DM','USB_DP_MCU','USB_DM_MCU']}
    issue('USB_DIFFERENTIAL','OPEN','Paired/equal-length90-ohm routing, matched transitions, reference continuity and return vias are not qualified by mere net connectivity.',usb,ESP_LAYOUT)
    crossing={k:v for k,v in n.items() if k.startswith('SDMMC_') and (v['via_count'] or len(v['layers'])>1)}
    if crossing:issue('SDIO_LAYER_CHANGES','BLOCKED','Current SDIO routes cross layers; close the native same-layer/length/50-ohm review instead of waiving it.',crossing,ESP_LAYOUT)
    issue('CLOCK_PATH','OPEN','Inspect actual display-clock topology and shorten avoidable detours; gross copper inventory is not a timing measurement.',n.get('EPD_D0'),None)
    issue('STACKUP_AND_SMT','OPEN','The actual board stackup/controlled impedance, current via-in-pad list, stencil and exact-part supply require the selected fabricator assembly process.',None,None)
    if not layout['evidence']['mechanical_tolerance_stack_verified']:
        issue('WHOLE_DEVICE_7MM','OPEN','Panel/FPC/battery maximum envelopes and final tolerances have not proven<=7mm assembled thickness.',None,None)
    return issues


def audit(candidate):
    import wx
    app=wx.GetApp() or wx.App(False)
    candidate=Path(candidate).resolve();before={n:hashlib.sha256((candidate/(n+'.kicad_pcb')).read_bytes()).hexdigest() for n in ['Core','Display']}
    native={n:verify_native_clean(candidate/(n+'.kicad_pcb')) for n in ['Core','Display']}
    copper={n:inspect_copper(candidate/(n+'.kicad_pcb')) for n in ['Core','Display']}
    issues=evaluate(copper['Core'],json.loads((ROOT/'seven_mm_layout.json').read_text()))
    if any(hashlib.sha256((candidate/(n+'.kicad_pcb')).read_bytes()).hexdigest()!=v for n,v in before.items()):raise ValueError('Read-only prototype audit modified a PCB')
    return {'schema':'panda-seven-mm-prototype-review-v1','native':native,'copper_inventory':copper,'engineering_issues':issues,'electrical_connectivity_complete':True,'gross_lengths_are_not_path_delay_or_skew':True,'prototype_order_ready':not issues,'manufacturing_release':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args();r=audit(a.candidate)
    if a.output:
        output=a.output.resolve()
        if not output.is_relative_to(a.candidate.resolve()):raise ValueError('Review output must stay inside the untracked candidate directory')
        output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'electrical_connectivity_complete':r['electrical_connectivity_complete'],'issues':[{'id':x['id'],'status':x['status']} for x in r['engineering_issues']],'prototype_order_ready':r['prototype_order_ready']},indent=2))
    raise SystemExit(0 if r['prototype_order_ready'] else 2)
