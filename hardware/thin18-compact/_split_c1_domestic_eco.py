#!/usr/bin/env python3
"""Replay exact mainland substitutions with checked predecessor identities."""
from pathlib import Path
import hashlib, json, re, uuid
from _split_c1_sourcing import blocks, property_value, balanced, patch_block

ROOT = Path(__file__).resolve().parent
REL = Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
SWITCH_FP = 'panda-standard:SGM2578SD_WLCSP_09x09_P05'
SWITCH_DOC = 'https://www.sg-micro.com/rect/assets/d7f6bab2-25db-4935-8da5-745cf9661265/SGM2578S_SGM2578SD.pdf'
SWITCH_DESCRIPTION = 'SGMICRO SGM2578SDYG/TR; active-high 2A load switch with QOD; January 2026 Rev.A.2 p9 specifies RCB with ON high/low. WLCSP 0.5mm pitch, 0.22mm lands. Leakage/rise-time/RCB qualification pending.'

def set_prop(block, field, value):
    pattern = r'(\(property\s+' + re.escape(json.dumps(field)) + r'\s+)("(?:\\.|[^"\\])*")'
    result, count = re.subn(pattern, lambda m: m.group(1)+json.dumps(value), block, count=1)
    if count==0 and field=='Description':
        templates=[(a,b,p) for a,b,p in blocks(block,r'\(property\s') if property_value(p,'Datasheet') is not None]
        if len(templates)!=1:raise ValueError('Description template absent')
        _,end,prop=templates[0]
        prop=re.sub(r'\(property\s+"Datasheet"\s+"(?:\\.|[^"\\])*"','(property "Description" '+json.dumps(value),prop,count=1)
        prop=re.sub(r'\(uuid "[^"]+"\)','(uuid "'+eco_uuid('Description/'+str(property_value(block,'Reference')))+'")',prop)
        return block[:end]+'\n'+prop+block[end:]
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

def change_wire_connector_geometry(fp, pins):
    """HCTL HC-1.0 PWT p18 lands, in the retained signal-row datum."""
    if pins not in (2,3): raise ValueError('Unreviewed HCTL pin count')
    for a,b,pad in reversed(list(blocks(fp,r'\(pad\s'))):
        number=re.match(r'\(pad\s+"([^"]+)"',pad).group(1)
        if number=='MP':
            x=float(re.search(r'\(at\s+([-\d.]+)',pad).group(1))
            new_x=(1 if x>0 else -1)*((pins-1)/2+1.1)
            pad=re.sub(r'(\(at\s+)[-\d.]+\s+[-\d.]+',lambda m:m.group(1)+str(new_x)+' 1.7',pad,count=1)
            size='1.0 2.55'
        else:
            if number not in {str(n) for n in range(1,pins+1)}:raise ValueError('Unexpected HCTL pad')
            size='0.7 1.75'
        pad=re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)','(size '+size+')',pad,count=1)
        pad=pad.replace('smd roundrect','smd rect')
        pad=re.sub(r'\s*\(roundrect_rratio\s+[-\d.]+\)','',pad)
        fp=fp[:a]+pad+fp[b:]
    for a,b,_ in reversed(list(blocks(fp,r'\((?:fp_line|fp_text|model)\s'))):fp=fp[:a]+fp[b:]
    # Fab is explicitly a conservative land/housing envelope, not a 3D body model.
    width=pins+2.3
    extras=[]
    for layer,half,top,bottom,stroke in [('F.Fab',width/2,-2.875,2.975,0.1),('F.CrtYd',width/2+0.25,-3.125,3.225,0.05)]:
        corners=[(-half,top),(half,top),(half,bottom),(-half,bottom)]
        for n,(s,e) in enumerate(zip(corners,corners[1:]+corners[:1])):
            extras.append('(fp_line (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (layer "%s") (uuid "%s"))'%(*s,*e,stroke,layer,eco_uuid('HC10/'+str(pins)+'/'+layer+'/'+str(n))))
    fp=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)', '(descr "HCTL HC-1.0 PWT original p18 land pattern: signal 0.7x1.75, anchors 1.0x2.55, signal-to-anchor center rows 3.70mm. Fab is conservative envelope; maximum height budget 3.2mm.")',fp,count=1)
    fp=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)','(tags "HCTL HC-1.0 PWT domestic side-entry 1A")',fp,count=1)
    return fp[:fp.rfind(')')]+'\n'+'\n'.join(extras)+'\n)'

