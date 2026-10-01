#!/usr/bin/env python3
"""Replay exact mainland substitutions with checked predecessor identities."""
from pathlib import Path
import json, re, uuid
from _split_c1_sourcing import blocks, property_value, balanced, patch_block

ROOT = Path(__file__).resolve().parent
REL = Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
SWITCH_FP = 'panda-standard:SGM2578SD_WLCSP_09x09_P05'
SWITCH_DOC = 'https://www.sg-micro.com/rect/assets/d7f6bab2-25db-4935-8da5-745cf9661265/SGM2578S_SGM2578SD.pdf'
SWITCH_DESCRIPTION = 'SGMICRO SGM2578SDYG/TR; active-high 2A load switch with QOD; January 2026 Rev.A.2 p9 specifies RCB with ON high/low. WLCSP 0.5mm pitch, 0.22mm lands. Leakage/rise-time/RCB qualification pending.'

def set_prop(block, field, value):
    pattern = r'(\(property\s+' + re.escape(json.dumps(field)) + r'\s+)("(?:\\.|[^"\\])*")'
    result, count = re.subn(pattern, lambda m: m.group(1)+json.dumps(value), block, count=1)
    if count != 1:
        raise ValueError('Required field absent: '+field)
    return result

def change_pad_geometry(fp, switch):
    for a,b,pad in reversed(list(blocks(fp,r'\(pad\s'))):
        if switch:
            pad = re.sub(r'(\(at\s+)([-\d.]+)\s+([-\d.]+)',
                         lambda m:m.group(1)+str(float(m.group(2))*1.25)+' '+str(float(m.group(3))*1.25),pad,count=1)
            pad = re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)', '(size 0.22 0.22)',pad,count=1)
        else:
            pad = re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)', '(size 0.94 0.91)',pad,count=1)
            pad = pad.replace('smd roundrect','smd rect')
            pad = re.sub(r'\s*\(roundrect_rratio\s+[-\d.]+\)', '',pad)
        fp=fp[:a]+pad+fp[b:]
    if switch:
        fp=fp.replace('TPS22916CYFPT_YFP0004','SGM2578SD_WLCSP_09x09_P05')
        for old,new in [('0.655','0.715'),('0.39','0.465'),('0.19','0.215')]:
            fp=re.sub(r'(?<![\d.])'+re.escape(old)+r'(?![\d.])',new,fp)
        fp=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)', '(descr "SGMICRO WLCSP-0.9x0.9-4B-D; max body 0.93mm; recommended land 0.22mm at 0.5mm pitch; TX00541.000")',fp,count=1)
        fp=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)', '(tags "SGM2578SD WLCSP QOD RCB")',fp,count=1)
    return fp

def clone_switch_symbol(text, cache):
    old='panda-standard:TPS22916CYFPT' if cache else 'TPS22916CYFPT'
    new='panda-standard:SGM2578SDYG_TR' if cache else 'SGM2578SDYG_TR'
    if '(symbol "'+new+'"' in text:return text
    a=text.index('(symbol "'+old+'"');b=balanced(text,a)
    symbol=text[a:b].replace('TPS22916CYFPT','SGM2578SDYG_TR')
    symbol=set_prop(symbol,'Value','SGM2578SDYG/TR')
    symbol=set_prop(symbol,'Footprint',SWITCH_FP)
    symbol=set_prop(symbol,'Datasheet',SWITCH_DOC)
    symbol=set_prop(symbol,'Description',SWITCH_DESCRIPTION)
    if cache:
        i=text.index('(lib_symbols');end=balanced(text,i)-1
    else:end=text.rfind(')')
    return text[:end]+'\n'+symbol+'\n'+text[end:]

