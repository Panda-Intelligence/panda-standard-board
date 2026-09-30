#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,shutil,subprocess,uuid,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'c4d1-96x68-sgm41513-additive'
DST=ROOT/'c4d2-96x68-sgm62125'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
SCH=DST/REL/(STEM+'.kicad_sch')
PCB=DST/REL/(STEM+'.kicad_pcb')
PLIB=ROOT/'c4d-power-lib'
KICAD='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'

def balanced(text,start):
    dep=0;q=False;esc=False
    for i in range(start,len(text)):
        c=text[i]
        if q:
            if esc: esc=False
            elif c=='\\': esc=True
            elif c=='"': q=False
        else:
            if c=='"': q=True
            elif c=='(': dep+=1
            elif c==')':
                dep-=1
                if dep==0:return i+1
    raise RuntimeError('unterminated')

def block_by_ref(text,kind,ref):
    i=text.index(f'(property "Reference" "{ref}"')
    a=text.rfind('('+kind+' ',0,i); b=balanced(text,a)
    return a,b,text[a:b]

def mark_offboard(block,new_value):
    block=block.replace('(in_bom yes)','(in_bom no)',1)
    block=block.replace('(on_board yes)','(on_board no)',1)
    block=block.replace('(in_pos_files yes)','(in_pos_files no)',1)
    block=block.replace('(dnp no)','(dnp yes)',1)
    block=re.sub(r'(\(property "Value" ")[^"]+(")',lambda m:m.group(1)+new_value+m.group(2),block,count=1)
    return block

def top_children(text):
    out=[];dep=0;q=False;esc=False;st=None
    for i,c in enumerate(text):
        if q:
            if esc:esc=False
            elif c=='\\':esc=True
            elif c=='"':q=False
            continue
        if c=='"': q=True; continue
        if c=='(':
            dep+=1
            if dep==2:st=i
        elif c==')':
            if dep==2 and st is not None:
                out.append(text[st:i+1]);st=None
            dep-=1
    return out

if DST.exists():shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()

# Merge exact SGM62125 library assets into the already registered project library.
proj_sym=DST/'lib/panda-standard.kicad_sym'
proj_fp=DST/'lib/panda-standard.pretty'
lib_src=(PLIB/'PandaDomesticPower.kicad_sym').read_text()
pos=lib_src.index('(symbol "SGM62125AXG_TR"')
sym_raw=lib_src[pos:balanced(lib_src,pos)]
plib=proj_sym.read_text()
if '(symbol "SGM62125AXG_TR"' not in plib:
    pe=plib.rfind(')')
    proj_sym.write_text(plib[:pe]+' '+sym_raw+plib[pe:])
shutil.copy2(PLIB/'PandaDomesticPower.pretty/SGM62125_XG_WLCSP15_1.46x2.3_P0.4.kicad_mod',
             proj_fp/'SGM62125_XG_WLCSP15_1.46x2.3_P0.4.kicad_mod')

s=SCH.read_text()

# Retire legacy TPS63802 stage completely from the C4D schematic candidate.
# DNP power-output symbols still participate in ERC, so remove them from this
# derived candidate while preserving the immutable source separately.
for ref in ['U401','R401','R402','R403']:
    a,b,_=block_by_ref(s,'symbol',ref)
    s=s[:a]+s[b:]