def change_fpc6_geometry(fp):
    """XKB X05A10H06G, p2 A2 dated 2026-01-15; rotate physical part, never renumber pins."""
    m=re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)',fp)
    x,y,angle=[float(v or 0) for v in m.groups()]
    if x!=6.35 or y not in (39.37,45.5) or angle!=0:raise ValueError('FPC6 pose predecessor differs')
    fp=fp[:m.start()]+'(at %s %s 180)'%(x,y-2.5)+fp[m.end():]
    for a,b,pad in reversed(list(blocks(fp,r'\(pad\s'))):
        number=re.match(r'\(pad\s+"([^"]+)"',pad).group(1)
        if number in ('S1','S2'):
            px=-2.3 if number=='S1' else 2.3;py=1.25;size='0.4 0.8'
        elif number in {str(n) for n in range(1,7)}:
            px=(int(number)-3.5)*0.5;py=-1.25;size='0.3 0.8'
        else:raise ValueError('Unexpected FPC6 pad')
        pad=re.sub(r'\(at\s+[-\d.]+\s+[-\d.]+(?:\s+[-\d.]+)?\)','(at %s %s 180)'%(px,py),pad,count=1)
        pad=re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)','(size '+size+')',pad,count=1)
        fp=fp[:a]+pad+fp[b:]
    for a,b,_ in reversed(list(blocks(fp,r'\((?:fp_line|fp_rect|fp_text|model)\s'))):fp=fp[:a]+fp[b:]
    fp=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)', '(descr "XKB X05A10H06G A2 p2: 6-pin dual-contact back-flip, 0.5mm pitch, 0.3mm FPC. Signal lands 0.3x0.8mm, anchors 0.4x0.8mm, rows 2.5mm apart. Conservative land/body envelope, not 3D model.")',fp,count=1)
    fp=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)', '(tags "XKB X05A10H06G FPC 6pin 0.5mm dual-contact A2")',fp,count=1)
    extras=[]
    for layer,x,y1,y2,stroke in [('F.Fab',2.65,-1.65,1.9,.1),('F.CrtYd',2.9,-1.9,2.15,.05)]:
        extras.append('(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))'%(-x,y1,x,y2,stroke,layer,eco_uuid('XKB6/'+str(property_value(fp,'Reference'))+'/'+layer)))
    return fp[:fp.rfind(')')]+'\n'+'\n'.join(extras)+'\n)'