def apply_domestic_eco(candidate, board, refs_only=None):
    candidate=Path(candidate)
    evidence=json.loads((ROOT/'split-c1-domestic-eco.json').read_text())
    targets={ref:item for item in evidence['applied_groups'] if item['board']==board for ref in item['refs']}
    if refs_only is not None:
        targets={ref:item for ref,item in targets.items() if ref in refs_only}
        if set(targets)!=set(refs_only):raise ValueError('Unknown ECO refs')
    folder=candidate/REL if board=='Core-C1' else candidate
    seen={True:set(),False:set()}
    for path in sorted(folder.glob('*.kicad_sch'))+sorted(folder.glob('*.kicad_pcb')):
        pcb=path.suffix=='.kicad_pcb';text=path.read_text()
        if not pcb and board=='Core-C1' and '(symbol "panda-standard:TPS22916CYFPT"' in text:
            text=clone_switch_symbol(text,True)
        pattern=r'\(footprint\s' if pcb else r'\(symbol\s+\(lib_id\s'
        for a,b,block in reversed(list(blocks(text,pattern))):
            ref=property_value(block,'Reference')
            if ref not in targets:continue
            item=targets[ref]
            if property_value(block,'MPN')!=item['old_mpn'] or property_value(block,'Manufacturer')!=item['old_manufacturer']:
                raise ValueError('Domestic ECO predecessor changed: '+ref)
            seen[pcb].add(ref)
            for field,value in item['new_fields'].items():
                if pcb and field=='Footprint':
                    block=re.sub(r'^\(footprint\s+"[^"]+"','(footprint '+json.dumps(value),block,count=1)
                elif field == 'LCSC' and property_value(block, field) is None:
                    continue
                else:block=set_prop(block,field,value)
            if property_value(block, 'LCSC') is None:
                fields=item['new_fields']
                block=patch_block(block,ref,{'manufacturer':fields['Manufacturer'], 'mpn':fields['MPN'],
                                            'library_id':fields['LCSC'], 'board':board},pcb)
            if item.get('switch'):
                if pcb:block=change_pad_geometry(block,True)
                else:block=block.replace('(lib_id "panda-standard:TPS22916CYFPT")','(lib_id "panda-standard:SGM2578SDYG_TR")',1)
            if item.get('connector_footprint') and pcb:
                block=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)', '(descr '+json.dumps(item['qualification'])+')',block,count=1)
                block=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)', '(tags "HCTL 60pin 0.4mm 1.5mm mate")',block,count=1)
                for c,d,_ in reversed(list(blocks(block,r'\(model\s'))):block=block[:c]+block[d:]
                block=re.sub(r'(?m)^[ \t]+$','',block)
            if item.get('diode_land') and pcb:
                block=re.sub(r'^\(footprint\s+"[^"]+"','(footprint "panda-r6-display:MBR0530_JSCJ_SOD123"',block,count=1)
                block=change_pad_geometry(block,False)
            text=text[:a]+block+text[b:]
        path.write_text(text)
    expected_pcb={ref for ref,item in targets.items() if not item.get('manual')}
    if seen[False]!=set(targets) or seen[True]!=expected_pcb:raise ValueError('Domestic ECO ref coverage differs')
    if board=='Core-C1':
        lib=candidate/'lib/panda-standard.kicad_sym'
        lib.write_text(clone_switch_symbol(lib.read_text(),False))
        src=candidate/'lib/panda-standard.pretty/TPS22916CYFPT_YFP0004.kicad_mod'
        text=change_pad_geometry(src.read_text(),True)
        text=set_prop(text,'Value','SGM2578SD_WLCSP_09x09_P05')
        text=set_prop(text,'Datasheet',SWITCH_DOC)
        text=set_prop(text,'Description',SWITCH_DESCRIPTION)
        src.with_name('SGM2578SD_WLCSP_09x09_P05.kicad_mod').write_text(text)
    else:
        from _split_c1_prototype_eco import library_from_board
        pcb=next(folder.glob('*.kicad_pcb'))
        diode=next(b for _,_,b in blocks(pcb.read_text(),r'\(footprint\s') if property_value(b,'Reference')=='D1')
        lib=folder/'panda-r6-display.pretty/MBR0530_JSCJ_SOD123.kicad_mod'
        lib.write_text(library_from_board(diode,'MBR0530_JSCJ_SOD123'))
    from _split_c1_prototype_eco import library_from_board
    for ref,item in targets.items():
        if not item.get('connector_footprint'):continue
        pcb=next(folder.glob('*.kicad_pcb'))
        fp=next(b for _,_,b in blocks(pcb.read_text(),r'\(footprint\s') if property_value(b,'Reference')==ref)
        name=item['new_fields']['Footprint'].split(':')[1]
        libdir=candidate/'lib/panda-standard.pretty' if board=='Core-C1' else folder/'panda-r6-display.pretty'
        (libdir/(name+'.kicad_mod')).write_text(library_from_board(fp,name))
    if refs_only is None:apply_domestic_support(candidate,board)
    return {'board':board,'applied_refs':sorted(targets),'manufacturing_release':False}