# Remove only the legacy stage wire/FB-label objects that become dangling after
# U401/R401-R403 removal. UUIDs are inherited from the immutable C4D-1 source.
legacy_object_uuids = [
 '0f0cd97d-6080-4de5-8804-f90a78e245b4',
 '6b1ed367-6e81-4c37-923c-40041c96dcf7',
 'd8ce54ee-25c6-4820-81cc-0a25db222cef',
 '222d9429-b55c-4639-bba7-b736acc250da',
 'a9976bf9-6b96-427b-ab15-f2ee9ef2a103',
 '3d11153d-a28a-435d-b96f-67f628775368',
 'f79d7ee7-d519-4222-93c8-8b6aeeb8ed4e',
 'fe506da3-ffe7-4be4-97dd-7f4a4bee531f',
 '64cb8d5d-c7a6-4d28-8273-ff58ed6fc29f',
 'b2e11261-77ef-4a13-9017-997e7996160c',
 '0c6a9d39-65c4-48d2-b4ea-b401f633c6d5',
 '18d0a840-4be3-4943-8cf7-33906e752ae9',
 'd6710227-c0bb-492d-8fe2-3426d1b225e9',
 'c3ec50d5-1b3f-4fc8-8669-20ba64f38f8f',
 '181a5d47-9fd7-4d1e-bee8-ce0ae6139cc3',
 'b3898549-21f6-4df6-b702-e4e08d51d580',
 '2a3b33e6-deca-45bc-b3f1-0368dfb89df0',
 '015c57cc-6671-4a76-b46e-c03310367fab',
 'd98f7916-299a-419d-b357-8bf68db393fb',
 '16247444-1d89-4e23-a448-fc0c280216b1',
 '02af1d2f-96f1-4b3a-a5b6-7dfb037a0c1a',
 '64d407d0-8d85-4d63-89d1-909de13ad4f3',
 '0f520e13-7caf-4f49-b8d3-5b6ffa77c8ba',
 '0146bf83-46a3-4aa3-9d44-d935249cc3ca',
 '0840b3af-c5cb-479d-86b9-34ca1c33da6a',
 'c68029d0-3a1f-4baf-bd6a-7edd0ba900ea',
 'b5f66d91-7b88-4f42-bd10-79f5dcdec293',
 '722c8914-d1c5-499f-99b6-6fcc544fcf5e',
 '80325c9d-f6b7-457e-a7f5-e944eeaafba3',
 'd8b7db8b-1044-4034-8b96-7f20e51bf7db',
 'a1e12546-6960-428c-8042-8978fadac710',
 'f783a9fd-1c16-4ceb-ba30-ebe727c0560a',
]
def remove_object_with_uuid(text, uid):
    marker=f'(uuid "{uid}")'
    i=text.find(marker)
    if i < 0:
        raise SystemExit(f'legacy object UUID not found: {uid}')
    starts=[text.rfind('(wire ',0,i), text.rfind('(global_label ',0,i)]
    a=max(starts)
    if a < 0:
        raise SystemExit(f'legacy object start not found: {uid}')
    b=balanced(text,a)
    return text[:a]+text[b:]
for uid in legacy_object_uuids:
    s=remove_object_with_uuid(s,uid)

# Inject cached SGM62125 symbol.
symdef=sym_raw.replace('(symbol "SGM62125AXG_TR"', '(symbol "panda-standard:SGM62125AXG_TR"',1)
# E2/E3 are parallel VOUT balls. Keep E2 as power_out and classify E3
# passive for ERC; electrical/net connectivity remains identical.
parts=symdef.rsplit('(pin power_out line',1)
if len(parts)!=2:
    raise SystemExit('SGM62125 expected two power_out VOUT pins')
symdef=parts[0]+'(pin passive line'+parts[1]
ls=s.index('(lib_symbols ');le=balanced(s,ls)
s=s[:le-1]+' '+symdef+s[le-1:]

cx,cy=205.74,170.18
pins=' '.join(f'(pin "{n}" (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,"thin18-c4d2-u902-"+n)}"))'
              for n in ['A1','A2','A3','B1','B2','B3','C1','C2','C3','D1','D2','D3','E1','E2','E3'])
root_uuid=re.search(r'^\(kicad_sch .*?\(uuid "([^"]+)"\)',s).group(1)
inst=f'''(symbol (lib_id "panda-standard:SGM62125AXG_TR") (at {cx} {cy} 0) (unit 1) (body_style 1)
(exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes) (dnp no) (fields_autoplaced yes)
(uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d2-u902')}")
(property "Reference" "U902" (at {cx} {cy-12.7} 0) (effects (font (size 1.27 1.27))))
(property "Value" "SGM62125AXG/TR" (at {cx} {cy-10.16} 0) (effects (font (size 1.27 1.27))))
(property "Footprint" "panda-standard:SGM62125_XG_WLCSP15_1.46x2.3_P0.4" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Datasheet" "https://www.sg-micro.com/product/SGM62125" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Description" "C4D-2 SGMICRO low-Iq I2C buck-boost; ADDR high startup 3.4V then firmware 3.3V; EVT only." (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Manufacturer" "SGMICRO" (at {cx} {cy} 0) (hide yes) (effects (font (size 1 1))))
(property "MPN" "SGM62125AXG/TR" (at {cx} {cy} 0) (hide yes) (effects (font (size 1 1))))
{pins}
(instances (project "PANDA-STD-CORE-EVT" (path "/{root_uuid}" (reference "U902") (unit 1)))))'''

