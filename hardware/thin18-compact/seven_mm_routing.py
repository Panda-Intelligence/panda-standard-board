#!/usr/bin/env python3
"""Semantic routing-plan freeze/replay for generated seven-mm native boards.

Routing plans are source artifacts; router DSN/SES, logs and generated boards are
not. Replay checks footprint/pad/outline semantics, not runtime-generated UUIDs.
"""
from pathlib import Path
import hashlib
import json
import re
from seven_mm_native_evidence import verify_native_clean, sha

def balanced(text,start):
    depth=0;quoted=escaped=False
    for i in range(start,len(text)):
        c=text[i]
        if quoted:
            if escaped: escaped=False
            elif c=="\\": escaped=True
            elif c=='"': quoted=False
        elif c=='"': quoted=True
        elif c=='(': depth+=1
        elif c==')':
            depth-=1
            if depth==0:return i+1
    raise ValueError("unterminated expression")

def sexpr_blocks(text,token):
    """Match full S-expression atoms, never prefix keys or quoted examples."""
    out=[];pos=0;quoted=escaped=False
    while pos<len(text):
        char=text[pos]
        if quoted:
            if escaped:escaped=False
            elif char=="\\":escaped=True
            elif char=='"':quoted=False
            pos+=1;continue
        if char=='"':quoted=True;pos+=1;continue
        end_atom=pos+len(token)
        if text.startswith(token,pos) and end_atom<len(text) and (text[end_atom].isspace() or text[end_atom]==')'):
            end=balanced(text,pos);out.append(text[pos:end]);pos=end
        else:pos+=1
    return out

def native_semantic_fingerprint(path):
    import wx
    app=wx.GetApp() or wx.App(False)
    import pcbnew as P
    board=P.LoadBoard(str(path))
    mm=lambda value:round(P.ToMM(value),6)
    rows=[]
    for f in board.GetFootprints():
        pads=[]
        for p in f.Pads():
            drill=p.GetDrillSize()
            pads.append([p.GetNumber(),str(p.GetNetname()),mm(p.GetPosition().x),mm(p.GetPosition().y),
                         mm(p.GetSize().x),mm(p.GetSize().y),mm(drill.x),mm(drill.y),
                         round(p.GetOrientationDegrees(),6),board.GetLayerName(p.GetLayer())])
        rows.append([f.GetReference(),mm(f.GetPosition().x),mm(f.GetPosition().y),
                     round(f.GetOrientationDegrees(),6),board.GetLayerName(f.GetLayer()),sorted(pads)])
    edges=[]
    for item in board.GetDrawings():
        if item.GetLayer()!=P.Edge_Cuts:continue
        if isinstance(item,P.PCB_SHAPE) and item.GetShape()==P.SHAPE_T_SEGMENT:
            a=[mm(item.GetStart().x),mm(item.GetStart().y)]
            b=[mm(item.GetEnd().x),mm(item.GetEnd().y)]
            edges.append(sorted([a,b]))
        else:
            raise ValueError("Routing fingerprint only supports reviewed segment outlines")
    payload={"footprints":sorted(rows),"edges":sorted(edges),"layers":board.GetCopperLayerCount(),
             "thickness_mm":mm(board.GetDesignSettings().GetBoardThickness())}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def copper_blocks(path):
    text=Path(path).read_text()
    return sexpr_blocks(text,'(segment')+sexpr_blocks(text,'(via')

