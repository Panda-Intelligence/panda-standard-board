#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, re, shutil, subprocess, uuid
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'hardware/thin18-compact/c3a-96x68-touch-frontlight-reserved'
DST=ROOT/'hardware/thin18-compact/c4a-96x68-domestic-xl9535'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
SCH=DST/REL/(STEM+'.kicad_sch')
PCB=DST/REL/(STEM+'.kicad_pcb')

if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()

def balanced_block(text, pos, opener):
    start=text.rfind(opener,0,pos)
    if start<0: raise RuntimeError('block start missing')
    depth=0; quote=False; esc=False; j=start
    while j<len(text):
        c=text[j]
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
                    return start,j+1,text[start:j+1]
        j+=1
    raise RuntimeError('unterminated block')

def prop_line(name,value,uid,layer=None):
    if layer:
        return f'(property "{name}" "{value}" (at 0 0 0) (layer "{layer}") (hide yes) (uuid "{uid}") (effects (font (size 1 1) (thickness 0.15))))'
    return f'(property "{name}" "{value}" (at 60.96 68.58 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))'

# Schematic instance U601: same cached symbol/pins, update procurement identity only.
s=SCH.read_text()
pos=s.index('(property "Reference" "U601"')
a,b,block=balanced_block(s,pos,'(symbol ')
block=block.replace('(property "Value" "TCA9535PWR"','(property "Value" "XL9535"',1)
block=block.replace('https://www.ti.com/lit/ds/symlink/tca9535.pdf','https://datasheet.lcsc.com/lcsc/2006030032_XINLUDA-XL9535_C561273.pdf',1)
old_desc='TI TCA9535PWR Active/Production 16-bit I2C I/O expander; PW0024A exact-copper A-stage candidate; P outputs are push-pull, no internal P-port pulls; F0/B-stage pending.'
new_desc='XINLUDA XL9535 mainland 16-bit I2C/SMBus GPIO expander; TSSOP24 pinout matches TCA9535 PW; same-net C4 engineering substitution; firmware/reset/interrupt regression and physical qualification remain open.'
block=block.replace(old_desc,new_desc,1)
anchor='(property "Description" "'+new_desc+'"'
di=block.index(anchor)
# insert after complete Description property by finding next '(pin "1"'
pin1=block.index('(pin "1"',di)
extra=' '.join([
 prop_line('Manufacturer','XINLUDA',''),
 prop_line('MPN','XL9535',''),
 prop_line('LCSC','C561273',''),
 prop_line('ECO_ID','THIN18-C4-XL9535',''),
 prop_line('Qualification','Pin/package/net documentary match; firmware + physical qualification open','')
])
block=block[:pin1]+extra+' '+block[pin1:]
s=s[:a]+block+s[b:]
SCH.write_text(s)

# PCB footprint U601: preserve exact copper/pose/footprint, update identity metadata.
p=PCB.read_text()
pos=p.index('(property "Reference" "U601"')
a,b,block=balanced_block(p,pos,'(footprint ')
block=block.replace('(property "Value" "TCA9535PWR"','(property "Value" "XL9535"',1)
block=block.replace('https://www.ti.com/lit/ds/symlink/tca9535.pdf','https://datasheet.lcsc.com/lcsc/2006030032_XINLUDA-XL9535_C561273.pdf',1)
block=block.replace(old_desc,new_desc,1)
anchor='(property "Description" "'+new_desc+'"'
di=block.index(anchor)
attr=block.index('(attr smd)',di)
extra=' '.join([
 prop_line('Manufacturer','XINLUDA',str(uuid.uuid5(uuid.NAMESPACE_URL,'c4-u601-mfr')),'F.Fab'),
 prop_line('MPN','XL9535',str(uuid.uuid5(uuid.NAMESPACE_URL,'c4-u601-mpn')),'F.Fab'),
 prop_line('LCSC','C561273',str(uuid.uuid5(uuid.NAMESPACE_URL,'c4-u601-lcsc')),'F.Fab'),
 prop_line('ECO_ID','THIN18-C4-XL9535',str(uuid.uuid5(uuid.NAMESPACE_URL,'c4-u601-eco')),'F.Fab'),
 prop_line('Qualification','Pin/package/net documentary match; firmware + physical qualification open',str(uuid.uuid5(uuid.NAMESPACE_URL,'c4-u601-qual')),'F.Fab')
])
block=block[:attr]+extra+' '+block[attr:]
p=p[:a]+block+p[b:]
PCB.write_text(p)

