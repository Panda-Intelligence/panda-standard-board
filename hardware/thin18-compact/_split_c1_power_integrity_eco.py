"""Deterministic Split-C1 PG/PSEL ECO; no board outline or interface changes.

The native candidate must pass fresh DRC/ERC/parity before adoption. This is not
physical qualification, an assembly authorization, or USB compliance approval.
"""
from pathlib import Path
import json
import re
import subprocess
import uuid
from _split_c1_common import ROOT, REL, STEM, kicad_python
from _split_c1_sourcing import blocks, property_value
from _split_c1_domestic_eco import set_prop

ECO = 'SPLIT-C1-POWER-INTEGRITY-01'
MPN = 'SGM809B-TXN3LG/TR'
NAME = 'SGM809B_TXN3LG_TR'
FP_NAME = 'SGM809B_SOT23_TX00031'
FP = 'panda-standard:' + FP_NAME
DOC = 'https://www.sg-micro.com/rect/assets/50d03578-1421-4ff6-a32f-020bee34d824/SGM803B_SGM809B_SGM810B.pdf'
DESCRIPTION = 'SGMICRO 3.08V AON status monitor; push-pull active-low nRESET drives PG_3V3_MAIN. Pin1GND/2nRESET/3VCC. Not a hard MCU reset or guaranteed 3.0V brownout protector. Supply, timing, temperature and board EVT remain unqualified.'
NEW_VALUES = {'R201':'5.6k / PSEL low leg', 'R204':'1.2k / REGN to PSEL', 'C204':'330n / U906 bypass'}
NEW_DESCRIPTIONS = {
 'R201':'FH RS-03K5601FT 5.6k 1% lower leg from SGM41513_PSEL to GND; reuses exact domestic part. Not an analog ILIM resistor.',
 'R204':'FH RS-03K1201FT 1.2k 1% upper leg from SGM41513_REGN to SGM41513_PSEL. REGN powers before input-source detection; 500mA nominal reset selection, not a hard firmware-independent current ceiling.',
 'C204':'FH 0603B334K500NT 330nF 50V X7R local 3V3_AON/GND bypass for U906; exact prior part reused, no PSEL timing capacitor.'}
PADS = {'1':('GND','power_in'), '2':('PG_3V3_MAIN','output'), '3':('3V3_AON','power_in')}

def uid(tag):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'panda/split-c1/power-integrity/'+tag))


def supervisor_symbol(qualified=False):
    name = 'panda-standard:'+NAME if qualified else NAME
    props = {'Reference':'U','Value':MPN,'Footprint':FP,'Datasheet':DOC,'Description':DESCRIPTION}
    s = '(symbol '+json.dumps(name)+' (pin_names (offset 0.508)) (in_bom yes) (on_board yes)\n'
    for i,(k,v) in enumerate(props.items()):
        s += '(property '+json.dumps(k)+' '+json.dumps(v)+' (at 0 '+str(8-i*2)+' 0) (effects (font (size 1.27 1.27))))\n'
    s += '(symbol "'+NAME+'_0_1" (rectangle (start -6.35 5.08) (end 6.35 -5.08) (stroke (width 0.254) (type default)) (fill (type background))))\n'
    s += '(symbol "'+NAME+'_1_1"\n'
    for number,typ,label,x,y,angle in [('1','power_in','GND',-10.16,-2.54,0),('3','power_in','VCC',-10.16,2.54,0),('2','output','nRESET',10.16,0,180)]:
        s += f'(pin {typ} line (at {x} {y} {angle}) (length 3.81) (name "{label}" (effects (font (size 1.27 1.27)))) (number "{number}" (effects (font (size 1.27 1.27)))))\n'
    return s+'))\n'


