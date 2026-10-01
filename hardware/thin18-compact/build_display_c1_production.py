#!/usr/bin/env python3
from pathlib import Path
import shutil,re,uuid,json,subprocess,argparse,itertools,hashlib

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'c4d20-96x68-production-bom/display/PANDA-EPD0426-SPI-EVT'
DST=ROOT/'display-c1-45x36-production-bom'
ap=argparse.ArgumentParser()
ap.add_argument('--output',type=Path,default=DST)
args=ap.parse_args()
DST=args.output.resolve()
UUID_COUNTER=itertools.count()
def new_uuid():
    return uuid.uuid5(uuid.NAMESPACE_URL,'panda/build_display_c1_production.py/'+str(next(UUID_COUNTER)))

K='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
STEM='PANDA-EPD0426-SPI-EVT'

parts={}
def add(refs,mfr,mpn,lcsc=''):
    for ref in refs: parts[ref]=(mfr,mpn,lcsc)
add(['C1','C2','C3'],'FH (Fenghua Advanced)','0603B105K250NT','C59302')
add(['C4','C5','C6','C7','C8','C9'],'Murata','GRM21BR61E475KA12L','')
add(['C10'],'Murata','GRM21BR71E105KA99L','')
add(['C11','C12','C13'],'Murata','GRM188R71E104KA01D','')
add(['D1','D2','D3'],'onsemi','MBR0530T1G','')
add(['J1'],'Hirose','DF40C-60DP-0.4V(51)','')
add(['J2'],'Hirose','FH12-24S-0.5SH(55)','')
add(['L1'],'Taiyo Yuden','LSXNE3030KKT470MN','')
add(['Q1'],'Nexperia','NX3008NBK,215','')
add(['R1','R2','R3','R4','R5'],'YAGEO','RC0402FR-0722RL','')
add(['R6'],'YAGEO','RC0402FR-07100RL','')
add(['R7','R8','R9','R10','R11','R12'],'UNI-ROYAL','0402WGF1003TCE','C25741')
add(['R13'],'YAGEO','RC0603FR-072R2L','')
add(['R14'],'UNI-ROYAL','0402WGF1002TCE','C25744')
add(['U1','U2','U3'],'Wuxi I-core Elec','AIP74LVC2G17GC363.TR','C3294722')
value_override={r:'AIP74LVC2G17GC363.TR' for r in ['U1','U2','U3']}

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

def replace_prop_value(block,name,value):
    n=f'(property "{name}" "'
    st=block.find(n)
    if st<0:return block,False
    a=st+len(n); b=block.find('"',a)
    return block[:a]+value+block[b:],True

def datasheet_at_layer(block, pcb=False):
    st=block.find('(property "Datasheet" ')
    if st<0:return ('0','0','0','F.Fab')
    en=balanced(block,st); p=block[st:en]
    m=re.search(r'\(at ([^ ]+) ([^ ]+) ([^)]+)\)',p)
    x,y,r=m.groups() if m else ('0','0','0')
    lm=re.search(r'\(layer "([^"]+)"\)',p)
    layer=lm.group(1) if lm else 'F.Fab'
    return x,y,r,layer

def sync_fields(block,ref,pcb=False):
    mfr,mpn,lcsc=parts[ref]
    if ref in value_override:
        block,_=replace_prop_value(block,'Value',value_override[ref])
    x,y,r,layer=datasheet_at_layer(block,pcb)
    for name,val in [('Manufacturer',mfr),('MPN',mpn),('LCSC',lcsc)]:
        st=block.find(f'(property "{name}" ')
        if st>=0:
            block,_=replace_prop_value(block,name,val)
        elif val or name in ('Manufacturer','MPN'):
            if pcb:
                puid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'panda/display-c1/{ref}/{name}'))
                ins=f'(property "{name}" "{val}" (at {x} {y} {r}) (layer "{layer}") (hide yes) (uuid "{puid}") (effects (font (size 1 1))))'
            else:
                ins=f'(property "{name}" "{val}" (at {x} {y} {r}) (hide yes) (effects (font (size 1 1))))'
            ds=block.find('(property "Datasheet" ')
            de=balanced(block,ds)
            block=block[:de]+ins+block[de:]
    return block

