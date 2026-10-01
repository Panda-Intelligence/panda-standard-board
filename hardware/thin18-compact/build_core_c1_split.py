#!/usr/bin/env python3
from pathlib import Path
import shutil,re,uuid,json,subprocess,argparse,itertools

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'c4d20-96x68-production-bom'
DST=ROOT/'core-c1-96x68-split'
ap=argparse.ArgumentParser()
ap.add_argument('--output',type=Path,default=DST)
args=ap.parse_args()
DST=args.output.resolve()
UUID_COUNTER=itertools.count()
def new_uuid():
    return uuid.uuid5(uuid.NAMESPACE_URL,'panda/build_core_c1_split.py/'+str(next(UUID_COUNTER)))

REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
K='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
KPY='/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'
ADAPTER_REFS=set()
for a,b,prefix in [(801,813,'C'),(801,803,'D'),(801,803,'U'),(801,814,'R')]:
    ADAPTER_REFS.update(f'{prefix}{i}' for i in range(a,b+1))
ADAPTER_REFS.update({'J802','L801','Q801'})
TP_REFS={f'TP80{i}' for i in range(1,7)}
OFFBOARD_REFS=ADAPTER_REFS|TP_REFS

def balanced(text,start):
    depth=0; quoted=False; esc=False
    for i in range(start,len(text)):
        c=text[i]
        if quoted:
            if esc: esc=False
            elif c=='\\': esc=True
            elif c=='"': quoted=False
        else:
            if c=='"': quoted=True
            elif c=='(': depth+=1
            elif c==')':
                depth-=1
                if depth==0:return i+1
    raise RuntimeError('unterminated s-expression')

def prop_value(block,name):
    n=f'(property "{name}" "'
    st=block.find(n)
    if st<0:return None
    a=st+len(n); b=block.find('"',a)
    return block[a:b]

def mark_offboard(block):
    block=re.sub(r'\(in_bom yes\)','(in_bom no)',block,count=1)
    block=re.sub(r'\(on_board yes\)','(on_board no)',block,count=1)
    block=re.sub(r'\(in_pos_files yes\)','(in_pos_files no)',block,count=1)
    block=re.sub(r'\(dnp no\)','(dnp yes)',block,count=1)
    return block

def extract_symbol_definition(s,name):
    needle=f'(symbol "{name}"'
    st=s.find(needle)
    if st<0: raise RuntimeError(f'lib symbol missing {name}')
    return s[st:balanced(s,st)]

def extract_instance_symbol(s,ref):
    needle=f'(property "Reference" "{ref}"'
    i=s.find(needle)
    if i<0: raise RuntimeError(f'instance missing {ref}')
    st=s.rfind('(symbol ',0,i)
    return s[st:balanced(s,st)]

def replace_prop(block,name,value):
    n=f'(property "{name}" "'
    st=block.find(n)
    if st<0:return block
    a=st+len(n); b=block.find('"',a)
    return block[:a]+value+block[b:]

if DST.exists(): raise SystemExit('Candidate exists; preserve it and choose --output for a fresh rebuild: '+str(DST))
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','display','*.kicad_prl','*.lck'))

core= DST/REL
sheet=core/'display-integrated.kicad_sch'
s=sheet.read_text()

# Historical adapter slice remains visible in schematic history but is not on-board/in-BOM.
pos=0; chunks=[]; seen=set()
while True:
    st=s.find('(symbol ',pos)
    if st<0:
        chunks.append(s[pos:]); break
    en=balanced(s,st); blk=s[st:en]
    chunks.append(s[pos:st])
    ref=prop_value(blk,'Reference')
    if ref in OFFBOARD_REFS and '(uuid "' in blk:
        blk=mark_offboard(blk); seen.add(ref)
    chunks.append(blk); pos=en
s=''.join(chunks)
missing=OFFBOARD_REFS-seen
if missing: raise RuntimeError(f'offboard schematic refs missing: {sorted(missing)}')