def supervisor_footprint():
    s = f'''(footprint "{FP_NAME}" (version 20241229) (generator "pcbnew") (layer "F.Cu")
 (descr "SGMICRO SOT-23 TX00031.001,0.76mm square lands,2.29mm row pitch,1.90mm split pitch")
 (property "Reference" "REF**" (at 0 -2.1 0) (layer "F.Fab") (hide yes) (effects (font (size 0.6 0.6) (thickness 0.1))))
 (property "Value" "{MPN}" (at 0 2.1 0) (layer "F.Fab") (hide yes) (effects (font (size 0.6 0.6) (thickness 0.1))))
 (attr smd)
 (fp_rect (start -0.70 -1.52) (end 0.70 1.52) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))
 (fp_line (start -0.70 -1.15) (end -0.33 -1.52) (stroke (width 0.1) (type solid)) (layer "F.Fab"))
 (fp_rect (start -1.775 -1.77) (end 1.775 1.77) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))
 (pad "1" smd rect (at -1.145 -0.95) (size 0.76 0.76) (layers "F.Cu" "F.Paste" "F.Mask"))
 (pad "2" smd rect (at -1.145 0.95) (size 0.76 0.76) (layers "F.Cu" "F.Paste" "F.Mask"))
 (pad "3" smd rect (at 1.145 0) (size 0.76 0.76) (layers "F.Cu" "F.Paste" "F.Mask"))
 (embedded_fonts no))'''
    return s+'\n'


def board_zones(text):
    footprints=[(a,b) for a,b,f in blocks(text,r'\(footprint\s')]
    return [(a,b,z) for a,b,z in blocks(text,r'\(zone\s')
            if not any(left<=a<right for left,right in footprints)]


def refill_zones(pcb):
    import pcbnew as P
    import tempfile
    pcb=Path(pcb);original=pcb.read_text();b=P.LoadBoard(str(pcb))
    b.BuildConnectivity()
    for z in b.Zones():z.SetNeedRefill(True)
    P.ZONE_FILLER(b).Fill(b.Zones())
    with tempfile.TemporaryDirectory(prefix='split-c1-power-refill-') as temp:
        native=Path(temp)/'native.kicad_pcb';P.SaveBoard(str(native),b);fresh=board_zones(native.read_text())
    previous=board_zones(original)
    if len(previous)!=len(fresh):raise ValueError('Board-zone inventory changed')
    for (a,b,z),(c,d,replacement) in reversed(list(zip(previous,fresh))):original=original[:a]+replacement+original[b:]
    pcb.write_text(original)


