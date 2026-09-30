#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,shutil,subprocess,uuid,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'c4d4-96x68-qmi8658'
DST=ROOT/'c4d5-96x68-cw2217'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
SCH=DST/REL/(STEM+'.kicad_sch')
PCB=DST/REL/(STEM+'.kicad_pcb')
KICAD='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
SYSFP=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')

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
    return a,balanced(text,a),text[a:balanced(text,a)]

def remove_by_ref(text,kind,ref):
    a,b,_=block_by_ref(text,kind,ref)
    return text[:a]+text[b:]

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
            if dep==2: st=i
        elif c==')':
            if dep==2 and st is not None:
                out.append(text[st:i+1]); st=None
            dep-=1
    return out

def newid(seed):
    return str(uuid.uuid5(uuid.NAMESPACE_URL,'thin18-c4d5-'+seed))

def glabel(name,x,y,key):
    return f'(global_label "{name}" (shape passive) (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{newid("label-"+key)}"))'

def passive_inst(kind,ref,value,footprint,cx,cy,p1,p2,extra_props):
    libid='Device:R' if kind=='R' else 'Device:C'
    pin1=newid(ref+'-pin1'); pin2=newid(ref+'-pin2')
    root_uuid=re.search(r'^\(kicad_sch .*?\(uuid "([^"]+)"\)',SCH.read_text()).group(1)
    props=' '.join(f'(property "{k}" "{v}" (at {cx} {cy} 0) (hide yes) (effects (font (size 1 1))))' for k,v in extra_props.items())
    inst=f'''(symbol (lib_id "{libid}") (at {cx} {cy} 0) (unit 1) (body_style 1)
(exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes) (dnp no) (fields_autoplaced yes)
(uuid "{newid(ref+'-symbol')}")
(property "Reference" "{ref}" (at {cx+3.81} {cy-1.27} 0) (effects (font (size 1.27 1.27)) (justify left)))
(property "Value" "{value}" (at {cx+3.81} {cy+1.27} 0) (effects (font (size 1.27 1.27)) (justify left)))
(property "Footprint" "{footprint}" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Datasheet" "" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Description" "C4D-5 CW2217 support component" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(pin "1" (uuid "{pin1}")) (pin "2" (uuid "{pin2}"))
(instances (project "PANDA-STD-CORE-EVT" (path "/{root_uuid}" (reference "{ref}") (unit 1)))) {props})'''
    labels=glabel(p1,cx,cy-3.81,ref+'-p1')+' '+glabel(p2,cx,cy+3.81,ref+'-p2')
    return inst+' '+labels

