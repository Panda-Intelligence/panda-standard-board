#!/usr/bin/env python3
"""Export a manufacturing-data candidate only after fresh native CAD/BOM gates."""
from pathlib import Path
import argparse, csv, hashlib, json, re, shutil, subprocess, sys, zipfile
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
REL = Path("eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16")
STEM = "PANDA-STD-CORE-EVT-quilter-j501-merged"
K = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p): return str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p)
def run(*args):
    r = subprocess.run([K,*map(str,args)], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr + r.stdout)
def checks(d,e):
    return {"drc":len(d.get("violations",[])),
        "open":len(d.get("unconnected_items",[])),
        "parity":len(d.get("schematic_parity",[])),
        "erc":sum(len(s.get("violations",[])) for s in e.get("sheets",[]))}
ap = argparse.ArgumentParser()
ap.add_argument("--candidate",type=Path,required=True)
ap.add_argument("--output",type=Path,required=True)
ap.add_argument("--pcb-relative",type=Path,default=REL/(STEM+".kicad_pcb"))
ap.add_argument("--schematic-relative",type=Path,default=REL/(STEM+".kicad_sch"))
ap.add_argument("--board-id",default="")
ap.add_argument("--nominal-size",nargs=2,type=float)
a = ap.parse_args()
cand,out = a.candidate.resolve(),a.output.resolve()
pcb,sch = cand/a.pcb_relative,cand/a.schematic_relative
if not pcb.is_file() or not sch.is_file(): raise SystemExit("missing PCB/schematic")
if not out.is_relative_to(ROOT/"production"): raise SystemExit("output must be a production subdirectory")
if out == ROOT/"production": raise SystemExit("refusing production root")
if out.exists(): shutil.rmtree(out)
verify,mfg = out/"verification",out/"manufacturing"
verify.mkdir(parents=True);mfg.mkdir()
run("pcb","drc","--format","json","--severity-all","--schematic-parity",
    "--output",verify/"drc.json",pcb)
run("sch","erc","--format","json","--severity-all","--output",verify/"erc.json",sch)
run("sch","export","netlist","--format","kicadxml","--output",verify/"netlist.xml",sch)
d=json.loads((verify/"drc.json").read_text())
e=json.loads((verify/"erc.json").read_text())
counts=checks(d,e)
def blocked(reason,**detail):
    (out/"BLOCKED.json").write_text(json.dumps({"candidate":cand.name,
        "native_checks":counts,"production_exported":False,"reason":reason,
        **detail},indent=2)+"\n")
    raise SystemExit(reason)
if any(counts.values()): blocked("requires DRC/open/parity/ERC = 0/0/0/0")
text=pcb.read_text()
start=text.find("(layers");end=text.find("(setup",start)
copper=[x for x in ["F.Cu","In1.Cu","In2.Cu","B.Cu"]
    if re.search(r'\(\d+ "'+re.escape(x)+r'" ',text[start:end])]
if copper not in [["F.Cu","B.Cu"],["F.Cu","In1.Cu","In2.Cu","B.Cu"]]:
    blocked("unsupported stackup",copper_layers=copper)
# Measure the main outline rectangle from long, axis-aligned Edge.Cuts lines.
sys.path.insert(0,str(ROOT/"tools"))
from prune_core_c1_stubs import blocks
edges=[]
for _,_,b in blocks(text,"(gr_line"):
    if '(layer "Edge.Cuts")' not in b: continue
    p=re.search(r"\(start ([^ ]+) ([^)]+)\)",b)
    q=re.search(r"\(end ([^ ]+) ([^)]+)\)",b)
    edges.append(tuple(map(float,(*p.groups(),*q.groups()))))