def apply_structure(candidate):
    candidate = Path(candidate); folder = candidate/REL
    pcb = folder/(STEM+'.kicad_pcb'); sch = folder/(STEM+'.kicad_sch')
    text = sch.read_text()
    if '(reference "U906")' in text:
        raise ValueError('Power ECO is already applied; refusing a second application')
    labels = {'5d321a87-7e70-43c1-9c12-20d6e1ca1202':('BQ_ILIM_RC','SGM41513_REGN'),
              '5e321a87-7e70-43c1-9c12-20d6e1ca1201':('BQ_ILIM_RC','3V3_AON'),
              '95191a35-fd75-5671-a507-d346336f00d9':('3V3_AON','SGM41513_PSEL')}
    seen=set()
    for a,b,s in reversed(list(blocks(text,r'\(global_label\s'))):
        for identity,(old,new) in labels.items():
            if identity in s:
                if not s.startswith('(global_label '+json.dumps(old)):raise ValueError('Label predecessor mismatch')
                s=s.replace(json.dumps(old),json.dumps(new),1);seen.add(identity)
        text=text[:a]+s+text[b:]
    if seen!=set(labels):raise ValueError('Missing reviewed PSEL/bypass labels')
    text=text.replace('"BQ_ILIM"','"SGM41513_PSEL"')
    for a,b,s in reversed(list(blocks(text,r'\(symbol\s+\(lib_id\s'))):
        ref=property_value(s,'Reference')
        if ref in NEW_VALUES:
            s=set_prop(s,'Value',NEW_VALUES[ref]);s=set_prop(s,'Description',NEW_DESCRIPTIONS[ref])
            if ref=='C204':s=set_prop(s,'Datasheet','https://www.fhcomp.com/en/product_info/?prod_code=0603B334K500NT')
        elif ref=='U901':
            s=set_prop(s,'Description','SGM41513 non-A/non-D. PSEL uses REGN/R204/R201 before AON starts. Reset nominal input selection 500mA; host writes may override. No PD/OTG; current, NTC and USB qualification remain open.')
        text=text[:a]+s+text[b:]
    la,lb,lib=next(blocks(text,r'\(lib_symbols\s'))
    text=text[:lb-1]+supervisor_symbol(True)+text[lb-1:]
    root_id=re.search(r'\(uuid\s+"([^"]+)"',text).group(1)
    x,y=99.06,149.86
    inst=f'(symbol (lib_id "panda-standard:{NAME}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid("U906-instance")}")\n'
    fields={'Reference':'U906','Value':MPN,'Footprint':FP,'Datasheet':DOC,'Description':DESCRIPTION,'Manufacturer':'SGMICRO','MPN':MPN,'LCSC':'C699619'}
    for k,v in fields.items():
        yy=y-8 if k=='Reference' else y-6 if k=='Value' else y
        hide='' if k in ['Reference','Value'] else '(hide yes) '
        inst+=f'(property {json.dumps(k)} {json.dumps(v)} (at {x} {yy} 0) {hide}(effects (font (size 1.0 1.0))))\n'
    for n in ['1','2','3']:inst+=f'(pin "{n}" (uuid "{uid("U906-pin-"+n)}"))\n'
    inst+=f'(instances (project "{STEM}" (path "/{root_id}" (reference "U906") (unit 1)))))\n'
    for net,px,py,orientation in [('3V3_AON',x-10.16,y-2.54,0),('GND',x-10.16,y+2.54,0),('PG_3V3_MAIN',x+10.16,y,180)]:
        justify='left' if orientation==0 else 'right'
        inst+=f'(global_label "{net}" (shape passive) (at {px:.6f} {py:.6f} {orientation}) (effects (font (size 1.0 1.0)) (justify {justify} bottom)) (uuid "{uid("label-"+net)}"))\n'
    e=text.rfind(')');text=text[:e]+inst+text[e:];sch.write_text(text)
    library=candidate/'lib/panda-standard.kicad_sym';s=library.read_text();e=s.rfind(')');library.write_text(s[:e]+supervisor_symbol()+s[e:])
    (candidate/'lib/panda-standard.pretty'/ (FP_NAME+'.kicad_mod')).write_text(supervisor_footprint())
    text=pcb.read_text()
    remove={'e001293c-55cb-4c51-9201-9c6900b24690','fd8a115f-6382-461a-96b0-14db5a54b48c'}
    for a,b,s in reversed(list(blocks(text,r'\((?:segment|via)\s'))):
        if any(identity in s for identity in remove) or '(net "BQ_ILIM_RC")' in s:
            text=text[:a]+text[b:]
    text=text.replace('"BQ_ILIM"','"SGM41513_PSEL"')
    for a,b,f in reversed(list(blocks(text,r'\(footprint\s'))):
        ref=property_value(f,'Reference')
        if ref in NEW_VALUES:
            f=set_prop(f,'Value',NEW_VALUES[ref]);f=set_prop(f,'Description',NEW_DESCRIPTIONS[ref])
        if ref=='R204':f=f.replace('"BQ_ILIM_RC"','"SGM41513_REGN"')
        if ref=='C204':
            f=f.replace('"BQ_ILIM_RC"','"3V3_AON"');f=set_prop(f,'Datasheet','https://www.fhcomp.com/en/product_info/?prod_code=0603B334K500NT')
        if ref=='U901':
            for c,d,pad in reversed(list(blocks(f,r'\(pad\s'))):
                if re.match(r'\(pad\s+"2"\s',pad):
                    if '(net "3V3_AON")' not in pad:raise ValueError('PSEL PCB predecessor differs')
                    pad=pad.replace('"3V3_AON"','"SGM41513_PSEL"');f=f[:c]+pad+f[d:]
            f=set_prop(f,'Description','SGM41513 non-A/non-D. PSEL uses REGN/R204/R201 before AON starts. Reset nominal input selection 500mA; host writes may override. No PD/OTG; current, NTC and USB qualification remain open.')
        text=text[:a]+f+text[b:]
    pcb.write_text(text)
    return root_id