# Exact symbol derived from Cellwise/JLC EasyEDA model C5203993.
CW_SYMBOL='''(symbol "CW2217BAAD" (exclude_from_sim no) (in_bom yes) (on_board yes)
(property "Reference" "U" (at 0 12.7 0) (effects (font (size 1.1 1.1))))
(property "Value" "CW2217BAAD" (at 0 10.16 0) (effects (font (size 1.1 1.1))))
(property "Footprint" "panda-standard:CW2217BAAD_DFN12_L4.0_W2.5_P0.4_EP" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
(property "Datasheet" "http://www.cellwise-semi.com/Public/assests/menu/20260416/69e07bdb6c434.pdf" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
(property "Description" "Cellwise CW2217BAAD mainland current-sensing fuel gauge; DFN12; JLC C5203993" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
(property "Manufacturer" "Cellwise" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
(property "MPN" "CW2217BAAD" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
(property "JLCPCB" "C5203993" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
(symbol "CW2217BAAD_0_1" (rectangle (start -10.16 10.16) (end 10.16 -10.16) (stroke (width 0.254) (type default)) (fill (type background))))
(symbol "CW2217BAAD_1_1"
(pin power_in line (at -12.7 7.62 0) (length 2.54) (name "VDD" (effects (font (size 1 1)))) (number "3" (effects (font (size 1 1)))))
(pin input line (at -12.7 5.08 0) (length 2.54) (name "VCELL" (effects (font (size 1 1)))) (number "4" (effects (font (size 1 1)))))
(pin input line (at -12.7 2.54 0) (length 2.54) (name "CSP" (effects (font (size 1 1)))) (number "7" (effects (font (size 1 1)))))
(pin input line (at -12.7 0 0) (length 2.54) (name "CSN" (effects (font (size 1 1)))) (number "8" (effects (font (size 1 1)))))
(pin input line (at -12.7 -2.54 0) (length 2.54) (name "TS" (effects (font (size 1 1)))) (number "9" (effects (font (size 1 1)))))
(pin power_in line (at -12.7 -5.08 0) (length 2.54) (name "VSS" (effects (font (size 1 1)))) (number "6" (effects (font (size 1 1)))))
(pin power_in line (at -12.7 -7.62 0) (length 2.54) (name "PAD" (effects (font (size 1 1)))) (number "13" (effects (font (size 1 1)))))
(pin open_collector line (at 12.7 7.62 180) (length 2.54) (name "INT_N" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
(pin bidirectional line (at 12.7 2.54 180) (length 2.54) (name "SDA" (effects (font (size 1 1)))) (number "10" (effects (font (size 1 1)))))
(pin input line (at 12.7 0 180) (length 2.54) (name "SCL" (effects (font (size 1 1)))) (number "11" (effects (font (size 1 1)))))
(pin no_connect line (at -5.08 12.7 270) (length 2.54) (name "NC" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))
(pin no_connect line (at 0 12.7 270) (length 2.54) (name "NC" (effects (font (size 1 1)))) (number "5" (effects (font (size 1 1)))))
(pin no_connect line (at 5.08 12.7 270) (length 2.54) (name "NC" (effects (font (size 1 1)))) (number "12" (effects (font (size 1 1)))))
))'''

CW_FOOTPRINT='''(footprint "CW2217BAAD_DFN12_L4.0_W2.5_P0.4_EP" (version 20260206) (generator pcbnew)
(layer "F.Cu")
(descr "CW2217BAAD DFN-12 4.0x2.5 P0.4 with EP; geometry transcribed from JLC EasyEDA C5203993")
(tags "DFN-12 CW2217")
(property "Reference" "REF**" (at 0 -3 0) (layer "F.SilkS") (effects (font (size 0.8 0.8))))
(property "Value" "CW2217BAAD" (at 0 3 0) (layer "F.Fab") (effects (font (size 0.8 0.8))))
(property "Datasheet" "http://www.cellwise-semi.com/Public/assests/menu/20260416/69e07bdb6c434.pdf" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))
(property "Description" "Cellwise CW2217BAAD mainland current-sensing fuel gauge; DFN12; C4D-5 EVT" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))
(property "Manufacturer" "Cellwise" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))
(property "MPN" "CW2217BAAD" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))
(property "JLCPCB" "C5203993" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))
(attr smd)
(duplicate_pad_numbers_are_jumpers no)
(fp_rect (start -1.25 -2.0) (end 1.25 2.0) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))
(fp_rect (start -1.75 -2.55) (end 1.75 2.55) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))
(fp_circle (center -1.55 2.15) (end -1.45 2.15) (stroke (width 0.15) (type default)) (fill none) (layer "F.SilkS"))
(pad "1" smd rect (at -1.0 1.975) (size 0.2 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "2" smd rect (at -0.6 1.975) (size 0.2 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "3" smd rect (at -0.2 1.975) (size 0.2 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "4" smd rect (at 0.2 1.975) (size 0.2 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "5" smd rect (at 0.6 1.975) (size 0.2 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "6" smd rect (at 1.0 1.975) (size 0.2 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "7" smd rect (at 1.0 -1.975) (size 0.2 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "8" smd rect (at 0.6 -1.975) (size 0.2 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "9" smd rect (at 0.2 -1.975) (size 0.2 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "10" smd rect (at -0.2 -1.975) (size 0.2 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "11" smd rect (at -0.6 -1.975) (size 0.2 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "12" smd rect (at -1.0 -1.975) (size 0.2 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "13" smd custom (at 0 0) (size 0.2 0.2) (layers "F.Cu" "F.Paste" "F.Mask")
  (options (clearance outline) (anchor rect))
  (primitives
    (gr_poly (pts (xy -1.6505 -1.2703) (xy 1.6515 -1.2703) (xy 1.6515 -1.0163) (xy 1.0165 -1.0163)
                  (xy 1.0165 1.0163) (xy 1.6515 1.0163) (xy 1.6515 1.2703) (xy -1.6505 1.2703)
                  (xy -1.6505 1.0163) (xy -1.0155 1.0163) (xy -1.0155 -1.0163) (xy -1.6505 -1.0163))
      (stroke (width 0) (type default)) (fill yes))
  )
)
)'''

