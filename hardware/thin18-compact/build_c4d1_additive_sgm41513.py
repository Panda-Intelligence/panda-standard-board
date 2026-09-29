#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,shutil,subprocess,uuid,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'c4d-96x68-power-usb-reserved'
DST=ROOT/'c4d1-96x68-sgm41513-additive'
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
    a=text.rfind('('+kind+' ',0,i)
    b=balanced(text,a)
    return a,b,text[a:b]

def top_children(text):
    out=[];dep=0;q=False;esc=False;st=None
    for i,c in enumerate(text):
        if q:
            if esc:esc=False
            elif c=='\\':esc=True
            elif c=='"':q=False
            continue
        if c=='"': q=True;continue
        if c=='(':
            dep+=1
            if dep==2: st=i
        elif c==')':
            if dep==2 and st is not None:
                out.append(text[st:i+1]);st=None
            dep-=1
    return out

if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()

# Merge the exact domestic power symbol/footprint into the already-registered panda-standard libraries.
proj_sym=DST/'lib/panda-standard.kicad_sym'
proj_fp=DST/'lib/panda-standard.pretty'
proj_fp.mkdir(parents=True,exist_ok=True)
shutil.copy2(PLIB/'PandaDomesticPower.pretty/SGM41513_YTQF24_4x4_P0.5_EP2.7.kicad_mod',
             proj_fp/'SGM41513_YTQF24_4x4_P0.5_EP2.7.kicad_mod')
lib_src=(PLIB/'PandaDomesticPower.kicad_sym').read_text()
sym_pos=lib_src.index('(symbol "SGM41513YTQF24G_TR"')
sym_raw=lib_src[sym_pos:balanced(lib_src,sym_pos)]
plib=proj_sym.read_text()
if '(symbol "SGM41513YTQF24G_TR"' not in plib:
    pe=plib.rfind(')')
    proj_sym.write_text(plib[:pe]+' '+sym_raw+plib[pe:])
# Keep the inherited library tables byte-identical to the known-good source.
shutil.copy2(SRC/REL/'sym-lib-table',DST/REL/'sym-lib-table')
shutil.copy2(SRC/REL/'fp-lib-table',DST/REL/'fp-lib-table')

s=SCH.read_text()

# Remove legacy U201 entirely from the C4D electrical candidate.
# The source candidate remains immutable and preserves the historical BQ25628E design.
a,b,_=block_by_ref(s,'symbol','U201')
s=s[:a]+s[b:]
# Remove only the exact legacy U201 wire/label S-expressions by UUID.
def remove_block_uuid(text,kind,u):
    marker=f'(uuid "{u}")'
    pos=text.find(marker)
    if pos < 0:
        return text
    start=text.rfind('('+kind+' ',0,pos)
    if start < 0:
        raise RuntimeError(f'{kind} block not found for {u}')
    end=balanced(text,start)
    return text[:start]+text[end:]
for i in range(1,20):
    s=remove_block_uuid(s,'wire',f'1a6b2b49-9f0a-4908-ac42-6b27f3dc0a{i:02d}')
    s=remove_block_uuid(s,'global_label',f'2a6b2b49-9f0a-4908-ac42-6b27f3dc0a{i:02d}')

# Inject exact SGM cached symbol.
lib=(PLIB/'PandaDomesticPower.kicad_sym').read_text()
pos=lib.index('(symbol "SGM41513YTQF24G_TR"')
symdef=lib[pos:balanced(lib,pos)]
symdef=symdef.replace('(symbol "SGM41513YTQF24G_TR"', '(symbol "panda-standard:SGM41513YTQF24G_TR"',1)
symdef=symdef.replace('(pin power_in line (at -12.7 -7.62 0)', '(pin passive line (at -12.7 -7.62 0)')
ls=s.index('(lib_symbols '); le=balanced(s,ls)
s=s[:le-1]+' '+symdef+s[le-1:]

# Add U901 at a clean schematic position. Direct global labels attach to exact pin endpoints.
cx,cy=160.02,170.18
pins=' '.join(f'(pin "{n}" (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,"thin18-c4d1-u901-"+n)}"))' for n in
 ['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24','25'])