kicad='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
subprocess.run([kicad,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(DST/'verification/drc.json'),str(PCB)],check=True)
subprocess.run([kicad,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc.json'),str(SCH)],check=True)
subprocess.run([kicad,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(SCH)],check=True)

drc=json.load(open(DST/'verification/drc.json'))
erc=json.load(open(DST/'verification/erc.json'))
dv=len(drc.get('violations',[])); du=len(drc.get('unconnected_items',[])); dp=len(drc.get('schematic_parity',[]))
ev=sum(len(x.get('violations',[])) for x in erc.get('sheets',[]))
if (dv,du,dp,ev)!=(0,447,0,0): raise SystemExit(f'native checks changed {(dv,du,dp,ev)}')

def sem(path):
    r=ET.parse(path).getroot()
    refs=sorted(c.get('ref') for c in r.findall('components/comp'))
    t=[]
    vals={}
    fields={}
    for c in r.findall('components/comp'):
        vals[c.get('ref')]=c.findtext('value') or ''
        fields[c.get('ref')]={f.get('name'):f.text or '' for f in c.findall('fields/field')}
    for n in r.findall('nets/net'):
        name=n.get('name','')
        for x in n.findall('node'): t.append((x.get('ref'),x.get('pin'),name))
    return refs,sorted(t),vals,fields
ar,at,av,af=sem(SRC/'verification/netlist.xml')
br,bt,bv,bf=sem(DST/'verification/netlist.xml')
if ar!=br or at!=bt: raise SystemExit('unexpected electrical topology change')
if bv.get('U601')!='XL9535': raise SystemExit('U601 value not updated')
if bf.get('U601',{}).get('MPN')!='XL9535' or bf.get('U601',{}).get('LCSC')!='C561273':
    raise SystemExit('U601 production fields missing')

report={
 'kind':'C4A mainland GPIO expander substitution, same-net same-footprint candidate',
 'source':'c3a-96x68-touch-frontlight-reserved',
 'change':{'ref':'U601','before':'TCA9535PWR','after':'XL9535','manufacturer':'XINLUDA','lcsc':'C561273'},
 'documentary_evidence':{
   'pinout':'TSSOP24 pins match TCA9535 PW: INT,A1,A2,P00..P17,GND,SCL,SDA,A0,VCC',
   'supply':'2.3V..5.5V','i2c':'up to 400kHz','interrupt':'open-drain active-low',
   'power_on':'ports default inputs'
 },
 'refs':len(br),'pin_net_tuples':len(bt),'refs_identical':ar==br,'pin_nets_identical':at==bt,
 'drc_violations':dv,'unconnected_items':du,'schematic_parity':dp,'erc':ev,
 'pcb_sha256':hashlib.sha256(PCB.read_bytes()).hexdigest(),
 'firmware_regression_required':True,'physical_qualification':False,'manufacturing_release':False
}
(DST/'c4a-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(DST/'README.md').write_text(
 '# Thin18 Compact C4A — XL9535 domestic GPIO expander\n\n'
 'U601 is changed from TI TCA9535PWR to mainland XINLUDA XL9535 / LCSC C561273 while preserving the existing TSSOP-24 copper, pose and all nets.\n\n'
 f'Fresh checks: DRC {dv}; parity {dp}; ERC {ev}; open {du} (expected because compact is intentionally unrouted).\n'
 f'{len(br)} refs and {len(bt)} pin/net tuples are unchanged.\n\n'
 'Firmware register/reset/interrupt regression and physical EVT remain open. Not a manufacturing release.\n'
)
print(json.dumps(report,ensure_ascii=False,indent=2))