def glabel(name,x,y,key):
    u=uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d2-u902-label-'+key)
    return f'(global_label "{name}" (shape passive) (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{u}"))'

# Library local coordinates: left x=-11.43, right x=+11.43, bottom y=-11.43.
labels=[
 ('VSYS_RAW',cx-11.43,cy-6.35,'A1_EN'),
 ('VSYS_RAW',cx-11.43,cy-3.81,'A2_VIN'),
 ('VSYS_RAW',cx-11.43,cy-1.27,'A3_VIN'),
 ('VSYS_RAW',cx-11.43,cy+1.27,'B1_ADDR_HIGH'),
 ('SGM62125_SW1',cx-11.43,cy+3.81,'B2_SW1'),
 ('SGM62125_SW1',cx-11.43,cy+6.35,'B3_SW1'),
 ('I2C_SCL',cx+11.43,cy+6.35,'D1_SCL'),
 ('SGM62125_SW2',cx+11.43,cy+3.81,'D2_SW2'),
 ('SGM62125_SW2',cx+11.43,cy+1.27,'D3_SW2'),
 ('I2C_SDA',cx+11.43,cy-1.27,'E1_SDA'),
 ('3V3_AON_SRC',cx+11.43,cy-3.81,'E2_VOUT'),
 ('3V3_AON_SRC',cx+11.43,cy-6.35,'E3_VOUT'),
 ('GND',cx,cy+11.43,'C1_AGND'),
 ('GND',cx+2.54,cy+11.43,'C2_PGND'),
 ('GND',cx+5.08,cy+11.43,'C3_PGND'),
]
root_end=s.rfind(')')
s=s[:root_end]+' '+inst+' '+' '.join(glabel(*x) for x in labels)+s[root_end:]

# Migrate inductor nets on all hierarchical schematic files.
renames={'"SW_L1"':'"SGM62125_SW1"','"SW_L2"':'"SGM62125_SW2"'}
for a,b in renames.items():s=s.replace(a,b)
SCH.write_text(s)
for sp in (DST/REL).glob('*.kicad_sch'):
    if sp==SCH:continue
    t=sp.read_text()
    for a,b in renames.items():t=t.replace(a,b)
    sp.write_text(t)

# PCB: remove retired U401/R401/R402/R403 footprints; preserve L401 and C401/C402/C403.
p=PCB.read_text()
for ref in ['U401','R401','R402','R403']:
    a,b,_=block_by_ref(p,'footprint',ref);p=p[:a]+p[b:]
for a,b in renames.items():p=p.replace(a,b)

mod=(PLIB/'PandaDomesticPower.pretty/SGM62125_XG_WLCSP15_1.46x2.3_P0.4.kicad_mod').read_text()
geom=[x for x in top_children(mod) if x.startswith('(pad ') or x.startswith('(fp_rect') or x.startswith('(fp_circle') or x.startswith('(fp_line') or x.startswith('(fp_poly')]
netmap={
 'A1':'VSYS_RAW','A2':'VSYS_RAW','A3':'VSYS_RAW','B1':'VSYS_RAW',
 'B2':'SGM62125_SW1','B3':'SGM62125_SW1','C1':'GND','C2':'GND','C3':'GND',
 'D1':'I2C_SCL','D2':'SGM62125_SW2','D3':'SGM62125_SW2','E1':'I2C_SDA',
 'E2':'3V3_AON_SRC','E3':'3V3_AON_SRC'
}
gg=[]
for x in geom:
    m=re.match(r'\(pad "([^"]*)"',x)
    if m and m.group(1) in netmap:x=x[:-1]+f' (net "{netmap[m.group(1)]}"))'
    gg.append(x)
