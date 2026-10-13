#!/usr/bin/env python3
"""Build a fresh native 7mm electrical/placement candidate from current Split-C1.

No donor CAD is modified. Actual schematic pin types/net names are preserved,
except explicit reviewed MCU/connector ECOs. Generated output never belongs in Git.
This is still an engineering candidate: RTC low-profile backup, routing, supplier
maximum envelopes and physical/SMT acceptance are separately blocking gates.
"""
from pathlib import Path
import argparse,hashlib,json,math,re,shutil,subprocess,sys,uuid,xml.etree.ElementTree as ET
import wx
APP=wx.App(False)
import pcbnew as P
from _split_c1_common import ROOT,REPO,REL,STEM,kicad_cli
from _split_c1_sourcing import blocks,property_value
from seven_mm_low_profile_parts import bare_host,write_custom_lands,split_60_interconnect,ESP_DOC,ESP_GUIDE,USB_DOC,FFC_DOC
from seven_mm_layout import CONTRACT,validate_plan
from seven_mm_routing import apply as apply_routing

UID=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'panda/seven-mm/low-profile/'+s))
Q=lambda s:json.dumps(str(s),ensure_ascii=False)
MM=lambda x,y:P.VECTOR2I(P.FromMM(x),P.FromMM(y))
STOCK=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bbox(f):
    b=f.GetBoundingBox(False,False);return [P.ToMM(b.GetX()),P.ToMM(b.GetY()),P.ToMM(b.GetRight()),P.ToMM(b.GetBottom())]
def intersects(a,b,gap=.25):return not(a[2]+gap<=b[0] or b[2]+gap<=a[0] or a[3]+gap<=b[1] or b[3]+gap<=a[1])
def run(args,log):
    with Path(log).open('w') as f:subprocess.run([kicad_cli(),*map(str,args)],stdout=f,stderr=subprocess.STDOUT,check=True)
def fields_fp(f,part):
    f.SetReference(part['ref']);f.SetValue(part['value']);f.SetFPIDAsString(part['footprint'])
    props={**part['fields'],'Datasheet':part['datasheet']}
    for key,val in props.items():
        if key in {'Footprint','Reference','Value'}:continue
        field=next((v for v in f.GetFields() if v.GetName()==key),None)
        if field is None:field=P.PCB_FIELD(f,P.FIELD_T_USER,key);f.Add(field)
        field.SetText(str(val));field.SetVisible(False);field.SetLayer(P.F_Fab)
    f.Reference().SetLayer(P.F_Fab);f.Reference().SetVisible(False)
    f.Value().SetLayer(P.F_Fab);f.Value().SetVisible(False)


