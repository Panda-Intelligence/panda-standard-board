#!/usr/bin/env python3
import hashlib, json, re, shutil, subprocess, sys, uuid
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'c1-96x68-battery-ring'
DST=ROOT/'c2-96x68-ft01c-eco'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
PCB_NAME='PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_pcb'
SCH_NAME='PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_sch'
DISP='display-integrated.kicad_sch'

if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()

# Patch display schematic: pins 6/7 are Good Display NC, not GND.
sp=DST/REL/DISP
s=sp.read_text()
def replace_ground_with_nc(text,y,pin):
    pat=(rf'\(wire \(pts \(xy 534\.67 {y}\) \(xy 529\.59 {y}\)\) '
         rf'\(stroke .*?\) \(uuid "[^"]+"\)\) '
         rf'\(global_label "GND" .*?\(uuid "[^"]+"\)\)')
    nc=f'(no_connect (at 534.67 {y}) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL, f"thin18-c2-j802-{pin}-nc")}"))'
    out,n=re.subn(pat,nc,text,count=1)
    if n!=1: raise SystemExit(f'failed schematic J802 pin {pin} patch, matches={n}')
    return out
s=replace_ground_with_nc(s,'74.93',6)
s=replace_ground_with_nc(s,'77.47',7)
s=s.replace('PANDA EPD0426A02 SPI ELECTRICAL PROTOTYPE','PANDA GDEQ0426T82-FT01C DISPLAY ELECTRICAL C2')
sp.write_text(s)

# Patch only J802 PCB pads 6/7: remove GND net assignment.
pp=DST/REL/PCB_NAME
ps=pp.read_text()
ri=ps.find('(property "Reference" "J802"')
if ri<0: raise SystemExit('J802 not found')
fs=ps.rfind('(footprint ',0,ri)
depth=0; quote=False; esc=False; j=fs
while j<len(ps):
    c=ps[j]
    if quote:
        if esc: esc=False
        elif c=='\\': esc=True
        elif c=='"': quote=False
    else:
        if c=='"': quote=True
        elif c=='(': depth+=1
        elif c==')':
            depth-=1
            if depth==0:
                j+=1; break
    j+=1
block=ps[fs:j]
for pin in ('6','7'):
    pat=rf'(\(pad "{pin}" .*?\(layers "F\.Cu" "F\.Mask" "F\.Paste"\)) \(net "GND"\)'
    replacement=rf'\1 (net "unconnected-(J802-Pin_{pin}-Pad{pin})")'
    block,n=re.subn(pat,replacement,block,count=1)
    if n!=1: raise SystemExit(f'failed PCB J802 pad {pin} patch, matches={n}')
ps=ps[:fs]+block+ps[j:]
pp.write_text(ps)

# Fresh native checks.
kicad='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
pcb=str(pp); root_sch=str(DST/REL/SCH_NAME)
subprocess.run([kicad,'pcb','drc','--format','json','--severity-all','--schematic-parity',
                '--output',str(DST/'verification/drc.json'),pcb],check=True)
subprocess.run([kicad,'sch','erc','--format','json','--severity-all',
                '--output',str(DST/'verification/erc.json'),root_sch],check=True)
subprocess.run([kicad,'sch','export','netlist','--format','kicadxml',
                '--output',str(DST/'verification/netlist.xml'),root_sch],check=True)

# Validate counts and exact netlist delta.
drc=json.load(open(DST/'verification/drc.json'))
erc=json.load(open(DST/'verification/erc.json'))
dv=len(drc.get('violations',[])); du=len(drc.get('unconnected_items',[])); dp=len(drc.get('schematic_parity',[]))
ev=sum(len(x.get('violations',[])) for x in erc.get('sheets',[]))
if (dv,dp,ev)!=(0,0,0): raise SystemExit(f'checks failed drc={dv} parity={dp} erc={ev}')

def pinmap(path):
    root=ET.parse(path).getroot(); out={}
    for net in root.findall('nets/net'):
        name=net.get('name','')
        for node in net.findall('node'):
            out[(node.get('ref'),node.get('pin'))]=name
    return out
a=pinmap(SRC/'verification/netlist.xml')
b=pinmap(DST/'verification/netlist.xml')
keys=set(a)|set(b)
delta=[]
for k in sorted(keys):
    if a.get(k)!=b.get(k): delta.append({'ref':k[0],'pin':k[1],'before':a.get(k),'after':b.get(k)})
allowed={('J802','6'),('J802','7')}
if {(x['ref'],x['pin']) for x in delta} != allowed:
    raise SystemExit(f'unexpected netlist delta: {delta}')

report={
 'kind':'C2 FT01C J802 NC ECO, unrouted placement candidate',
 'source':'c1-96x68-battery-ring',
 'target_panel':'GDEQ0426T82-FT01C',
 'pcb_target_mm':[96.0,68.0],
 'drc_violations':dv,'unconnected_items':du,'schematic_parity':dp,'erc':ev,
 'expected_unrouted':True,
 'netlist_delta':delta,
 'allowed_delta_only':True,
 'j802_eco_pins':[6,7],
 'manufacturing_release':False,
 'physical_qualification':False,
 'pcb_sha256':hashlib.sha256(pp.read_bytes()).hexdigest()
}
(DST/'c2-eco-report.json').write_text(json.dumps(report,indent=2)+'\n')
(DST/'README.md').write_text(
    '# Thin18 compact C2 — FT01C display ECO\n\n'
    'This candidate derives from C1 and remains intentionally unrouted.\n\n'
    'Changes:\n'
    '- target panel contract: GDEQ0426T82-FT01C;\n'
    '- J802 pin 6: GND -> NC;\n'
    '- J802 pin 7: GND -> NC;\n'
    '- no placement coordinates are intentionally changed.\n\n'
    f'Fresh verification:\n- DRC violations: {dv}\n- schematic parity: {dp}\n- ERC: {ev}\n'
    f'- unconnected: {du} (expected for the unrouted compact candidate)\n'
    '- netlist delta is restricted to J802 pins 6 and 7.\n\n'
    'Touch and front-light connectors/driver are reserved by C2 but are not yet added to this candidate.\n'
    'This is not a manufacturing release.\n')
print(json.dumps(report,indent=2))