root_uuid=re.search(r'^\(kicad_sch .*?\(uuid "([^"]+)"\)',s).group(1)
inst=f'''(symbol (lib_id "panda-standard:SGM41513YTQF24G_TR") (at {cx} {cy} 0) (unit 1) (body_style 1)
(exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes) (dnp no) (fields_autoplaced yes)
(uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d1-u901')}")
(property "Reference" "U901" (at {cx} {cy-16.51} 0) (effects (font (size 1.27 1.27))))
(property "Value" "SGM41513YTQF24G/TR" (at {cx} {cy-13.97} 0) (effects (font (size 1.27 1.27))))
(property "Footprint" "panda-standard:SGM41513_YTQF24_4x4_P0.5_EP2.7" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Datasheet" "https://www.sg-micro.com/product/SGM41513" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Description" "C4D-1 mainland SGM41513 switching charger/NVDC; 500mA-safe PSEL policy; EVT only." (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Manufacturer" "SGMICRO" (at {cx} {cy} 0) (hide yes) (effects (font (size 1 1))))
(property "MPN" "SGM41513YTQF24G/TR" (at {cx} {cy} 0) (hide yes) (effects (font (size 1 1))))
(property "LCSC" "C5153778" (at {cx} {cy} 0) (hide yes) (effects (font (size 1 1))))
{pins}
(instances (project "PANDA-STD-CORE-EVT" (path "/{root_uuid}" (reference "U901") (unit 1)))))'''

def glabel(name,x,y,key):
    u=uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d1-u901-label-'+key)
    return f'(global_label "{name}" (shape passive) (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{u}"))'

labels=[
 ('SGM41513_BTST',cx-12.7,cy-10.16,'21'),
 ('SGM41513_REGN',cx-12.7,cy-7.62,'22'),
 ('BQ_PG',cx-12.7,cy-5.08,'3'),
 ('3V3_AON',cx-12.7,cy-2.54,'2'),
 ('BQ_TS',cx-12.7,cy+2.54,'11'),
 ('BQ_QON',cx-12.7,cy+5.08,'12'),
 ('PACK_BAT',cx-12.7,cy+7.62,'13'),
 ('VSYS_RAW',cx-12.7,cy+10.16,'15'),
 ('BQ_STAT',cx+12.7,cy+7.62,'4'),
 ('BQ_INT',cx+12.7,cy+5.08,'7'),
 ('I2C_SDA',cx+12.7,cy+2.54,'6'),
 ('I2C_SCL',cx+12.7,cy,'5'),
 ('BQ_CE',cx+12.7,cy-2.54,'9'),
 ('SGM41513_SW',cx+12.7,cy-5.08,'19'),
 ('SGM41513_PMID',cx+12.7,cy-7.62,'23'),
 ('VBUS_USB',cx+12.7,cy-10.16,'24'),
 ('GND',cx,cy+15.24,'17'),
]
ncs=[
 f'(no_connect (at {cx-2.54:.2f} {cy-15.24:.2f}) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,"thin18-c4d1-u901-nc8")}"))',
 f'(no_connect (at {cx+2.54:.2f} {cy-15.24:.2f}) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,"thin18-c4d1-u901-nc10")}"))',
]
root_end=s.rfind(')')
s=s[:root_end]+' '+inst+' '+' '.join(glabel(*x) for x in labels)+' '+' '.join(ncs)+s[root_end:]

# Reuse legacy charger passives by migrating their net names to SGM functions.
renames={
 '"BQ_BTST"':'"SGM41513_BTST"',
 '"BQ_SW"':'"SGM41513_SW"',
 '"BQ_REGN"':'"SGM41513_REGN"',
 '"BQ_PMID"':'"SGM41513_PMID"',
 '"BQ_TS_BIAS"':'"SGM41513_REGN"',
}
for x,y in renames.items(): s=s.replace(x,y)
SCH.write_text(s)
# Apply the same net migration to every hierarchical schematic so parity remains coherent.
for sp in (DST/REL).glob('*.kicad_sch'):
    if sp == SCH:
        continue
    txt=sp.read_text()
    for x,y in renames.items():
        txt=txt.replace(x,y)
    sp.write_text(txt)

# PCB: remove old U201 copper completely.
p=PCB.read_text()
a,b,_=block_by_ref(p,'footprint','U201')
p=p[:a]+p[b:]
for x,y in renames.items(): p=p.replace(x,y)

# Build U901 exact footprint and assign its nets.
mod=(PLIB/'PandaDomesticPower.pretty/SGM41513_YTQF24_4x4_P0.5_EP2.7.kicad_mod').read_text()
geom=[x for x in top_children(mod) if x.startswith('(pad ') or x.startswith('(fp_rect') or x.startswith('(fp_circle') or x.startswith('(fp_line') or x.startswith('(fp_poly')]
netmap={
 '1':'VBUS_USB','2':'3V3_AON','3':'BQ_PG','4':'BQ_STAT','5':'I2C_SCL','6':'I2C_SDA','7':'BQ_INT',
 '9':'BQ_CE','11':'BQ_TS','12':'BQ_QON','13':'PACK_BAT','14':'PACK_BAT','15':'VSYS_RAW','16':'VSYS_RAW',
 '17':'GND','18':'GND','19':'SGM41513_SW','20':'SGM41513_SW','21':'SGM41513_BTST','22':'SGM41513_REGN',
 '23':'SGM41513_PMID','24':'VBUS_USB','25':'GND',
 '8':'unconnected-(U901-NC-Pad8)','10':'unconnected-(U901-NC-Pad10)'
}
out=[]
for x in geom:
    m=re.match(r'\(pad "([^"]*)"',x)
    if m and m.group(1) in netmap:
        x=x[:-1]+f' (net "{netmap[m.group(1)]}"))'
    out.append(x)