# Import the standard 60-pin connector library definition and reuse the
# complete, already ERC-clean J1 connector wiring section from Display-C1.
display_s=(ROOT/'display-c1-45x36-production-bom/PANDA-EPD0426-SPI-EVT.kicad_sch').read_text()
libname='Connector_Generic:Conn_02x30_Odd_Even'
if f'(symbol "{libname}"' not in s:
    definition=extract_symbol_definition(display_s,libname)
    ls=s.find('(lib_symbols ')
    ls_end=balanced(s,ls)
    s=s[:ls_end-1]+definition+s[ls_end-1:]

j1_prop=display_s.find('(property "Reference" "J1"')
j1_st=display_s.rfind('(symbol ',0,j1_prop)
j2_prop=display_s.find('(property "Reference" "J2"')
j2_st=display_s.rfind('(symbol ',0,j2_prop)
section=display_s[j1_st:j2_st]
section=re.sub(r'\(uuid "[^"]+"\)',lambda m:f'(uuid "{new_uuid()}")',section)
section=section.replace('(property "Reference" "J1"','(property "Reference" "J601"',1)
section=section.replace('(reference "J1")','(reference "J601")',1)
section=section.replace('DF40C-60DP-0.4V(51)','DF40C-60DS-0.4V(58)')
# Socket is a different purchasable part; do not inherit the plug library ID.
section=replace_prop(section,'LCSC','')
section=section.replace('Connector_Hirose_DF40:Hirose_DF40C-60DP-0.4V_2x30-1MP_P0.4mm',
                        'Connector_Hirose_DF40:Hirose_DF40C-60DS-0.4V_2x30_P0.4mm')
section=section.replace('https://www.hirose.com/en/product/p/CL0684-4003-3-51',
                        'https://www.hirose.com/en/product/series/DF40')
for old,newnet in {
    '"HOST_SCLK"':'"EPD_D0"',
    '"HOST_MOSI"':'"EPD_D1"',
    '"HOST_CS"':'"EPD_D2"',
    '"HOST_DC"':'"EPD_D3"',
    '"HOST_RESET"':'"EPD_D4"',
    '"HOST_BUSY"':'"EPD_D5"',
    '"EPD_3V3"':'"3V3_EPD_LOGIC"',
}.items():
    section=section.replace(old,newnet)

# Core child sheet already uses these as global nets. Convert the imported
# Display-C1 local labels to globals to avoid local/global-name ERC conflicts.
for net in ['EPD_D0','EPD_D1','EPD_D2','EPD_D3','EPD_D4','EPD_D5','GND','3V3_EPD_LOGIC']:
    section=section.replace(f'(label "{net}" ',f'(global_label "{net}" (shape passive) ')

u905=extract_instance_symbol(s,'U905')
im=re.search(r'\(instances \(project "([^"]+)" \(path "([^"]+)" \(reference "U905"\) \(unit 1\)\)\)\)',u905)
if not im: raise RuntimeError('unable to derive child sheet instance path')
project,path=im.groups()
section=re.sub(r'\(instances \(project "[^"]+" \(path "[^"]+" \(reference "J601"\) \(unit 1\)\)\)\)',
               f'(instances (project "{project}" (path "{path}" (reference "J601") (unit 1))))',
               section,count=1)
anchor=s.find('(symbol (lib_id "PandaDomestic:FH34SRJ-6S-0.5SH_50")')
if anchor < 0: raise RuntimeError('J804 symbol anchor missing')
s=s[:anchor]+section+s[anchor:]
sheet.write_text(s)

# PCB text ECO: remove the duplicated adapter slice and inject J601 without pcbnew mutation.
pcb=core/(STEM+'.kicad_pcb')
bs=pcb.read_text()
remove_refs=set(OFFBOARD_REFS)

# Remove selected footprint blocks.
pos=0; chunks=[]; pcb_removed=set()
while True:
    st=bs.find('(footprint ',pos)
    if st<0:
        chunks.append(bs[pos:]); break
    en=balanced(bs,st); blk=bs[st:en]
    chunks.append(bs[pos:st])
    ref=prop_value(blk,'Reference')
    if ref in remove_refs:
        pcb_removed.add(ref)
    else:
        chunks.append(blk)
    pos=en
bs=''.join(chunks)
missing=remove_refs-pcb_removed
if missing: raise RuntimeError(f'PCB refs missing for removal: {sorted(missing)}')