def freeze(source_pcb,routed_pcb,output,board_id):
    source_pcb=Path(source_pcb);routed_pcb=Path(routed_pcb);output=Path(output)
    source_fp=native_semantic_fingerprint(source_pcb)
    routed_fp=native_semantic_fingerprint(routed_pcb)
    if source_fp!=routed_fp:raise ValueError("Router changed footprint/pad/outline semantics")
    if copper_blocks(source_pcb):raise ValueError("Freeze source already contains routed copper")
    items=copper_blocks(routed_pcb)
    if not items:raise ValueError("Routed candidate contains no copper")
    segments=sum(b.startswith('(segment') for b in items);vias=len(items)-segments
    evidence=verify_native_clean(routed_pcb)
    if sha(source_pcb.with_suffix(".kicad_pro"))!=evidence["project_sha256"]:
        raise ValueError("Routing project rules/settings differ from source")
    source_rules=sha(source_pcb.with_suffix('.kicad_dru')) if source_pcb.with_suffix('.kicad_dru').exists() else None
    if source_rules!=evidence['design_rules_sha256']:
        raise ValueError('Source custom rules differ from the verified route')
    if sha(source_pcb.with_suffix('.kicad_sch'))!=evidence['schematic_sha256']:
        raise ValueError('Source schematic differs from the verified route')
    plan={"schema":"panda-seven-mm-routing-v1","board":board_id,
          "source_semantic_sha256":source_fp,"segment_count":segments,"via_count":vias,
          "copper_items":items,"native_checks":evidence["counts"],
          "native_evidence":evidence,
          "copper_sha256":hashlib.sha256("\n".join(items).encode()).hexdigest(),
          "zones_included":False,"component_geometry_changed":False,"manufacturing_release":False}
    output.write_text(json.dumps(plan,indent=2)+'\n')
    return plan

def apply(pcb,plan_path,board_id):
    pcb=Path(pcb);plan=json.loads(Path(plan_path).read_text())
    if plan.get("schema")!="panda-seven-mm-routing-v1" or plan.get("board")!=board_id:
        raise ValueError("Wrong routing plan")
    if plan.get("native_checks")!={"drc":0,"open":0,"parity":0,"erc":0}:
        raise ValueError("Routing plan was not frozen from a native-clean candidate")
    if native_semantic_fingerprint(pcb)!=plan["source_semantic_sha256"]:
        raise ValueError("Routing plan placement/pad/outline predecessor differs")
    text=pcb.read_text()
    existing=sexpr_blocks(text,'(segment')+sexpr_blocks(text,'(via')
    if existing:raise ValueError("Refusing to stack routing onto existing copper")
    items=plan["copper_items"]
    evidence=plan.get("native_evidence",{})
    if not all(evidence.get(k) is True for k in ["refill_before_drc","severity_all","schematic_parity_requested"]):
        raise ValueError("Routing plan lacks fresh native evidence")
    if evidence.get("counts")!=plan["native_checks"]:
        raise ValueError("Native evidence/count mismatch")
    if sha(pcb.with_suffix(".kicad_pro"))!=evidence.get("project_sha256"):
        raise ValueError("Routing plan rules no longer match this project")
    rules=sha(pcb.with_suffix('.kicad_dru')) if pcb.with_suffix('.kicad_dru').exists() else None
    if rules!=evidence.get('design_rules_sha256') or 'design_rules_sha256' not in evidence:
        raise ValueError('Custom rules changed after verification')
    if not pcb.with_suffix('.kicad_sch').is_file() or sha(pcb.with_suffix('.kicad_sch'))!=evidence.get('schematic_sha256'):
        raise ValueError('Schematic changed after verification')
    if hashlib.sha256("\n".join(items).encode()).hexdigest()!=plan.get("copper_sha256"):
        raise ValueError("Routing copper changed after native verification")
    if sum(b.startswith('(segment') for b in items)!=plan["segment_count"] or len(items)-plan["segment_count"]!=plan["via_count"]:
        raise ValueError("Routing inventory differs")
    ids=[]
    for block in items:
        m=re.search(r'\(uuid "([^"]+)"\)',block)
        if not m:raise ValueError("Frozen copper without UUID")
        ids.append(m.group(1))
    if len(ids)!=len(set(ids)):raise ValueError("Duplicate frozen copper UUID")
    end=text.rfind(')')
    pcb.write_text(text[:end]+'\n'+'\n'.join(items)+'\n'+text[end:])
    return {"segments":plan["segment_count"],"vias":plan["via_count"],"semantic_sha256":plan["source_semantic_sha256"]}
