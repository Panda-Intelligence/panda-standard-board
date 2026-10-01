#!/usr/bin/env python3
from pathlib import Path
import json,re,shutil,subprocess,hashlib

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'c4d19-96x68-routing-closed'
DST=ROOT/'c4d20-96x68-production-bom'
K='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'

parts = {
'C201':('FH (Fenghua Advanced)','0603B473K500NT','C285123'),
'C202':('FH (Fenghua Advanced)','0603B105K250NT','C59302'),
'C203':('FH (Fenghua Advanced)','1206B106K250NT','C90538'),
'C204':('FH (Fenghua Advanced)','0603B334K500NT','C188679'),
'C205':('FH (Fenghua Advanced)','0805B475K160NT','C880382'),
'C206':('FH (Fenghua Advanced)','0805B106K100NT','C90544'),
'C207':('FH (Fenghua Advanced)','0805X226M250NT','C129303'),
'C208':('FH (Fenghua Advanced)','0805X226M250NT','C129303'),
'C301':('Seiko Instruments','CPH3225A',''),
'C303':('FH (Fenghua Advanced)','0402B105K100NT','C1526'),
'C304':('CCTC','TCC0402X5R225M100AT','C18164608'),
'C401':('FH (Fenghua Advanced)','0603X226M100NT','C60077'),
'C402':('FH (Fenghua Advanced)','0603X226M100NT','C60077'),
'C403':('FH (Fenghua Advanced)','0603X226M100NT','C60077'),
'C501':('FH (Fenghua Advanced)','0805X226M250NT','C129303'),
'C506':('FH (Fenghua Advanced)','0603B106K100NT',''),
'C513':('FH (Fenghua Advanced)','0603B106K100NT',''),
'D201':('Texas Instruments','TPD4E05U06DQAR',''),
'D202':('Texas Instruments','TPD1E10B06DPYR',''),
'J201':('GCT','USB4500-03-0-A',''),
'J301':('Hirose','DF58-2P-1.2V(21)',''),
'J302':('JST','SM03B-SRSS-TB(LF)(SN)','C160403'),
'J501':('Molex','104031-0811',''),
'J502':('JST','SM02B-SRSS-TB(LF)(SN)','C160402'),
'L401':('Coilcraft','XFL4015-471MEC','C18221164'),
'L402':('Coilcraft','XGL4015-222MEC',''),
'R201':('UNI-ROYAL','0603WAF5601T5E','C23189'),
'R204':('UNI-ROYAL','0603WAF1201T5E','C22765'),
'R508':('UNI-ROYAL','0805W8F0000T5E','C17477'),
'R509':('UNI-ROYAL','0805W8F0000T5E','C17477'),
'R514':('UNI-ROYAL','0805W8F0000T5E','C17477'),
'R515':('UNI-ROYAL','0805W8F0000T5E','C17477'),
'R516':('UNI-ROYAL','0805W8F0000T5E','C17477'),
'R517':('UNI-ROYAL','0603WAF0000T5E','C21189'),
'R518':('UNI-ROYAL','0603WAF0000T5E','C21189'),
'R519':('UNI-ROYAL','0603WAF0000T5E','C21189'),
'R520':('UNI-ROYAL','0603WAF0000T5E','C21189'),
'R521':('UNI-ROYAL','0603WAF0000T5E','C21189'),
'R522':('UNI-ROYAL','0603WAF0000T5E','C21189'),
'R529':('UNI-ROYAL','0402WGF220JTCE','C25092'),
'R530':('UNI-ROYAL','0402WGF220JTCE','C25092'),
'R615':('UNI-ROYAL','0603WAF5231T5E','C23068'),
'R616':('UNI-ROYAL','0603WAF3012T5E','C23000'),
'SW201':('ALPSALPINE','SKSCLCE010','C139799'),
'SW202':('ALPSALPINE','SKSCLCE010','C139799'),
'U302':('Micro Crystal','RV-3028-C7-32.768KHZ-1PPM-TA-QA','C3304278'),
'U402':('Texas Instruments','TPS22916CYFPT','C2680456'),
'U403':('Texas Instruments','TPS22916CYFPT','C2680456'),
'U404':('Texas Instruments','TPS22916CYFPT','C2680456'),
'U405':('Texas Instruments','TPS22916CYFPT','C2680456'),
'C804':('Murata','GRM21BR61E475KA12L',''),
'C805':('Murata','GRM21BR61E475KA12L',''),
'C806':('Murata','GRM21BR61E475KA12L',''),
'C807':('Murata','GRM21BR61E475KA12L',''),
'C808':('Murata','GRM21BR61E475KA12L',''),
'C809':('Murata','GRM21BR61E475KA12L',''),
'C810':('Murata','GRM21BR71E105KA99L',''),
'C811':('Murata','GRM188R71E104KA01D',''),
'C812':('Murata','GRM188R71E104KA01D',''),
'C813':('Murata','GRM188R71E104KA01D',''),
'D801':('onsemi','MBR0530T1G',''),
'D802':('onsemi','MBR0530T1G',''),
'D803':('onsemi','MBR0530T1G',''),
'J802':('Hirose','FH12-24S-0.5SH(55)',''),
'L801':('Taiyo Yuden','LSXNE3030KKT470MN',''),
'Q801':('Nexperia','NX3008NBK,215',''),
'R801':('YAGEO','RC0402FR-0722RL',''),
'R802':('YAGEO','RC0402FR-0722RL',''),
'R803':('YAGEO','RC0402FR-0722RL',''),
'R804':('YAGEO','RC0402FR-0722RL',''),
'R805':('YAGEO','RC0402FR-0722RL',''),
'R806':('YAGEO','RC0402FR-07100RL',''),
'R813':('YAGEO','RC0603FR-072R2L',''),
'TH301':('SEMITEC','103JT-025-600AY',''),
}

