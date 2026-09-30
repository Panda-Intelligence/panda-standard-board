#!/usr/bin/env python3
"""Export a JLC-ready production package only from a native-clean routed candidate."""
from pathlib import Path
import argparse,csv,hashlib,json,shutil,subprocess,sys,zipfile,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
REL=Path("eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16")
STEM="PANDA-STD-CORE-EVT-quilter-j501-merged"
K="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def fail(s): print("FAIL:",s,file=sys.stderr); raise SystemExit(2)

ap=argparse.ArgumentParser()
ap.add_argument("--candidate",type=Path,required=True)
ap.add_argument("--output",type=Path,required=True)
a=ap.parse_args()
cand=a.candidate.resolve(); out=a.output.resolve()
pcb=cand/REL/(STEM+".kicad_pcb"); sch=cand/REL/(STEM+".kicad_sch")
if not pcb.exists() or not sch.exists(): fail("candidate PCB/schematic missing")
verify=out/"verification"; mfg=out/"manufacturing"
if out.exists(): shutil.rmtree(out)
verify.mkdir(parents=True);mfg.mkdir()

subprocess.run([K,"pcb","drc","--format","json","--severity-all","--schematic-parity","--output",str(verify/"drc.json"),str(pcb)],check=True)
subprocess.run([K,"sch","erc","--format","json","--severity-all","--output",str(verify/"erc.json"),str(sch)],check=True)
subprocess.run([K,"sch","export","netlist","--format","kicadxml","--output",str(verify/"netlist.xml"),str(sch)],check=True)
d=json.load(open(verify/"drc.json")); e=json.load(open(verify/"erc.json"))
counts={"drc":len(d.get("violations",[])),"open":len(d.get("unconnected_items",[])),"parity":len(d.get("schematic_parity",[])),"erc":sum(len(s.get("violations",[])) for s in e.get("sheets",[]))}
if counts != {"drc":0,"open":0,"parity":0,"erc":0}:
    (out/"BLOCKED.json").write_text(json.dumps({"candidate":cand.name,"native_checks":counts,"production_exported":False,"reason":"requires DRC/open/parity/ERC = 0/0/0/0"},indent=2)+"\n")
    print(json.dumps({"result":"BLOCKED","native_checks":counts},indent=2))
    raise SystemExit(2)

ger=mfg/"gerber";ger.mkdir()
layers="F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts"
subprocess.run([K,"pcb","export","gerbers","--output",str(ger), "--layers",layers,"--subtract-soldermask","--precision","6",str(pcb)],check=True)
subprocess.run([K,"pcb","export","drill","--output",str(ger),"--format","excellon","--excellon-units","mm","--excellon-separate-th","--generate-report","--report-path",str(ger/"drill-report.txt"),str(pcb)],check=True)
subprocess.run([K,"pcb","export","pos","--output",str(mfg/"cpl.csv"),"--side","both","--format","csv","--units","mm","--smd-only","--exclude-dnp",str(pcb)],check=True)
subprocess.run([K,"sch","export","bom","--output",str(mfg/"bom.csv"),"--fields","Reference,Value,Footprint,Manufacturer,MPN,LCSC,QUANTITY,DNP","--labels","Refs,Value,Footprint,Manufacturer,MPN,LCSC,Qty,DNP","--group-by","Value,Footprint,Manufacturer,MPN,LCSC","--exclude-dnp",str(sch)],check=True)

# BOM must be production-resolved for every populated row.
with (mfg/"bom.csv").open(encoding="utf-8-sig",newline="") as f:
    rows=list(csv.DictReader(f))
missing=[]
for row in rows:
    refs=row.get("Refs","")
    # Mechanical/test-only items may not need LCSC, but all electrical populated components require MPN.
    if refs.startswith(("R","C","L","D","Q","U","J","SW")) and not row.get("MPN","").strip():
        missing.append({"refs":refs,"field":"MPN"})
if missing:
    (out/"BLOCKED.json").write_text(json.dumps({"candidate":cand.name,"native_checks":counts,"production_exported":False,"reason":"production BOM unresolved","missing":missing},indent=2)+"\n")
    print(json.dumps({"result":"BLOCKED_BOM","missing_count":len(missing)},indent=2))
    raise SystemExit(2)

zip_path=mfg/"gerber-drill.zip"
with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
    for p in sorted(ger.iterdir()):
        if p.is_file(): z.write(p,p.name)
manifest={"candidate":cand.name,"native_checks":counts,"production_exported":True,"manufacturing_release":False,
          "files":{"pcb":{"path":str(pcb),"sha256":sha(pcb)},"bom":{"path":str(mfg/"bom.csv"),"sha256":sha(mfg/"bom.csv")},
                   "cpl":{"path":str(mfg/"cpl.csv"),"sha256":sha(mfg/"cpl.csv")},"gerber_zip":{"path":str(zip_path),"sha256":sha(zip_path)},
                   "drc":{"path":str(verify/"drc.json"),"sha256":sha(verify/"drc.json")},"erc":{"path":str(verify/"erc.json"),"sha256":sha(verify/"erc.json")}},
          "note":"Production files generated from a CAD-clean routed candidate. Manufacturing release remains false until Q04-Q12 physical qualification passes."}
(out/"production-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps(manifest,indent=2))
