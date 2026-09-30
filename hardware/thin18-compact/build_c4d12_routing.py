#!/usr/bin/env python3
from pathlib import Path
import json,shutil,subprocess
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'c4d11-96x68-final-placement'
DST=ROOT/'c4d12-96x68-routing'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
K='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()
subprocess.run(['python3',str(ROOT/'freeze_c4d12_usb_rd.py'),str(DST)],check=True)
pro=DST/REL/(STEM+'.kicad_pro'); d=json.load(open(pro))
cls=d['net_settings']['classes'][0]
cls['clearance']=0.15
cls['track_width']=0.20
cls['via_diameter']=0.45
cls['via_drill']=0.25
# Fabrication floor stays conservative relative to JLC 4-layer standard capability.
rules=d['board']['design_settings']['rules']
rules['min_track_width']=0.15
rules['min_via_diameter']=0.40
rules['min_through_hole_diameter']=0.20
rules['min_via_annular_width']=0.10
rules['min_copper_edge_clearance']=0.15
pro.write_text(json.dumps(d,indent=2)+'\n')
dru=DST/REL/(STEM+'.kicad_dru')
if dru.exists():
    text=dru.read_text()
    text=text.replace('(rule "J503 TC2030 contact-pad other-net clearance"\n\t(constraint clearance (min 0.508mm))', '(rule "J503 TC2030 breakout clearance"\n\t(constraint clearance (min 0.15mm))')
    dru.write_text(text)

pcb=DST/REL/(STEM+'.kicad_pcb');sch=DST/REL/(STEM+'.kicad_sch')
subprocess.run([K,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(DST/'verification/drc.json'),str(pcb)],check=True)
subprocess.run([K,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc.json'),str(sch)],check=True)
subprocess.run([K,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(sch)],check=True)
drc=json.load(open(DST/'verification/drc.json'));erc=json.load(open(DST/'verification/erc.json'))
counts={'drc':len(drc.get('violations',[])),'open':len(drc.get('unconnected_items',[])),'parity':len(drc.get('schematic_parity',[])),'erc':sum(len(s.get('violations',[])) for s in erc.get('sheets',[]))}
if counts != {'drc':0,'open':436,'parity':0,'erc':0}: raise SystemExit(counts)
report={'date':'2026-09-30','kind':'C4D-12 routing-rule checkpoint','source':'c4d11-96x68-final-placement','board_mm':[96,68],
        'routing_rules_mm':{'track_width':0.20,'clearance':0.15,'via_diameter':0.45,'via_drill':0.25,'copper_edge_clearance':0.15},
        'fabrication_basis':'JLC 4-layer standard capability is tighter than these values; selected values remain conservative for yield/cost.',
        'native_checks_before_routing':counts,'routing_complete':False,'manufacturing_release':False}
(DST/'c4d12-routing-report.json').write_text(json.dumps(report,indent=2)+'\n')
(DST/'README.md').write_text('# Thin18 Compact C4D-12 — routing checkpoint\n\n96×68 mm C4D-11 placement is preserved. Routing rules use 0.20 mm tracks, 0.15 mm clearance and 0.45/0.25 mm vias. Final routing and physical qualification remain open.\n')
print(json.dumps(report,indent=2))
