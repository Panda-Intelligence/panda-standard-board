#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_c0_fold import parse, render, children, child, props

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'hardware/thin18-compact/c4c-96x68-domestic-passives'
DST=ROOT/'hardware/thin18-compact/c4d-96x68-power-usb-reserved'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
BBOX=json.loads((ROOT/'hardware/thin18-compact/routing142-footprint-bboxes.json').read_text())
CONTRACT=json.loads((ROOT/'hardware/thin18-compact/c4d-power-usb-contract.json').read_text())
CLEAR=CONTRACT['placement']['clearance_mm']

if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()

pcb=DST/REL/(STEM+'.kicad_pcb')
root=parse(pcb.read_text())
fps={props(f).get('Reference'):f for f in children(root,'footprint')}

def bbox_for(ref):
    f=fps[ref]; at=child(f,'at'); x=float(at[1]); y=float(at[2]); o=BBOX[ref]['bbox_offset']
    return (x+o[0],y+o[1],x+o[2],y+o[3])

def hit(a,b):
    return min(a[2],b[2])-max(a[0],b[0])>0 and min(a[3],b[3])-max(a[1],b[1])>0

hits={}
rects={}
for name,t in CONTRACT['placement']['targets'].items():
    cx,cy=t['center_mm']; w,h=t['reserve_size_mm']
    r=(cx-w/2,cy-h/2,cx+w/2,cy+h/2)
    e=(r[0]-CLEAR,r[1]-CLEAR,r[2]+CLEAR,r[3]+CLEAR)
    remove=set(t['replaces'])
    hh=[]
    for ref,f in fps.items():
        if ref in remove or ref not in BBOX or BBOX[ref]['layer']!='Top Layer': continue
        if hit(e,bbox_for(ref)): hh.append(ref)
    hits[name]=sorted(hh); rects[name]=r
    root.append(parse(f'(gr_rect (start {r[0]} {r[1]}) (end {r[2]} {r[3]}) (stroke (width 0.15) (type dash)) (fill none) (layer "Dwgs.User"))'))
    root.append(parse(f'(gr_text "C4D {name} RESERVE" (at {cx} {cy} 90) (layer "Dwgs.User") (effects (font (size 0.7 0.7) (thickness 0.12))))'))

if any(hits.values()): raise SystemExit(f'power reservation overlap: {hits}')
pcb.write_text(render(root)+'\n')

k='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
sch=DST/REL/(STEM+'.kicad_sch')
subprocess.run([k,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(DST/'verification/drc.json'),str(pcb)],check=True)
subprocess.run([k,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc.json'),str(sch)],check=True)
subprocess.run([k,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(sch)],check=True)
drc=json.load(open(DST/'verification/drc.json')); erc=json.load(open(DST/'verification/erc.json'))
counts={'drc':len(drc.get('violations',[])),'open':len(drc.get('unconnected_items',[])),'parity':len(drc.get('schematic_parity',[])),'erc':sum(len(x.get('violations',[])) for x in erc.get('sheets',[]))}
if counts!={'drc':0,'open':447,'parity':0,'erc':0}: raise SystemExit(f'native checks changed: {counts}')

report={
 'kind':'C4D power/USB placement reservation; no electrical change',
 'source':'c4c-96x68-domestic-passives',
 'target_mm':[96.0,68.0],
 'reserved_rectangles_mm':rects,
 'clearance_mm':CLEAR,
 'top_side_overlap_hits':hits,
 'charger_variant':'SGM41513 non-D / PSEL high baseline 500mA',
 'usb_delta':'remove U202-U205; R206/R207 become 5.1k Rd in electrical C4D ECO',
 'native_checks':counts,
 'routing_authority':False,'electrical_redesign_applied':False,'manufacturing_release':False,'physical_qualification':False,
 'pcb_sha256':hashlib.sha256(pcb.read_bytes()).hexdigest()
}
(DST/'c4d-reservation-report.json').write_text(json.dumps(report,indent=2)+'\n')
(DST/'README.md').write_text(
 '# Thin18 Compact C4D — power / USB integration reservation\n\n'
 'This candidate overlays physical reservation envelopes for the selected SGM41513, CW2215B and SGM62125 architecture on C4C. It intentionally makes no electrical changes.\n\n'
 f'Fresh checks: DRC {counts["drc"]}; parity {counts["parity"]}; ERC {counts["erc"]}; open {counts["open"]} (expected, compact remains unrouted).\n'
 'All three reservation envelopes have zero top-side footprint collisions after excluding only components targeted for replacement.\n\n'
 'Not a manufacturing release.\n'
)
print(json.dumps(report,indent=2))