def balanced(text,start):
    depth=0; quoted=False; esc=False
    for i in range(start,len(text)):
        ch=text[i]
        if quoted:
            if esc: esc=False
            elif ch=='\\': esc=True
            elif ch=='"': quoted=False
        else:
            if ch=='"': quoted=True
            elif ch=='(': depth+=1
            elif ch==')':
                depth-=1
                if depth==0:return i+1
    raise RuntimeError('unterminated s-expression')

def q(s): return s.replace('\\','\\\\').replace('"','\\"')

def prop(name,value,x,y,r):
    return f'(property "{q(name)}" "{q(value)}" (at {x} {y} {r}) (hide yes) (effects (font (size 1 1))))'

def patch_symbol(block, values):
    manufacturer,mpn,lcsc=values
    dm=block.find('(property "Datasheet" ')
    if dm < 0: raise RuntimeError('Datasheet property missing')
    de=balanced(block,dm)
    dprop=block[dm:de]
    at=re.search(r'\(at ([^ ]+) ([^ ]+) ([^)]+)\)',dprop)
    if not at: raise RuntimeError('Datasheet property has no at')
    x,y,r=at.groups()
    fields={'Manufacturer':manufacturer,'MPN':mpn,'LCSC':lcsc}
    for name,value in fields.items():
        pat=f'(property "{name}" '
        st=block.find(pat)
        if st>=0:
            en=balanced(block,st)
            old=block[st:en]
            old=re.sub(r'^(\(property "'+re.escape(name)+r'" ")[^"]*(")',r'\1'+q(value)+r'\2',old,count=1)
            block=block[:st]+old+block[en:]
        elif value or name in ('Manufacturer','MPN'):
            ins=prop(name,value,x,y,r)
            block=block[:de]+ins+block[de:]
            de += len(ins)
    return block

if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','*.kicad_prl','*.lck'))
seen={}
for sch in DST.rglob('*.kicad_sch'):
    text=sch.read_text()
    pos=0; chunks=[]; changed=False
    while True:
        st=text.find('(symbol ',pos)
        if st<0:
            chunks.append(text[pos:]);break
        en=balanced(text,st)
        block=text[st:en]
        chunks.append(text[pos:st])
        refmatch=re.search(r'\(property "Reference" "([^"]+)"',block)
        ref=refmatch.group(1) if refmatch else None
        if ref in parts and '(uuid "' in block:
            block=patch_symbol(block,parts[ref])
            seen[ref]=str(sch.relative_to(DST))
            changed=True
        chunks.append(block);pos=en
    if changed: sch.write_text(''.join(chunks))

missing=sorted(set(parts)-set(seen))
if missing: raise SystemExit('references not patched: '+','.join(missing))

