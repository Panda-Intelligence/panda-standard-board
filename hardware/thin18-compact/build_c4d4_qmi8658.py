#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,shutil,subprocess,uuid
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'hardware/thin18-compact/c4d3-96x68-passive-usbc'
DST=ROOT/'hardware/thin18-compact/c4d4-96x68-qmi8658'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
SCH=DST/REL/(STEM+'.kicad_sch')
PCB=DST/REL/(STEM+'.kicad_pcb')
REF='U503'

if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()

def balanced(text,pos,opener):
    start=text.rfind(opener,0,pos)
    if start<0: raise RuntimeError('block start missing')
    depth=0;q=False;esc=False;j=start
    while j<len(text):
        c=text[j]
        if q:
            if esc: esc=False
            elif c=='\\': esc=True
            elif c=='"': q=False
        else:
            if c=='"': q=True
            elif c=='(': depth+=1
            elif c==')':
                depth-=1
                if depth==0:return start,j+1,text[start:j+1]
        j+=1
    raise RuntimeError('unterminated')

def sch_prop(name,value):
    return f'(property "{name}" "{value}" (at 0 0 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))'
def pcb_prop(name,value):
    u=uuid.uuid5(uuid.NAMESPACE_URL,f'c4d4-u503-{name}')
    return f'(property "{name}" "{value}" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{u}") (effects (font (size 1 1) (thickness 0.15))))'

# U503 lives in root schematic and already uses the QMI8658 pin contract.
s=SCH.read_text()
pos=s.index('(property "Reference" "U503"')
a,b,block=balanced(s,pos,'(symbol ')
block=block.replace('(property "Value" "LSM6DSO32XTR"','(property "Value" "QMI8658A"',1)
# replace existing procurement properties if present, otherwise insert before pin list
for name in ['Manufacturer','MPN','LCSC','ECO_ID','Qualification','Datasheet']:
    block=re.sub(rf' \(property "{name}" ".*?" .*?\) (?=\(property|\(pin)', ' ', block, count=1)
pinpos=block.index('(pin "1"')
extra=' '.join([
    sch_prop('Manufacturer','QST (Shanghai QST)'),
    sch_prop('MPN','QMI8658A'),
    sch_prop('LCSC','C3021082'),
    sch_prop('ECO_ID','THIN18-C4D4-QMI8658'),
    sch_prop('Qualification','Existing QMI8658A pin/net contract; firmware, orientation, calibration and physical qualification open'),
    sch_prop('Datasheet','https://www.qstcorp.com/upload/pdf/202301/13-52-25%20QMI8658A%20Datasheet%20Rev%20A.pdf')
])
block=block[:pinpos]+extra+' '+block[pinpos:]
s=s[:a]+block+s[b:]
SCH.write_text(s)

p=PCB.read_text()
pos=p.index('(property "Reference" "U503"')
a,b,block=balanced(p,pos,'(footprint ')
block=block.replace('(property "Value" "LSM6DSO32XTR"','(property "Value" "QMI8658A"',1)
for name in ['Manufacturer','MPN','LCSC','ECO_ID','Qualification','Datasheet']:
    block=re.sub(rf' \(property "{name}" ".*?" .*?\) (?=\(property|\(attr)', ' ', block, count=1)
attr=block.index('(attr smd)')
extra=' '.join([
    pcb_prop('Manufacturer','QST (Shanghai QST)'),
    pcb_prop('MPN','QMI8658A'),
    pcb_prop('LCSC','C3021082'),
    pcb_prop('ECO_ID','THIN18-C4D4-QMI8658'),
    pcb_prop('Qualification','Existing QMI8658A pin/net contract; firmware, orientation, calibration and physical qualification open'),
    pcb_prop('Datasheet','https://www.qstcorp.com/upload/pdf/202301/13-52-25%20QMI8658A%20Datasheet%20Rev%20A.pdf')
])
block=block[:attr]+extra+' '+block[attr:]
p=p[:a]+block+p[b:]
PCB.write_text(p)

