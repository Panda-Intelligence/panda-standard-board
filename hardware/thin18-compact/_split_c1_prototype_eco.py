#!/usr/bin/env python3
"""Deterministic prototype ECO: manufacturer land and exact commodity identity."""
from pathlib import Path
import json, re, uuid
from _split_c1_sourcing import blocks, property_value, balanced
ROOT = Path(__file__).resolve().parent
REL = Path("eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16")
C301_FP = "panda-standard:CPH3225A_Polarized_Derived"
L402_FP = "panda-standard:XGL4015_Coilcraft"
C301_DESC = "Seiko CPH3225A polarized EDLC; pin 1 positive RTC_VBACKUP, pin 2 GND. Prototype-derived 1.3x1.3 mm lands at x=+/-1.1 mm from manufacturer 1x1 mm bottom terminals; not a supplier-recommended land. Confirm physical polarity to pin 1; do not infer it from logo orientation."
L402_DESC = "Coilcraft XGL4015-222MEC; manufacturer recommended lands 0.98x3.4 mm, center pitch 2.37 mm; 4.0+/-0.3 mm body, height 1.5 mm max."
CAP_URL = "https://jlcpcb.com/partdetail/HRE-CGA0603X7R106K100JT/C22399626"
COIL_URL = "https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xgl/xgl4015/xgl4015-222/"
def set_prop(block, name, value):
    pat = r'(\(property\s+' + re.escape(json.dumps(name)) + r'\s+)("(?:\\.|[^"\\])*")'
    if not re.search(pat, block): raise ValueError("Missing property " + name)
    return re.sub(pat, lambda m: m.group(1)+json.dumps(value), block, count=1)
def pad_patch(block, ref):
    for start,end,pad in reversed(list(blocks(block, r"\(pad\s"))):
        number = re.match(r'\(pad\s+"([^"]+)"', pad).group(1)
        if number not in ("1","2"): raise ValueError("Unexpected pad")
        sign = -1 if number=="1" else 1
        x = sign*(1.185 if ref=="L402" else 1.1)
        pad = re.sub(r'(\(at\s+)[-\d.]+(\s+[-\d.]+)', lambda m:m.group(1)+str(x)+m.group(2), pad, count=1)
        size = "0.98 3.4" if ref=="L402" else "1.3 1.3"
        pad = re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)', "(size "+size+")", pad, count=1)
        # Manufacturer square lands, without removing terminal coverage at corners.
        pad = pad.replace("smd roundrect","smd rect")
        pad = re.sub(r'\s*\(roundrect_rratio\s+[-\d.]+\)', "", pad)
        block = block[:start]+pad+block[end:]
    return block
def patch(block, ref, pcb):
    if ref=="J201":
        return set_prop(block,"Description","GCT USB4500-03-0-A mid-mount 0.8 mm board. CAD includes 9.24 mm wide edge cutout with corner relief; prior straight-edge/no-cutout description was incorrect. Manufacturer-pattern SMT lands approach cutout by 0.02 mm. Requires explicit JLC CAM acceptance of this edge clearance; no standard fabrication release inferred from the inherited DRC exception.")
    if ref in ("C506","C513"):
        if property_value(block,"MPN") not in ("0603B106K100NT","CGA0603X7R106K100JT"): raise ValueError("Unexpected capacitor identity")
        block=set_prop(block,"Manufacturer","HRE")
        block=set_prop(block,"MPN","CGA0603X7R106K100JT")
        block=set_prop(block,"Datasheet",CAP_URL)
        block=set_prop(block,"Description","Controlled prototype ECO: HRE 10uF 10V X7R +/-10% 0603, C22399626; effective DC-bias capacitance remains a physical qualification item.")
        return block
    new_name = C301_FP if ref=="C301" else L402_FP
    desc = C301_DESC if ref=="C301" else L402_DESC
    block=set_prop(block,"Description",desc)
    if ref=="L402":
        block=set_prop(block,"Datasheet",COIL_URL)
    if not pcb: return set_prop(block,"Footprint",new_name)
    block=re.sub(r'^\(footprint\s+"[^"]+"', '(footprint "'+new_name+'"', block, count=1)
    block=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)', "(descr "+json.dumps(desc)+")", block, count=1)
    block=pad_patch(block,ref)
    if ref=="L402":
        block=block.replace("(start -2.2 -2.2) (end 2.2 2.2)","(start -2.4 -2.4) (end 2.4 2.4)")
    else:
        for s,e,_ in reversed(list(blocks(block,r"\(model\s"))): block=block[:s]+block[e:]
        marker='(fp_text user "+" (at -1.1 0 90) (layer "F.Fab") (uuid "'+str(uuid.uuid5(uuid.NAMESPACE_URL,"panda/C301/positive-marker"))+'") (effects (font (size 1 1) (thickness 0.15))))'
        for a,b,t in reversed(list(blocks(block,r"\(fp_text\s+user\s+\"\+\""))): block=block[:a]+block[b:]
        block=block[:-1]+" "+marker+")"
    return block