if DST.exists(): raise SystemExit('Candidate exists; preserve it and choose --output for a fresh rebuild: '+str(DST))
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('*.kicad_prl','*.lck'))

# Patch schematic instance symbols.
sch=DST/(STEM+'.kicad_sch')
s=sch.read_text(); out=[]; pos=0; seen=set()
while True:
    st=s.find('(symbol ',pos)
    if st<0: out.append(s[pos:]); break
    en=balanced(s,st); blk=s[st:en]; out.append(s[pos:st])
    ref=prop_value(blk,'Reference')
    if ref in parts and '(uuid "' in blk:
        blk=sync_fields(blk,ref,False); seen.add(ref)
    out.append(blk); pos=en
sch.write_text(''.join(out))
if set(parts)-seen: raise SystemExit(f'schematic refs missing: {sorted(set(parts)-seen)}')

# Patch PCB footprint fields, no geometry mutation.
pcb=DST/(STEM+'.kicad_pcb')
s=pcb.read_text(); out=[]; pos=0; seen=set()
while True:
    st=s.find('(footprint ',pos)
    if st<0: out.append(s[pos:]); break
    en=balanced(s,st); blk=s[st:en]; out.append(s[pos:st])
    ref=prop_value(blk,'Reference')
    if ref in parts:
        blk=sync_fields(blk,ref,True); seen.add(ref)
    out.append(blk); pos=en
pcb.write_text(''.join(out))
if set(parts)-seen: raise SystemExit(f'pcb refs missing: {sorted(set(parts)-seen)}')

verify=DST/'verification'; verify.mkdir(exist_ok=True)
subprocess.run([K,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(verify/'drc.json'),str(pcb)],check=True)
subprocess.run([K,'sch','erc','--format','json','--severity-all','--output',str(verify/'erc.json'),str(sch)],check=True)
subprocess.run([K,'sch','export','netlist','--format','kicadxml','--output',str(verify/'netlist.xml'),str(sch)],check=True)
d=json.loads((verify/'drc.json').read_text()); e=json.loads((verify/'erc.json').read_text())
counts={'drc':len(d.get('violations',[])),'open':len(d.get('unconnected_items',[])),'parity':len(d.get('schematic_parity',[])),'erc':sum(len(x.get('violations',[])) for x in e.get('sheets',[]))}
if counts!={'drc':0,'open':0,'parity':0,'erc':0}: raise SystemExit(counts)
(DST/'production-bom-resolution.json').write_text(json.dumps({
 'date':'2026-10-01','candidate':DST.name,'native_checks':counts,
 'domestic_changes':{'U1-U3':'SN74AUP2G17DCKR -> AIP74LVC2G17GC363.TR / Wuxi I-core / C3294722'},
 'retained_blocked':{
  'J1':'Hirose DF40 retained: mating geometry contract',
  'J2':'Hirose FH12 retained: FPC geometry contract',
  'Q1':'Nexperia NX3008 retained: mainland MOSFET VDS/Rds/Qg not qualified',
  'L1':'Taiyo Yuden LSXNE3030 retained: domestic exact magnetic not qualified'
 },
 'manufacturing_release':False
},indent=2)+'\n')
print(json.dumps({'patched_refs':len(parts),'native_checks':counts},indent=2))

(DST/'README.md').write_text('# Display-C1 display board\n\n45 x 36 mm, two copper layers.\nNative checks: '+json.dumps(counts)+'\nU1-U3: AIP74LVC2G17GC363.TR. J1: B.Cu, (23,4) mm, rotation 0 degrees.\nmanufacturing_release=false; physical EVT and actual fit remain open.\n')
(DST/'.gitignore').write_text('*.kicad_prl\n*.lck\n__pycache__/\n')