k='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
subprocess.run([k,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(DST/'verification/drc.json'),str(PCB)],check=True)
subprocess.run([k,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc.json'),str(SCH)],check=True)
subprocess.run([k,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(SCH)],check=True)

drc=json.load(open(DST/'verification/drc.json'))
erc=json.load(open(DST/'verification/erc.json'))
counts={'drc':len(drc.get('violations',[])),'open':len(drc.get('unconnected_items',[])),'parity':len(drc.get('schematic_parity',[])),'erc':sum(len(x.get('violations',[])) for x in erc.get('sheets',[]))}
if counts!={'drc':0,'open':403,'parity':0,'erc':0}: raise SystemExit(f'native checks changed {counts}')

def sem(path):
    r=ET.parse(path).getroot(); refs=sorted(c.get('ref') for c in r.findall('components/comp')); tuples=[]; vals={}; fields={}
    for c in r.findall('components/comp'):
        vals[c.get('ref')]=c.findtext('value') or ''
        fields[c.get('ref')]={f.get('name'):f.text or '' for f in c.findall('fields/field')}
    for n in r.findall('nets/net'):
        for x in n.findall('node'): tuples.append((x.get('ref'),x.get('pin'),n.get('name','')))
    return refs,sorted(tuples),vals,fields
ar,at,av,af=sem(SRC/'verification/netlist.xml')
br,bt,bv,bf=sem(DST/'verification/netlist.xml')
if ar!=br or at!=bt: raise SystemExit('unexpected topology change')
if bv.get(REF)!='QMI8658A' or bf.get(REF,{}).get('MPN')!='QMI8658A' or bf.get(REF,{}).get('LCSC')!='C3021082':
    raise SystemExit('U503 production fields not updated')

pinmap={}
r=ET.parse(DST/'verification/netlist.xml').getroot()
for n in r.findall('nets/net'):
    for x in n.findall('node'):
        if x.get('ref')==REF: pinmap[x.get('pin')]=n.get('name','')
expected={'1':'3V3_AON','2':'GND','3':'GND','4':'IMU_INT1','5':'3V3_AON','6':'GND','7':'GND','8':'3V3_AON','9':'unconnected-(U503-INT2-Pad9)','10':'unconnected-(U503-NC-Pad10)','11':'unconnected-(U503-NC-Pad11)','12':'3V3_AON','13':'I2C_SCL','14':'I2C_SDA'}
if pinmap!=expected: raise SystemExit(f'QMI pin contract mismatch {pinmap}')

report={
 'date':'2026-09-29','kind':'C4D-4 QMI8658A IMU correction/substitution',
 'source':'c4d3-96x68-passive-usbc','ref':'U503',
 'before':'LSM6DSO32XTR','after':'QMI8658A','vendor':'QST','lcsc':'C3021082',
 'finding':'Existing U503 pin functions and nets already matched QMI8658A, so this corrects the component identity without topology changes.',
 'pinmap':pinmap,'native_checks':counts,
 'refs':len(br),'pin_net_tuples':len(bt),'topology_identical':ar==br and at==bt,
 'firmware_required':['QMI8658 initialization/sample driver','orientation map','interrupt/FIFO if used','calibration'],
 'product_gate':'±16g ceiling accepted; no repository dependency on ±32g/MLC/FSM found',
 'physical_qualification':False,'manufacturing_release':False,
 'pcb_sha256':hashlib.sha256(PCB.read_bytes()).hexdigest()
}
(DST/'c4d4-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(DST/'README.md').write_text('# Thin18 Compact C4D-4 — QMI8658A\n\nU503 identity is corrected from LSM6DSO32XTR to QST QMI8658A / C3021082. The existing LGA-14 pin/net contract already matches QMI8658A; no topology change is introduced. Firmware and physical IMU qualification remain open.\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