def eco_uuid(value):
    return str(uuid.uuid5(uuid.NAMESPACE_URL,'panda/split-c1/domestic-support/'+value))

def regenerate_uuids(text, prefix):
    return re.sub(r'\(uuid "([^"]+)"\)',lambda m:'(uuid "'+eco_uuid(prefix+'/'+m.group(1))+'")',text)

def apply_domestic_support(candidate, board):
    """Local U403 output bypass and corrected component documentation, once."""
    candidate=Path(candidate)
    if board=='Display-C1':
        doc='https://datasheet.lcsc.com/datasheet/pdf/788534d9ddb7ae9e0dfc8df35b525e01.pdf?productCode=C3294723'
        seen={True:set(),False:set()}
        for path in sorted(candidate.glob('*.kicad_sch'))+sorted(candidate.glob('*.kicad_pcb')):
            pcb=path.suffix=='.kicad_pcb';text=path.read_text()
            for a,b,block in reversed(list(blocks(text,r'\(footprint\s' if pcb else r'\(symbol\s+\(lib_id\s'))):
                ref=property_value(block,'Reference')
                if ref not in {'U1','U2','U3'}:continue
                if property_value(block,'Manufacturer')!='Wuxi I-core Elec' or property_value(block,'MPN')!='AIP74LVC2G17GC363.TR':
                    raise ValueError('Icore documentation predecessor changed')
                block=set_prop(block,'Datasheet',doc)
                seen[pcb].add(ref);text=text[:a]+block+text[b:]
            path.write_text(text)
        if any(v!={'U1','U2','U3'} for v in seen.values()):raise ValueError('Icore documentation coverage')
        return
    folder=candidate/REL;pcbpath=next(folder.glob('*.kicad_pcb'))
    pcb=pcbpath.read_text()
    if any(property_value(b,'Reference')=='C516' for _,_,b in blocks(pcb,r'\(footprint\s')):
        raise ValueError('C516 support ECO was already applied')
    # Copy the existing qualified 0603 1uF bypass, retaining its library geometry.
    source=next(b for _,_,b in blocks(pcb,r'\(footprint\s') if property_value(b,'Reference')=='C509')
    fp=regenerate_uuids(source,'C516/pcb')
    fp=set_prop(fp,'Reference','C516');fp=set_prop(fp,'Value','1u / U403 VOUT')
    fp=set_prop(fp,'Datasheet','https://www.fhcomp.com/en/product_info/?prod_code=0603B105K250NT')
    fp=set_prop(fp,'Description','SGM2578SD U403 local output bypass, 1uF 25V X7R +/-10%; 3V3_TOUCH_SW to GND. Effective DC-bias and switch stability remain EVT.')
    fp=re.sub(r'\(at\s+40\s+17\.25\s+180\)','(at 37.9 15.9)',fp,count=1)
    fp=re.sub(r'(\(at\s+[-\d.]+\s+[-\d.]+)\s+180\)',r'\1 0)',fp)
    fp=fp.replace('"F.Cu"','"B.Cu"').replace('"F.Mask"','"B.Mask"').replace('"F.Paste"','"B.Paste"')
    fp=fp.replace('"F.Fab"','"B.Fab"').replace('"F.SilkS"','"B.SilkS"').replace('"F.CrtYd"','"B.CrtYd"')
    fp=fp.replace('(net "3V3_AON")','(net "3V3_TOUCH_SW")')
    # KiCad mirrored bottom-side text; pads and symmetric body retain x coordinates.
    for a,b,item in reversed(list(blocks(fp,r'\((?:property|fp_text)\s'))):
        if '(justify' not in item:item=item.replace('(effects (font','(effects (justify mirror) (font',1)
        fp=fp[:a]+item+fp[b:]
    extras=[fp]
    for number,(start,end,net) in enumerate([
        ((37.125,15.9),(36.8242,16.3642),'3V3_TOUCH_SW'),
        ((38.675,15.9),(38.675,16.4),'GND'),
        ((38.675,16.4),(36.25,19.225),'GND')]):
        extras.append('(segment (start %s %s) (end %s %s) (width 0.2) (layer "B.Cu") (net "%s") (uuid "%s"))'%(*start,*end,net,eco_uuid('C516/track/'+str(number))))
    extras.append('(via (at 36.25 19.225) (size 0.4) (drill 0.2) (layers "F.Cu" "B.Cu") (net "GND") (uuid "'+eco_uuid('C516/gnd-via')+'"))')
    pcbpath.write_text(pcb[:pcb.rfind(')')]+'\n'+'\n'.join(extras)+'\n)\n')
    schpath=next(p for p in folder.glob('*.kicad_sch') if '(reference "C509")' in p.read_text())
    text=schpath.read_text()
    source=next(b for _,_,b in blocks(text,r'\(symbol\s+\(lib_id\s') if property_value(b,'Reference')=='C509')
    symbol=regenerate_uuids(source,'C516/sch').replace('"C509"','"C516"')
    symbol=set_prop(symbol,'Value','1u / U403 VOUT')
    symbol=set_prop(symbol,'Datasheet','https://www.fhcomp.com/en/product_info/?prod_code=0603B105K250NT')
    symbol=set_prop(symbol,'Description','SGM2578SD U403 local output bypass, 1uF 25V X7R +/-10%; 3V3_TOUCH_SW to GND. Effective DC-bias and switch stability remain EVT.')
    def move(m):
        x,y=map(float,m.groups())
        return '(at %.4f %.4f'%(x+279.4,y+149.86) if x else m.group(0)
    symbol=re.sub(r'\(at\s+([-\d.]+)\s+([-\d.]+)',move,symbol)
    extras=[symbol]
    for n,(pin_y,label_y,net) in enumerate([(270.51,267.97,'3V3_TOUCH_SW'),(278.13,280.67,'GND')]):
        extras.append('(wire (pts (xy 304.8 %s) (xy 304.8 %s)) (stroke (width 0) (type default)) (uuid "%s"))'%(pin_y,label_y,eco_uuid('C516/wire/'+str(n))))
        extras.append('(global_label "%s" (shape passive) (at 304.8 %s 90) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "%s"))'%(net,label_y,eco_uuid('C516/label/'+str(n))))
    schpath.write_text(text[:text.rfind(')')]+'\n'+'\n'.join(extras)+'\n)\n')
    for path in sorted(folder.glob('*.kicad_sch'))+sorted(folder.glob('*.kicad_pcb')):
        text=path.read_text();pcb=path.suffix=='.kicad_pcb'
        for a,b,block in reversed(list(blocks(text,r'\(footprint\s' if pcb else r'\(symbol\s+\(lib_id\s'))):
            ref=property_value(block,'Reference')
            if ref not in {'C508','C509','C510','C511'}:continue
            if property_value(block,'MPN')!='0603B105K250NT':raise ValueError('Input bypass identity drift')
            block=set_prop(block,'Datasheet','https://www.fhcomp.com/en/product_info/?prod_code=0603B105K250NT')
            block=set_prop(block,'Description','FH 1uF 25V X7R +/-10% 0603 local input bypass for SGM2578SD. Application review in split-c1-domestic-eco.json; DC-bias remains qualification.')
            text=text[:a]+block+text[b:]
        path.write_text(text)