def change_inductor_geometry(fp, series):
    if series=='MWSA0402S':center,size,body,clear=(1.85,'1.5 2.5',(2.375,2.225),(2.625,2.475))
    elif series=='SWPA3012S':center,size,body,clear=(1.15,'0.8 2.7',(1.6,1.6),(1.85,1.85))
    else:raise ValueError('Unreviewed Sunlord series')
    for a,b,pad in reversed(list(blocks(fp,r'\(pad\s'))):
        number=re.match(r'\(pad\s+"([^"]+)"',pad).group(1)
        if number not in ('1','2'):raise ValueError('Unexpected inductor pad')
        x=float(re.search(r'\(at\s+([-\d.]+)',pad).group(1))
        pad=re.sub(r'(\(at\s+)[-\d.]+\s+[-\d.]+',lambda m:m.group(1)+str(center if x>0 else -center)+' 0',pad,count=1)
        pad=re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)','(size '+size+')',pad,count=1)
        pad=pad.replace('smd roundrect','smd rect');pad=re.sub(r'\s*\(roundrect_rratio\s+[-\d.]+\)','',pad)
        fp=fp[:a]+pad+fp[b:]
    for a,b,_ in reversed(list(blocks(fp,r'\((?:fp_line|fp_rect|fp_text|model)\s'))):fp=fp[:a]+fp[b:]
    extras=[]
    for layer,(x,y),stroke in [('F.Fab',body,0.1),('F.CrtYd',clear,0.05)]:
        extras.append('(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))'%(-x,-y,x,y,stroke,layer,eco_uuid(series+'/'+str(property_value(fp,'Reference'))+'/'+layer)))
    fp=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)', '(descr '+json.dumps('Sunlord '+series+' manufacturer land pattern; original series drawing reviewed; Fab uses maximum body XY and no foreign 3D model.')+')',fp,count=1)
    fp=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)', '(tags '+json.dumps('Sunlord '+series+' power inductor')+')',fp,count=1)
    return fp[:fp.rfind(')')]+'\n'+'\n'.join(extras)+'\n)'

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
        if not pcb and board=='Core-C1' and 'D202' in targets and '(symbol "panda-standard:TPD1E10B06DPYR"' in text:
            from _split_c1_vbus_eco import clone_vbus_symbol
            text=clone_vbus_symbol(text,True)
        if not pcb and board=='Core-C1' and 'D201' in targets and '(symbol "panda-standard:TPD4E05U06DQAR"' in text:
            from _split_c1_esd_eco import clone_esd_symbol
            text=clone_esd_symbol(text,True)
        if not pcb and board=='Core-C1' and 'J501' in targets and '(lib_id "Connector:Micro_SD_Card_Det2")' in text:
            from _split_c1_microsd_eco import clone_microsd_symbol
            text=clone_microsd_symbol(text,True)
        if not pcb and board=='Display-C1' and 'Q1' in targets:
            from _split_c1_mos_eco import clone_mos_symbol
            text=clone_mos_symbol(text)
        if not pcb and board=='Core-C1' and 'U302' in targets and '(symbol "Timer_RTC:RV-3028-C7"' in text:
            from _split_c1_rtc_eco import clone_rtc_symbol
            text=clone_rtc_symbol(text)
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
            if item.get('wire_connector_pins') and pcb:
                block=change_wire_connector_geometry(block,item['wire_connector_pins'])
            if item.get('fpc6_footprint') and pcb:
                block=change_fpc6_geometry(block)
            if item.get('side_switch') and pcb:
                from _split_c1_switch_eco import switch_geometry
                block=switch_geometry(block)
            if item.get('vbus_protector'):
                from _split_c1_vbus_eco import vbus_geometry,SYMBOL
                if pcb:block=vbus_geometry(block)
                else:block=block.replace('(lib_id "panda-standard:TPD1E10B06DPYR")','(lib_id "panda-standard:'+SYMBOL+'")',1)
            if item.get('usb_esd'):
                from _split_c1_esd_eco import esd_geometry,SYMBOL
                if pcb:block=esd_geometry(block)
                else:block=block.replace('(lib_id "panda-standard:TPD4E05U06DQAR")','(lib_id "panda-standard:'+SYMBOL+'")',1)
            if item.get('usb_topmount') and pcb:
                from _split_c1_usb_eco import usb_geometry
                block=usb_geometry(block)
            if item.get('battery_connector') and pcb:
                from _split_c1_battery_eco import battery_geometry
                block=battery_geometry(block)
            if item.get('micro_sd'):
                from _split_c1_microsd_eco import microsd_geometry
                if pcb:block=microsd_geometry(block)
                else:block=block.replace('(lib_id "Connector:Micro_SD_Card_Det2")','(lib_id "panda-standard:XUNPU_TF_122_CCP9")',1)
            if item.get('rtc'):
                from _split_c1_rtc_eco import rtc_geometry,rtc_instance
                block=rtc_geometry(block) if pcb else rtc_instance(block)
            if item.get('rtc_cap') and pcb:
                from _split_c1_rtc_eco import cap_geometry
                block=cap_geometry(block)
            if item.get('display_mos'):
                from _split_c1_mos_eco import mos_geometry,SYMBOL
                if pcb:block=mos_geometry(block)
                else:block=block.replace('(lib_id "Transistor_FET:Q_NMOS_GSD")','(lib_id "'+SYMBOL+'")',1)
            if item.get('panel_fpc') and pcb:
                from _split_c1_panel_eco import panel_geometry
                block=panel_geometry(block)
            if item.get('inductor_land') and pcb:
                block=change_inductor_geometry(block,item['inductor_land'])
            if item.get('diode_land') and pcb:
                block=re.sub(r'^\(footprint\s+"[^"]+"','(footprint "panda-r6-display:MBR0530_JSCJ_SOD123"',block,count=1)
                block=change_pad_geometry(block,False)
            text=text[:a]+block+text[b:]
        path.write_text(text)
    expected_pcb={ref for ref,item in targets.items() if not item.get('manual')}
    if seen[False]!=set(targets) or seen[True]!=expected_pcb:raise ValueError('Domestic ECO ref coverage differs')
    if board=='Core-C1' and {'L401','L402'} <= set(targets):apply_power_layout(candidate)
    if board=='Core-C1':
        lib=candidate/'lib/panda-standard.kicad_sym'
        lib.write_text(clone_switch_symbol(lib.read_text(),False))
        if 'D202' in targets:
            from _split_c1_vbus_eco import clone_vbus_symbol
            lib.write_text(clone_vbus_symbol(lib.read_text(),False))
        if 'D201' in targets:
            from _split_c1_esd_eco import clone_esd_symbol
            lib.write_text(clone_esd_symbol(lib.read_text(),False))
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
        if not (item.get('connector_footprint') or item.get('wire_connector_pins') or item.get('inductor_land') or item.get('fpc6_footprint') or item.get('usb_topmount') or item.get('side_switch') or item.get('vbus_protector') or item.get('panel_fpc') or item.get('usb_esd') or item.get('battery_connector') or item.get('micro_sd') or item.get('display_mos') or item.get('rtc') or item.get('rtc_cap')):continue
        pcb=next(folder.glob('*.kicad_pcb'))
        fp=next(b for _,_,b in blocks(pcb.read_text(),r'\(footprint\s') if property_value(b,'Reference')==ref)
        name=item['new_fields']['Footprint'].split(':')[1]
        libdir=candidate/'lib/panda-standard.pretty' if board=='Core-C1' else folder/'panda-r6-display.pretty'
        library=library_from_board(fp,name)
        if item.get('panel_fpc'):library=re.sub(r'(?m)^[ \t]*\n','',library)
        if item.get('display_mos') or item.get('rtc') or item.get('rtc_cap'):
            library=re.sub(r'[ \t]+$', '',library,flags=re.M)
        (libdir/(name+'.kicad_mod')).write_text(library)
    if board=='Core-C1' and 'J302' in targets:apply_wire_connector_routing(candidate)
    if board=='Core-C1' and {'J803','J804'}<=set(targets):apply_fpc6_support(candidate)
    if refs_only is None:apply_domestic_support(candidate,board)
    if board=='Core-C1' and 'J201' in targets:
        from _split_c1_usb_eco import apply_usb_layout
        apply_usb_layout(candidate)
    if board=='Core-C1' and {'SW201','SW202'}<=set(targets):
        from _split_c1_switch_eco import apply_switch_layout
        apply_switch_layout(candidate)
    if board=='Core-C1' and 'J301' in targets:
        from _split_c1_battery_eco import apply_battery_routing
        apply_battery_routing(candidate)
    if board=='Display-C1' and 'J2' in targets:
        from _split_c1_panel_eco import apply_panel_routing
        apply_panel_routing(candidate)
    if board=='Core-C1' and 'J501' in targets:
        from _split_c1_microsd_eco import install_symbol_library,apply_microsd_routing
        install_symbol_library(candidate)
        apply_microsd_routing(candidate)
    if board=='Core-C1' and {'U302','C301'}<=set(targets):
        from _split_c1_rtc_eco import support,apply_rtc_routing
        support(candidate)
        apply_rtc_routing(candidate)
    if board=='Display-C1' and 'Q1' in targets:
        from _split_c1_mos_eco import install_mos_library,apply_mos_routing
        install_mos_library(candidate)
        apply_mos_routing(candidate)
    for path in folder.glob('*.kicad_pcb'):
        path.write_text(re.sub(r'(?m)^[ \t]+$', '',path.read_text()))
    return {'board':board,'applied_refs':sorted(targets),'manufacturing_release':False}