newfp=f'''(footprint "panda-standard:SGM41513_YTQF24_4x4_P0.5_EP2.7" (locked yes) (layer "F.Cu")
(uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d1-u901-fp')}") (at 47.2 6.8)
(property "Reference" "U901" (at 0 -3 0) (layer "F.Fab") (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d1-u901-ref')}") (effects (font (size 0.75 0.75))))
(property "Value" "SGM41513YTQF24G/TR" (at 0 3 0) (layer "F.Fab") (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d1-u901-val')}") (effects (font (size 0.65 0.65))))
(property "Datasheet" "https://www.sg-micro.com/product/SGM41513" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d1-u901-ds')}") (effects (font (size 1 1))))
(property "Description" "C4D-1 mainland SGM41513 switching charger/NVDC; 500mA-safe PSEL policy; EVT only." (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d1-u901-pcb-desc')}") (effects (font (size 1 1))))
(property "Manufacturer" "SGMICRO" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d1-u901-mfr')}") (effects (font (size 1 1))))
(property "MPN" "SGM41513YTQF24G/TR" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d1-u901-mpn')}") (effects (font (size 1 1))))
(property "LCSC" "C5153778" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d1-u901-lcsc')}") (effects (font (size 1 1))))
(attr smd)
{' '.join(out)}
)'''
root_end=p.rfind(')')
p=p[:root_end]+' '+newfp+p[root_end:]
PCB.write_text(p)

# Restore known-good inherited library tables immediately before native checks.
shutil.copy2(SRC/REL/'sym-lib-table',DST/REL/'sym-lib-table')
shutil.copy2(SRC/REL/'fp-lib-table',DST/REL/'fp-lib-table')

# Fresh native checks.
subprocess.run([KICAD,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc.json'),str(SCH)],check=True)
subprocess.run([KICAD,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(SCH)],check=True)
subprocess.run([KICAD,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(DST/'verification/drc.json'),str(PCB)],check=True)

erc=json.load(open(DST/'verification/erc.json')); drc=json.load(open(DST/'verification/drc.json'))
counts={'erc':sum(len(x.get('violations',[])) for x in erc.get('sheets',[])),
        'drc':len(drc.get('violations',[])),'parity':len(drc.get('schematic_parity',[])),
        'open':len(drc.get('unconnected_items',[]))}

root=ET.parse(DST/'verification/netlist.xml').getroot()
pinmap={}
for net in root.findall('nets/net'):
    for node in net.findall('node'):
        if node.get('ref')=='U901': pinmap[node.get('pin')]=net.get('name','')
expected={
 '1':'VBUS_USB','2':'3V3_AON','3':'BQ_PG','4':'BQ_STAT','5':'I2C_SCL','6':'I2C_SDA','7':'BQ_INT',
 '9':'BQ_CE','11':'BQ_TS','12':'BQ_QON','13':'PACK_BAT','14':'PACK_BAT','15':'VSYS_RAW','16':'VSYS_RAW',
 '17':'GND','18':'GND','19':'SGM41513_SW','20':'SGM41513_SW','21':'SGM41513_BTST','22':'SGM41513_REGN',
 '23':'SGM41513_PMID','24':'VBUS_USB','25':'GND'
}
wrong={k:(pinmap.get(k),v) for k,v in expected.items() if pinmap.get(k)!=v}
if wrong: raise SystemExit(f'U901 pin/net mismatch {wrong}')
if counts['erc'] or counts['parity'] or counts['drc']:
    raise SystemExit(f'native checks not clean {counts}')

report={
 'date':'2026-09-29','kind':'C4D-1 additive SGM41513 power redesign',
 'source':'c4d-96x68-power-usb-reserved','legacy_u201':'removed from C4D candidate; preserved only in immutable source candidate',
 'new_ref':'U901','mpn':'SGM41513YTQF24G/TR','lcsc':'C5153778','pinmap':pinmap,
 'native_checks':counts,'pSEL_policy':'direct 3V3_AON high; default-current startup behavior still EVT gate',
 'reused_support_nets':['SGM41513_BTST','SGM41513_SW','SGM41513_REGN','SGM41513_PMID','BQ_TS'],
 'physical_qualification':False,'manufacturing_release':False,'pcb_sha256':hashlib.sha256(PCB.read_bytes()).hexdigest()
}
(DST/'c4d1-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(DST/'README.md').write_text('# Thin18 Compact C4D-1 additive SGM41513\n\nU201 is retired from the board/BOM but retained as a DNP historical schematic reference. U901 is the new SGM41513 charger/NVDC at the reserved power location. All U901 functional pins are checked against the frozen pin-level contract. Physical qualification remains open.\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