if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()

# Persist exact local library source.
proj_sym=DST/'lib/panda-standard.kicad_sym'
proj_fp=DST/'lib/panda-standard.pretty'
proj_fp.mkdir(parents=True,exist_ok=True)
cwmod=proj_fp/'CW2217BAAD_DFN12_L4.0_W2.5_P0.4_EP.kicad_mod'
cwmod.write_text(CW_FOOTPRINT+'\n')
plib=proj_sym.read_text()
if '(symbol "CW2217BAAD"' not in plib:
    pe=plib.rfind(')')
    proj_sym.write_text(plib[:pe]+' '+CW_SYMBOL+plib[pe:])

# Schematic migration.
s=SCH.read_text()
# Retire legacy U301 and R307 from the product candidate but keep their historic drawings.
for ref in ['U301','R307']:
    a,b,block=block_by_ref(s,'symbol',ref)
    block=block.replace('(in_bom yes)','(in_bom no)',1).replace('(on_board yes)','(on_board no)',1).replace('(in_pos_files yes)','(in_pos_files no)',1).replace('(dnp no)','(dnp yes)',1)
    s=s[:a]+block+s[b:]
# System battery is the shunt's system side now.
s=s.replace('"PACK_BAT"','"BAT_PACKP"')

# R306 becomes an exact mainland current shunt, footprint upgraded to 1206.
a,b,block=block_by_ref(s,'symbol','R306')
block=re.sub(r'\(property "Value" "[^"]+"', '(property "Value" "10m / CW2217 SHUNT"',block,count=1)
block=re.sub(r'\(property "Footprint" "[^"]+"', '(property "Footprint" "Resistor_SMD:R_1206_3216Metric"',block,count=1)
block=re.sub(r'\(property "Datasheet" "[^"]+"', '(property "Datasheet" "https://jlcpcb.com/partdetail/FOJAN-FRM121WFR010TM/C7467248"',block,count=1)
block=re.sub(r'\(property "Description" "[^"]+"', '(property "Description" "FOJAN 10mΩ 1W ±1% ±50ppm 1206 current sense shunt for CW2217"',block,count=1)
# remove old procurement properties
for name in ['Manufacturer','MPN','LCSC','JLCPCB','Tolerance','Power_Rating','Voltage_Rating','ECO_ID','Source_URL','Qualification']:
    block=re.sub(rf' \(property "{name}" ".*?" .*?\) (?=\(property|\(pin|\(instances)', ' ', block, count=1)
pinpos=block.index('(pin "1"')
extra=' '.join([
 '(property "Manufacturer" "FOJAN" (at 0 0 0) (hide yes) (effects (font (size 1 1))))',
 '(property "MPN" "FRM121WFR010TM" (at 0 0 0) (hide yes) (effects (font (size 1 1))))',
 '(property "JLCPCB" "C7467248" (at 0 0 0) (hide yes) (effects (font (size 1 1))))',
 '(property "Tolerance" "1%" (at 0 0 0) (hide yes) (effects (font (size 1 1))))',
 '(property "Power_Rating" "1W" (at 0 0 0) (hide yes) (effects (font (size 1 1))))',
 '(property "Tempco" "50ppm/C" (at 0 0 0) (hide yes) (effects (font (size 1 1))))',
 '(property "ECO_ID" "THIN18-C4D5-CW2217-SHUNT" (at 0 0 0) (hide yes) (effects (font (size 1 1))))',
])
block=block[:pinpos]+extra+' '+block[pinpos:]
s=s[:a]+block+s[b:]

