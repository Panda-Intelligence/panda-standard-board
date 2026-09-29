#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,shutil,subprocess,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'c4d6-96x68-ns4168'
DST=ROOT/'c4d9-96x68-aip-buffers'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
SCH=DST/REL/(STEM+'.kicad_sch')
DISP=DST/REL/'display-integrated.kicad_sch'
PCB=DST/REL/(STEM+'.kicad_pcb')
LIB=DST/REL/'panda-r6-display.kicad_sym'
K='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
REFS=['U801','U802','U803']

def balanced(text,start):
    dep=0;q=False;esc=False
    for i in range(start,len(text)):
        c=text[i]
        if q:
            if esc:esc=False
            elif c=='\\':esc=True
            elif c=='"':q=False
        else:
            if c=='"':q=True
            elif c=='(':dep+=1
            elif c==')':
                dep-=1
                if dep==0:return i+1
    raise RuntimeError('unterminated')

def block_by_ref(text,kind,ref):
    i=text.index(f'(property "Reference" "{ref}"')
    a=text.rfind('('+kind+' ',0,i); b=balanced(text,a)
    return a,b,text[a:b]

if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()

s=DISP.read_text()

# Clone the proven cached symbol definition, preserving pin positions/types.
old='(symbol "panda-r6-display:SN74AUP2G17DCKR"'
i=s.index(old); j=balanced(s,i); lib=s[i:j]
newlib=lib.replace('panda-r6-display:SN74AUP2G17DCKR','panda-r6-display:AIP74LVC2G17GC363.TR',1)
newlib=newlib.replace('SN74AUP2G17DCKR','AIP74LVC2G17GC363.TR')
newlib=newlib.replace('https://www.ti.com/lit/ds/symlink/sn74aup2g17.pdf','https://www.lcsc.com/product-detail/C3294722.html')
# append new cached library symbol before lib_symbols close
ls=s.index('(lib_symbols '); le=balanced(s,ls)
s=s[:le-1]+' '+newlib+s[le-1:]

for ref in REFS:
    a,b,blk=block_by_ref(s,'symbol',ref)
    blk=blk.replace('(lib_id "panda-r6-display:SN74AUP2G17DCKR")','(lib_id "panda-r6-display:AIP74LVC2G17GC363.TR")',1)
    blk=blk.replace('(property "Value" "SN74AUP2G17DCKR"','(property "Value" "AIP74LVC2G17GC363.TR"',1)
    blk=blk.replace('(property "Datasheet" "https://www.ti.com/lit/ds/symlink/sn74aup2g17.pdf"','(property "Datasheet" "https://www.lcsc.com/product-detail/C3294722.html"',1)
    blk=blk.replace('(property "MPN" "SN74AUP2G17DCKR"','(property "MPN" "AIP74LVC2G17GC363.TR"',1)
    # existing Manufacturer field if present
    if '(property "Manufacturer"' in blk:
        blk=re.sub(r'\(property "Manufacturer" "[^"]*"', '(property "Manufacturer" "Wuxi I-core Elec"', blk, count=1)
    else:
        p=blk.index('(pin "1"')
        blk=blk[:p]+'(property "Manufacturer" "Wuxi I-core Elec" (at 0 0 0) (hide yes) (effects (font (size 1 1)))) (property "LCSC" "C3294722" (at 0 0 0) (hide yes) (effects (font (size 1 1)))) '+blk[p:]
    if '(property "LCSC"' in blk:
        blk=re.sub(r'\(property "LCSC" "[^"]*"', '(property "LCSC" "C3294722"', blk, count=1)
    s=s[:a]+blk+s[b:]
DISP.write_text(s)

# Keep the project symbol library in sync with the schematic cache.
libtxt=LIB.read_text()
oldlib='(symbol "SN74AUP2G17DCKR"'
li=libtxt.index(oldlib); lj=balanced(libtxt,li); srcdef=libtxt[li:lj]
newdef=srcdef.replace('(symbol "SN74AUP2G17DCKR"', '(symbol "AIP74LVC2G17GC363.TR"',1)
newdef=newdef.replace('SN74AUP2G17DCKR','AIP74LVC2G17GC363.TR')
newdef=newdef.replace('https://www.ti.com/lit/ds/symlink/sn74aup2g17.pdf','https://www.lcsc.com/product-detail/C3294722.html')
if '(symbol "AIP74LVC2G17GC363.TR"' not in libtxt:
    # root kicad_symbol_lib closes with a single final ')'
    k=libtxt.rfind(')')
    libtxt=libtxt[:k]+' '+newdef+' '+libtxt[k:]
LIB.write_text(libtxt)