# Remove copper belonging only to the old adapter/panel-side nets.
def remove_items(text, token, predicate):
    pos=0; out=[]; removed=0
    while True:
        st=text.find(token,pos)
        if st<0:
            out.append(text[pos:]); break
        en=balanced(text,st); blk=text[st:en]
        out.append(text[pos:st])
        if predicate(blk):
            removed+=1
        else:
            out.append(blk)
        pos=en
    return ''.join(out),removed

def adapter_copper(blk):
    m=re.search(r'\(net "([^"]+)"\)',blk)
    if not m:return False
    n=m.group(1)
    return (n.startswith('EPD16_') or n.startswith('EPD16_BUF_') or
            n in {'EPD_CKH','EPD_STV','EPD_CKV','EPD_D6','EPD_D7','EPD_STH'})

bs,removed_segments=remove_items(bs,'(segment',adapter_copper)
bs,removed_vias=remove_items(bs,'(via',adapter_copper)

# Build a native board-footprint block from the exact Hirose socket library.
# Keep the library geometry on F.Cu here; after insertion KiCad pcbnew performs
# the native side flip so pads/text/courtyard retain library equivalence.
mod=(DST/'lib/Connector_Hirose_DF40.pretty/Hirose_DF40C-60DS-0.4V_2x30_P0.4mm.kicad_mod').read_text()
mod=mod.replace('(footprint "Hirose_DF40C-60DS-0.4V_2x30_P0.4mm"',
                '(footprint "Connector_Hirose_DF40:Hirose_DF40C-60DS-0.4V_2x30_P0.4mm"',1)
mod=mod.replace('(layer "F.Cu")',
                f'(layer "F.Cu")\n\t(uuid "{new_uuid()}")\n\t(at 61 62)',1)
mod=mod.replace('(property "Reference" "REF**"','(property "Reference" "J601"',1)
mod=mod.replace('(property "Value" "Hirose_DF40C-60DS-0.4V_2x30_P0.4mm"',
                '(property "Value" "DF40C-60DS-0.4V(58)"',1)

# Inject footprint procurement fields.
val_st=mod.find('(property "Value" ')
val_en=balanced(mod,val_st)
extra=(
 f'(property "Datasheet" "https://www.hirose.com/en/product/series/DF40" (at 0 0 0) '
 f'(layer "F.Fab") (hide yes) (uuid "{new_uuid()}") (effects (font (size 1 1))))'
 f'(property "Manufacturer" "Hirose" (at 0 0 0) '
 f'(layer "F.Fab") (hide yes) (uuid "{new_uuid()}") (effects (font (size 1 1))))'
 f'(property "MPN" "DF40C-60DS-0.4V(58)" (at 0 0 0) '
 f'(layer "F.Fab") (hide yes) (uuid "{new_uuid()}") (effects (font (size 1 1))))'
)
mod=mod[:val_en]+extra+mod[val_en:]

padnets={1:'EPD_D0',3:'EPD_D1',5:'EPD_D2',7:'EPD_D3',9:'EPD_D4',11:'EPD_D5',
         35:'3V3_EPD_LOGIC',36:'3V3_EPD_LOGIC'}
for i in range(2,35,2): padnets[i]='GND'
for i in range(55,61): padnets[i]='GND'

# Add net names + deterministic UUIDs to pad blocks.
pos=0; out=[]
while True:
    st=mod.find('(pad "',pos)
    if st<0:
        out.append(mod[pos:]); break
    en=balanced(mod,st); blk=mod[st:en]
    out.append(mod[pos:st])
    m=re.match(r'\(pad "([^"]+)"',blk)
    num=int(m.group(1)) if m and m.group(1).isdigit() else None
    insert=''
    if num in padnets:
        insert+=f'(net "{padnets[num]}")'
    elif num is not None:
        insert+=f'(net "unconnected-(J601-Pin_{num}-Pad{num})")'
    insert+=f'(uuid "{new_uuid()}")'
    blk=blk[:-1]+insert+')'
    out.append(blk); pos=en
mod=''.join(out)

# Insert before first remaining footprint in a temporary stage board.
i=bs.find('(footprint ')
if i<0:
    raise RuntimeError('no insertion point for J601')
stage_text=bs[:i]+mod+'\n\t'+bs[i:]
stage_pcb=DST/'_j601_stage.kicad_pcb'
stage_pcb.write_text(stage_text)