newfp=f'''(footprint "panda-standard:SGM62125_XG_WLCSP15_1.46x2.3_P0.4" (locked yes) (layer "F.Cu")
(uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d2-u902-fp')}") (at 31.725 6.975)
(property "Reference" "U902" (at 0 -2.4 0) (layer "F.Fab") (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d2-u902-ref')}") (effects (font (size 0.65 0.65))))
(property "Value" "SGM62125AXG/TR" (at 0 2.4 0) (layer "F.Fab") (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d2-u902-val')}") (effects (font (size 0.55 0.55))))
(property "Datasheet" "https://www.sg-micro.com/product/SGM62125" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d2-u902-ds')}") (effects (font (size 1 1))))
(property "Description" "C4D-2 SGMICRO low-Iq I2C buck-boost; ADDR high startup 3.4V then firmware 3.3V; EVT only." (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d2-u902-desc')}") (effects (font (size 1 1))))
(property "Manufacturer" "SGMICRO" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d2-u902-mfr')}") (effects (font (size 1 1))))
(property "MPN" "SGM62125AXG/TR" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d2-u902-mpn')}") (effects (font (size 1 1))))
(attr smd)
{' '.join(gg)}
)'''
pe=p.rfind(')');p=p[:pe]+' '+newfp+p[pe:]
PCB.write_text(p)

# Exact 0.4-mm WLCSP geometry leaves about 0.17 mm between adjacent lands.
# Restrict a 0.15-mm clearance exception to U902 internal pads only.
dru=DST/REL/(STEM+'.kicad_dru')
dt=dru.read_text()
rule="""
(rule "U902 SGM62125 exact WLCSP internal pad clearance"
    (constraint clearance (min 0.15mm))
    (condition "A.memberOfFootprint('U902') && B.memberOfFootprint('U902')")
)
"""
if 'U902 SGM62125 exact WLCSP internal pad clearance' not in dt:
    dru.write_text(dt+rule)

# Native validation.
subprocess.run([KICAD,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc.json'),str(SCH)],check=True)
subprocess.run([KICAD,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(SCH)],check=True)
subprocess.run([KICAD,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(DST/'verification/drc.json'),str(PCB)],check=True)
erc=json.load(open(DST/'verification/erc.json'));drc=json.load(open(DST/'verification/drc.json'))
counts={'erc':sum(len(x.get('violations',[])) for x in erc.get('sheets',[])),
        'drc':len(drc.get('violations',[])),'parity':len(drc.get('schematic_parity',[])),
        'open':len(drc.get('unconnected_items',[]))}

root=ET.parse(DST/'verification/netlist.xml').getroot()
pm={}
for n in root.findall('nets/net'):
    for x in n.findall('node'):
        if x.get('ref')=='U902':pm[x.get('pin')]=n.get('name','')
expected=netmap
wrong={k:(pm.get(k),v) for k,v in expected.items() if pm.get(k)!=v}
if wrong:raise SystemExit(f'U902 pin/net mismatch {wrong}')
if counts['erc'] or counts['drc'] or counts['parity']:raise SystemExit(f'native checks not clean {counts}')

report={
 'date':'2026-09-29','kind':'C4D-2 SGM62125 AON buck-boost redesign',
 'source':'c4d1-96x68-sgm41513-additive','new_ref':'U902','mpn':'SGM62125AXG/TR',
 'retired_offboard':['U401','R401','R402','R403'],
 'reused':['L401 0.47uH value/footprint subject Isat/DCR qualification','C401 input 22uF','C402/C403 output 2x22uF'],
 'startup':'ADDR tied high to VSYS_RAW -> 3.4V startup; firmware target 3.3V',
 'pinmap':pm,'native_checks':counts,'physical_qualification':False,'manufacturing_release':False,
 'pcb_sha256':hashlib.sha256(PCB.read_bytes()).hexdigest()
}
(DST/'c4d2-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(DST/'README.md').write_text('# Thin18 Compact C4D-2 — SGM62125 AON buck-boost\n\nU902 replaces the populated TPS63802 stage. Legacy U401/R401/R402/R403 remain only as off-board/DNP schematic history. L401 and C401/C402/C403 are reused pending magnetic/DC-bias qualification. Native checks are recorded in c4d2-report.json. Not a manufacturing release.\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