def apply_native(candidate):
    import wx
    app=wx.App(False)
    import pcbnew as P
    candidate=Path(candidate);folder=candidate/REL;pcb=folder/(STEM+'.kicad_pcb')
    root_id=apply_structure(candidate)
    original=pcb.read_text()
    b=P.LoadBoard(str(pcb))
    f=P.FootprintLoad(str(candidate/'lib/panda-standard.pretty'),FP_NAME)
    if f is None:raise ValueError('Supervisor footprint failed native load')
    f.SetFPID(P.LIB_ID('panda-standard',FP_NAME));f.SetReference('U906');f.SetValue(MPN)
    f.SetPath(P.KIID_PATH('/'+root_id+'/'+uid('U906-instance')))
    f.SetPosition(P.VECTOR2I(P.FromMM(17),P.FromMM(18.75)));f.SetLocked(True)
    for k,v in {'Manufacturer':'SGMICRO','MPN':MPN,'LCSC':'C699619','Datasheet':DOC,'Description':DESCRIPTION}.items():
        field=next((p for p in f.GetFields() if p.GetName()==k),None)
        if field is None:field=P.PCB_FIELD(f,P.FIELD_T_USER,k);f.Add(field)
        field.SetText(v);field.SetVisible(False);field.SetLayer(P.F_Fab)
    for p in f.Pads():
        net,typ=PADS[p.GetNumber()];p.SetNet(b.FindNet(net));p.SetPinType(typ)
        p.SetPinFunction({'1':'GND','2':'nRESET','3':'VCC'}[p.GetNumber()])
    b.Add(f)
    cap=b.FindFootprintByReference('C204');cap.SetPosition(P.VECTOR2I(P.FromMM(16.5),P.FromMM(16)));cap.SetOrientationDegrees(180)
    b.BuildConnectivity()
    for z in b.Zones():z.SetNeedRefill(True)
    P.ZONE_FILLER(b).Fill(b.Zones());P.SaveBoard(str(pcb),b)
    # KiCad 10 exposes native UUID fields as read-only. Canonicalize only the
    # new footprint UUIDs after saving; retain the schematic instance path.
    text=pcb.read_text()
    for a,c,part in blocks(text,r'\(footprint\s'):
        if property_value(part,'Reference')=='U906':
            counter=iter(range(1000))
            part=re.sub(r'\(uuid "[^\"]+"\)',lambda m:'(uuid "'+uid('U906-object-'+str(next(counter)))+'")',part)
            text=text[:a]+part+text[c:];break
    # Preserve every unrelated footprint byte-for-byte. Native save otherwise
    # normalizes the historical U903 footprint differently from its local library.
    selected={property_value(part,'Reference'):part for a,c,part in blocks(text,r'\(footprint\s') if property_value(part,'Reference') in {'C204','U906'}}
    for a,c,part in reversed(list(blocks(original,r'\(footprint\s'))):
        if property_value(part,'Reference')=='C204':original=original[:a]+selected['C204']+original[c:]
    i=original.find('(footprint ');original=original[:i]+selected['U906']+'\n'+original[i:]
    # Refilled zones are the only board-wide native output adopted.
    filled=[part for a,c,part in board_zones(text)]
    existing=board_zones(original)
    if len(existing)!=len(filled):raise ValueError('Unexpected zone inventory change')
    for (a,c,part),replacement in reversed(list(zip(existing,filled))):original=original[:a]+replacement+original[c:]
    pcb.write_text(original)


def apply_routing(candidate):
    from _core_c1_pcb_patch import copper, digest
    p=Path(candidate)/REL/(STEM+'.kicad_pcb');text=p.read_text()
    plan=json.loads((ROOT/'split-c1-power-integrity-layout.json').read_text())
    if digest(text)!=plan['source_copper_sha256']:raise ValueError('Power ECO copper predecessor differs')
    existing=copper(text)
    if plan['removed_copper'] or plan['modified_copper']:raise ValueError('Unreviewed route removal in additive closure')
    if set(existing)&set(plan['added_copper']):raise ValueError('Power route UUID collision')
    e=text.rfind(')');text=text[:e]+'\n'+'\n'.join(plan['added_copper'].values())+'\n'+text[e:]
    if digest(text)!=plan['routed_copper_sha256']:raise ValueError('Power route replay digest differs')
    p.write_text(text);refill_zones(p)


def apply_power_integrity_eco(candidate):
    subprocess.run([kicad_python(),str(Path(__file__).resolve()),'--candidate',str(Path(candidate).resolve()),'--with-routing'],check=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--with-routing',action='store_true')
    args=parser.parse_args();apply_native(args.candidate.resolve())
    if args.with_routing:apply_routing(args.candidate.resolve())