# PCB same footprints/nets/poses; only procurement identity changes.
p=PCB.read_text()
for ref in REFS:
    a,b,blk=block_by_ref(p,'footprint',ref)
    blk=blk.replace('(property "Value" "SN74AUP2G17DCKR"','(property "Value" "AIP74LVC2G17GC363.TR"',1)
    blk=blk.replace('https://www.ti.com/lit/ds/symlink/sn74aup2g17.pdf','https://www.lcsc.com/product-detail/C3294722.html')
    if '(property "Manufacturer"' in blk:
        blk=re.sub(r'\(property "Manufacturer" "[^"]*"', '(property "Manufacturer" "Wuxi I-core Elec"', blk, count=1)
    if '(property "MPN"' in blk:
        blk=re.sub(r'\(property "MPN" "[^"]*"', '(property "MPN" "AIP74LVC2G17GC363.TR"', blk, count=1)
    if '(property "LCSC"' in blk:
        blk=re.sub(r'\(property "LCSC" "[^"]*"', '(property "LCSC" "C3294722"', blk, count=1)
    # Source footprints have MPN but no Manufacturer/LCSC. Add explicit fields so
    # schematic parity can verify procurement identity.
    attr=blk.index('(attr smd)')
    extra=[]
    if '(property "Manufacturer"' not in blk:
        extra.append(f'(property "Manufacturer" "Wuxi I-core Elec" (at 0 0 90) (layer "F.Fab") (hide yes) (uuid "{hashlib.sha256((ref+"-mfr").encode()).hexdigest()[:8]}-0000-4000-8000-000000000000") (effects (font (size 1 1) (thickness 0.15))))')
    if '(property "LCSC"' not in blk:
        extra.append(f'(property "LCSC" "C3294722" (at 0 0 90) (layer "F.Fab") (hide yes) (uuid "{hashlib.sha256((ref+"-lcsc").encode()).hexdigest()[:8]}-0000-4000-8000-000000000000") (effects (font (size 1 1) (thickness 0.15))))')
    if extra:
        blk=blk[:attr]+' '.join(extra)+' '+blk[attr:]
    p=p[:a]+blk+p[b:]
PCB.write_text(p)

subprocess.run([K,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc.json'),str(SCH)],check=True)
subprocess.run([K,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(SCH)],check=True)
subprocess.run([K,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(DST/'verification/drc.json'),str(PCB)],check=True)
erc=json.load(open(DST/'verification/erc.json'));drc=json.load(open(DST/'verification/drc.json'))
counts={'erc':sum(len(x.get('violations',[])) for x in erc.get('sheets',[])),'drc':len(drc.get('violations',[])),'parity':len(drc.get('schematic_parity',[])),'open':len(drc.get('unconnected_items',[]))}
if counts['erc'] or counts['drc'] or counts['parity']: raise SystemExit(f'native checks not clean {counts}')

def sem(path):
    r=ET.parse(path).getroot(); t=[]
    for n in r.findall('nets/net'):
        for x in n.findall('node'): t.append((x.get('ref'),x.get('pin'),n.get('name','')))
    return sorted(t)
a=sem(SRC/'verification/netlist.xml'); b=sem(DST/'verification/netlist.xml')
# Net topology for all pre-existing refs must be identical.
for ref in REFS:
    aa=[x for x in a if x[0]==ref]; bb=[x for x in b if x[0]==ref]
    if aa!=bb: raise SystemExit(f'{ref} topology changed')

root=ET.parse(DST/'verification/netlist.xml').getroot()
vals={c.get('ref'):c.findtext('value') for c in root.findall('components/comp')}
for ref in REFS:
    if vals.get(ref)!='AIP74LVC2G17GC363.TR': raise SystemExit(ref+' value mismatch')
report={
 'date':'2026-09-29','kind':'C4D-9 mainland EPD Schmitt buffer substitution',
 'source':'c4d6-96x68-ns4168',
 'changes':[{'ref':r,'before':'SN74AUP2G17DCKR','after':'AIP74LVC2G17GC363.TR','lcsc':'C3294722'} for r in REFS],
 'topology_preserved':True,'footprint_preserved':'SOT-363_SC-70-6',
 'evidence':['1.65-5.5V','dual Schmitt non-inverting buffer','power-off isolation/IOFF','24mA drive at 3.0V'],
 'native_checks':counts,
 'physical_qualification':['VIH/VIL hysteresis','static ICC vs AUP','power-off leakage','EPD edge/ringing/EMI'],
 'manufacturing_release':False,'pcb_sha256':hashlib.sha256(PCB.read_bytes()).hexdigest()
}
(DST/'c4d9-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(DST/'README.md').write_text('# Thin18 Compact C4D-9 — AIP74LVC2G17 EPD buffers\n\nU801-U803 are changed to Wuxi I-core AIP74LVC2G17GC363.TR / C3294722 using the existing SOT-363 footprints and identical nets. Native ERC/DRC/parity are clean. Threshold/leakage/waveform qualification remains open.\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