def eco_uuid(value):
    return str(uuid.uuid5(uuid.NAMESPACE_URL,'panda/split-c1/domestic-support/'+value))

def apply_wire_connector_routing(candidate):
    """Move the NTC spur via and ground escape away from enlarged HCTL lands."""
    path=next((Path(candidate)/REL).glob('*.kicad_pcb'));text=path.read_text()
    changes={
        '64af7e6b-0c6c-48d6-8c8f-9036f573ea9c':{'start':((48.3378,19.3008),(48.5,19.3008)),'end':((48.3378,17.2335),(48.5,16.5))},
        '855526fb-cf8f-45d8-9735-0f6e7ae96985':{'start':((48.3378,17.2335),(48.5,16.5))},
        '8ba710f5-f668-4595-9bc1-4445b586d3e8':{'end':((48.3378,19.3008),(48.5,19.3008))},
        'e8eec420-2290-46ae-8611-878f7672a3f5':{'start':((48.3378,19.3008),(48.5,19.3008))},
        '48929bd4-5e9d-4210-845f-2dae2f353b9a':{'at':((49.8046,19.0727),(49.8046,19.7))},
        'f777faa2-f915-4b21-85c6-95b2db668ec6':{'start':((49.8046,19.0727),(49.8046,19.7))},
        'fa4afe0f-2518-4973-b2b9-6e36fa8cc076':{'start':((49.8046,19.0727),(49.8046,19.7))}}
    seen=set()
    for a,b,block in reversed(list(blocks(text,r'\((?:segment|via)\s'))):
        uid=re.search(r'\(uuid "([^"]+)"\)',block).group(1)
        if uid not in changes:continue
        for field,(old,new) in changes[uid].items():
            pattern=r'\('+field+r'\s+([-\d.]+)\s+([-\d.]+)\)'
            found=re.search(pattern,block)
            if not found or tuple(map(float,found.groups()))!=old:raise ValueError('HCTL routing predecessor differs: '+uid)
            block=re.sub(pattern,'('+field+' %s %s)'%new,block,count=1)
        seen.add(uid);text=text[:a]+block+text[b:]
    if seen!=set(changes):raise ValueError('HCTL routing coverage differs')
    path.write_text(text)