# Flip only J601 in the temporary board using KiCad native geometry handling.
flip_script=DST/'_flip_j601.py'
flip_script.write_text("""import wx
app=wx.App(False)
import pcbnew,sys
p=sys.argv[1]
b=pcbnew.LoadBoard(p)
f=b.FindFootprintByReference('J601')
if f is None:
    raise SystemExit('J601 missing')
f.SetLayerAndFlip(pcbnew.B_Cu)
f.SetOrientationDegrees(0)
pcbnew.SaveBoard(p,b)
""")
subprocess.run([KPY,str(flip_script),str(stage_pcb)],check=True)
flip_script.unlink()

# Extract only the correctly flipped J601 footprint and inject it back into
# the raw source-derived board so no unrelated footprint/copper gets serialized.
flipped=stage_pcb.read_text()
rp=flipped.find('(property "Reference" "J601"')
if rp < 0:
    raise RuntimeError('flipped J601 reference missing')
fst=flipped.rfind('(footprint ',0,rp)
fen=balanced(flipped,fst)
j601_block=flipped[fst:fen]
stage_pcb.unlink()

# Replace the unflipped temporary J601 block in the source-derived board.
rp=stage_text.find('(property "Reference" "J601"')
fst=stage_text.rfind('(footprint ',0,rp)
fen=balanced(stage_text,fst)
bs=stage_text[:fst]+j601_block+stage_text[fen:]
pcb.write_text(bs)

# Replay the reviewed, frozen copper closure without an autorouter dependency.
closure=ROOT/'core-c1-routing-closure.json'
if closure.exists():
    from _core_c1_pcb_patch import apply_closure
    apply_closure(pcb,closure)
from _split_c1_sourcing import apply_sourcing
apply_sourcing(DST, 'Core-C1')
verify=DST/'verification'; verify.mkdir(exist_ok=True)
subprocess.run([K,'sch','erc','--format','json','--severity-all','--output',str(verify/'erc.json'),str(core/(STEM+'.kicad_sch'))],check=True)
subprocess.run([K,'sch','export','netlist','--format','kicadxml','--output',str(verify/'netlist.xml'),str(core/(STEM+'.kicad_sch'))],check=True)
# Fresh builds without a closure are exploratory; reviewed closure builds must be native clean.
subprocess.run([K,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(verify/'drc.json'),str(pcb)],check=True)
d=json.loads((verify/'drc.json').read_text()); e=json.loads((verify/'erc.json').read_text())
counts={'drc':len(d.get('violations',[])),'open':len(d.get('unconnected_items',[])),'parity':len(d.get('schematic_parity',[])),'erc':sum(len(x.get('violations',[])) for x in e.get('sheets',[]))}
if closure.exists() and any(counts.values()):
    raise SystemExit('Frozen closure replay failed native gates: '+str(counts))
(DST/'split-transform-report.json').write_text(json.dumps({
 'date':'2026-10-01','source':SRC.name,'candidate':DST.name,
 'offboard_adapter_refs':sorted(OFFBOARD_REFS),
 'j601':{'mpn':'DF40C-60DS-0.4V(58)','position_mm':[61,62],'layer':'B.Cu','rotation_deg':0,
         'pins':{'1':'EPD_D0/SCLK','3':'EPD_D1/MOSI','5':'EPD_D2/CS','7':'EPD_D3/DC','9':'EPD_D4/RESET','11':'EPD_D5/BUSY','35-36':'3V3_EPD_LOGIC','even2-34+55-60':'GND'}},
 'pcb_eco':{'method':'deterministic KiCad S-expression transform','removed_segments':removed_segments,'removed_vias':removed_vias},
 'native_checks_initial':counts,'manufacturing_release':False
},indent=2)+'\n')
(DST/'README.md').write_text('# Core-C1 split main board\n\n96 x 68 mm, four copper layers.\nNative checks: '+json.dumps(counts)+'\n\nJ601: B.Cu, (61,62) mm, rotation 0 degrees.\nFrozen routing closure replayed: '+str(closure.exists())+'\nmanufacturing_release=false; physical EVT and enclosure/battery Z-stack remain open.\n')
print(json.dumps(counts,indent=2))