# KiCad schematic-parity requires custom BOM fields to exist on PCB footprints too.
# Synchronize the same fields without touching footprint pose, pads, tracks, vias or zones.
import uuid
pcb=DST/REL/(STEM+'.kicad_pcb')
pcb_text=pcb.read_text()
pos=0; chunks=[]; pcb_seen=set()
while True:
    st=pcb_text.find('(footprint ',pos)
    if st<0:
        chunks.append(pcb_text[pos:]); break
    en=balanced(pcb_text,st)
    block=pcb_text[st:en]
    chunks.append(pcb_text[pos:st])
    rm=re.search(r'\(property "Reference" "([^"]+)"',block)
    ref=rm.group(1) if rm else None
    if ref in parts:
        manufacturer,mpn,lcsc=parts[ref]
        dm=block.find('(property "Datasheet" ')
        if dm<0: raise RuntimeError(f'{ref}: PCB Datasheet property missing')
        de=balanced(block,dm)
        dprop=block[dm:de]
        at=re.search(r'\(at ([^ ]+) ([^ ]+) ([^)]+)\)',dprop)
        layer=re.search(r'\(layer "([^"]+)"\)',dprop)
        x,y,r=at.groups() if at else ('0','0','0')
        lay=layer.group(1) if layer else 'F.Fab'
        fields={'Manufacturer':manufacturer,'MPN':mpn,'LCSC':lcsc}
        for name,value in fields.items():
            pat=f'(property "{name}" '
            ps=block.find(pat)
            if ps>=0:
                pe=balanced(block,ps)
                oldp=block[ps:pe]
                oldp=re.sub(r'^(\(property "'+re.escape(name)+r'" ")[^"]*(")',r'\1'+q(value)+r'\2',oldp,count=1)
                block=block[:ps]+oldp+block[pe:]
            elif value or name in ('Manufacturer','MPN'):
                puid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'panda-standard-board/{ref}/{name}'))
                ins=(f'(property "{q(name)}" "{q(value)}" (at {x} {y} {r}) '
                     f'(layer "{lay}") (hide yes) (uuid "{puid}") '
                     f'(effects (font (size 1 1))))')
                block=block[:de]+ins+block[de:]
                de += len(ins)
        pcb_seen.add(ref)
    chunks.append(block); pos=en
pcb.write_text(''.join(chunks))
pcb_missing=sorted((set(parts)-{'TH301'})-pcb_seen)
if pcb_missing: raise SystemExit('PCB references not patched: '+','.join(pcb_missing))

verification=DST/'verification'; verification.mkdir()
sch=DST/REL/(STEM+'.kicad_sch')
subprocess.run([K,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(verification/'drc.json'),str(pcb)],check=True)
subprocess.run([K,'sch','erc','--format','json','--severity-all','--output',str(verification/'erc.json'),str(sch)],check=True)
subprocess.run([K,'sch','export','netlist','--format','kicadxml','--output',str(verification/'netlist.xml'),str(sch)],check=True)
d=json.load(open(verification/'drc.json'));e=json.load(open(verification/'erc.json'))
counts={'drc':len(d.get('violations',[])),'open':len(d.get('unconnected_items',[])),'parity':len(d.get('schematic_parity',[])),'erc':sum(len(x.get('violations',[])) for x in e.get('sheets',[]))}
if counts != {'drc':0,'open':0,'parity':0,'erc':0}: raise SystemExit(counts)

evidence={
 'date':'2026-10-01',
 'kind':'C4D-20 production BOM resolution checkpoint',
 'source':SRC.name,
 'native_checks':counts,
 'routing_unchanged': True,
 'routing_unchanged_basis':'C4D-20 builder only edits schematic/footprint BOM properties; no pad/pose/track/via/zone code path.',
 'resolved_refs':parts,
 'selection_notes':{
  'L401':'Coilcraft XFL4015-471MEC: 0.47uH family frozen to exact orderable suffix; physical power/thermal qualification remains open.',
  'L402':'Coilcraft XGL4015-222MEC: 2.2uH exact orderable part selected for >2A saturation-current margin; physical thermal/EMI qualification remains open.',
  'capacitors':'Exact MPNs selected by value/package/voltage class. DC-bias verification remains a physical/qualification gate where applicable.',
  'physical_release':'This checkpoint resolves procurement identity only. Q04-Q12 physical EVT gates remain mandatory.'
 },
 'manufacturing_release':False
}
(DST/'production-bom-resolution.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+'\n')
(DST/'README.md').write_text(
 '# C4D-20 — production BOM checkpoint\n\n'
 'Derived from C4D-19 routing closure. PCB copper is unchanged. Native KiCad: '
 'DRC=0, open=0, parity=0, ERC=0. Previously unresolved populated BOM rows now '
 'carry exact MPNs. Physical EVT Q04-Q12 remains open; manufacturing_release=false.\n'
)
print(json.dumps({'patched':len(seen),'native_checks':counts,'routing_unchanged':evidence['routing_unchanged']},indent=2))
