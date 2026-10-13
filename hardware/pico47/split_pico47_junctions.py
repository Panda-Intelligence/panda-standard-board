#!/usr/bin/env python3
"""Split residual E0 segments at actual same-net junctions without erasing copper.

Only segments currently reported as dangling are considered. This allows a later
pad-connectivity-guarded prune to remove their dead tails, not their live branch.
No footprint, network, rule, or material identity changes are made.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import shutil
import sys
import uuid

HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
sys.path.insert(0,str(HERE.parent/'thin18-compact'))
from seven_mm_routing import sexpr_blocks,native_semantic_fingerprint
from prune_pico47_stubs import drc,snapshot,preserves_groups


def split(source,output,board_name):
    import wx
    app=wx.GetApp() or wx.App(False)
    import pcbnew as P
    source,output=Path(source).resolve(),Path(output).resolve()
    if output.exists() or (output.is_relative_to(REPO) and not output.is_relative_to(REPO/'.work')):
        raise ValueError('Choose a fresh ignored/external output')
    output.mkdir(parents=True)
    for item in source.iterdir():
        if item.is_file() and (item.suffix in {'.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru','.kicad_sym'}
                or item.name in ['fp-lib-table','sym-lib-table']):
            shutil.copy2(item,output/item.name)
    shutil.copytree(source/'Panda47.pretty',output/'Panda47.pretty')
    pcb=output/(board_name+'.kicad_pcb')
    before=drc(pcb,output/(board_name+'-drc.json'))
    baseline=snapshot(pcb,output/'junction-pad-groups-before.json')
    semantic=native_semantic_fingerprint(pcb)
    ids={i['uuid'] for v in before['violations'] if v['type']=='track_dangling' for i in v['items']}
    text=pcb.read_text()
    b=P.LoadBoard(str(pcb))
    xy=lambda p:(P.ToMM(p.x),P.ToMM(p.y))
    points={}
    tracks={}
    for t in b.GetTracks():
        key=str(t.GetNetname())
        uid=str(t.m_Uuid.AsString())
        if isinstance(t,P.PCB_VIA):
            for layer in [P.F_Cu,P.In1_Cu,P.In2_Cu,P.B_Cu]:
                points.setdefault((key,layer),[]).append((xy(t.GetPosition()),P.ToMM(t.GetWidth(layer))/2,uid))
        else:
            tracks[uid]=t
            for p in [t.GetStart(),t.GetEnd()]:
                points.setdefault((key,t.GetLayer()),[]).append((xy(p),P.ToMM(t.GetWidth())/2,uid))
    for f in b.GetFootprints():
        for pad in f.Pads():
            for layer in [P.F_Cu,P.In1_Cu,P.In2_Cu,P.B_Cu]:
                if pad.IsOnLayer(layer):
                    points.setdefault((str(pad.GetNetname()),layer),[]).append(
                        (xy(pad.GetPosition()),min(xy(pad.GetSize()))/2,str(pad.m_Uuid.AsString())))
    changes=[]
    for block in sexpr_blocks(text,'(segment'):
        uid=re.search(r'\(uuid "([^\"]+)"\)',block)[1]
        if uid not in ids:
            continue
        t=tracks[uid]
        x,y=xy(t.GetStart());xx,yy=xy(t.GetEnd())
        dx,dy=xx-x,yy-y;den=dx*dx+dy*dy
        if den<1e-12:
            continue
        cuts={0.,1.}
        for (px,py),radius,other in points.get((str(t.GetNetname()),t.GetLayer()),[]):
            if uid==other:
                continue
            a=((px-x)*dx+(py-y)*dy)/den
            if 1e-6<a<1-1e-6 and math.hypot(x+a*dx-px,y+a*dy-py)<=P.ToMM(t.GetWidth())/2+radius+1e-7:
                cuts.add(a)
        coords=[]
        for a in sorted(cuts):
            p=(round(x+a*dx,6),round(y+a*dy,6))
            if not coords or p!=coords[-1]:coords.append(p)
        if len(coords)<=2:
            continue
        pieces=[]
        for a,z in zip(coords,coords[1:]):
            row=re.sub(r'\(start [^)]*\)','(start %s %s)'%a,block,count=1)
            row=re.sub(r'\(end [^)]*\)','(end %s %s)'%z,row,count=1)
            new_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'panda47-junction/'+uid+str(a)+str(z)))
            row=re.sub(r'\(uuid "[^\"]+"\)','(uuid "'+new_id+'")',row,count=1)
            pieces.append(row)
        text=text.replace(block,'\n'.join(pieces),1)
        changes.append({'source_uuid':uid,'net':str(t.GetNetname()),'pieces':len(pieces)})
    backup=pcb.read_bytes()
    pcb.write_text(text)
    try:
        after=drc(pcb,output/(board_name+'-drc.json'))
        groups=snapshot(pcb,output/'junction-pad-groups-after.json')
        valid=preserves_groups(baseline,groups) and preserves_groups(groups,baseline)
        valid=valid and native_semantic_fingerprint(pcb)==semantic
        valid=valid and not after.get('schematic_parity')
        valid=valid and sum(v['severity']=='error' for v in after['violations'])<=sum(v['severity']=='error' for v in before['violations'])
        if not valid:raise ValueError('Junction split did not preserve native connectivity and DRC')
    except Exception:
        pcb.write_bytes(backup)
        drc(pcb,output/(board_name+'-drc.json'))
        raise
    result={'board':board_name,'segment_splits':changes,'native_pad_connectivity_identical':True,
            'drc':len(after['violations']),'open':len(after['unconnected_items']),
            'manufacturing_release':False}
    (output/'JUNCTION-REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
    print('JUNCTION_SPLITS',len(changes),'DRC',result['drc'],'OPEN',result['open'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--board',choices=['Core','Display'],default='Core')
    a=p.parse_args();split(a.source,a.output,a.board)
