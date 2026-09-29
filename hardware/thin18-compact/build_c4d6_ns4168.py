#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,shutil,subprocess,uuid,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'c4d5-96x68-cw2217'
DST=ROOT/'c4d6-96x68-ns4168'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
SCH=DST/REL/(STEM+'.kicad_sch'); PCB=DST/REL/(STEM+'.kicad_pcb')
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

def remove_by_ref(text,kind,ref):
    a,b,_=block_by_ref(text,kind,ref); return text[:a]+text[b:]

def top_children(text):
    out=[];dep=0;q=False;esc=False;st=None
    for i,c in enumerate(text):
        if q:
            if esc:esc=False
            elif c=='\\':esc=True
            elif c=='"':q=False
            continue
        if c=='"':q=True;continue
        if c=='(':
            dep+=1
            if dep==2:st=i
        elif c==')':
            if dep==2 and st is not None:out.append(text[st:i+1]);st=None
            dep-=1
    return out

def uid(seed): return str(uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d6-'+seed))
def glabel(name,x,y,key):
    return f'(global_label "{name}" (shape passive) (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uid("label-"+key)}"))'

NS_SYMBOL='''(symbol "NS4168" (exclude_from_sim no) (in_bom yes) (on_board yes)
(property "Reference" "U" (at 0 11.43 0) (effects (font (size 1.1 1.1))))
(property "Value" "NS4168" (at 0 8.89 0) (effects (font (size 1.1 1.1))))
(property "Footprint" "panda-standard:NS4168_ESOP8_EP_L4.9_W3.9_P1.27" (at 0 0 0) (hide yes) (effects (font (size 1 1))))
(property "Datasheet" "https://www.lcsc.com/product-detail/C910588.html" (at 0 0 0) (hide yes) (effects (font (size 1 1))))
(property "Description" "Nsiway NS4168 mainland I2S mono Class-D audio power amplifier; ESOP8-EP; LCSC C910588" (at 0 0 0) (hide yes) (effects (font (size 1 1))))
(property "Manufacturer" "Shenzhen Nsiway Tech" (at 0 0 0) (hide yes) (effects (font (size 1 1))))
(property "MPN" "NS4168" (at 0 0 0) (hide yes) (effects (font (size 1 1))))
(property "LCSC" "C910588" (at 0 0 0) (hide yes) (effects (font (size 1 1))))
(symbol "NS4168_0_1" (rectangle (start -8.89 8.89) (end 8.89 -8.89) (stroke (width 0.254) (type default)) (fill (type background))))
(symbol "NS4168_1_1"
(pin input line (at -11.43 6.35 0) (length 2.54) (name "CTRL" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
(pin input line (at -11.43 3.81 0) (length 2.54) (name "LRCLK" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))
(pin input line (at -11.43 1.27 0) (length 2.54) (name "BCLK" (effects (font (size 1 1)))) (number "3" (effects (font (size 1 1)))))
(pin input line (at -11.43 -1.27 0) (length 2.54) (name "SDATA" (effects (font (size 1 1)))) (number "4" (effects (font (size 1 1)))))
(pin output line (at 11.43 -3.81 180) (length 2.54) (name "VON" (effects (font (size 1 1)))) (number "5" (effects (font (size 1 1)))))
(pin power_in line (at 0 11.43 270) (length 2.54) (name "VDD" (effects (font (size 1 1)))) (number "6" (effects (font (size 1 1)))))
(pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1 1)))) (number "7" (effects (font (size 1 1)))))
(pin output line (at 11.43 3.81 180) (length 2.54) (name "VOP" (effects (font (size 1 1)))) (number "8" (effects (font (size 1 1)))))
(pin power_in line (at 3.81 -11.43 90) (length 2.54) (name "EP" (effects (font (size 1 1)))) (number "9" (effects (font (size 1 1)))))
))'''

NS_FP='''(footprint "NS4168_ESOP8_EP_L4.9_W3.9_P1.27" (version 20260206) (generator pcbnew)
(layer "F.Cu")
(descr "NS4168 ESOP8-EP 3.9x4.9 P1.27; geometry transcribed from public EasyEDA C910588")
(tags "ESOP-8 NS4168")
(property "Reference" "REF**" (at 0 -4.2 0) (layer "F.SilkS") (effects (font (size 0.8 0.8))))
(property "Value" "NS4168" (at 0 4.2 0) (layer "F.Fab") (effects (font (size 0.8 0.8))))
(property "Datasheet" "https://www.lcsc.com/product-detail/C910588.html" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))
(property "Description" "Nsiway NS4168 mainland I2S mono Class-D audio power amplifier; ESOP8-EP; LCSC C910588" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))
(property "Manufacturer" "Shenzhen Nsiway Tech" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))
(property "MPN" "NS4168" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))
(property "LCSC" "C910588" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))
(attr smd)
(duplicate_pad_numbers_are_jumpers no)
(fp_rect (start -1.95 -2.45) (end 1.95 2.45) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))
(fp_rect (start -3.35 -3.55) (end 3.35 3.55) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))
(pad "1" smd rect (at -1.905 2.9083) (size 0.6 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "2" smd rect (at -0.635 2.9083) (size 0.6 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "3" smd rect (at 0.635 2.9083) (size 0.6 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "4" smd rect (at 1.905 2.9083) (size 0.6 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "5" smd rect (at 1.905 -2.9083) (size 0.6 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "6" smd rect (at 0.635 -2.9083) (size 0.6 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "7" smd rect (at -0.635 -2.9083) (size 0.6 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "8" smd rect (at -1.905 -2.9083) (size 0.6 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "9" smd rect (at 0 0) (size 3.3 2.4) (layers "F.Cu" "F.Paste" "F.Mask"))
)'''

if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()
proj_sym=DST/'lib/panda-standard.kicad_sym'; proj_fp=DST/'lib/panda-standard.pretty'; proj_fp.mkdir(parents=True,exist_ok=True)
(proj_fp/'NS4168_ESOP8_EP_L4.9_W3.9_P1.27.kicad_mod').write_text(NS_FP+'\n')
plib=proj_sym.read_text()
if '(symbol "NS4168"' not in plib:
    pe=plib.rfind(')'); proj_sym.write_text(plib[:pe]+' '+NS_SYMBOL+plib[pe:])

# Schematic: retain the legacy audio symbols as explicit DNP/off-board references so
# their surrounding wires/labels remain well-formed for ERC, but neutralize the
# obsolete amplifier output pins in the cached symbol definition.
s=SCH.read_text()
for ref in ['U502','R503','R504','R505','R506']:
    a,b,block=block_by_ref(s,'symbol',ref)
    block=block.replace('(in_bom yes)','(in_bom no)',1).replace('(on_board yes)','(on_board no)',1).replace('(in_pos_files yes)','(in_pos_files no)',1).replace('(dnp no)','(dnp yes)',1)
    s=s[:a]+block+s[b:]

# KiCad ERC evaluates DNP symbol pin electrical types. The retired MAX98357A
# shares SPK_P/SPK_N with U904, so mark only its cached OUTP/OUTN pins passive.
lib_id='(symbol "panda-standard:MAX98357AETE+T"'
li=s.index(lib_id)
le=balanced(s,li)
lib=s[li:le]
for pin,name in [('9','OUTP'),('10','OUTN')]:
    pat=rf'\(pin output line (?=\(at [^\)]*\) \(length [^\)]*\) \(name "{name}")'
    lib,n=re.subn(pat,'(pin passive line ',lib,count=1)
    if n != 1: raise SystemExit(f'failed to neutralize legacy U502 pin {pin}/{name}')
s=s[:li]+lib+s[le:]

symdef=NS_SYMBOL.replace('(symbol "NS4168"', '(symbol "panda-standard:NS4168"',1)
ls=s.index('(lib_symbols '); le=balanced(s,ls); s=s[:le-1]+' '+symdef+s[le-1:]
root_uuid=re.search(r'^\(kicad_sch .*?\(uuid "([^"]+)"\)',s).group(1)
cx,cy=220.98,213.36
pins=' '.join(f'(pin "{n}" (uuid "{uid("u904-"+n)}"))' for n in [str(i) for i in range(1,10)])
u904=f'''(symbol (lib_id "panda-standard:NS4168") (at {cx} {cy} 0) (unit 1) (body_style 1)
(exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes) (dnp no) (fields_autoplaced yes)
(uuid "{uid('u904-symbol')}")
(property "Reference" "U904" (at {cx} {cy-12.7} 0) (effects (font (size 1.27 1.27))))
(property "Value" "NS4168" (at {cx} {cy-10.16} 0) (effects (font (size 1.27 1.27))))
(property "Footprint" "panda-standard:NS4168_ESOP8_EP_L4.9_W3.9_P1.27" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Datasheet" "https://www.lcsc.com/product-detail/C910588.html" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Description" "Nsiway NS4168 mainland I2S mono Class-D audio power amplifier; ESOP8-EP; LCSC C910588" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Manufacturer" "Shenzhen Nsiway Tech" (at {cx} {cy} 0) (hide yes) (effects (font (size 1 1))))
(property "MPN" "NS4168" (at {cx} {cy} 0) (hide yes) (effects (font (size 1 1))))
(property "LCSC" "C910588" (at {cx} {cy} 0) (hide yes) (effects (font (size 1 1))))
{pins}
(instances (project "PANDA-STD-CORE-EVT" (path "/{root_uuid}" (reference "U904") (unit 1)))))'''
labels=[
 ('VSYS_AUDIO',cx-11.43,cy-6.35,'1'),('I2S_LRCLK',cx-11.43,cy-3.81,'2'),('I2S_BCLK',cx-11.43,cy-1.27,'3'),('I2S_DIN',cx-11.43,cy+1.27,'4'),
 ('SPK_N',cx+11.43,cy+3.81,'5'),('VSYS_AUDIO',cx,cy-11.43,'6'),('GND',cx,cy+11.43,'7'),('SPK_P',cx+11.43,cy-3.81,'8'),('GND',cx+3.81,cy+11.43,'9')
]
end=s.rfind(')'); SCH.write_text(s[:end]+' '+u904+' '+' '.join(glabel(*x) for x in labels)+s[end:])

# PCB: remove old amp/config network.
p=PCB.read_text()
for ref in ['U502','R503','R504','R505','R506']:
    p=remove_by_ref(p,'footprint',ref)

# Add NS4168 exact footprint at collision-free location.
mod=NS_FP
geom=[g for g in top_children(mod) if g.startswith('(pad ') or g.startswith('(fp_rect') or g.startswith('(fp_circle') or g.startswith('(fp_line') or g.startswith('(fp_poly')]
netmap={'1':'VSYS_AUDIO','2':'I2S_LRCLK','3':'I2S_BCLK','4':'I2S_DIN','5':'SPK_N','6':'VSYS_AUDIO','7':'GND','8':'SPK_P','9':'GND'}
go=[]
for g in geom:
    m=re.match(r'\(pad "([^"]*)"',g)
    if m and m.group(1) in netmap:g=g[:-1]+f' (net "{netmap[m.group(1)]}"))'
    go.append(g)
u904fp=f'''(footprint "panda-standard:NS4168_ESOP8_EP_L4.9_W3.9_P1.27" (locked yes) (layer "F.Cu")
(uuid "{uid('u904-fp')}") (at 13.75 33.0)
(descr "NS4168 ESOP8-EP 3.9x4.9 P1.27; geometry transcribed from public EasyEDA C910588")
(tags "ESOP-8 NS4168")
(property "Reference" "U904" (at 0 -4.2 0) (layer "F.SilkS") (hide yes) (uuid "{uid('u904-ref')}") (effects (font (size 0.8 0.8))))
(property "Value" "NS4168" (at 0 4.2 0) (layer "F.Fab") (uuid "{uid('u904-val')}") (effects (font (size 0.8 0.8))))
(property "Datasheet" "https://www.lcsc.com/product-detail/C910588.html" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uid('u904-ds')}") (effects (font (size 1 1))))
(property "Description" "Nsiway NS4168 mainland I2S mono Class-D audio power amplifier; ESOP8-EP; LCSC C910588" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uid('u904-desc')}") (effects (font (size 1 1))))
(property "Manufacturer" "Shenzhen Nsiway Tech" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uid('u904-mfr')}") (effects (font (size 1 1))))
(property "MPN" "NS4168" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uid('u904-mpn')}") (effects (font (size 1 1))))
(property "LCSC" "C910588" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uid('u904-lcsc')}") (effects (font (size 1 1))))
(attr smd) {' '.join(go)})'''
end=p.rfind(')'); PCB.write_text(p[:end]+' '+u904fp+p[end:])

subprocess.run([KICAD,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc.json'),str(SCH)],check=True)
subprocess.run([KICAD,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(SCH)],check=True)
subprocess.run([KICAD,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(DST/'verification/drc.json'),str(PCB)],check=True)
erc=json.load(open(DST/'verification/erc.json'));drc=json.load(open(DST/'verification/drc.json'))
counts={'erc':sum(len(x.get('violations',[])) for x in erc.get('sheets',[])),'drc':len(drc.get('violations',[])),'parity':len(drc.get('schematic_parity',[])),'open':len(drc.get('unconnected_items',[]))}
if counts['erc'] or counts['drc'] or counts['parity']: raise SystemExit(f'native checks not clean {counts}')

root=ET.parse(DST/'verification/netlist.xml').getroot(); pinmap={}
for net in root.findall('nets/net'):
    for node in net.findall('node'):
        if node.get('ref')=='U904':pinmap[node.get('pin')]=net.get('name','')
expected={'1':'VSYS_AUDIO','2':'I2S_LRCLK','3':'I2S_BCLK','4':'I2S_DIN','5':'SPK_N','6':'VSYS_AUDIO','7':'GND','8':'SPK_P','9':'GND'}
wrong={k:(pinmap.get(k),v) for k,v in expected.items() if pinmap.get(k)!=v}
if wrong:raise SystemExit(f'U904 pin/net mismatch {wrong}')
refs=sorted(c.get('ref') for c in root.findall('components/comp'))
tuples=[(n.get('ref'),n.get('pin'),net.get('name','')) for net in root.findall('nets/net') for n in net.findall('node')]
report={
 'date':'2026-09-29','kind':'C4D-6 NS4168 mainland audio redesign','source':'c4d5-96x68-cw2217',
 'new_ref':'U904','mpn':'NS4168','lcsc':'C910588','package':'ESOP-8-EP(3.9x4.9x1.27)',
 'retired':['U502 MAX98357A','R503 SD_MODE pullup','R504-R506 GAIN network'],
 'retained':['C505/C506 VSYS_AUDIO decoupling','U405/R507 switched audio power domain','J502 speaker connector'],
 'ctrl_policy':'CTRL=VSYS_AUDIO -> enabled/right-channel while audio domain powered; U405 power-off provides hard shutdown',
 'firmware_gate':'I2S stream must provide valid right-channel audio or duplicate mono to both channels',
 'pinmap':pinmap,'native_checks':counts,'refs':len(refs),'pin_net_tuples':len(tuples),
 'physical_qualification':['4/8ohm output power','idle current','pop/click','speaker polarity','thermal','EMI'],
 'physical_qualification_complete':False,'manufacturing_release':False,'pcb_sha256':hashlib.sha256(PCB.read_bytes()).hexdigest()
}
(DST/'c4d6-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(DST/'README.md').write_text('# Thin18 Compact C4D-6 — NS4168 audio\n\nMAX98357A and its SD/GAIN configuration network are retired. NS4168 / C910588 is added as the mainland I2S mono Class-D amplifier. Fresh native ERC/DRC/parity are clean; board remains intentionally unrouted. Audio/thermal/EMI qualification remains open.\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