# Inject cached CW symbol into root schematic library.
symdef=CW_SYMBOL.replace('(symbol "CW2217BAAD"', '(symbol "panda-standard:CW2217BAAD"',1)
ls=s.index('(lib_symbols '); le=balanced(s,ls)
s=s[:le-1]+' '+symdef+s[le-1:]

root_uuid=re.search(r'^\(kicad_sch .*?\(uuid "([^"]+)"\)',s).group(1)
cx,cy=320.04,215.90
pins=' '.join(f'(pin "{n}" (uuid "{newid("u903-"+n)}"))' for n in [str(i) for i in range(1,14)])
u903=f'''(symbol (lib_id "panda-standard:CW2217BAAD") (at {cx} {cy} 0) (unit 1) (body_style 1)
(exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes) (dnp no) (fields_autoplaced yes)
(uuid "{newid('u903-symbol')}")
(property "Reference" "U903" (at {cx} {cy-13.97} 0) (effects (font (size 1.27 1.27))))
(property "Value" "CW2217BAAD" (at {cx} {cy-11.43} 0) (effects (font (size 1.27 1.27))))
(property "Footprint" "panda-standard:CW2217BAAD_DFN12_L4.0_W2.5_P0.4_EP" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Datasheet" "http://www.cellwise-semi.com/Public/assests/menu/20260416/69e07bdb6c434.pdf" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Description" "Cellwise CW2217BAAD mainland current-sensing fuel gauge; DFN12; C4D-5 EVT" (at {cx} {cy} 0) (hide yes) (effects (font (size 1.27 1.27))))
(property "Manufacturer" "Cellwise" (at {cx} {cy} 0) (hide yes) (effects (font (size 1 1))))
(property "MPN" "CW2217BAAD" (at {cx} {cy} 0) (hide yes) (effects (font (size 1 1))))
(property "JLCPCB" "C5203993" (at {cx} {cy} 0) (hide yes) (effects (font (size 1 1))))
{pins}
(instances (project "PANDA-STD-CORE-EVT" (path "/{root_uuid}" (reference "U903") (unit 1)))))'''
labels=[
 ('FUEL_VDD',cx-12.7,cy-7.62,'3'),('FUEL_VCELL',cx-12.7,cy-5.08,'4'),
 ('BAT_PACKP',cx-12.7,cy-2.54,'7'),('BAT_CONN_P',cx-12.7,cy,'8'),('BQ_TS',cx-12.7,cy+2.54,'9'),
 ('GND',cx-12.7,cy+5.08,'6'),('GND',cx-12.7,cy+7.62,'13'),
 ('FUEL_GPOUT',cx+12.7,cy-7.62,'1'),('I2C_SDA',cx+12.7,cy-2.54,'10'),('I2C_SCL',cx+12.7,cy,'11')
]
ncs=[
 f'(no_connect (at {cx-5.08:.2f} {cy-12.7:.2f}) (uuid "{newid("u903-nc2")}"))',
 f'(no_connect (at {cx:.2f} {cy-12.7:.2f}) (uuid "{newid("u903-nc5")}"))',
 f'(no_connect (at {cx+5.08:.2f} {cy-12.7:.2f}) (uuid "{newid("u903-nc12")}"))'
]
r903=passive_inst('R','R903','100R / CW2217 VDD','Resistor_SMD:R_0603_1608Metric',269.24,212.09,'BAT_PACKP','FUEL_VDD',
 {'Description':'C4D-5 CW2217 support component','Manufacturer':'FOJAN','MPN':'FRC0603F1000TS','JLCPCB':'C2906981','Tolerance':'1%','Power_Rating':'100mW','ECO_ID':'THIN18-C4D5-CW2217'})
r904=passive_inst('R','R904','100R / CW2217 VCELL','Resistor_SMD:R_0603_1608Metric',284.48,212.09,'BAT_CONN_P','FUEL_VCELL',
 {'Description':'C4D-5 CW2217 support component','Manufacturer':'FOJAN','MPN':'FRC0603F1000TS','JLCPCB':'C2906981','Tolerance':'1%','Power_Rating':'100mW','ECO_ID':'THIN18-C4D5-CW2217'})
