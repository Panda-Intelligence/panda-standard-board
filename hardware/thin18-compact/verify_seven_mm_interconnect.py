#!/usr/bin/env python3
"""Independently verify the 40P+20P seven-mm board-to-board FFC split.

Checks every donor logical position, exact connector identities, opposite-facing
pad alignment, and cable conductor mapping. It does not certify an actual cable
lot, bend, insertion process, or supplier assembly.
"""
from pathlib import Path
import argparse,copy,json,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
LAYOUT=ROOT/'seven_mm_layout.json'
DONOR=ROOT/'split-c1-interface.json'

def require(v,m):
    if not v: raise ValueError(m)

def fields(netlist):
    root=ET.parse(netlist).getroot()
    return {c.get('ref'):{f.get('name'):f.text or '' for f in c.findall('fields/field')}
            for c in root.findall('components/comp')}

def pcb_connectors(path,refs):
    import wx
    app=wx.GetApp() or wx.App(False)
    import pcbnew as P
    b=P.LoadBoard(str(path));out={}
    for ref in refs:
        f=b.FindFootprintByReference(ref);require(f is not None,'Missing footprint '+ref)
        pads={}
        for p in f.Pads():
            if not p.GetNumber() or p.GetNumber()=='MP': continue
            pads[p.GetNumber()]={'net':str(p.GetNetname()),
                'xy':[round(P.ToMM(p.GetPosition().x),6),round(P.ToMM(p.GetPosition().y),6)]}
        out[ref]={'xy':[round(P.ToMM(f.GetPosition().x),6),round(P.ToMM(f.GetPosition().y),6)],
                  'angle':round(f.GetOrientationDegrees()%360,6),'pads':pads}
    return out

def verify(candidate,mapping=None):
    candidate=Path(candidate)
    d=json.loads((candidate/'INTERCONNECT-MAP.json').read_text()) if mapping is None else mapping
    donor=json.loads(DONOR.read_text());layout=json.loads(LAYOUT.read_text())
    require(d['schema']=='panda-seven-mm-interconnect-v1','Wrong map schema')
    rows=d['cable'];require(len(rows)==60 and [r['logical_position'] for r in rows]==list(range(1,61)),'Missing/reordered donor positions')
    dm={int(r['pin']):r for r in donor['mapping']};require(set(dm)==set(range(1,61)),'Donor interface incomplete')
    for r in rows:
        old=dm[r['logical_position']]
        require((r['core_net'] or '')==(old['core_net'] or ''),'Core logical net changed at '+str(r['logical_position']))
        require((r['display_net'] or '').lstrip('/')==(old['display_net'] or '').lstrip('/'),'Display logical net changed at '+str(r['logical_position']))
        if r['logical_position']<=40:
            require((r['core_ref'],r['core_pin'],r['display_ref'],r['display_pin'],r['cable']) ==
                    ('J601',r['logical_position'],'J1',41-r['logical_position'],'FFC40'),'Wrong40P conductor map')
        else:
            p=r['logical_position']-40
            require((r['core_ref'],r['core_pin'],r['display_ref'],r['display_pin'],r['cable']) ==
                    ('J602',p,'J4',21-p,'FFC20'),'Wrong20P conductor map')
    expected={'J601':('X05A10L40G','C21261162'),'J602':('X05A10L20G','C2880915'),
              'J1':('X05A10L40G','C21261162'),'J4':('X05A10L20G','C2880915')}
    cf=fields(candidate/'Core-netlist.xml');df=fields(candidate/'Display-netlist.xml')
    for ref,(mpn,code) in expected.items():
        f=(cf if ref in {'J601','J602'} else df)[ref]
        require(f.get('Manufacturer')=='XKB Connection' and f.get('MPN')==mpn and f.get('LCSC')==code,'Wrong exact connector '+ref)
    cp=pcb_connectors(candidate/'Core.kicad_pcb',['J601','J602'])
    dp=pcb_connectors(candidate/'Display.kicad_pcb',['J1','J4'])
    require(cp['J601']['xy']==[42.5,76.2] and cp['J602']['xy']==[42.5,94.2],'Core FFC placement differs')
    require(dp['J1']['xy']==[35.0,76.2] and dp['J4']['xy']==[35.0,94.2],'Display FFC placement differs')
    require(cp['J601']['angle']==270 and cp['J602']['angle']==270 and dp['J1']['angle']==90 and dp['J4']['angle']==90,'FFC orientation differs')
    norm=lambda n:'' if not n or n.startswith('unconnected-') else n.lstrip('/')
    for r in rows:
        a=cp[r['core_ref']]['pads'][str(r['core_pin'])]
        b=dp[r['display_ref']]['pads'][str(r['display_pin'])]
        require(norm(a['net'])==norm(r['core_net']) and norm(b['net'])==norm(r['display_net']),'PCB pad net differs')
        require(abs(a['xy'][1]-b['xy'][1])<1e-6,'Straight FFC conductor Y alignment differs at '+str(r['logical_position']))
        require(a['xy'][0]>b['xy'][0],'Core/Display connector sides reversed')
    inter=layout['interconnect']
    require(inter['contacts']==60 and inter['exact_parts_selected'] is True,'Source interconnect selection incomplete')
    require(inter['cable']['conductors']==[40,20] and inter['cable']['type']=='same-side-contact FFC','Cable source contract differs')
    require(inter['cable']['exact_length_and_supplier_accepted'] is False,'Unproven cable marked accepted')
    return {'all_60_logical_positions_verified':True,'exact_connector_identities_verified':True,
            'straight_conductor_alignment_verified':True,'physical_cable_acceptance':False,
            'manufacturing_release':False}

def negative_controls(candidate):
    d=json.loads((Path(candidate)/'INTERCONNECT-MAP.json').read_text());cases=[]
    bad=copy.deepcopy(d);bad['cable'][0]['display_pin']=1;cases.append(bad)
    bad=copy.deepcopy(d);bad['cable'][40]['core_pin']=2;cases.append(bad)
    bad=copy.deepcopy(d);bad['cable'][5]['display_net']='WRONG';cases.append(bad)
    for item in cases:
        try:verify(candidate,item)
        except ValueError:continue
        raise AssertionError('Invalid interconnect fixture accepted')
    return len(cases)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--negative-controls',action='store_true');a=p.parse_args()
    r=verify(a.candidate)
    if a.negative_controls:r['negative_controls_rejected']=negative_controls(a.candidate)
    print(json.dumps(r,indent=2))
