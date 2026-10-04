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
    if data["violations"]:
        raise ValueError("Prototype DFM failure: "+data["violations"][0]["description"])
    if data["unconnected_items"]: raise ValueError("DFM copy has unconnected items")
    return {"standard_fabrication_ready":True,"cam_acceptance_required":False,
            "pending_violations":[]}
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
def verify_new_connectors(text):
    """Reject wrong primary lands, reversed pin numbering or unreviewed poses."""
    from _split_c1_vbus_eco import MPN,FP
    protector=verify_land(text,'D202',(.25,.5),.325)
    pose=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)',protector).groups()))
    nets={re.match(r'\(pad\s+"([^"]+)"',p).group(1):re.search(r'\(net\s+"([^"]+)"\)',p).group(1) for _,_,p in blocks(protector,r'\(pad\s')}
    if property_value(protector,'MPN')!=MPN or not protector.startswith('(footprint '+json.dumps(FP)) or pose!=(48.6,60,180) or nets!={'1':'VBUS_USB','2':'GND'} or '(model ' in protector:
        raise ValueError('VBUS protector reviewed identity/polarity/pose differs')
    usb=next(b for _,_,b in blocks(text,r"\(footprint\s") if property_value(b,'Reference')=='J201')
    if property_value(usb,'MPN')!='U20405-01' or re.search(r'\(at\s+39\s+68\)',usb) is None:raise ValueError('USB identity/PCB-edge datum differs')
    if '"Edge.Cuts"' in usb or '(model ' in usb:raise ValueError('USB foreign model or old cutout retained')
    order=['B12','A1','B9','A4','A5','A6','A7','A8','B8','B7','B6','B5','B4','A9','B1','A12']
    nets={'A1':'GND','B12':'GND','A4':'VBUS_USB','B9':'VBUS_USB','A5':'USB_CC1','A6':'USB_DP','A7':'USB_DM','A8':'unconnected-(J201-PadA8)','B8':'unconnected-(J201-PadB8)','B7':'USB_DM','B6':'USB_DP','B5':'USB_CC2','B4':'VBUS_USB','A9':'VBUS_USB','B1':'GND','A12':'GND'}
    pads=list(blocks(usb,r'\(pad\s'));found=set();shells=[]
    if len(pads)!=20:raise ValueError('USB must have16 independent signals and4 shell lands')
    for _,_,pad in pads:
        n=re.match(r'\(pad\s+"([^"]+)"',pad).group(1)
        xy=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',pad).groups()))
        size=tuple(map(float,re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)',pad).groups()))
        net=re.search(r'\(net\s+"([^"]+)"\)',pad).group(1)
        if n=='SH':
            drill=tuple(map(float,re.search(r'\(drill oval\s+([-\d.]+)\s+([-\d.]+)',pad).groups()))
            if net!='GND':raise ValueError('USB shell grounding differs')
            shells.append((xy,size,drill))
        elif n not in order or n in found or xy!=(round(-3+order.index(n)*.4,6),-6.55) or size!=(.25,.8) or net!=nets[n]:raise ValueError('Incorrect MUP USB land/pin/net '+n)
        else:found.add(n)
    expected_shells=[((x,y),(1.2,2.0 if y==-6.2 else 2.1),(.6,1.4 if y==-6.2 else 1.5)) for x in [-4.32,4.32] for y in [-6.2,-1.7]]
    if found!=set(order) or sorted(shells)!=sorted(expected_shells):raise ValueError('Incorrect MUP USB shell land')
    expected={
        'J302':('HC-1.0-3PWT', {str(n):((n-2,-2),(0.7,1.75)) for n in range(1,4)}, [((-2.1,1.7),(1.0,2.55)),((2.1,1.7),(1.0,2.55))]),
        'J502':('HC-1.0-2PWT', {'1':((-0.5,-2),(0.7,1.75)),'2':((0.5,-2),(0.7,1.75))}, [((-1.6,1.7),(1.0,2.55)),((1.6,1.7),(1.0,2.55))])}
    for ref,(mpn,signals,mounts) in expected.items():
        fp=next(b for _,_,b in blocks(text,r"\(footprint\s") if property_value(b,'Reference')==ref)
        if property_value(fp,'MPN')!=mpn:raise ValueError('Unexpected connector identity '+ref)
        found={};anchors=[]
        for _,_,pad in blocks(fp,r"\(pad\s"):
            num=re.match(r'\(pad\s+"([^"]+)"',pad).group(1)
            xy=tuple(map(float,re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)",pad).groups()))
            size=tuple(map(float,re.search(r"\(size\s+([-\d.]+)\s+([-\d.]+)",pad).groups()))
            if num=='MP':anchors.append((xy,size))
            elif num in found:raise ValueError('Duplicate connector signal '+ref)
            else:found[num]=(xy,size)
        if found!=signals or sorted(anchors)!=sorted(mounts):raise ValueError('Incorrect HCTL lands '+ref)
    for ref,y in [('J803',36.87),('J804',43.0)]:
        fp=next(b for _,_,b in blocks(text,r"\(footprint\s") if property_value(b,'Reference')==ref)
        if property_value(fp,'MPN')!='X05A10H06G':raise ValueError('Unexpected FPC6 identity')
        pose=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)',fp).groups()))
        if pose!=(6.35,y,180):raise ValueError('FPC6 entry/pose differs '+ref)
        pads=list(blocks(fp,r"\(pad\s"))
        if len(pads)!=8:raise ValueError('FPC6 land count')
        for _,_,pad in pads:
            n=re.match(r'\(pad\s+"([^"]+)"',pad).group(1)
            if n in ['S1','S2']:xy=(-2.3 if n=='S1' else 2.3,1.25);size=(.4,.8)
            elif n in {str(k) for k in range(1,7)}:xy=((int(n)-3.5)*.5,-1.25);size=(.3,.8)
            else:raise ValueError('Unexpected FPC6 pin')
            actualxy=tuple(map(float,re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)",pad).groups()))
            actualsize=tuple(map(float,re.search(r"\(size\s+([-\d.]+)\s+([-\d.]+)",pad).groups()))
            if actualxy!=xy or actualsize!=size:raise ValueError('Incorrect XKB A2 land/pin '+ref)

    for ref,y,signal in [('SW201',6.75,'KEY_POWER_MCU'),('SW202',13.25,'BQ_QON')]:
        fp=next(b for _,_,b in blocks(text,r"\(footprint\s") if property_value(b,'Reference')==ref)
        if property_value(fp,'MPN')!='TS-1186E-B-B':raise ValueError('Side-switch identity differs')
        pose=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)',fp).groups()))
        if pose!=(2.3,y,-90) or '(model ' in fp:raise ValueError('Side-switch pose/model differs')
        pads=list(blocks(fp,r"\(pad\s"))
        if len(pads)!=2:raise ValueError('Side-switch must have two no-post lands')
        seen=set()
        for _,_,pad in pads:
            n=re.match(r'\(pad\s+"([^"]+)"',pad).group(1)
            xy=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',pad).groups()))
            size=tuple(map(float,re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)',pad).groups()))
            net=re.search(r'\(net\s+"([^"]+)"\)',pad).group(1)
            if n not in {'1','2'} or n in seen or xy!=(-2.45 if n=='1' else 2.45,0) or size!=(.6,1.6) or net!=(signal if n=='1' else 'GND'):
                raise ValueError('Side-switch reviewed land/pin/net differs')
            seen.add(n)

def run(*args):
    subprocess.run([K,*map(str,args)],check=True,capture_output=True)
def main():
    validation=json.loads((ROOT/"split-c1-validation.json").read_text())
    for label,info in validation["files"].items():
        if "sha256" in info and sha(REPO/label)!=info["sha256"]:
            raise ValueError("Stale CAD validation "+label)
    from audit_split_c1_domestic import verify_fresh
    domestic=json.loads((ROOT/'split-c1-domestic-audit.json').read_text());verify_fresh(domestic)
    from verify_split_c1_control import verify_fresh as verify_control_fresh
    control=json.loads((ROOT/'split-c1-control-verification.json').read_text());verify_control_fresh(control)
    core=ROOT/BOARDS[0][1]/BOARDS[0][3]
    text=core.read_text()
    cap=verify_land(text,"C301",(2.4,2.0),10)
    capnets={re.match(r'\(pad\s+"(\d+)"',p).group(1): re.search(r'\(net\s+"([^"]+)"',p).group(1) for _,_,p in blocks(cap,r"\(pad\s")}
    if capnets!={"1":"RTC_VBACKUP","2":"GND"} or '(fp_text user "+"' not in cap: raise ValueError("EDLC polarity missing or reversed")
    verify_land(text,"L401",(1.5,2.5),1.85)
    verify_land(text,"L402",(1.5,2.5),1.85)
    display_text=(ROOT/BOARDS[1][1]/BOARDS[1][3]).read_text()
    verify_land(display_text,"L1",(0.8,2.7),1.15)
    verify_new_connectors(text)
    from _split_c1_land_guards import verify_20261002_lands
    verify_20261002_lands(text,display_text)
    out=ROOT/"production/jlc-prototype-orderpack"
    if out.exists(): shutil.rmtree(out)
    out.mkdir()
    shutil.copy2(ROOT/"JLC-PROTOTYPE-HANDOFF.md",out/"START-HERE.md")
    registry=json.loads((ROOT/"split-c1-sourcing-evidence.json").read_text())
    from verify_split_c1_supply import audit as audit_supply
    supply=audit_supply(json.loads((ROOT/"split-c1-supply-plan.json").read_text()))
    expected={b:{ref for row in registry["unresolved_smt"] if row["board"]==b for ref in row["refs"]} for b,_,_,_ in BOARDS}
    report={"schema":"panda-split-c1-prototype-orderpack-v1","date":"2026-10-02",
            "purpose":"Bench EVT prototype; no physical board exists yet","manufacturing_release":False,
            "physical_evt_passed":False,"assembly_request_ready":False,
            "all_domestic_bom_complete":domestic["all_domestic_bom_complete"],
            "domestic_foreign_ref_count":domestic["foreign_ref_count"],
            "domestic_status":domestic["status"],"requested_supply":supply,"boards":{}}
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
                         assembly_acceptance_required=["Exact stock/My Parts confirmation","Standard double-sided assembly, ENIG, carrier panel/rails/fiducials","CPL bottom rotation and all polarized pin-1 orientations in JLC preview","C301 independently procured and customer hand-soldered after PCBA return; no JLC ultracap consignment. Exact current H3C20mm drawing/C2894294, plated slots, positive terminal, <=0.5mm trimmed rear leads"])
            report["boards"][board]=state
    for name in ["split-c1-power-integrity.json","split-c1-power-integrity-verification.json",
                 "SPLIT-C1-POWER-INTEGRITY.md","split-c1-domestic-audit.json","split-c1-domestic-policy.json",
                 "split-c1-domestic-eco.json","SPLIT-C1-DOMESTICIZATION.md",
                 "C4D8-RTC-DECISION.md","SPLIT-C1-PACK-INPUTS.md",
                 "SPLIT-C1-ENCLOSURE-STUDY.scad","split-c1-jlc-catalog-observation.json",
                 "split-c1-candidate-review.json","split-c1-microsd-layout.json",
                 "split-c1-rtc-layout.json","split-c1-mos-layout.json","SPLIT-C1-RTC-FIRMWARE.md",
                 "split-c1-smt-consignment.json", "split-c1-supply-plan.json",
                 "SPLIT-C1-SUPPLY-REQUEST.md", "SPLIT-C1-PROCUREMENT-QUESTIONS.md"]:
        shutil.copy2(ROOT/name,out/name)
    shutil.copy2(ROOT/"split-c1-sourcing-evidence.json",out/"sourcing-evidence.json")
    shutil.copy2(ROOT/"split-c1-mechanical-audit.json",out/"mechanical-audit.json")
    for name in ["split-c1-control-contract.json", "split-c1-control-host-tests.json", "split-c1-control-verification.json"]:
        shutil.copy2(ROOT/name,out/name)
    shutil.copy2(REPO/"firmware/split_c1/README.md",out/"CONTROL-FIRMWARE-README.md")
    report["host_control_tested"]=True
    report["target_firmware_integration_verified"]=False
    report["pre_firmware_charging_inhibit_proven"]=False
    report["control_open_hardware_findings"]=control["open_hardware_findings"]
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