c903=passive_inst('C','C903','1u / CW2217 VCELL','Capacitor_SMD:C_0603_1608Metric',299.72,212.09,'FUEL_VCELL','GND',
 {'Description':'C4D-5 CW2217 support component','Manufacturer':'FH (Fenghua Advanced)','MPN':'0603B105K250NT','LCSC':'C59302','Voltage_Rating':'25V','ECO_ID':'THIN18-C4D5-CW2217'})

root_end=s.rfind(')')
s=s[:root_end]+' '+u903+' '+' '.join(glabel(*x) for x in labels)+' '+' '.join(ncs)+' '+r903+' '+r904+' '+c903+s[root_end:]
SCH.write_text(s)
# Rename PACK_BAT in hierarchical sheets too.
for sp in (DST/REL).glob('*.kicad_sch'):
    if sp==SCH: continue
    txt=sp.read_text().replace('"PACK_BAT"','"BAT_PACKP"')
    sp.write_text(txt)

# PCB migration.
p=PCB.read_text().replace('"PACK_BAT"','"BAT_PACKP"')
# Remove old U301 and R307 footprints; replace R306 with standard 1206 at same pose.
for ref in ['U301','R307','R306']:
    p=remove_by_ref(p,'footprint',ref)

def fp_from_mod(mod_path,libname,ref,value,x,y,nets,props,rot=0):
    mod=Path(mod_path).read_text()
    geom=[g for g in top_children(mod) if g.startswith('(pad ') or g.startswith('(fp_rect') or g.startswith('(fp_circle') or g.startswith('(fp_line') or g.startswith('(fp_poly')]
    out=[]
    for g in geom:
        m=re.match(r'\(pad "([^"]*)"',g)
        if m and m.group(1) in nets:
            g=g[:-1]+f' (net "{nets[m.group(1)]}"))'
        out.append(g)
    proptext=' '.join(f'(property "{k}" "{v}" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{newid(ref+"-"+k)}") (effects (font (size 1 1))))' for k,v in props.items())
    return f'''(footprint "{libname}" (locked yes) (layer "F.Cu") (uuid "{newid(ref+'-fp')}") (at {x} {y} {rot})
(property "Reference" "{ref}" (at 0 -2 0) (layer "F.SilkS") (hide yes) (uuid "{newid(ref+'-ref')}") (effects (font (size 0.8 0.8))))
(property "Value" "{value}" (at 0 2 0) (layer "F.Fab") (hide yes) (uuid "{newid(ref+'-val')}") (effects (font (size 0.8 0.8))))
{proptext} (attr smd) {' '.join(out)})'''

# R306 mainland 10m shunt.
r1206=SYSFP/'Resistor_SMD.pretty/R_1206_3216Metric.kicad_mod'
padd=[
 fp_from_mod(r1206,'Resistor_SMD:R_1206_3216Metric','R306','10m / CW2217 SHUNT',36.0,9.25,
             {'1':'BAT_CONN_P','2':'BAT_PACKP'},
             {'Datasheet':'https://jlcpcb.com/partdetail/FOJAN-FRM121WFR010TM/C7467248','Description':'FOJAN 10mΩ 1W ±1% ±50ppm 1206 current sense shunt for CW2217','Manufacturer':'FOJAN','MPN':'FRM121WFR010TM','JLCPCB':'C7467248','Tolerance':'1%','Power_Rating':'1W','Tempco':'50ppm/C','ECO_ID':'THIN18-C4D5-CW2217-SHUNT','Qualification':'10m 1% 1W 50ppm; shunt thermal/accuracy EVT open'}),
]

# CW2217 footprint from controlled model.
mod=CW_FOOTPRINT
geom=[g for g in top_children(mod) if g.startswith('(pad ') or g.startswith('(fp_rect') or g.startswith('(fp_circle') or g.startswith('(fp_line') or g.startswith('(fp_poly')]
netmap={'1':'FUEL_GPOUT','2':'unconnected-(U903-NC-Pad2)','3':'FUEL_VDD','4':'FUEL_VCELL','5':'unconnected-(U903-NC-Pad5)',
        '6':'GND','7':'BAT_PACKP','8':'BAT_CONN_P','9':'BQ_TS','10':'I2C_SDA','11':'I2C_SCL','12':'unconnected-(U903-NC-Pad12)','13':'GND'}