def schematic(out,name,parts):
    """Explicit symbol per reference; known power sources are not guessed from ERC."""
    rootid=UID(name+'/root');definitions=[];instances=[];labels=[];col=0;y=40.64;nettypes={}
    eff=lambda size=.85,justify='':f'(effects (font (size {size} {size}))'+(f'(justify {justify})' if justify else '')+')'
    def prop(key,val,x,y,hide=False):return f'(property {Q(key)} {Q(val)} (at {x} {y} 0) '+('(hide yes)' if hide else '')+eff()+')'
    for ref,part in sorted(parts.items()):
        pins=part['pins'];nums=sorted(pins,key=lambda n:(not n.isdigit(),int(n) if n.isdigit() else n));rows=max(1,(len(nums)+1)//2);h=max(5.08,(rows+1)*2.54)
        if y+h+18>755:col+=1;y=40.64
        x=76.2+col*165.1;sy=y+h/2+5.08;y+=h+17.78;loc={};sp=[]
        for j,num in enumerate(nums):
            left=j<rows;index=j if left else j-rows;px=-12.7 if left else 12.7;py=(rows-1)*1.27-index*2.54;a=0 if left else 180
            typ=pins[num]['type'].split('+')[0];typ={'openCol':'open_collector','openEmit':'open_emitter'}.get(typ,typ)
            if typ not in {'input','output','bidirectional','tri_state','passive','free','unspecified','power_in','power_out','open_collector','open_emitter','no_connect'}:raise ValueError('Unknown source pin type '+typ)
            pname=pins[num]['name'];pname=pname.rsplit('_',1)[0] if pname.rsplit('_',1)[-1].isdigit() else pname
            sp.append(f'(pin {typ} line (at {px} {py} {a}) (length 2.54) (name {Q(pname)} {eff()})(number {Q(num)} {eff()}))')
            loc[num]=(px,py,typ)
        libname='Panda7:'+ref
        definition=f'(symbol {Q(libname)} (pin_names(offset .5))(in_bom {"yes" if part["in_bom"] else "no"})(on_board yes)'+prop('Reference',ref,0,h/2+2)+prop('Value',part['value'],0,-h/2-2)+prop('Footprint',part['footprint'],0,0,True)+f'(symbol {Q(ref+"_0_1")}(rectangle(start -10.16 {h/2})(end 10.16 {-h/2})(stroke(width .254)(type default))(fill(type background))))(symbol {Q(ref+"_1_1")}'+''.join(sp)+'))'
        definitions.append(definition)
        s=f'(symbol(lib_id {Q(libname)})(at {x} {sy} 0)(unit 1)(in_bom {"yes" if part["in_bom"] else "no"})(on_board {"yes" if part.get("on_board",True) else "no"})(dnp {"yes" if part["dnp"] else "no"})(uuid {Q(UID(name+"/"+ref))})'
        s+=prop('Reference',ref,x,sy-h/2-3)+prop('Value',part['value'],x,sy+h/2+3)+prop('Footprint',part['footprint'],x,sy,True)+prop('Datasheet',part['datasheet'],x,sy,True)
        for key,val in part['fields'].items():
            if key not in {'Reference','Value','Footprint','Datasheet'}:s+=prop(key,val,x,sy,True)
        s+=f'(instances(project {Q(name)}(path {Q("/"+rootid)}(reference {Q(ref)})(unit 1)))))';instances.append(s)
        for num,(px,py,typ) in loc.items():
            xx,yy=round(x+px,5),round(sy-py,5);net=part['nets'].get(num,'')
            if not net or net.startswith('unconnected-') or typ=='no_connect':
                labels.append(f'(no_connect(at {xx} {yy})(uuid {Q(UID(name+"/nc/"+ref+"/"+num))}))');continue
            nettypes.setdefault(net,set()).add(typ)
            labels.append(f'(global_label {Q(net)} (shape passive)(at {xx} {yy} {180 if px>0 else 0}) {eff(.9,"left")}(uuid {Q(UID(name+"/net/"+ref+"/"+num))}))')
    # External rails and passive-isolated branches carried by the original design.
    # Unknown power domains fail, never auto-insert flags to silence a real error.
    permitted={'GND','3V3_AON','3V3_RF','VBUS_USB','VSYS_RAW','VSYS_AUDIO','BAT_PACKP','BAT_CONN_P','RTC_VBACKUP','FUEL_VDD','3V3_SD','3V3_TOUCH','3V3_EPD_LOGIC','EPD_3V3','FL_VIN','3V3_AON_SRC','3V3_EPD_LOGIC_SW','VSYS_AUDIO_SW','BAT_PROT_VDD','BAT_CELL_N'}
    needed={n for n,t in nettypes.items() if 'power_in' in t and 'power_out' not in t}
    if needed-permitted:raise ValueError('Unreviewed power-source flags '+repr(needed-permitted))
    flag='(symbol "Panda7:POWER_SOURCE"(power)(pin_names(offset 0))(in_bom no)(on_board no)(property "Reference" "#FLG"(at 0 1 0)'+eff()+')(property "Value" "POWER_SOURCE"(at 0 2 0)'+eff()+')(symbol "POWER_SOURCE_0_1"(polyline(pts(xy 0 0)(xy 0 2))(stroke(width .254)(type default))(fill(type none))))(symbol "POWER_SOURCE_1_1"(pin power_out line(at 0 0 90)(length 0)(name "pwr" '+eff()+')(number "1" '+eff()+'))))'
    definitions.append(flag)
    for i,net in enumerate(sorted(needed)):
        ref='#FLG'+str(i+1);x=30.48+i*31.75;yy=792.48
        instances.append(f'(symbol(lib_id "Panda7:POWER_SOURCE")(at {x} {yy} 0)(unit 1)(in_bom no)(on_board no)(dnp no)(uuid {Q(UID(name+"/"+ref))})'+prop('Reference',ref,x,yy,True)+prop('Value','POWER_SOURCE',x,yy,True)+f'(instances(project {Q(name)}(path {Q("/"+rootid)}(reference {Q(ref)})(unit 1)))))')
        labels.append(f'(global_label {Q(net)}(shape passive)(at {x} {yy} 90){eff(.9,"left")}(uuid {Q(UID(name+"/flag/"+net))}))')
    s=f'(kicad_sch(version 20250114)(generator "eeschema")(uuid {Q(rootid)})(paper "A0")(title_block(title {Q(name+" low-profile ECO / not fabrication release")})(rev "7MM-CANDIDATE"))(lib_symbols '+''.join(definitions)+')'+''.join(instances+labels)+')\n'
    (out/(name+'.kicad_sch')).write_text(s)
    return rootid,definitions


def build(out):
    out=out.resolve()
    if out.exists():raise ValueError('Use a new candidate; no overwrite')
    if out.is_relative_to(REPO) and not out.is_relative_to(REPO/'.work'):raise ValueError('Generated native candidates stay ignored or external')
    plan=json.loads(CONTRACT.read_text());validate_plan(plan)
    out.mkdir(parents=True);lib=out/'Panda7.pretty';write_custom_lands(lib)
    sourcepaths={'Core':ROOT/'core-c1-96x68-split'/REL/(STEM+'.kicad_pcb'),'Display':ROOT/'display-c1-45x36-production-bom/PANDA-EPD0426-SPI-EVT.kicad_pcb'}
    hashes={n:sha(p) for n,p in sourcepaths.items()};sources={n:P.LoadBoard(str(p)) for n,p in sourcepaths.items()}
    parts={};fp={};original={};original_contract={};retained_boards=list(sources.values())
    for name,board in sources.items():
        netlist=out/(name+'-donor.xml');run(['sch','export','netlist','--format','kicadxml','--output',netlist,sourcepaths[name].with_suffix('.kicad_sch')],out/(name+'-donor.log'))
        tree=ET.parse(netlist);xmlpins={(v.get('ref'),v.get('pin')):{'name':v.get('pinfunction',''),'type':v.get('pintype','passive').split('+')[0]} for net in tree.findall('nets/net') for v in net.findall('node')}
        for f in board.GetFootprints():
            ref=f.GetReference();pins={};nets={}
            for p in f.Pads():
                num=p.GetNumber()
                if not num:continue
                pins[num]=xmlpins.get((ref,num),{'name':p.GetPinFunction() or num,'type':p.GetPinType() or 'passive'})
                net=str(p.GetNetname());net=net[1:] if name=='Display' and net.startswith('/') else net;nets[num]='' if net.startswith('unconnected-') else net
            if not pins:continue
            fields={g.GetName():g.GetText() for g in f.GetFields() if g.GetName() not in {'Reference','Value'}}
            item={'ref':ref,'value':f.GetValue(),'fields':fields,'datasheet':fields.get('Datasheet',''),'pins':pins,'nets':nets,'in_bom':not f.IsExcludedFromBOM(),'dnp':f.IsDNP(),'board':name,'source_pos':[P.ToMM(f.GetPosition().x),P.ToMM(f.GetPosition().y)],'on_board':True}
            parts[(name,ref)]=item;original[(name,ref)]=dict(nets);original_contract[(name,ref)]=dict(pins)
            clone=P.Cast_to_FOOTPRINT(f.Duplicate(False));fp[(name,ref)]=clone
        # Board-external NTC remains a real required BOM part, not dropped.
        if name=='Core':
            comp=next(c for c in tree.findall('components/comp') if c.get('ref')=='TH301')
            fields={f.get('name'):f.text or '' for f in comp.findall('fields/field')};nets={v.get('pin'):net.get('name') for net in tree.findall('nets/net') for v in net.findall('node') if v.get('ref')=='TH301'}
            parts[(name,'TH301')]={'ref':'TH301','value':comp.findtext('value'),'fields':fields,'datasheet':comp.findtext('datasheet',''),'pins':{n:xmlpins[("TH301",n)] for n in nets},'nets':nets,'in_bom':True,'dnp':False,'board':name,'source_pos':[0,0],'on_board':False,'footprint':fields.get('Footprint','')}
    def new(ref,value,land,nets,maker,mpn,code='',datasheet='',pininfo=None,name='Core',in_bom=True,note=''):
        if ':' in land:
            library,item=land.split(':',1);f=P.FootprintLoad(str(STOCK/(library+'.pretty')),item)
        else:f=P.FootprintLoad(str(lib),land)
        if f is None:raise ValueError('Missing footprint '+land)
        key=(name,ref);parts[key]={'ref':ref,'value':value,'fields':{'Manufacturer':maker,'MPN':mpn,'LCSC':code,'Description':note},'datasheet':datasheet,'pins':pininfo or {str(n):{'name':str(n),'type':'passive'} for n in nets},'nets':nets,'in_bom':in_bom,'dnp':False,'board':name,'on_board':True,'source_pos':parts.get(key,{}).get('source_pos',[50,75])}
        fp[key]=f
    # SGM41513 pins15/16 are the SAME internally common SYS power output.
    # Model one driver and one passive duplicate, rather than two conflicting
    # drivers in a per-pin audit symbol. No project ERC severity is relaxed.
    chg=parts[('Core','U901')]
    assert chg['fields']['MPN']=='SGM41513YTQF24G/TR'
    assert chg['nets']['15']==chg['nets']['16']=='VSYS_RAW'
    assert chg['pins']['15']['type']==chg['pins']['16']['type']=='power_out'
    chg['pins']['16']={**chg['pins']['16'],'type':'passive'}
    host,pins=bare_host(original[('Core','U501')])
    new('U501','ESP32-S3R8','Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP4x4mm',host,'Espressif','ESP32-S3R8',datasheet=ESP_DOC,pininfo=pins,note='Bare-chip functional migration;8MB3.3V octal PSRAM;GPIO33..37 remain reserved;GPIO2 direct inhibit preserved;RF/boot qualification OPEN.')
    fpn={'1':'FLASH_CS','2':'FLASH_Q','3':'FLASH_WP','4':'GND','5':'FLASH_D','6':'FLASH_CLK','7':'FLASH_HD','8':'VDD_SPI'}
    fpp={str(i):{'name':n,'type':t} for i,n,t in [(1,'CS#','input'),(2,'IO1','bidirectional'),(3,'IO2','bidirectional'),(4,'GND','power_in'),(5,'IO0','bidirectional'),(6,'CLK','input'),(7,'IO3','bidirectional'),(8,'VCC','power_in')]}
    new('U506','GD25Q128ESIG','Package_SO:SOIC-8_5.3x5.3mm_P1.27mm',fpn,'GigaDevice','GD25Q128ESIG','C2758105','https://www.gigadevice.com/product/flash/spi-nor-flash/gd25q128e',fpp,note='128Mbit=16MB;3.3V quad SPI;exact-SI package. Not1.8V R8V;actual supply/boot tests pending.')
    for i,(a,b) in enumerate([('SPICS0_SOC','FLASH_CS'),('SPIQ_SOC','FLASH_Q'),('SPIWP_SOC','FLASH_WP'),('SPID_SOC','FLASH_D'),('SPICLK_SOC','FLASH_CLK'),('SPIHD_SOC','FLASH_HD')],540):
        new('R'+str(i),'0R / Flash SI','Resistor_SMD:R_0402_1005Metric',{'1':a,'2':b},'FH (Fenghua Advanced)','RC-02K0000FT',datasheet=ESP_GUIDE,note='Source-side series tuning land;exact catalog/supply not asserted.')
    new('Y501','40MHz / 12pF','Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm',{'1':'XTAL_P','2':'GND','3':'XTAL_N','4':'GND'},'YXC (Yangxing)','X322540MOB4SI',datasheet=ESP_GUIDE,note='Exact crystal/load and startup/ppm require primary part validation before qualification.')
    for ref,val,a,b,mpn,land in [('L506','24nH / crystal','XTAL_P_SOC','XTAL_P','SDCL1005C24NJTDF','Inductor_SMD:L_0402_1005Metric'),('L507','2nH / RF supply','3V3_AON','3V3_RF','SDCL1608C2N0STDF','Inductor_SMD:L_0603_1608Metric'),('L508','2nH / RF match','LNA_IN','RF_ANT','SDCL1005C2N0STDF','Inductor_SMD:L_0402_1005Metric')]:
        new(ref,val,land,{'1':a,'2':b},'Sunlord',mpn,datasheet=ESP_GUIDE,note='Espressif reference starting network;RF/SI/current qualification not yet passed.')
    for ref,val,net,mpn in [('C520','100n','VDD_SPI','0402B104K250NT'),('C521','1u','VDD_SPI','0402B105K100NT'),('C522','100n','3V3_AON','0402B104K250NT'),('C523','100n','3V3_AON','0402B104K250NT'),('C524','100n','3V3_RF','0402B104K250NT'),('C525','1u','3V3_RF','0402B105K100NT'),('C526','100n','3V3_AON','0402B104K250NT'),('C527','1u','3V3_AON','0402B105K100NT'),('C528','18p / crystal','XTAL_P','0402CG180J500NT'),('C529','18p / crystal','XTAL_N','0402CG180J500NT'),('C530','0.8p / RF','LNA_IN','0402CG0R8C500NT'),('C531','0.8p / RF','RF_ANT','0402CG0R8C500NT')]:
        new(ref,val,'Capacitor_SMD:C_0402_1005Metric',{'1':net,'2':'GND'},'FH (Fenghua Advanced)',mpn,datasheet=ESP_GUIDE)
    # The original module antenna jack was on the module, not J503. J503 is
    # the six-pin debug connector and MUST retain reset/UART/boot pin functions.
    new('J507','RF COAX LANDING','RF_CoaxLanding',{'1':'RF_ANT','2':'GND'},'PCB fabricated terminal','NOT_A_PURCHASED_PART',datasheet=ESP_GUIDE,in_bom=False,note='New RF landing replacing module-integrated antenna connection; exact mainland antenna/coax assembly,impedance and radio test pending.')
    new('J201','U22401-17 / MID-MOUNT','MUP_U22401_17',original[('Core','J201')],'MUP','U22401-17',datasheet=USB_DOC,note='DWG-U22401-XX-01 Rev2 source drawing;0.8mm PCB;external opening bottom center;requires9.24mm edge notch.')
    # Preserve all60 donor logical positions with exact stocked 40P + 20P
    # bottom-contact connectors. Opposite rotations make straight same-side FFC
    # conductors pair Core local p with Display local(N+1-p).
    links=split_60_interconnect(original[('Core','J601')],original[('Display','J1')])
    specs={'J601':('X05A10L40G','C21261162',40),'J602':('X05A10L20G','C2880915',20),
           'J1':('X05A10L40G','C21261162',40),'J4':('X05A10L20G','C2880915',20)}
    for board in ['Core','Display']:
        for ref,nets in links[board].items():
            mpn,code,count=specs[ref]
            new(ref,mpn+' / '+str(count)+'P FFC','XKB_'+mpn,nets,'XKB Connection',mpn,code,FFC_DOC,name=board,
                note='Exact stocked0.5mm bottom-contact 1.0mm-high FFC connector. Cable uses same-side contacts; final cut length,lot and assembly acceptance pending.')
    (out/'INTERCONNECT-MAP.json').write_text(json.dumps({'schema':'panda-seven-mm-interconnect-v1','connectors':{k:{'mpn':v[0],'lcsc':v[1],'contacts':v[2]} for k,v in specs.items()},'cable':links['cable'],'all_60_positions_preserved':True,'same_side_0p3mm_ffc_required':True,'physical_cable_acceptance':False},indent=2)+'\n')
    # Main-cell protection lives on Core so the selected thin pouch does not
    # carry a stacked PCM. Raw cell positive remains BAT_CONN_P; raw cell negative
    # becomes BAT_CELL_N. XB7608A switches only the negative path to system GND.
    # Exact circuit follows XySemi Figure6:1k VDD resistor and0.1uF VDD-cellGND.
    original[('Core','J301')]={'1':'BAT_CONN_P','2':'BAT_CELL_N'}
    new('U907','XB7608A / CELL PROTECTION','XB7608A_CPC5',{'1':'BAT_PROT_VDD','2':'BAT_CELL_N','3':'BAT_CELL_N','4':'GND','5':'GND'},'XySemi (Suzhou Saixin)','XB7608A','C669688','https://atta.szlcsc.com/upload/public/pdf/source/20200622/C669688_97E546DC5F96B64747F350EB5ED3036B.pdf',pininfo={'1':{'name':'VDD','type':'power_in'},'2':{'name':'GND','type':'power_in'},'3':{'name':'GND','type':'power_in'},'4':{'name':'VM','type':'passive'},'5':{'name':'VM','type':'passive'}},note='Single-cell protector with integrated14.5mOhm typ MOSFET;4.30V overcharge,2.40V overdischarge,9A typ overcurrent;CPC5;JLC C669688. Raw cell negative on pins2/3,protected system negative on4/5.')
    new('R940','1k / XB7608A VDD','Resistor_SMD:R_0402_1005Metric',{'1':'BAT_CONN_P','2':'BAT_PROT_VDD'},'FH (Fenghua Advanced)','RC-02K1001FT','C140197','https://www.lcsc.com/product-detail/C140197.html')
    new('C940','100n / XB7608A','Capacitor_SMD:C_0402_1005Metric',{'1':'BAT_PROT_VDD','2':'BAT_CELL_N'},'FH (Fenghua Advanced)','0402B104K250NT','C56392','https://www.lcsc.com/product-detail/C56392.html')
    for ref in ['J301','J302','J502']:
        original_nets=original[('Core',ref)]
        assert all(not value or value.startswith('unconnected-') for key,value in original_nets.items() if not key.isdigit()), 'Mechanical pad unexpectedly carries a function'
        nets={key:value for key,value in original_nets.items() if key.isdigit()}
        new(ref,'SOLDER LANDING / '+ref,'WireLanding_'+str(len(nets)),nets,'PCB fabricated terminal','NOT_A_PURCHASED_PART',in_bom=False,note='Required external insulated harness remains a separate procurement/strain-relief gate,not an omitted function or invented catalog item.')
    # Replace the 6.5mm supercap with a thin mainland primary cell and a
    # hardware series Schottky. BAT54WS pin1 is cathode, pin2 anode: RTC current
    # can flow cell->VBAT, while SD3078's internal charger cannot charge the cell.
    # Firmware must keep register18h charge disabled (reset default), but safety
    # no longer depends on that software setting alone.
    old=parts.pop(('Core','C301'));fp.pop(('Core','C301'))
    new('BT301','CR1216 / RTC PRIMARY','RTC_CR1216_LeadAssembly',{'1':'RTC_CELL_P','2':'GND'},'Yichang Power Glory Technology Co., Ltd.','CR1216',datasheet='https://www.omnergybattery.com/product/cr1216-coin-button-cell-battery-for-remote-controls',note='Mainland primary CR1216,25mAh,12.5x1.6mm;manual pre-welded insulated lead/tab assembly. Never recharge/reflow.')
    new('D306','BAT54WS / RTC charge block','Diode_SMD:D_SOD-323',{'1':'RTC_VBACKUP','2':'RTC_CELL_P'},'Shandong Jingdao Microelectronics','BAT54WS','C438012','https://datasheet.lcsc.com/lcsc/2005292133_Shandong-Jingdao-Microelectronics-BAT54WS_C438012.pdf',pininfo={'1':{'name':'K','type':'passive'},'2':{'name':'A','type':'passive'}},note='Hardware reverse-charge blocker for primary RTC cell;SOD-323;exact JLC C438012.')
    unresolved={}
    for key,part in parts.items():
        if key not in fp:continue
        f=fp[key]
        if f.GetLayer()!=P.F_Cu:f.SetLayerAndFlip(P.F_Cu)
        f.SetPosition(MM(0,0));f.SetOrientationDegrees(0);f.SetLocked(False)
        for p in f.Pads():p.SetNetCode(0)
        landname=part['ref']+'_'+key[0];part['footprint']='Panda7:'+landname
        fields_fp(f,part);f.SetFPIDAsString('Panda7:'+landname)
        if not part['in_bom']:f.SetAttributes(f.GetAttributes() | P.FP_EXCLUDE_FROM_BOM)
        P.FootprintSave(str(lib),f)
        actual=lib/(landname+'.kicad_mod')
        if not actual.exists():raise ValueError('Local footprint failed save '+str(actual))
    defs=[];report={'source_hashes':hashes,'parts_added':[],'unresolved':unresolved,'native_routing_complete':False,'manufacturing_release':False,'boards':{}}
    for name,source in sourcepaths.items():
        subset={ref:p for (b,ref),p in parts.items() if b==name};root,definitions=schematic(out,name,subset);defs+=definitions
        (out/(name+'.kicad_pro')).write_bytes(source.with_suffix('.kicad_pro').read_bytes())
        if source.with_suffix('.kicad_dru').exists():(out/(name+'.kicad_dru')).write_bytes(source.with_suffix('.kicad_dru').read_bytes())
        report['boards'][name]={'root_uuid':root,'parts':subset}
    unique={}
    for definition in defs:
        m=re.match(r'\(symbol\s+"([^"]+)"',definition);name=m[1].split(':',1)[1]
        unique[name]=definition.replace('"Panda7:'+name+'"',Q(name),1)
    (out/'Panda7.kicad_sym').write_text('(kicad_symbol_lib(version 20241209)(generator "kicad_symbol_editor")'+''.join(unique.values())+')\n')
    (out/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Panda7")(type "KiCad")(uri "${KIPRJMOD}/Panda7.kicad_sym")(options "")(descr "Explicit source-verified pin/net intent")))\n')
    (out/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Panda7")(type "KiCad")(uri "${KIPRJMOD}/Panda7.pretty")(options "")(descr "Candidate local lands")))\n')
    for name,source in sourcepaths.items():
        run(['sch','export','netlist','--format','kicadxml','--output',out/(name+'-netlist.xml'),out/(name+'.kicad_sch')],out/(name+'-netlist.log'))
        root=ET.parse(out/(name+'-netlist.xml'));actual={(v.get('ref'),v.get('pin')):net.get('name') for net in root.findall('nets/net') for v in net.findall('node')}
        board=P.BOARD();board.SetCopperLayerCount(4 if name=='Core' else 2);board.GetDesignSettings().SetBoardThickness(P.FromMM(.8))
        if name=='Core':
            assert board.SetLayerType(P.In1_Cu,P.LT_POWER), 'Failed to reserve In1 as the GND/power reference plane'
        netobjects={}
        for net in sorted(set(actual.values())):
            obj=P.NETINFO_ITEM(board,net);board.Add(obj);netobjects[net]=obj
        outline=plan['boards'][name]['outline_xy_mm']
        for a,b in zip(outline,outline[1:]+outline[:1]):
            edge=P.PCB_SHAPE(board);edge.SetShape(P.SHAPE_T_SEGMENT);edge.SetLayer(P.Edge_Cuts);edge.SetStart(MM(*a));edge.SetEnd(MM(*b));edge.SetWidth(P.FromMM(.05));board.Add(edge)
        placed=[];pending=[];occupied=[]
        fixed={'J201':(37.5,105.2,0),'J501':(60.8,96,90),'J601':(42.5,76.2,270),'J602':(42.5,94.2,270),'U501':(63.5,76.5,0),'U506':(63.5,65.5,0),'Y501':(62,85,0)} if name=='Core' else {'J1':(35,76.2,90),'J4':(35,94.2,90),'J2':(18,96,0),'R5':(7,68,0)}
        targets={'U901':(64,17),'U902':(64,30),'U601':(64,48),'U302':(63,44),'BT301':(63.5,57),'D306':(63,50),'U903':(64,40),'U904':(47,73),'U905':(15,105),'U503':(64,8),'U906':(47,95),'U907':(47,104),'R940':(51,104),'C940':(51,101),'J301':(55,107),'U501':(63.5,76.5),'U506':(63.5,65.5)}
        refs={ref:f for (b,ref),f in fp.items() if b==name}
        regions=plan['boards'][name]['regions_xyxy_mm']
        if name=='Core':regions=[r[:] for r in regions];regions[-1][3]=111
        origins={ref:p['source_pos'] for ref,p in report['boards'][name]['parts'].items()}
        for ref,f in refs.items():
            part=parts[(name,ref)];f.SetPath(P.KIID_PATH('/'+report['boards'][name]['root_uuid']+'/'+UID(name+'/'+ref)))
            for pad in f.Pads():
                n=pad.GetNumber()
                if n and (ref,n) in actual:
                    expected=part['nets'].get(n,'');net=actual[(ref,n)]
                    if expected and not expected.startswith('unconnected-') and net!=expected:raise ValueError('Unexpected schematic net '+ref+'.'+n+':'+net+' vs '+expected)
                    pad.SetNet(netobjects[net]);pad.SetPinType(part['pins'][n]['type'].split('+')[0]);pad.SetPinFunction(part['pins'][n]['name'])
            board.Add(f)
        for ref,(x,y,angle) in fixed.items():
            f=refs[ref];f.SetOrientationDegrees(angle);f.SetPosition(MM(x,y));f.SetLocked(True);occupied.append(bbox(f));placed.append(ref)
        if name=='Core':occupied.append([32.88,105.45,42.12,111])
        remaining=[]
        for ref,f in refs.items():
            if ref in placed:continue
            if ref in unresolved:
                pending.append(ref);continue
            r=bbox(f);remaining.append(((r[2]-r[0])*(r[3]-r[1]),ref))
        for _,ref in sorted(remaining,reverse=True):
            f=refs[ref];part=parts[(name,ref)]
            if name=='Display':target=(17,81)
            elif ref in targets:target=targets[ref]
            elif ref in ['L506','C528','C529']:target=(62,85)
            elif ref in ['L508','C530','C531','J507']:target=(58,74)
            elif ref.startswith('R54') or ref in ['C520','C521']:target=(63.5,69)
            elif ref in ['C522','C523','C524','C525','C526','C527','L507']:target=(63,77)
            else:
                closest=min([k for k in targets if k in origins],key=lambda k:math.dist(origins[ref],origins[k]));target=targets[closest]
            best=None
            for angle in [0,90,180,270]:
                f.SetOrientationDegrees(angle);f.SetPosition(MM(0,0));off=bbox(f)
                for a,b,c,d in regions:
                    lx=math.ceil((a+.2-off[0])*2)/2;ly=math.ceil((b+.2-off[1])*2)/2
                    for i in range(max(0,int((c-.2-off[2]-lx)*2)+1)):
                        x=lx+i*.5
                        for j in range(max(0,int((d-.2-off[3]-ly)*2)+1)):
                            y=ly+j*.5;score=math.dist((x,y),target)
                            if best and score>=best[0]:continue
                            r=[off[0]+x,off[1]+y,off[2]+x,off[3]+y]
                            if not any(intersects(r,o) for o in occupied):best=(score,x,y,angle,r)
            if best:
                _,x,y,angle,r=best;f.SetPosition(MM(x,y));f.SetOrientationDegrees(angle);occupied.append(r);placed.append(ref)
            else:pending.append(ref)
        for i,ref in enumerate(pending):refs[ref].SetPosition(MM(112+i%4*23,12+i//4*23));refs[ref].SetOrientationDegrees(0)
        # Apply the reviewed USB clamp move AFTER deterministic legacy packing
        # so no other component shifts. Only D201 changes pose; its exact part,
        # pad functions and all nets are retained. This brings the clamp close
        # to the bottom-centre USB receptacle rather than the old mid-side site.
        if name=='Core':
            clamp=refs['D201'];clamp.SetOrientationDegrees(90)
            clamp.SetPosition(MM(30.5,102.75));clamp.SetLocked(True)
        # Core In1 is a continuous GND reference plane. The polygon follows the
        # actual concave/USB-notched outline; KiCad fill applies native edge/pad
        # clearances. This is not a signal-routing layer.
        if name=='Core':
            z=P.ZONE(board);z.SetLayer(P.In1_Cu);z.SetNetCode(netobjects['GND'].GetNetCode())
            z.SetLocalClearance(P.FromMM(.20));z.SetMinThickness(P.FromMM(.15));z.SetPadConnection(P.ZONE_CONNECTION_THERMAL)
            z.SetThermalReliefGap(P.FromMM(.20));z.SetThermalReliefSpokeWidth(P.FromMM(.25))
            chain=P.SHAPE_LINE_CHAIN()
            for x,y in outline:chain.Append(MM(x,y))
            chain.SetClosed(True);z.AddPolygon(chain);board.Add(z)
            board.BuildConnectivity();P.ZONE_FILLER(board).Fill(board.Zones())
            report['boards'][name]['in1_gnd_reference_plane']=True
        title=board.GetTitleBlock();title.SetTitle('PANDA7 '+name+' LOW-PROFILE ECO / UNROUTED');title.SetRevision('CANDIDATE / NOT FOR FAB')
        pcb=out/(name+'.kicad_pcb');P.SaveBoard(str(pcb),board)
        # Stable generated object UUIDs; do not rewrite path/schematic identities.
        text=pcb.read_text();seq=iter(range(1000000));text=re.sub(r'\(uuid "[^\"]+"\)',lambda m:'(uuid "'+UID(name+'/object/'+str(next(seq)))+'")',text);pcb.write_text(text)
        (out/(name+'.kicad_pro')).write_bytes(source.with_suffix('.kicad_pro').read_bytes())
        if name=='Display':
            route_plan=ROOT/'seven_mm_display_routing.json'
            report['boards'][name]['routing_replay']=apply_routing(pcb,route_plan,'Display') if route_plan.exists() else {'pending':True,'reason':'Current exact 40P+20P interconnect placement requires a fresh native-clean Display routing plan.'}
        if name=='Core':
            route_plan=ROOT/'seven_mm_core_routing.json'
            report['boards'][name]['routing_replay']=apply_routing(pcb,route_plan,'Core') if route_plan.exists() else {'pending':True,'reason':'Core routing is not yet frozen from a fully native-verified predecessor.'}
        report['boards'][name].update(pcb_sha256=sha(pcb),placed_refs=sorted(placed),review_refs=sorted(pending),placement_optimized=False)
        # Native saving a fresh BOARD writes default project settings; restore
        # the source rule file AFTER save, never accidentally relax or replace it.
        (out/(name+'.kicad_pro')).write_bytes(source.with_suffix('.kicad_pro').read_bytes())
        run(['sch','erc','--severity-all','--format','json','--output',out/(name+'-erc.json'),out/(name+'.kicad_sch')],out/(name+'-erc.log'))
        run(['pcb','drc','--refill-zones','--save-board','--severity-all','--schematic-parity','--format','json','--output',out/(name+'-drc.json'),pcb],out/(name+'-drc.log'))
        drc=json.loads((out/(name+'-drc.json')).read_text());erc=json.loads((out/(name+'-erc.json')).read_text())
        report['boards'][name]['pcb_sha256']=sha(pcb)
        report['boards'][name]['native_counts']={'drc':len(drc['violations']),'open':len(drc['unconnected_items']),'parity':len(drc.get('schematic_parity',[])),'erc':sum(len(s.get('violations',[])) for s in erc['sheets'])}
        print(name,report['boards'][name]['native_counts'],'placed',len(placed),'review',pending,flush=True)
    assert all(sha(p)==hashes[n] for n,p in sourcepaths.items()),'Donor CAD changed'
    (out/'CANDIDATE-STATUS.json').write_text(json.dumps(report,indent=2)+'\n')
    print('NEW_CANDIDATE',out,'NOT_FOR_FABRICATION',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.output)