def apply_fpc6_support(candidate):
    """Move the provisional M1.2 hole and SDA escape, retaining all rule minima."""
    path=next((Path(candidate)/REL).glob('*.kicad_pcb'));text=path.read_text()
    data=json.loads((ROOT/'split-c1-domestic-eco.json').read_text())['fpc6_layout']
    replacements={i['uuid']:i for i in data['changed_blocks']};seen=set()
    for a,b,block in reversed(list(blocks(text,r'\((?:footprint|segment|via)\s'))):
        uid=re.search(r'\(uuid "([^"]+)"\)',block).group(1)
        if uid not in replacements:continue
        i=replacements[uid]
        if native_block_hash(block)!=i['predecessor_sha256']:raise ValueError('FPC6 support predecessor differs: '+uid)
        text=text[:a]+i['new_block']+text[b:];seen.add(uid)
    if seen!=set(replacements):raise ValueError('FPC6 support coverage differs')
    for block in data['new_copper']:
        uid=re.search(r'\(uuid "([^"]+)"\)',block).group(1)
        if '(uuid "'+uid+'")' in text:raise ValueError('FPC6 support already applied')
    path.write_text(text[:text.rfind(')')]+'\n'+'\n'.join(data['new_copper'])+'\n)\n')

def native_block_hash(block):
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+',block)
    return hashlib.sha256(json.dumps(tokens,separators=(',',':')).encode()).hexdigest()