go=[]
for g in geom:
    m=re.match(r'\(pad "([^"]*)"',g)
    if m and m.group(1) in netmap: g=g[:-1]+f' (net "{netmap[m.group(1)]}"))'
    go.append(g)
u903fp=f'''(footprint "panda-standard:CW2217BAAD_DFN12_L4.0_W2.5_P0.4_EP" (locked yes) (layer "F.Cu")
(uuid "{newid('u903-fp')}") (at 42.6 32.65)
(descr "CW2217BAAD DFN-12 4.0x2.5 P0.4 with EP; geometry transcribed from JLC EasyEDA C5203993")
(tags "DFN-12 CW2217")
(property "Reference" "U903" (at 0 -3 0) (layer "F.SilkS") (hide yes) (uuid "{newid('u903-ref')}") (effects (font (size 0.8 0.8))))
(property "Value" "CW2217BAAD" (at 0 3 0) (layer "F.Fab") (uuid "{newid('u903-val')}") (effects (font (size 0.8 0.8))))
(property "Datasheet" "http://www.cellwise-semi.com/Public/assests/menu/20260416/69e07bdb6c434.pdf" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{newid('u903-ds')}") (effects (font (size 1 1))))
(property "Description" "Cellwise CW2217BAAD mainland current-sensing fuel gauge; DFN12; C4D-5 EVT" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{newid('u903-desc')}") (effects (font (size 1 1))))
(property "Manufacturer" "Cellwise" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{newid('u903-mfr')}") (effects (font (size 1 1))))
(property "MPN" "CW2217BAAD" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{newid('u903-mpn')}") (effects (font (size 1 1))))
(property "JLCPCB" "C5203993" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{newid('u903-jlc')}") (effects (font (size 1 1))))
(attr smd) {' '.join(go)})'''
padd.append(u903fp)

# Add two 100R filters and VCELL cap near U903.
r0603=SYSFP/'Resistor_SMD.pretty/R_0603_1608Metric.kicad_mod'
c0603=SYSFP/'Capacitor_SMD.pretty/C_0603_1608Metric.kicad_mod'
padd.append(fp_from_mod(r0603,'Resistor_SMD:R_0603_1608Metric','R903','100R / CW2217 VDD',37.0,31.0,
                        {'1':'BAT_PACKP','2':'FUEL_VDD'},{'Description':'C4D-5 CW2217 support component','Manufacturer':'FOJAN','MPN':'FRC0603F1000TS','JLCPCB':'C2906981','Tolerance':'1%','Power_Rating':'100mW','ECO_ID':'THIN18-C4D5-CW2217'}))
padd.append(fp_from_mod(r0603,'Resistor_SMD:R_0603_1608Metric','R904','100R / CW2217 VCELL',37.0,34.0,
                        {'1':'BAT_CONN_P','2':'FUEL_VCELL'},{'Description':'C4D-5 CW2217 support component','Manufacturer':'FOJAN','MPN':'FRC0603F1000TS','JLCPCB':'C2906981','Tolerance':'1%','Power_Rating':'100mW','ECO_ID':'THIN18-C4D5-CW2217'}))
padd.append(fp_from_mod(c0603,'Capacitor_SMD:C_0603_1608Metric','C903','1u / CW2217 VCELL',48.0,32.5,
                        {'1':'FUEL_VCELL','2':'GND'},{'Description':'C4D-5 CW2217 support component','Manufacturer':'FH (Fenghua Advanced)','MPN':'0603B105K250NT','LCSC':'C59302','Voltage_Rating':'25V','ECO_ID':'THIN18-C4D5-CW2217'}))
root_end=p.rfind(')')
PCB.write_text(p[:root_end]+' '+' '.join(padd)+p[root_end:])