horizontal=[r for r in edges if abs(r[1]-r[3])<1e-6 and abs(r[0]-r[2])>10]
vertical=[r for r in edges if abs(r[0]-r[2])<1e-6 and abs(r[1]-r[3])>10]
if not horizontal or not vertical: blocked("nominal outline cannot be measured")
width=max(r[0] for r in vertical)-min(r[0] for r in vertical)
height=max(r[1] for r in horizontal)-min(r[1] for r in horizontal)
dims=[round(width,6),round(height,6)]
if a.nominal_size and any(abs(x-y)>0.001 for x,y in zip(dims,a.nominal_size)):
    blocked("board dimensions differ",measured=dims,expected=a.nominal_size)
ger=mfg/"gerber";ger.mkdir()
layers=",".join(copper+["F.Mask","B.Mask","F.Silkscreen","B.Silkscreen","Edge.Cuts"])
run("pcb","export","gerbers","--output",ger,"--layers",layers,
    "--subtract-soldermask","--precision","6",pcb)
run("pcb","export","drill","--output",ger,"--format","excellon",
    "--excellon-units","mm","--excellon-separate-th","--generate-report",
    "--report-path",ger/"drill-report.txt",pcb)
run("pcb","export","pos","--output",mfg/"cpl.csv","--side","both",
    "--format","csv","--units","mm","--smd-only","--exclude-dnp",pcb)
run("sch","export","bom","--output",mfg/"bom.csv",
    "--fields","Reference,Value,Footprint,Manufacturer,MPN,LCSC,QUANTITY,DNP",
    "--labels","Refs,Value,Footprint,Manufacturer,MPN,LCSC,Qty,DNP",
    "--group-by","Value,Footprint,Manufacturer,MPN,LCSC","--exclude-dnp",sch)
rows=list(csv.DictReader((mfg/"bom.csv").open(encoding="utf-8-sig",newline="")))
missing=[{"refs":r["Refs"],"field":field} for r in rows
    for field in ["Manufacturer","MPN"] if not r.get(field,"").strip()]
if missing: blocked("production BOM unresolved",missing=missing)
zip_path=mfg/"gerber-drill.zip"
with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
    for p in sorted(ger.iterdir()):
        if p.is_file(): z.write(p,p.name)
with zipfile.ZipFile(zip_path) as z:
    if z.testzip(): blocked("Gerber ZIP failed CRC")
    names=z.namelist()
if len([n for n in names if not n.endswith((".drl",".txt",".gbrjob"))]) != len(copper)+5:
    blocked("Gerber layer count mismatch",files=names)
if not any(n.endswith("-PTH.drl") for n in names) or not any(n.endswith("-NPTH.drl") for n in names):
    blocked("separate plated/nonplated drill files missing",files=names)
files={"pcb":pcb,"schematic":sch,"bom":mfg/"bom.csv","cpl":mfg/"cpl.csv",
    "gerber_zip":zip_path,"drc":verify/"drc.json","erc":verify/"erc.json",
    "netlist":verify/"netlist.xml"}
for child in sorted(sch.parent.glob("*.kicad_sch")):
    if child != sch: files["schematic_child_"+child.stem]=child
for ext in [".kicad_pro",".kicad_dru"]:
    config=pcb.with_suffix(ext)
    if config.exists(): files["cad_config_"+ext.lstrip(".")]=config
manifest={"schema":"panda-production-candidate-v2","board_id":a.board_id or cand.name,
    "candidate":cand.name,"board_dimensions_mm":dims,"copper_layers":copper,
    "native_checks":counts,"bom_complete":{"Manufacturer":True,"MPN":True},
    "zip_crc_verified":True,"production_exported":True,"manufacturing_release":False,
    "files":{k:{"path":rel(p),"sha256":sha(p)} for k,p in files.items()},
    "note":"CAD/manufacturing-data candidate. Physical EVT and enclosure qualification remain open."}
(out/"production-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps({"board":manifest["board_id"],"native_checks":counts,
    "dimensions_mm":dims,"copper_layers":copper,"bom_rows":len(rows)},indent=2))
