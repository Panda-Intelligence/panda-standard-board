#!/usr/bin/env python3
"""Package checked prototype data; keep CAM/supply acceptance separate from physical EVT."""
from pathlib import Path
import csv, hashlib, json, re, shutil, subprocess, tempfile, zipfile
from _split_c1_common import ROOT, REPO, REL, STEM, kicad_cli
from _split_c1_sourcing import blocks, property_value
K = kicad_cli()
BOARDS = [("Core-C1","core-c1-96x68-split","core-c1-96x68",REL/(STEM+".kicad_pcb")),
          ("Display-C1","display-c1-45x36-production-bom","display-c1-45x36",Path("PANDA-EPD0426-SPI-EVT.kicad_pcb"))]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def classify_dfm(board, data):
    pending=[]
    for item in data["violations"]:
        known=(board=="Core-C1" and item["type"]=="copper_edge_clearance"
               and "actual 0.0200 mm" in item["description"]
               and any("Pad " in x["description"] and "of J201" in x["description"] for x in item["items"]))
        if not known: raise ValueError("Unexpected prototype DFM failure: "+item["description"])
        pending.append(item)
    if data["unconnected_items"]: raise ValueError("DFM copy has unconnected items")
    return {"standard_fabrication_ready":not pending,"cam_acceptance_required":bool(pending),
            "pending_violations":pending}
def verify_land(text, ref, size, center):
    fp=next(b for _,_,b in blocks(text,r"\(footprint\s") if property_value(b,"Reference")==ref)
    pads=list(blocks(fp,r"\(pad\s"))
    if len(pads)!=2: raise ValueError("Wrong land count "+ref)
    for _,_,p in pads:
        n=re.match(r'\(pad\s+"(\d+)"',p).group(1)
        x,y=map(float,re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)",p).groups())
        w,h=map(float,re.search(r"\(size\s+([-\d.]+)\s+([-\d.]+)",p).groups())
        if abs(x-(-center if n=="1" else center))>1e-6 or y!=0 or (w,h)!=size:
            raise ValueError("Incorrect reviewed land "+ref)
    return fp
def run(*args):
    subprocess.run([K,*map(str,args)],check=True,capture_output=True)