def library_from_board(block, name):
    block=re.sub(r'^\(footprint\s+"[^"]+"', '(footprint "'+name+'" (version 20260206) (generator "pcbnew")', block, count=1)
    block=re.sub(r'\s*\(locked yes\)',"",block,count=1)
    # Board location follows the header; library origin is local (0,0).
    start=block.find("(at ")
    if start>=0:
        header=block[start:balanced(block,start)];vals=re.findall(r"[-\d.]+",header);angle=float(vals[2]) if len(vals)>2 else 0
        block=block[:start]+block[balanced(block,start):]
        def local_angle(m):
            a=float(m.group(3))-angle
            return m.group(1)+m.group(2)+" "+str(round(a,6))+")"
        block=re.sub(r"(\(at\s+)([-\d.]+\s+[-\d.]+)\s+([-\d.]+)\)",local_angle,block)
    for pattern in [r"\(uuid\s",r"\(net\s",r"\(path\s",r"\(sheetname\s",r"\(sheetfile\s"]:
        for s,e,_ in reversed(list(blocks(block,pattern))): block=block[:s]+block[e:]
    for field,val in [("Reference","REF**"),("Value",name)]: block=set_prop(block,field,val)
    return block+"\n"
def apply_prototype_eco(candidate, board_id):
    candidate=Path(candidate)
    if board_id=="Display-C1":
        pcb=candidate/"PANDA-EPD0426-SPI-EVT.kicad_pcb"
        text=pcb.read_text()
        for a,b,prop in reversed(list(blocks(text,r"\(property\s+\"Reference\""))):
            prop=re.sub(r"\(size\s+[-\d.]+\s+[-\d.]+\)","(size 1 1)",prop,count=1)
            prop=re.sub(r"\(thickness\s+[-\d.]+\)","(thickness 0.15)",prop,count=1)
            text=text[:a]+prop+text[b:]
        pcb.write_text(text)
        return
    if board_id!="Core-C1": raise ValueError("Unknown board")
    folder=candidate/REL
    refs={"C301","L402","C506","C513","J201"};seen={True:set(),False:set()};library={}
    for path in sorted(folder.glob("*.kicad_sch"))+sorted(folder.glob("*.kicad_pcb")):
        text=path.read_text();pcb=path.suffix==".kicad_pcb"
        pattern=r"\(footprint\s" if pcb else r"\(symbol\s+\(lib_id\s"
        for s,e,block in reversed(list(blocks(text,pattern))):
            ref=property_value(block,"Reference")
            if ref not in refs: continue
            if ref in seen[pcb]: raise ValueError("Duplicate ECO ref")
            seen[pcb].add(ref);new=patch(block,ref,pcb);text=text[:s]+new+text[e:]
            if pcb and ref in ("C301","L402"): library[ref]=new
        path.write_text(text)
    if any(v!=refs for v in seen.values()): raise ValueError("Missing ECO refs")
    lib=candidate/"lib/panda-standard.pretty";lib.mkdir(exist_ok=True,parents=True)
    for ref,name in [("C301","CPH3225A_Polarized_Derived"),("L402","XGL4015_Coilcraft")]:
        (lib/(name+".kicad_mod")).write_text(library_from_board(library[ref],name))
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--candidate",type=Path,required=True)
    apply_prototype_eco(p.parse_args().candidate,"Core-C1")