def apply_power_layout(candidate):
    """Replay reviewed power routing, checking exact canonical predecessors."""
    path=next((Path(candidate)/REL).glob('*.kicad_pcb'));text=path.read_text()
    layout=json.loads((ROOT/'split-c1-domestic-eco.json').read_text())['power_layout']
    moves={i['ref']:i for i in layout['footprint_moves']}
    replacements={i['ref']:i for i in layout['footprint_blocks']}
    seen=set()
    for a,b,fp in reversed(list(blocks(text,r'\(footprint\s'))):
        ref=property_value(fp,'Reference')
        if ref in moves:
            i=moves[ref];m=re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)',fp)
            if not m or [float(v or 0) for v in m.groups()]!=i['old_at']:raise ValueError('Power footprint predecessor differs: '+ref)
            fp=fp[:m.start()]+'(at %s %s %s)'%tuple(i['new_at'])+fp[m.end():]
            for c,d,pad in reversed(list(blocks(fp,r'\(pad\s'))):
                m=re.search(r'\(at\s+[-\d.]+\s+[-\d.]+\s+([-\d.]+)\)',pad)
                if not m or float(m.group(1))!=i['pad_angle_old']:raise ValueError('Power pad angle differs')
                pad=pad[:m.start(1)]+str(i['pad_angle_new'])+pad[m.end(1):];fp=fp[:c]+pad+fp[d:]
            seen.add(ref)
        if ref in replacements:
            if property_value(fp,'LCSC') is None:
                registry=json.loads((ROOT/'split-c1-sourcing-evidence.json').read_text())
                rows=[i for i in registry['entries'] if i['board']=='Core-C1' and ref in i['refs']]
                if len(rows)!=1:raise ValueError('Power support exact sourcing identity missing')
                fp=patch_block(fp,ref,rows[0],True)
            i=replacements[ref]
            if native_block_hash(fp)!=i['predecessor_sha256']:raise ValueError('Power support footprint differs: '+ref)
            fp=i['new_block'];seen.add(ref)
        text=text[:a]+fp+text[b:]
    if seen!=set(moves)|set(replacements):raise ValueError('Power footprint coverage differs')
    changes={i['uuid']:i for i in layout['copper_changes']};seen=set()
    for a,b,cu in reversed(list(blocks(text,r'\((?:segment|via)\s'))):
        uid=re.search(r'\(uuid "([^"]+)"\)',cu).group(1)
        if uid not in changes:continue
        i=changes[uid]
        if native_block_hash(cu)!=i['predecessor_sha256']:raise ValueError('Power copper predecessor differs: '+uid)
        text=text[:a]+i['new_block']+text[b:];seen.add(uid)
    if seen!=set(changes):raise ValueError('Power copper coverage differs')
    for cu in layout['new_copper']:
        uid=re.search(r'\(uuid "([^"]+)"\)',cu).group(1)
        if '(uuid "'+uid+'")' in text:raise ValueError('Power copper already applied')
    text=text[:text.rfind(')')]+'\n'+'\n'.join(layout['new_copper'])+'\n)\n';path.write_text(text)
    from _split_c1_prototype_eco import library_from_board
    fp=next(b for _,_,b in blocks(text,r'\(footprint\s') if property_value(b,'Reference')=='C201')
    lib=Path(candidate)/'lib/panda-standard.pretty/C201_CBOOT_0603_SEED.kicad_mod'
    lib.write_text(library_from_board(fp,'C201_CBOOT_0603_SEED'))

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
    # C201 belongs to SGM41513 now; remove stale BQ25628E documentation from live CAD.
    for path in sorted(folder.glob('*.kicad_sch'))+sorted(folder.glob('*.kicad_pcb')):
        text=path.read_text();pcb=path.suffix=='.kicad_pcb'
        for a,b,block in reversed(list(blocks(text,r'\(footprint\s' if pcb else r'\(symbol\s+\(lib_id\s'))):
            if property_value(block,'Reference')!='C201':continue
            if property_value(block,'MPN')!='0603B473K500NT':raise ValueError('C201 exact capacitor identity drift')
            block=set_prop(block,'Datasheet','https://www.sg-micro.com/rect/assets/58a4fe4d-da1d-49a3-b312-5664211d9016/SGM41513_SGM41513A_SGM41513D.pdf')
            block=set_prop(block,'Description','FH 47nF 50V X7R +/-10% 0603 bootstrap capacitor from SGM41513 BTST to SW; effective capacitance and switching qualification pending.')
            text=text[:a]+block+text[b:]
        path.write_text(text)
    from _split_c1_prototype_eco import library_from_board
    fp=next(b for _,_,b in blocks(pcbpath.read_text(),r'\(footprint\s') if property_value(b,'Reference')=='C201')
    (candidate/'lib/panda-standard.pretty/C201_CBOOT_0603_SEED.kicad_mod').write_text(library_from_board(fp,'C201_CBOOT_0603_SEED'))
