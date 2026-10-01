#!/usr/bin/env python3
"""Split the existing EPD power trunk at real copper junctions before leaf cleanup."""
from pathlib import Path
import argparse, math, re, sys, uuid
import wx
APP=wx.App(False)
import pcbnew
from prune_core_c1_stubs import blocks
ap=argparse.ArgumentParser()
ap.add_argument("pcb",type=Path)
ap.add_argument("--restore-from",type=Path)
a=ap.parse_args()
p=a.pcb;s=p.read_text()
existing={m[1] for m in re.finditer(r'\(uuid "([^"]+)"\)',s)}
restore=[]
if a.restore_from:
    for token in ["(segment","(via"]:
        for _,_,blk in blocks(a.restore_from.read_text(),token):
            uid=re.search(r'\(uuid "([^"]+)"\)',blk)
            if '(net "3V3_EPD_LOGIC")' in blk and uid[1] not in existing:
                restore.append(blk)
    end=s.rfind(")")
    s=s[:end]+"\n"+"\n".join(restore)+"\n"+s[end:]
    p.write_text(s)
b=pcbnew.LoadBoard(str(p))
def xy(v):return (pcbnew.ToMM(v.x),pcbnew.ToMM(v.y))
layers=[pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu]
names=dict(zip(layers,["F.Cu","In1.Cu","In2.Cu","B.Cu"]))
points=[];tracks=[]
for t in b.GetTracks():
    if t.GetNetname()!="3V3_EPD_LOGIC":continue
    if isinstance(t,pcbnew.PCB_VIA):
        for l in layers:
            points.append((l,xy(t.GetPosition()),pcbnew.ToMM(t.GetWidth(l))/2,t.m_Uuid.AsString()))
    else:
        tracks.append(t)
        for q in [t.GetStart(),t.GetEnd()]:
            points.append((t.GetLayer(),xy(q),pcbnew.ToMM(t.GetWidth())/2,t.m_Uuid.AsString()))
for f in b.GetFootprints():
    for pad in f.Pads():
        if pad.GetNetname()=="3V3_EPD_LOGIC":
            for l in layers:
                if pad.IsOnLayer(l):
                    points.append((l,xy(pad.GetPosition()),min(xy(pad.GetSize()))/2,pad.m_Uuid.AsString()))
replacements={}
for t in tracks:
    uid=t.m_Uuid.AsString()
    x,y=xy(t.GetStart());xx,yy=xy(t.GetEnd())
    dx,dy=xx-x,yy-y;den=dx*dx+dy*dy
    if not den:continue
    cuts={0.,1.}
    for layer,(px,py),radius,otheruid in points:
        if layer!=t.GetLayer() or uid==otheruid:continue
        alpha=((px-x)*dx+(py-y)*dy)/den
        if 1e-5<alpha<1-1e-5 and math.hypot(x+alpha*dx-px,y+alpha*dy-py)<=pcbnew.ToMM(t.GetWidth())/2+radius+1e-6:
            cuts.add(round(alpha,10))
    if len(cuts)<=2:continue
    cuts=sorted(cuts);rows=[]
    for start,end in zip(cuts,cuts[1:]):
        p1=(round(x+start*dx,6),round(y+start*dy,6))
        p2=(round(x+end*dx,6),round(y+end*dy,6))
        if math.dist(p1,p2)<0.0001:continue
        newuid=str(uuid.uuid5(uuid.NAMESPACE_URL,"panda/core-c1/power-junction/"+uid+str(p1)+str(p2)))
        rows.append('(segment (start %s %s) (end %s %s) (width %s) (layer "%s") (net "3V3_EPD_LOGIC") (uuid "%s"))' %
            (*p1,*p2,pcbnew.ToMM(t.GetWidth()),names[t.GetLayer()],newuid))
    replacements[uid]="\n".join(rows)
for start,end,blk in reversed(list(blocks(s,"(segment"))):
    uid=re.search(r'\(uuid "([^"]+)"\)',blk)[1]
    if uid in replacements:
        s=s[:start]+replacements[uid]+s[end:]
p.write_text(s)
print("restored",len(restore),"power items; split",len(replacements),"branched segments")
