#!/usr/bin/env python3
"""Freeze/replay reviewed J601 copper while preserving unrelated native board data."""
from pathlib import Path
import argparse, hashlib, json, re, sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"tools"))
from prune_core_c1_stubs import blocks, remove_uuids
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def copper(text):
    result={}
    for token in ["(segment","(via"]:
        for _,_,block in blocks(text,token):
            m=re.search(r'\(uuid "([^"]+)"\)',block)
            if not m: raise ValueError("copper without UUID")
            if m[1] in result: raise ValueError("duplicate copper UUID")
            result[m[1]]=block
    return result
def digest(text):
    return hashlib.sha256("\n".join(re.sub(r"\s+"," ",block)
        for uid,block in sorted(copper(text).items())).encode()).hexdigest()
def j601(text):
    return next((s,e,b) for s,e,b in blocks(text,"(footprint ")
        if '(property "Reference" "J601"' in b)
def apply_closure(pcb,closure):
    d=json.loads(closure.read_text());text=pcb.read_text()
    if digest(text)==d["routed_copper_sha256"]:
        return
    text,deleted=remove_uuids(text,set(d["removed_copper_uuids"]))
    s,e,_=j601(text)
    text=text[:s]+d["j601_footprint"]+text[e:]
    existing=copper(text)
    for uid,block in d["added_copper"].items():
        if uid in existing: raise ValueError("closure copper already exists")
    end=text.rfind(")")
    text=text[:end]+"\n"+"\n".join(d["added_copper"].values())+"\n"+text[end:]
    if digest(text)!=d["routed_copper_sha256"]:
        raise ValueError("closure replay copper differs from frozen routing")
    pcb.write_text(text)
    print("replayed closure:",len(deleted),"removed;",len(d["added_copper"]),"added")
def freeze(baseline,pcb,verification,output):
    d=json.loads((verification/"drc.json").read_text())
    e=json.loads((verification/"erc.json").read_text())
    assert not any(d[k] for k in ["violations","unconnected_items","schematic_parity"])
    assert not any(s["violations"] for s in e["sheets"])
    old,new=copper(baseline.read_text()),copper(pcb.read_text())
    modified={uid for uid in old.keys() & new.keys()
        if re.sub(r"\s+"," ",old[uid])!=re.sub(r"\s+"," ",new[uid])}
    assert not modified, "unrelated existing copper changed"
    result={"schema":"panda-core-c1-routing-closure-v1",
        "source":"c4d20-96x68-production-bom",
        "routed_pcb_sha256":sha(pcb),"routed_copper_sha256":digest(pcb.read_text()),
        "removed_copper_uuids":sorted(old.keys()-new.keys()),
        "added_copper":{uid:new[uid] for uid in sorted(new.keys()-old.keys())},
        "j601_footprint":j601(pcb.read_text())[2],
        "native_checks":{"drc":0,"open":0,"parity":0,"erc":0},
        "manufacturing_release":False}
    output.write_text(json.dumps(result,indent=2)+"\n")
    print("frozen closure:",len(result["removed_copper_uuids"]),"removed;",
        len(result["added_copper"]),"added")
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("operation",choices=["freeze","apply"])
    ap.add_argument("--pcb",type=Path,required=True)
    ap.add_argument("--closure",type=Path,required=True)
    ap.add_argument("--baseline",type=Path)
    ap.add_argument("--verification",type=Path)
    a=ap.parse_args()
    if a.operation=="apply": apply_closure(a.pcb,a.closure)
    else:
        if not a.baseline or not a.verification: ap.error("freeze needs baseline and verification")
        freeze(a.baseline,a.pcb,a.verification,a.closure)
