#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, subprocess, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_c0_fold import parse, render, children, child, props

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'hardware/thin18-compact/c2-96x68-ft01c-eco'
DST=ROOT/'hardware/thin18-compact/c3a-96x68-touch-frontlight-reserved'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
BBOX=json.loads((ROOT/'hardware/thin18-compact/routing142-footprint-bboxes.json').read_text())
RES={
  'J803_TOUCH':(1.0,36.5,11.0,41.5),
  'J804_FRONTLIGHT':(1.0,43.0,11.0,48.0),
  'FRONTLIGHT_DRIVER':(1.0,50.0,19.0,60.0),
}
CLEAR=0.5

def hit(a,b):
    return min(a[2],b[2])-max(a[0],b[0])>0 and min(a[3],b[3])-max(a[1],b[1])>0

if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()
pcb=DST/REL/(STEM+'.kicad_pcb')
root=parse(pcb.read_text())
fps={props(f).get('Reference'):f for f in children(root,'footprint')}

# Verify reserved rectangles do not hit any existing top-side footprint bbox.
hits={}
for name,r in RES.items():
    e=(r[0]-CLEAR,r[1]-CLEAR,r[2]+CLEAR,r[3]+CLEAR)
    hh=[]
    for ref,f in fps.items():
        if ref not in BBOX or BBOX[ref]['layer']!='Top Layer': continue
        at=child(f,'at'); x=float(at[1]); y=float(at[2]); o=BBOX[ref]['bbox_offset']
        b=(x+o[0],y+o[1],x+o[2],y+o[3])
        if hit(e,b): hh.append(ref)
    hits[name]=hh
if any(hits.values()): raise SystemExit(f'reservation overlap: {hits}')

for name,(x1,y1,x2,y2) in RES.items():
    root.append(parse(f'(gr_rect (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.15) (type dash)) (fill none) (layer "Dwgs.User"))'))
    root.append(parse(f'(gr_text "{name} C3A RESERVE" (at {(x1+x2)/2} {(y1+y2)/2} 90) (layer "Dwgs.User") (effects (font (size 0.8 0.8) (thickness 0.12))))'))

pcb.write_text(render(root)+'\n')

kicad='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
sch=DST/REL/(STEM+'.kicad_sch')
subprocess.run([kicad,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(DST/'verification/drc.json'),str(pcb)],check=True)
subprocess.run([kicad,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc.json'),str(sch)],check=True)
subprocess.run([kicad,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(sch)],check=True)

drc=json.load(open(DST/'verification/drc.json'))
erc=json.load(open(DST/'verification/erc.json'))
dv=len(drc.get('violations',[])); du=len(drc.get('unconnected_items',[])); dp=len(drc.get('schematic_parity',[]))
ev=sum(len(s.get('violations',[])) for s in erc.get('sheets',[]))
if (dv,du,dp,ev)!=(0,447,0,0): raise SystemExit(f'unexpected native checks {(dv,du,dp,ev)}')

# Netlist must remain semantically identical to C2: compare refs and pin/net tuples.
import xml.etree.ElementTree as ET
def semantic_netlist(path):
    root=ET.parse(path).getroot()
    refs=sorted(c.get('ref') for c in root.findall('components/comp'))
    tuples=[]
    for net in root.findall('nets/net'):
        name=net.get('name','')
        for node in net.findall('node'):
            tuples.append((node.get('ref'),node.get('pin'),name))
    return refs, sorted(tuples)
a_refs,a_tuples=semantic_netlist(SRC/'verification/netlist.xml')
b_refs,b_tuples=semantic_netlist(DST/'verification/netlist.xml')
refs_identical=a_refs==b_refs
pin_nets_identical=a_tuples==b_tuples
if not (refs_identical and pin_nets_identical):
    raise SystemExit('C3A reservation unexpectedly changed semantic netlist')

report={
  'kind':'C3A placement reservation; no electrical change',
  'source':'c2-96x68-ft01c-eco',
  'target_mm':[96.0,68.0],
  'reservations_mm':RES,
  'clearance_mm':CLEAR,
  'top_side_overlap_hits':hits,
  'frontlight_evt_reference':'LM36922HYFFR / C213572',
  'frontlight_control':'U601.P15 -> FL_HWEN; brightness/color by I2C',
  'touch_policy':'3V3_TOUCH switched; reset conditioning C3B; I2C polling baseline; TOUCH_INT reserved',
  'drc_violations':dv,'unconnected_items':du,'schematic_parity':dp,'erc':ev,
  'refs':len(b_refs),'pin_net_tuples':len(b_tuples),'refs_identical_to_c2':refs_identical,'pin_nets_identical_to_c2':pin_nets_identical,
  'routing_authority':False,'manufacturing_release':False,'physical_qualification':False,
  'pcb_sha256':hashlib.sha256(pcb.read_bytes()).hexdigest()
}
(DST/'c3a-reservation-report.json').write_text(json.dumps(report,indent=2)+'\n')
(DST/'README.md').write_text(
  '# Thin18 compact C3A — touch/front-light reservation\n\n'
  'C3A derives from C2 and makes no electrical changes. It reserves collision-free top-side space for J803, J804 and the front-light power cluster while the exact FPC connector geometry remains gated on the official display drawing.\n\n'
  f'Native checks: DRC={dv}, parity={dp}, ERC={ev}, unconnected={du} (expected; intentionally unrouted).\n'
  'The exported netlist is semantically identical to C2 (same refs and pin/net tuples).\n\n'
  'Not a manufacturing release.\n'
)
print(json.dumps(report,indent=2))