# Fresh native checks.
subprocess.run([KICAD,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc.json'),str(SCH)],check=True)
subprocess.run([KICAD,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(SCH)],check=True)
subprocess.run([KICAD,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(DST/'verification/drc.json'),str(PCB)],check=True)
erc=json.load(open(DST/'verification/erc.json')); drc=json.load(open(DST/'verification/drc.json'))
counts={'erc':sum(len(x.get('violations',[])) for x in erc.get('sheets',[])),'drc':len(drc.get('violations',[])),
        'parity':len(drc.get('schematic_parity',[])),'open':len(drc.get('unconnected_items',[]))}
if counts['erc'] or counts['drc'] or counts['parity']:
    raise SystemExit(f'native checks not clean {counts}')

root=ET.parse(DST/'verification/netlist.xml').getroot()
pinmap={}
for net in root.findall('nets/net'):
    for node in net.findall('node'):
        if node.get('ref')=='U903': pinmap[node.get('pin')]=net.get('name','')
expected={'1':'FUEL_GPOUT','3':'FUEL_VDD','4':'FUEL_VCELL','6':'GND','7':'BAT_PACKP','8':'BAT_CONN_P','9':'BQ_TS','10':'I2C_SDA','11':'I2C_SCL','13':'GND'}
wrong={k:(pinmap.get(k),v) for k,v in expected.items() if pinmap.get(k)!=v}
if wrong: raise SystemExit(f'U903 pin/net mismatch {wrong}')
# R306 must be the only direct path from battery connector positive to system battery positive.
netnodes={}
for net in root.findall('nets/net'):
    netnodes[net.get('name','')]={(n.get('ref'),n.get('pin')) for n in net.findall('node')}
for need in [('R306','1'),('R904','1'),('U903','8')]:
    if need not in netnodes.get('BAT_CONN_P',set()): raise SystemExit(f'BAT_CONN_P missing {need}')
for need in [('R306','2'),('R903','1'),('U903','7'),('U901','13'),('U901','14')]:
    if need not in netnodes.get('BAT_PACKP',set()): raise SystemExit(f'BAT_PACKP missing {need}')

refs=sorted(c.get('ref') for c in root.findall('components/comp'))
tuples=[(n.get('ref'),n.get('pin'),net.get('name','')) for net in root.findall('nets/net') for n in net.findall('node')]
report={
 'date':'2026-09-29','kind':'C4D-5 CW2217BAAD mainland fuel-gauge redesign',
 'source':'c4d4-96x68-qmi8658','new_ref':'U903','mpn':'CW2217BAAD','jlc':'C5203993',
 'legacy':['U301 BQ27427 DNP/off-board','R307 BIN pulldown DNP/off-board'],
 'shunt':{'ref':'R306','mpn':'FRM121WFR010TM','vendor':'FOJAN','jlc':'C7467248','value':'10mΩ','power':'1W','tolerance':'1%','tempco':'50ppm/C',
          'orientation':'CSP=BAT_PACKP system side, CSN=BAT_CONN_P battery side; charge positive, discharge negative'},
 'filters':{'R903':'100R BAT_PACKP->FUEL_VDD','R904':'100R BAT_CONN_P->FUEL_VCELL','C903':'1u FUEL_VCELL->GND','C304':'existing 2.2u FUEL_VDD->GND'},
 'ntc':'U903 TS reuses BQ_TS / TH301 10k B3435 path',
 'pinmap':pinmap,'native_checks':counts,'refs':len(refs),'pin_net_tuples':len(tuples),
 'footprint_source':{'JLC':'C5203993','symbol_uuid':'6efa8843943a419b98789a0afb1bd6fc','footprint_uuid':'500376b4a734461a9805a136657d45d6',
                     'package':'SON-12_L4.0-W2.5-P0.40-BL-EP'},
 'firmware_required':['CW2217 0x64 driver','profile data/FastCali','SOC/current/temp/INT mapping'],
 'physical_qualification':False,'manufacturing_release':False,'pcb_sha256':hashlib.sha256(PCB.read_bytes()).hexdigest()
}
(DST/'c4d5-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(DST/'README.md').write_text('# Thin18 Compact C4D-5 — CW2217BAAD fuel gauge\n\nBQ27427 is retired from the assembled compact candidate. CW2217BAAD / C5203993 is added with a mainland FOJAN 10mΩ 1W high-side shunt and dedicated VDD/VCELL filters. Native ERC/DRC/parity are clean; board remains intentionally unrouted. Physical gauge accuracy and profile qualification remain open.\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
