#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,shutil,subprocess,uuid
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'hardware/thin18-compact/c4a-96x68-domestic-xl9535'
DST=ROOT/'hardware/thin18-compact/c4c-96x68-domestic-passives'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
SCH=DST/REL/(STEM+'.kicad_sch'); PCB=DST/REL/(STEM+'.kicad_pcb')

if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()

# Exact same-footprint mainland passive selections.
# 25V ratings intentionally exceed the lower requirements on several nets.
TARGETS={
 '100n_0402':{
  'refs':[],
  'value_prefix':'100n',
  'footprint_contains':'R_0402_1005Metric', # corrected below for capacitors via detection
  'mpn':'0402B104K250NT','manufacturer':'FH (Fenghua Advanced)','lcsc':'C56392',
  'spec':'100nF ±10% 25V X7R 0402'
 },
 '1u_0603':{
  'refs':[],
  'value_prefix':'1u',
  'footprint_contains':'C_0603_1608Metric',
  'mpn':'0603B105K250NT','manufacturer':'FH (Fenghua Advanced)','lcsc':'C59302',
  'spec':'1uF ±10% 25V X7R 0603'
 }
}

# Derive refs from C4A netlist to avoid a hand-maintained list.
root=ET.parse(SRC/'verification/netlist.xml').getroot()
for c in root.findall('components/comp'):
    ref=c.get('ref'); val=(c.findtext('value') or '').strip(); fp=(c.findtext('footprint') or '')
    if ref.startswith('C') and val.startswith('100n') and 'C_0402_1005Metric' in fp:
        TARGETS['100n_0402']['refs'].append(ref)
    if ref.startswith('C') and val.startswith('1u') and 'C_0603_1608Metric' in fp:
        TARGETS['1u_0603']['refs'].append(ref)

def balanced(text,pos,opener):
    start=text.rfind(opener,0,pos); depth=0; q=False; esc=False; j=start
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
def pcb_prop(ref,name,value):
    u=uuid.uuid5(uuid.NAMESPACE_URL,f'c4c-{ref}-{name}')
    return f'(property "{name}" "{value}" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{u}") (effects (font (size 1 1) (thickness 0.15))))'

# Locate capacitor instances across all hierarchical schematic files.
sheet_paths=list((DST/REL).glob('*.kicad_sch'))
sheet_text={p:p.read_text() for p in sheet_paths}
for group,g in TARGETS.items():
    for ref in g['refs']:
        found=None
        for sp,txt in sheet_text.items():
            needle=f'(property "Reference" "{ref}"'
            if needle in txt:
                found=sp; break
        if found is None: raise SystemExit(f'schematic ref not found: {ref}')
        txt=sheet_text[found]
        pos=txt.index(f'(property "Reference" "{ref}"')
        a,b,block=balanced(txt,pos,'(symbol ')
        pinpos=block.index('(pin "1"')
        extra=' '.join([
          sch_prop('Manufacturer',g['manufacturer']),
          sch_prop('MPN',g['mpn']),
          sch_prop('LCSC',g['lcsc']),
          sch_prop('ECO_ID','THIN18-C4-FH-PASSIVE'),
          sch_prop('Qualification',g['spec']+'; same footprint; physical assembly/DC-bias qualification open')
        ])
        block=block[:pinpos]+extra+' '+block[pinpos:]
        sheet_text[found]=txt[:a]+block+txt[b:]
for sp,txt in sheet_text.items(): sp.write_text(txt)

p=PCB.read_text()
for group,g in TARGETS.items():
    for ref in g['refs']:
        pos=p.index(f'(property "Reference" "{ref}"')
        a,b,block=balanced(p,pos,'(footprint ')
        attr=block.index('(attr smd)')
        extra=' '.join([
          pcb_prop(ref,'Manufacturer',g['manufacturer']),
          pcb_prop(ref,'MPN',g['mpn']),
          pcb_prop(ref,'LCSC',g['lcsc']),
          pcb_prop(ref,'ECO_ID','THIN18-C4-FH-PASSIVE'),
          pcb_prop(ref,'Qualification',g['spec']+'; same footprint; physical assembly/DC-bias qualification open')
        ])
        block=block[:attr]+extra+' '+block[attr:]
        p=p[:a]+block+p[b:]
PCB.write_text(p)

k='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
subprocess.run([k,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(DST/'verification/drc.json'),str(PCB)],check=True)
subprocess.run([k,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc.json'),str(SCH)],check=True)
subprocess.run([k,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(SCH)],check=True)
drc=json.load(open(DST/'verification/drc.json')); erc=json.load(open(DST/'verification/erc.json'))
counts=(len(drc.get('violations',[])),len(drc.get('unconnected_items',[])),len(drc.get('schematic_parity',[])),sum(len(x.get('violations',[])) for x in erc.get('sheets',[])))
if counts!=(0,447,0,0):raise SystemExit(f'native checks changed {counts}')

def sem(path):
    r=ET.parse(path).getroot(); refs=sorted(c.get('ref') for c in r.findall('components/comp')); t=[]; fields={}
    for c in r.findall('components/comp'):
        fields[c.get('ref')]={f.get('name'):f.text or '' for f in c.findall('fields/field')}
    for n in r.findall('nets/net'):
        for x in n.findall('node'):t.append((x.get('ref'),x.get('pin'),n.get('name','')))
    return refs,sorted(t),fields
ar,at,af=sem(SRC/'verification/netlist.xml'); br,bt,bf=sem(DST/'verification/netlist.xml')
if ar!=br or at!=bt:raise SystemExit('topology changed')
changed=[]
for name,g in TARGETS.items():
    for ref in g['refs']:
        if bf.get(ref,{}).get('MPN')!=g['mpn'] or bf.get(ref,{}).get('LCSC')!=g['lcsc']:
            raise SystemExit(ref+' procurement fields failed')
        changed.append(ref)
report={
 'kind':'C4C mainland Fenghua same-footprint passive procurement selection',
 'source':'c4a-96x68-domestic-xl9535',
 'groups':TARGETS,'changed_refs':changed,'changed_count':len(changed),
 'refs':len(br),'pin_net_tuples':len(bt),'refs_identical':ar==br,'pin_nets_identical':at==bt,
 'drc_violations':counts[0],'unconnected_items':counts[1],'schematic_parity':counts[2],'erc':counts[3],
 'physical_qualification':False,'manufacturing_release':False,'pcb_sha256':hashlib.sha256(PCB.read_bytes()).hexdigest()
}
(DST/'c4c-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(DST/'README.md').write_text('# Thin18 Compact C4C — mainland Fenghua passives\n\nSame-footprint procurement metadata is selected for qualified 100nF/0402 and 1uF/0603 groups. Electrical topology is unchanged. Remaining passive groups stay blocked until exact evidence exists. Not a manufacturing release.\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