def main():
    validation=json.loads((ROOT/"split-c1-validation.json").read_text())
    for label,info in validation["files"].items():
        if "sha256" in info and sha(REPO/label)!=info["sha256"]:
            raise ValueError("Stale CAD validation "+label)
    from audit_split_c1_domestic import verify_fresh
    domestic=json.loads((ROOT/'split-c1-domestic-audit.json').read_text());verify_fresh(domestic)
    core=ROOT/BOARDS[0][1]/BOARDS[0][3]
    text=core.read_text()
    cap=verify_land(text,"C301",(1.3,1.3),1.1)
    capnets={re.match(r'\(pad\s+"(\d+)"',p).group(1): re.search(r'\(net\s+"([^"]+)"',p).group(1) for _,_,p in blocks(cap,r"\(pad\s")}
    if capnets!={"1":"RTC_VBACKUP","2":"GND"} or '(fp_text user "+"' not in cap: raise ValueError("EDLC polarity missing or reversed")
    verify_land(text,"L402",(0.98,3.4),1.185)
    out=ROOT/"production/jlc-prototype-orderpack"
    if out.exists(): shutil.rmtree(out)
    out.mkdir()
    shutil.copy2(ROOT/"JLC-PROTOTYPE-HANDOFF.md",out/"START-HERE.md")
    registry=json.loads((ROOT/"split-c1-sourcing-evidence.json").read_text())
    expected={b:{ref for row in registry["unresolved_smt"] if row["board"]==b for ref in row["refs"]} for b,_,_,_ in BOARDS}
    report={"schema":"panda-split-c1-prototype-orderpack-v1","date":"2026-10-02",
            "purpose":"Bench EVT prototype; no physical board exists yet","manufacturing_release":False,
            "physical_evt_passed":False,"assembly_request_ready":False,
            "all_domestic_bom_complete":domestic["all_domestic_bom_complete"],
            "domestic_foreign_ref_count":domestic["foreign_ref_count"],
            "domestic_status":domestic["status"],"boards":{}}
    with tempfile.TemporaryDirectory(prefix="panda-jlc-prototype-") as tmp:
        for board,candidate,production,relative in BOARDS:
            folder=ROOT/candidate;pcb=folder/relative
            current=validation["files"][board]["native_checks"]
            if any(any(v.values()) for v in current.values()): raise ValueError("Native gates not clean")
            prod=ROOT/"production"/production;manifest=json.loads((prod/"production-manifest.json").read_text())
            for key,entry in manifest["files"].items():
                if sha(REPO/entry["path"])!=entry["sha256"]: raise ValueError("Stale export "+key)
            if manifest["files"]["pcb"]["sha256"]!=sha(pcb): raise ValueError("Export source differs")
            work=Path(tmp)/candidate;shutil.copytree(folder,work);copy=work/relative
            pro=copy.with_suffix(".kicad_pro");settings=json.loads(pro.read_text())
            settings["board"]["design_settings"]["rules"].update(
                min_copper_edge_clearance=0.2,min_clearance=0.1,min_text_height=1.0,min_text_thickness=0.15)
            pro.write_text(json.dumps(settings))
            dru=copy.with_suffix(".kicad_dru")
            if dru.exists():
                d=re.sub(r"\(constraint edge_clearance \(min [^)]+\)\)","(constraint edge_clearance (min 0.2mm))",dru.read_text())
                dru.write_text(d)
            dfm=out/(board+"-DFM.json")
            run("pcb","drc","--format","json","--severity-all","--output",dfm,copy)
            state=classify_dfm(board,json.loads(dfm.read_text()))
            dest=out/board;dest.mkdir()
            jlc=prod/"manufacturing/jlcpcb"
            for name in ["BOM_JLCPCB.csv","CPL_JLCPCB.csv","assembly-sourcing.csv","jlc-summary.json"]:
                shutil.copy2(jlc/name,dest/name)
            shutil.copy2(prod/"manufacturing/bom.csv",dest/"full-system-BOM.csv")
            shutil.copy2(prod/"manufacturing/gerber-drill.zip",dest/(board+"-Gerber-Drill.zip"))
            with zipfile.ZipFile(dest/(board+"-Gerber-Drill.zip")) as z:
                if z.testzip(): raise ValueError("Gerber CRC error")
            bom=list(csv.DictReader((dest/"BOM_JLCPCB.csv").open(encoding="utf-8-sig")))
            cpl=list(csv.DictReader((dest/"CPL_JLCPCB.csv").open(encoding="utf-8-sig")))
            refs={v for row in bom for v in row["Designator"].split(",")}
            cplrefs={row["Designator"] for row in cpl}
            if refs!=cplrefs or len(cplrefs)!=len(cpl): raise ValueError("SMT BOM/CPL mismatch")
            missing={v for row in bom if not row["LCSC Part #"] for v in row["Designator"].split(",")}
            if missing!=expected[board]: raise ValueError("Unexpected unresolved SMT identities")
            # Human assembly views: hide value strings and show refdes on Fab; copper/placement unchanged.
            view=copy.read_text()
            # Remove historical Fab prose and duplicate user ref text from the plotting copy.
            for a,b,t in reversed(list(blocks(view,r"\((?:fp_text|gr_text)\s"))):
                if re.match(r'\(fp_text\s+user\s+"\+"',t): continue
                if '"F.Fab"' in t or '"B.Fab"' in t: view=view[:a]+view[b:]
            for a,b,prop in reversed(list(blocks(view,r"\(property\s"))):
                field=re.match(r'\(property\s+"([^"]+)"',prop)
                if not field: continue
                name=field.group(1)
                if name!="Reference":
                    if "(hide yes)" not in prop: prop=prop.replace("(effects","(hide yes) (effects",1)
                elif name=="Reference":
                    if property_value(prop,"Reference")=="C301":
                        prop=re.sub(r"\(at\s+[-\d.]+\s+[-\d.]+", "(at 0 -2.2",prop,count=1)
                    prop=prop.replace("(hide yes)","").replace('"F.SilkS"','"F.Fab"').replace('"B.SilkS"','"B.Fab"')
                    prop=re.sub(r"\(size\s+[-\d.]+\s+[-\d.]+\)","(size 0.65 0.65)",prop,count=1)
                view=view[:a]+prop+view[b:]
            copy.write_text(view)
            for side,layer in [("Top","F.Fab"),("Bottom","B.Fab")]:
                extra=["--mirror"] if side=="Bottom" else []
                run("pcb","export","svg","--output",dest/("Assembly-"+side+".svg"),
                    "--layers",layer+",Edge.Cuts","--mode-single","--page-size-mode","2",
                    "--exclude-drawing-sheet","--black-and-white",*extra,copy)
            state.update(pcb_sha256=sha(pcb),native_checks=current["current"],
                         dimensions_mm=manifest["board_dimensions_mm"],copper_layers=manifest["copper_layers"],
                         smt_positions=len(cpl),unmapped_smt_refs=sorted(missing),
                         assembly_order_released=False,assembly_request_ready=False,
                         all_domestic_bom_complete=domestic["all_domestic_bom_complete"],
                         foreign_refs=domestic["boards"][board]["foreign_refs"],
                         assembly_acceptance_required=["Exact stock/My Parts confirmation","Standard double-sided assembly, ENIG, carrier panel/rails/fiducials","CPL bottom rotation and all polarized pin-1 orientations in JLC preview","C301 derived land and terminal-positive mounting review"])
            report["boards"][board]=state
    for name in ["split-c1-domestic-audit.json","split-c1-domestic-policy.json",
                 "split-c1-domestic-eco.json","SPLIT-C1-DOMESTICIZATION.md"]:
        shutil.copy2(ROOT/name,out/name)
    shutil.copy2(ROOT/"split-c1-sourcing-evidence.json",out/"sourcing-evidence.json")
    shutil.copy2(ROOT/"split-c1-mechanical-audit.json",out/"mechanical-audit.json")
    (out/"prototype-status.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"SHA256SUMS").write_text("".join(sha(p)+"  "+str(p.relative_to(out))+"\n" for p in sorted(out.rglob("*")) if p.is_file() and p.name!="SHA256SUMS"))
    archive=ROOT/"production/Panda-Split-C1-JLC-Prototype.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file(): z.write(p,str(p.relative_to(out)))
    with zipfile.ZipFile(archive) as z:
        if z.testzip(): raise ValueError("Orderpack CRC error")
    print(json.dumps({"archive":str(archive.relative_to(REPO)),"sha256":sha(archive),
          "standard_fabrication_ready":{b:s["standard_fabrication_ready"] for b,s in report["boards"].items()},
          "ready_for_cam_review":True,"assembly_request_ready":False,
          "all_domestic_bom_complete":domestic["all_domestic_bom_complete"],
          "remaining_foreign_refs":domestic["foreign_ref_count"],"assembly_order_released":False},indent=2))
if __name__=="__main__":main()