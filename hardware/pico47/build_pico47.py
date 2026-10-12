#!/usr/bin/env python3
"""Build real E0 Core/Display native CAD from a verified Product-D donor.

This is an unrouted electrical redesign, not a manufacturing release. The exact
Pico battery pack and full touch/frontlight stack have no verified drawing yet.
Never overwrites donor CAD, source PCB, supplier records or an existing output.
"""
from pathlib import Path
import argparse, copy, hashlib, json, math, os, re, shutil, subprocess, sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
LEGACY=HERE.parent/'thin18-compact'
sys.path.insert(0,str(LEGACY))
import wx
APP=wx.GetApp() or wx.App(False)
import pcbnew as P
from build_seven_mm_candidate import schematic, fields_fp, MM, UID, bbox, intersects
from seven_mm_low_profile_parts import custom_land
from seven_mm_native_evidence import verify_native_clean
from seven_mm_sourcing import inspect_fields, validate as validate_sourcing, CONTRACT as SOURCING
from _split_c1_common import kicad_cli

STOCK=Path(os.environ.get('KICAD_FOOTPRINT_DIR','/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'))
CONTRACT=HERE/'design.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
FH='FH (Fenghua Advanced)'

def require(ok,msg):
    if not ok:raise ValueError(msg)

def run(args,log):
    with Path(log).open('w') as f:
        subprocess.run([kicad_cli(),*map(str,args)],cwd=Path(log).parent,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)


def load_parts(donor,name,board):
    tree=ET.parse(donor/(name+'-netlist.xml')).getroot()
    entries={c.get('ref'):c for c in tree.findall('components/comp') if not c.get('ref','').startswith('#')}
    pins={};nets={}
    for n in tree.findall('nets/net'):
        for node in n.findall('node'):
            ref=node.get('ref');num=node.get('pin');net=n.get('name','')
            pins.setdefault(ref,{})[num]={'name':node.get('pinfunction') or num,'type':node.get('pintype','passive').split('+')[0]}
            nets.setdefault(ref,{})[num]='' if net.startswith('unconnected-') else net
    fps={f.GetReference():P.Cast_to_FOOTPRINT(f.Duplicate(False)) for f in board.GetFootprints()}
    parts={}
    for ref,c in entries.items():
        f=fps.get(ref)
        props={v.get('name'):v.text or '' for v in c.findall('fields/field')}
        ps=copy.deepcopy(pins.get(ref,{}));ns=copy.deepcopy(nets.get(ref,{}))
        if f:
            for pad in f.Pads():
                num=pad.GetNumber()
                if not num:continue
                ps.setdefault(num,{'name':pad.GetPinFunction() or num,'type':pad.GetPinType().split('+')[0] or 'passive'})
                ns.setdefault(num,'')
        parts[ref]={'ref':ref,'value':c.findtext('value',''),'fields':props,'datasheet':c.findtext('datasheet','') or '',
           'pins':ps,'nets':ns,'in_bom':not f.IsExcludedFromBOM() if f else True,'dnp':f.IsDNP() if f else False,
           'board':name,'on_board':f is not None,'footprint':c.findtext('footprint',''),
           'source_pos':[P.ToMM(f.GetPosition().x),P.ToMM(f.GetPosition().y)] if f else [0,0],
           'source_angle':f.GetOrientationDegrees() if f else 0}
    return parts,fps

def create(out,donor):
    out=Path(out).resolve();donor=Path(donor).resolve()
    require(not out.exists(),'Output exists; choose a fresh candidate')
    require(not out.is_relative_to(REPO) or out.is_relative_to(REPO/'.work'),'Generated native output must be ignored/external')
    require(not donor.is_relative_to(out),'Output cannot contain donor')
    plan=json.loads(CONTRACT.read_text())
    from pico47_contract import validate
    validate(plan)
    from pico47_placement import load_layout, add_mcu_ground_vias, route_ordered_data_necks, add_display_ground_return, LAYOUT
    ordered_layout=load_layout()
    require(plan['revision']=='E0' and plan['manufacturing_release'] is False,'Wrong redesign contract')
    require(plan['donor_sourcing_sha256']==sha(SOURCING),'Wrong sourced predecessor')
    require(plan['donor_product_source_sha256']==sha(LEGACY/'seven_mm_product_source.json'),'Wrong routing predecessor')
    sourcing=json.loads(SOURCING.read_text());validate_sourcing(sourcing);inspect_fields(donor,sourcing)
    receipt=json.loads((donor/'SOURCING-REBUILD.json').read_text())
    require(receipt['contract_sha256']==sha(SOURCING),'Stale donor metadata')
    proof={n:verify_native_clean(donor/(n+'.kicad_pcb')) for n in ['Core','Display']}
    require(all(proof[n]['pcb_sha256']==receipt['native'][n]['pcb_sha256'] for n in proof),'Donor changed after source binding')
    before={str(p):sha(p) for p in donor.rglob('*') if p.is_file() and p.suffix in {'.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru','.kicad_mod','.kicad_sym'}}
    source={n:P.LoadBoard(str(donor/(n+'.kicad_pcb'))) for n in ['Core','Display']}
    old={n:load_parts(donor,n,source[n]) for n in source}
    parts={'Core':old['Core'][0],'Display':{}};fps={'Core':old['Core'][1],'Display':{}}
    out.mkdir(parents=True);lib=out/'Panda47.pretty';lib.mkdir()
    newly_added={'Core':set(),'Display':set()}
    specs=[]
    def new(board,ref,value,land,nets,maker='',mpn='',code='',datasheet='',pininfo=None,note='',dnp=False,in_bom=True):
        if isinstance(land,tuple):
            b,r=land;f=P.Cast_to_FOOTPRINT(old[b][1][r].Duplicate(False))
        else:
            library,name=land.split(':',1);f=P.FootprintLoad(str(STOCK/(library+'.pretty')),name)
        require(f is not None,'Missing footprint '+str(land))
        fields={'Manufacturer':maker,'MPN':mpn,'LCSC':code,'Description':note,'PandaRevision':'E0',
                'PandaQualification':'UNQUALIFIED_ELECTRICAL_CANDIDATE','PandaSupplyStatus':'CATALOG_IDENTITY_ONLY' if code else 'EXACT_SUPPLY_NOT_VERIFIED'}
        ns={str(k):v for k,v in nets.items()}
        pininfo=pininfo or {n:{'name':n,'type':'passive'} for n in ns}
        parts[board][ref]={'ref':ref,'value':value,'fields':fields,'datasheet':datasheet,'pins':pininfo,'nets':ns,
              'in_bom':in_bom,'dnp':dnp,'board':board,'on_board':True,'source_pos':[0,0],'source_angle':0}
        fps[board][ref]=f;newly_added[board].add(ref)
        specs.append({'board':board,'ref':ref,'value':value,'manufacturer':maker,'mpn':mpn,'lcsc':code,'catalog_code_present':bool(code),'qualified':False})
        return parts[board][ref]
    def resistor(board,ref,value,a,b):
        known={'1k':('RC-02K1001FT','C140197'),'22':('RC-02K22R0FT','C324769'),'10k':('RC-02K1002FT','C140215'),'100k':('RC-02K1003FT','C140219'),'0':('RC-02000FT','C140225')}
        mpn,code=known.get(value,('',''))
        return new(board,ref,value,('Core','R529'),{'1':a,'2':b},FH,mpn,code,
             'https://www.lcsc.com/product-detail/'+code+'.html' if code else '',note='Electrical value target; empty MPN means an actual exact domestic part is still required.')
    def capacitor(board,ref,value,a,b):
        known={'100n/25V/0402':('0402B104K250NT','C56392',('Core','C524')),
               '4.7u/25V/0805':('0805B475K250NT','C37818',('Display','C4')),
               '1u/25V/0603':('0603B105K250NT','C59302',('Display','C1'))}
        mpn,code,land=known.get(value,('','','Capacitor_SMD:C_0805_2012Metric'))
        return new(board,ref,value,land,{'1':a,'2':b},FH,mpn,code,note='Voltage, DC bias and ripple ratings require exact datasheet selection for any blank MPN.')
    # Native GPIO remap. In the bare QFN,36 isGPIO48 and37 isGPIO47.
    core=parts['Core'];host=core['U501']
    for pin in [str(i) for i in range(5,20)]+['21','22','23','24','25','26','27','36','37','38','39','40','41','42','43','44','45','47','48','49','50','51','52']:
        host['nets'][pin]=''
    for gpio,item in plan['gpio'].items():
        p=str(item['package_pin']);host['nets'][p]=item['net'];host['pins'][p]={'name':'GPIO'+gpio,'type':'bidirectional'}
    for g,p in [(33,38),(34,39),(35,40),(36,41),(37,42)]:
        host['pins'][str(p)]={'name':'GPIO'+str(g)+'_RESERVED_OCTAL_PSRAM','type':'no_connect'}
        host['nets'][str(p)]=''
    host['fields']['Description']='E0 bare-chip pin map: physical36=GPIO48,37=GPIO47. All33 usableGPIO allocated. KeepGPIO33..37 reserved,GPIO2 direct inhibit,GPIO19/20USB. Incompatible with D firmware.'
    for ref,oldnet,newnet in [('R512','EPD_LE','P47_D8_SRC'),('R513','EPD_OE','P47_BUS_SELECT')]:
        require(core[ref]['nets']['1']==oldnet,'Unexpected strap predecessor')
        core[ref]['nets']['1']=newnet;core[ref]['fields']['Description']='E0 explicit10k strap pulldown for '+newnet
    core['U601']['nets']['18']='P47_BUS_OE_N';core['U601']['pins']['18']={'name':'P15','type':'bidirectional'}
    for ref,count in [('J601','40'),('J602','20')]:
        core[ref]['nets']={**plan['interconnect'][count],'MP':'GND'}
        core[ref]['pins']={n:{'name':n,'type':'passive'} for n in core[ref]['nets']}
        core[ref]['fields']['Description']='E0 parallel display interconnect. NOT PIN-COMPATIBLE WITH PRODUCT D.'
    core['J301']['fields']['Description']='Historical two-pad bench landing ONLY. Not the Pico pack connector. Keep charge inhibited until exact protected2050mAh Pico pack,NTC/polarity/CV/current and protection interaction are confirmed.'
    core['J301']['fields']['PandaRequiredReplacement']='EXACT_PICO_2050MAH_PACK_SOCKET_NOT_YET_IDENTIFIED'
    # Preserve the old frontlight/touch electrical domains, not the old module fit claim.
    for ref in ['J803','J804']:
        core[ref]['fields']['PandaModuleCompatibility']='E0 TOUCH/FRONTLIGHT ASSEMBLY PINOUT AND CONTACT SIDE UNCONFIRMED;NOT VERIFIED BY OLD FT01C DRAWING'
    muxpin={'1':('IN','input'),'8':('GND','power_in'),'15':('EN_N','input'),'16':('VCC','power_in')}
    for idx,ref in enumerate(['U710','U711']):
        ns={'1':'P47_BUS_SELECT','8':'GND','15':'P47_BUS_OE_N','16':'3V3_AON'};pi={p:{'name':n,'type':t} for p,(n,t) in muxpin.items()}
        for item,(a,b,common) in zip(plan['mux']['channels'][idx*4:idx*4+4],plan['mux']['source_terminal_pins']):
            for p,n,nm in [(a,item['select_0_net'],'S1'),(b,item['select_1_net'],'S2'),(common,item['common_net'],'D')]:
                ns[str(p)]=n;pi[str(p)]={'name':nm+str(item['channel']%4),'type':'passive'}
        new('Core',ref,'SGM330A-YTS/TR','Package_SO:TSSOP-16_4.4x5mm_P0.65mm',ns,'SGMICRO','SGM330A-YTS/TR','C700205',plan['evidence']['mux_datasheet'],pi,
            note='Four bidirectional SPDT channels,IN0=SD/UART,IN1=EPD. EN_N1 isolates all channels before selection.3.3V digital timing and handover require bench qualification.')
        capacitor('Core','C'+str(710+idx),'100n/25V/0402','3V3_AON','GND')
    for i in range(16):resistor('Core','R'+str(710+i),'22','P47_D'+str(i)+'_SRC','P47_D'+str(i))
    for i,n in enumerate(['XCL','XLE','XSTL','CKV','SPV'],726):resistor('Core','R'+str(i),'22','P47_'+n+'_SRC','P47_'+n)
    resistor('Core','R731','10k','P47_XSTL_SRC','GND')
    resistor('Core','R732','10k','P47_BUS_OE_N','GND')
    new('Core','TP712','P47_PGOOD','TestPoint:TestPoint_Pad_D1.0mm',{'1':'P47_PGOOD'},'PCB fabricated terminal','NOT_A_PURCHASED_PART',in_bom=False,note='Physical PMIC power-good probe; not a claim that VCOM is valid.')
    # New Display native connector geometry from the reviewed XKB local lands.
    for ref,donor_ref,count in [('J1','J601',40),('J4','J602',20)]:
        ns={str(count+1-int(p)):n for p,n in plan['interconnect'][str(count)].items()};ns['MP']='GND'
        oldp=old['Core'][0][donor_ref]
        new('Display',ref,oldp['value'],('Core',donor_ref),ns,'XKB Connection',oldp['fields']['MPN'],oldp['fields']['LCSC'],oldp['datasheet'],note='E0 opposite-contact mapping; actual cable fold/length not yet qualified.')
    oldp=old['Core'][0]['J601']
    new('Display','J820','X05A10L40G / E0470A01',('Core','J601'),{**plan['panel']['source_family_pinmap'],'MP':'GND'},'XKB Connection','X05A10L40G','C21261162',oldp['datasheet'],note='40pin0.5mm electrical mapping from E0470A01-AF-S family. Exact Pico full suffix,contact face and fold remain unverified. Never plug old24pinSPI panel.')
    # SY7636A perimeter follows manufacturer p24,NOT a generic grounded exposed pad.
    sy_pads=[]
    for i in range(12):
        v=round(-2.2+i*.4,5)
        sy_pads.extend([(str(i+1),-2.95,v,.8,.2),(str(13+i),v,2.95,.2,.8),
                        (str(25+i),2.95,-v,.8,.2),(str(37+i),-v,-2.95,.2,.8)])
    sy_pads.append(('49',0,0,4.4,4.4))
    (lib/'SY7636ARMC_isolated_EP.kicad_mod').write_text(custom_land('SY7636ARMC_isolated_EP',sy_pads,[-3,-3,3,3],
        'Manufacturer QFN6x6-48 p24:0.4pitch0.8x0.2leads,6.7span,4.4squareEP. EP49 is internally NEGATIVE and MUST NOT be GND. No external tie or thermal vias until current manufacturer approval.'))
    sy=P.FootprintLoad(str(lib),'SY7636ARMC_isolated_EP')
    old['Display'][1]['SY_TEMPLATE']=sy
    names={1:'VREF',3:'VNEG',4:'VNEG_IN',7:'VCC',8:'AGND1',10:'VIN',12:'VCOM_EN',15:'VCOM',17:'SCL',18:'SDA',21:'EN',23:'PGOOD',24:'VN_IN',25:'VN_LX',26:'VN',28:'VEE_DRV',30:'VEE_D',31:'VEE_FB',32:'PGND2',33:'VDDH_FB',34:'VDDH_D',35:'VDDH_DIS',36:'VDDH_DRV',40:'VP_LX',41:'PGND1',42:'VP',44:'VPOS',47:'TS',48:'AGND2',49:'EP_NEGATIVE_ISOLATED'}
    ns={str(i):'' for i in range(1,50)}
    ns.update({str(k):v for k,v in {1:'P47_VREF',3:'P47_VNEG',4:'P47_VN',7:'P47_VCC',8:'GND',10:'VSYS_RAW',12:'P47_VCOM_EN',15:'P47_VCOM',17:'I2C_SCL',18:'I2C_SDA',21:'P47_HV_EN',23:'P47_PGOOD',24:'VSYS_RAW',25:'P47_VN_LX',26:'P47_VN',28:'P47_VEE_DRV',30:'P47_VEE_BASE',31:'P47_VEE_FB',32:'GND',33:'P47_VGH_FB',34:'P47_VGH_BASE',35:'P47_VGH',36:'P47_VGH_DRV',40:'P47_VP_LX',41:'GND',42:'P47_VP',44:'P47_VPOS',47:'P47_TS',48:'GND'}.items()})
    pi={}
    for p,n in ns.items():
        i=int(p);typ='no_connect' if not n else 'input'
        if i in [8,10,24,32,41,48,4]:typ='power_in'
        elif i in [1,3,7,15,26,42,44]:typ='power_out'
        elif i in [25,28,30,34,36,40]:typ='output'
        elif i==18:typ='bidirectional'
        elif i==23:typ='open_collector'
        pi[p]={'name':names.get(i,'TP_FLOAT' if i in [13,38,39] else 'NC'),'type':typ}
    new('Display','U810','SY7636ARMC',('Display','SY_TEMPLATE'),ns,'Silergy','SY7636ARMC','',plan['evidence']['pmic_product'],pi,
        note='Source-table exact pin map;TP/NC float. Exposed pad must NOT connect GND.2020 reference requires current manufacturer recheck; not authorized for power-on.')
    # AuxiliaryGPIO: address0x21; first legacy expander remains0x20.
    exp=copy.deepcopy(old['Core'][0]['U601']);ex={str(i):'' for i in range(1,25)}
    ex.update({'1':'EXP_INT','2':'GND','3':'GND','4':'P47_HV_EN','5':'P47_VCOM_EN','6':'P47_MODE','7':'P47_XOE','12':'GND','13':'P47_PGOOD','14':'HW_ARM_GPIO','21':'3V3_AON','22':'I2C_SCL','23':'I2C_SDA','24':'3V3_AON'})
    epi=copy.deepcopy(exp['pins'])
    for p in ex:
        epi.setdefault(p,{'name':p,'type':'bidirectional'})
        if p not in ['1','2','3','12','21','22','23','24']:epi[p]['type']='bidirectional'
    epi['4']={'name':'P00_ENABLE_MONITOR','type':'input'}
    new('Display','U811','XL9535 / ADDRESS0x21',('Core','U601'),ex,'XINLUDA','XL9535','C561273',exp['datasheet'],epi,
        note='Address A0=1,A1=A2=0. P00INPUT ONLY monitors HV_EN driven by nativeGPIO2 viaR813;P01VCOM_EN,P02MODE,P03XOE;P10PGOOD,P11HW_ARM inputs. Never drive P00. No old D control masks may be used.')
    # Larger actual power inductor lands; never retain the old3mm footprint
    # when replacing a 1A-class part with a7mm part.
    induct=plan['power_stage']['inductors']
    (lib/'MWSA0618S.kicad_mod').write_text(custom_land('MWSA0618S',induct['pads'],[-3.65,-3.4,3.65,3.4],
        'Sunlord MWSA0618S manufacturer p3 lands I2.35,J3.7,H3.5mm. Maximum body7.3x6.8mm,height1.8mm. Current table p10 preserved; hot fault qualification remains open.'))
    old['Display'][1]['INDUCT_TEMPLATE']=P.FootprintLoad(str(lib),'MWSA0618S')
    for ref,a,b in [('L801','VSYS_RAW','P47_VP_LX'),('L802','P47_VN_LX','GND')]:
        new('Display',ref,'4.7uH / MWSA0618S-4R7MT',('Display','INDUCT_TEMPLATE'),{'1':a,'2':b},'Sunlord',induct['mpn'],induct['catalog_code'],induct['source_url'],
            note='Manufacturer DCR62mOhm max,height1.8mm max; Isat columns Max/Typ4/5A and Irms3.5/4A. Do NOT rename a Max column as a guaranteed minimum. Startup/hot/short-circuit margin remains unqualified.')
    resistor('Display','R813','1k','HW_ARM_GPIO','P47_HV_EN')
    for ref,a,k in [('D801','P47_VP_LX','P47_VP'),('D802','P47_VN','P47_VN_LX')]:
        new('Display',ref,'MBR0530 / PEAK REVIEW',('Display','D1'),{'1':k,'2':a},'JSCJ','MBR0530','C77336',old['Display'][0]['D1']['datasheet'],
             {'1':{'name':'K','type':'passive'},'2':{'name':'A','type':'passive'}},note='Engineering0.5A/30V Schottky selection; surge/current-loss review pending.')
    for ref,a,k,mid in [('D803','P47_VGH_BASE','P47_VGH','P47_PUMP_POS'),('D804','P47_VGL','P47_VEE_BASE','P47_PUMP_NEG')]:
        new('Display',ref,'BAV99','Package_TO_SOT_SMD:SOT-23',{'1':a,'2':k,'3':mid},'JSCJ','BAV99','C68983','https://www.lcsc.com/product-detail/C68983.html',
            {'1':{'name':'A1','type':'passive'},'2':{'name':'K2','type':'passive'},'3':{'name':'K1_A2','type':'passive'}},note='Series diode pair for positive/negative charge pump; exact supplier latest diode drawing review remains open.')
    caps=[('C801','10u/10V/0805','VSYS_RAW','GND'),('C802','4.7u/25V/0805','P47_VP','GND'),
      ('C803','10u/10V/0805','VSYS_RAW','GND'),('C804','4.7u/25V/0805','P47_VN','GND'),
      ('C805','4.7u/25V/0805','P47_VPOS','GND'),('C806','4.7u/25V/0805','P47_VNEG','GND'),
      ('C807','1u/50V/0805','P47_VGH_BASE','GND'),('C808','47n/50V/0805','P47_PUMP_POS','P47_VGH_DRV'),('C809','1u/50V/0805','P47_VGH','GND'),
      ('C810','1u/50V/0805','P47_VEE_BASE','GND'),('C811','47n/50V/0805','P47_PUMP_NEG','P47_VEE_DRV'),('C812','1u/50V/0805','P47_VGL','GND'),
      ('C813','4.7u/25V/0805','P47_VCOM','GND'),('C814','4.7u/25V/0805','P47_VCC','GND'),('C815','100n/25V/0402','P47_VREF','GND'),
      ('C816','10u/10V/0805','VSYS_RAW','GND'),('C817','100n/25V/0402','3V3_AON','GND')]
    for r,v,a,b in caps:capacitor('Display',r,v,a,b)
    for r,v,a,b in [('R801','442k/0.1%','P47_VGH','P47_VGH_FB'),('R802','21k/0.1%','P47_VGH_FB','GND'),
      ('R803','750k/0.1%','P47_VGL','P47_VEE_FB'),('R804','59k/0.1%','P47_VEE_FB','P47_VREF'),
      ('R805','7.5k/1%','P47_VREF','P47_TS'),('R806','36k/1%','P47_TS','GND'),
      ('R807','10k','P47_PGOOD','3V3_AON'),('R808','100k','P47_HV_EN','GND'),('R809','100k','P47_VCOM_EN','GND'),
      ('R810','100k','P47_MODE','GND'),('R811','100k','P47_XOE','GND'),('R812','100k','P47_VGL','GND')]:resistor('Display',r,v,a,b)
    new('Display','TH801','10k NTC / CURVE TO QUALIFY','Resistor_SMD:R_0402_1005Metric',{'1':'P47_TS','2':'GND'},FH,'','',note='Required display thermistor. Exact domestic10k curve must match/qualify SY temperature conversion,not silently substitute the battery NTC.')
    for i,n in enumerate(['VGH','VGL','VPOS','VNEG','VCOM','BORDER_REVIEW'],801):
        new('Display','TP'+str(i),'P47_'+n,'TestPoint:TestPoint_Pad_D1.0mm',{'1':'P47_'+n},'PCB fabricated terminal','NOT_A_PURCHASED_PART','',in_bom=False,note='Probe landing. BORDER bias remains unresolved until exact panel instruction;NOT automatically grounded.')
    # Normalize footprints and regenerate truthful native local libraries.
    definitions=[];roots={};positions={};source_footprints={n:{f.GetReference():f for f in b.GetFootprints()} for n,b in source.items()}
    for name in ['Core','Display']:
        for ref,f in fps[name].items():
            p=parts[name][ref]
            f.SetPosition(MM(0,0));f.SetOrientationDegrees(0);f.SetLayer(P.F_Cu);f.SetLocked(False)
            f.SetDNP(p['dnp'])
            for pad in f.Pads():
                pad.SetNetCode(0)
                if name=='Display' and ref=='U810' and pad.GetNumber() in ['8','32','41','48']:
                    pad.SetLocalZoneConnection(P.ZONE_CONNECTION_FULL)
                if name=='Display' and pad.GetNumber() in plan['power_stage']['display_solid_ground_pads'].get(ref,[]):
                    require(p['nets'][pad.GetNumber()]=='GND','Solid plane connection must be actual GND')
                    pad.SetLocalZoneConnection(P.ZONE_CONNECTION_FULL)
                if name=='Core' and pad.GetNumber() in ordered_layout['core_solid_ground_pads'].get(ref,[]):
                    require(p['nets'][pad.GetNumber()]=='GND','Only actual ground pads get plane connections')
                    pad.SetLocalZoneConnection(P.ZONE_CONNECTION_FULL)
                if name=='Core' and ref=='C515' and pad.GetNumber()=='2':
                    pad.SetLocalZoneConnection(P.ZONE_CONNECTION_FULL)
            p['footprint']='Panda47:'+ref+'_'+name
            fields_fp(f,p);f.SetFPIDAsString(p['footprint'])
            f.SetAttributes((f.GetAttributes() | P.FP_EXCLUDE_FROM_BOM) if not p['in_bom'] else (f.GetAttributes() & ~P.FP_EXCLUDE_FROM_BOM))
            P.FootprintSave(str(lib),f)
        root,defs=schematic(out,name,parts[name]);definitions+=defs;roots[name]=root
        sch=out/(name+'.kicad_sch');text=sch.read_text().replace('low-profile ECO / not fabrication release','E0470A01 PARALLEL E0 / UNROUTED / NOT FOR FAB').replace('7MM-CANDIDATE','P47-E0')
        sch.write_text(text)
        for ext in ['.kicad_pro','.kicad_dru']:
            src=donor/(name+ext)
            if src.exists():(out/(name+ext)).write_bytes(src.read_bytes())
    unique={}
    for d in definitions:
        m=re.match(r'\(symbol\s+"([^"]+)"',d);n=m[1].split(':',1)[1];unique[n]=d.replace('"Panda7:'+n+'"',json.dumps(n),1)
    (out/'Panda7.kicad_sym').write_text('(kicad_symbol_lib(version 20241209)(generator "kicad_symbol_editor")'+''.join(unique.values())+')\n')
    (out/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Panda7")(type "KiCad")(uri "${KIPRJMOD}/Panda7.kicad_sym")(options "")(descr "E0 exact net intent;not fabrication release")))\n')
    (out/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Panda47")(type "KiCad")(uri "${KIPRJMOD}/Panda47.pretty")(options "")(descr "E0 native local lands")))\n')
    report={'revision':'E0.2','source_ordered_layout_sha256':sha(LAYOUT),'source_contract_sha256':sha(CONTRACT),'donor':proof,'boards':{},'manufacturing_release':False,
      'exact_pico_battery_verified':False,'panel_full_stack_verified':False,'routing_complete':False,'charge_enable_allowed':False,
      'open_engineering_gates':['Exact Pico battery MPN/pack envelope/connector/NTC/CV and protection','Exact panel full suffix,touch and frontlight stack/contact face','BORDER bias and per-panel VCOM','PMIC current-revision EP/NC clarification','Power inductors/diodes/startup saturation and complete passives sourcing','3.3V mux timing and safe SD/UART/display handover','Physical placement/routing/SI/EMI/thermal','Whole-device<=7mm maximum and cell swelling fit','CAM/SMT and supplier acceptance']}
    for name in ['Core','Display']:
        run(['sch','export','netlist','--format','kicadxml','--output',out/(name+'-netlist.xml'),out/(name+'.kicad_sch')],out/(name+'-netlist.log'))
        tree=ET.parse(out/(name+'-netlist.xml'));actual={(v.get('ref'),v.get('pin')):net.get('name') for net in tree.findall('nets/net') for v in net.findall('node')}
        b=P.BOARD();b.SetCopperLayerCount(4);b.GetDesignSettings().SetBoardThickness(P.FromMM(.8));b.SetLayerType(P.In1_Cu,P.LT_POWER)
        netobjs={}
        for net in sorted(set(actual.values())):obj=P.NETINFO_ITEM(b,net);b.Add(obj);netobjs[net]=obj
        outline=plan['physical_study'][name+'_outline']
        for a,z in zip(outline,outline[1:]+outline[:1]):
            line=P.PCB_SHAPE(b);line.SetShape(P.SHAPE_T_SEGMENT);line.SetLayer(P.Edge_Cuts);line.SetStart(MM(*a));line.SetEnd(MM(*z));line.SetWidth(P.FromMM(.05));b.Add(line)
        for ref,f in fps[name].items():
            f.SetPath(P.KIID_PATH('/'+roots[name]+'/'+UID(name+'/'+ref)))
            for pad in f.Pads():
                num=pad.GetNumber()
                if num and (ref,num) in actual:
                    pad.SetNet(netobjs[actual[(ref,num)]]);pad.SetPinFunction(parts[name][ref]['pins'][num]['name']);pad.SetPinType(parts[name][ref]['pins'][num]['type'])
            b.Add(f)
        occupied=[];placed=set();new_boxes=[];pending=[]
        if name=='Core':
            for ref,f in fps[name].items():
                if ref in newly_added[name]:continue
                p=parts[name][ref];x,y=p['source_pos'];yy=y+20 if y>=64.8 else y
                f.SetPosition(MM(x,yy));f.SetOrientationDegrees(p['source_angle']);f.SetLocked(True)
                occupied.append(bbox(f));placed.add(ref)
            occupied.append([32.88,125.45,42.12,131])
            for ref,(x,y,angle) in ordered_layout['core_poses'].items():
                require(ref in newly_added['Core'],'Do not move donor functions through new-part placement')
                f=fps[name][ref];f.SetPosition(MM(x,y));f.SetOrientationDegrees(angle);f.SetLocked(True)
                occupied.append(bbox(f));new_boxes.append(bbox(f));placed.add(ref)
            target={'U710':(48,96),'U711':(48,112),'C710':(50,94),'C711':(50,110)}
        else:
            fixed={'J1':(35,96.2,90),'J4':(35,114.2,90),'J820':(17.5,116,0),'U810':(15.5,96,0),'U811':(8,108,90)}
            for ref,(x,y,a) in fixed.items():
                f=fps[name][ref];f.SetPosition(MM(x,y));f.SetOrientationDegrees(a);f.SetLocked(True);occupied.append(bbox(f));placed.add(ref)
            target={'L801':(22,89),'C801':(24,88),'D801':(20,91),'C802':(18,91),
              'L802':(23,102),'D802':(23,98),'C803':(26,99),'C804':(20,103),'C805':(17,91),'C806':(11,93),
              'D803':(24,95),'D804':(23,101),'C807':(20,94),'C808':(22,94),'C809':(26,93),
              'C810':(22,100),'C811':(23,102),'C812':(27,104),'C813':(13,102),'C814':(10,96),'C815':(10,92),
              'C816':(11,100),'R801':(20,98),'R802':(20,99),'R803':(22,100),'R804':(21,101),'TH801':(4,91),
              'R805':(8,90),'R806':(7,92),'C817':(6,111)}
        regions=plan['physical_study'][name+'_regions'];remain=[]
        for ref,f in fps[name].items():
            if ref in placed:continue
            r=bbox(f);remain.append(((r[2]-r[0])*(r[3]-r[1]),ref))
        for _,ref in sorted(remain,reverse=True):
            f=fps[name][ref];wanted=target.get(ref,(52,104) if name=='Core' else (25,108));best=None
            for angle in [0,90,180,270]:
                f.SetOrientationDegrees(angle);f.SetPosition(MM(0,0));off=bbox(f)
                for a,c,xmax,ymax in regions:
                    lx=math.ceil((a+.18-off[0])*4)/4;ly=math.ceil((c+.18-off[1])*4)/4
                    for ix in range(max(0,int((xmax-.18-off[2]-lx)*4)+1)):
                        x=lx+ix*.25
                        for iy in range(max(0,int((ymax-.18-off[3]-ly)*4)+1)):
                            y=ly+iy*.25;score=math.dist((x,y),wanted)
                            if best is not None and score>=best[0]:continue
                            rr=[off[0]+x,off[1]+y,off[2]+x,off[3]+y]
                            if not any(intersects(rr,v,gap=.18) for v in occupied):best=(score,x,y,angle,rr)
            if best:
                _,x,y,a,rr=best;f.SetPosition(MM(x,y));f.SetOrientationDegrees(a);occupied.append(rr);placed.add(ref);new_boxes.append(rr)
            else:pending.append(ref)
        for i,ref in enumerate(pending):fps[name][ref].SetPosition(MM(90+(i%5)*10,10+(i//5)*10));fps[name][ref].SetOrientationDegrees(0)
        # Preserve only compatible native copper. Crossing the inserted20mm band
        # or an edited endpoint is deleted, never relabelled into a connection.
        kept=0;dropped=0;carried={}
        if name=='Core':
            edited={'EPD_LE','EPD_OE','P47_BUS_SELECT','P47_D8_SRC','UART0_TX','UART0_RX','3V3_EPD_LOGIC'}
            changed_lands=[bbox(fps['Core'][r]) for r in ['U501','J601','J602','R512','R513']]
            for t in source['Core'].GetTracks():
                n=str(t.GetNetname())
                if n not in netobjs or n.startswith(('EPD_','SDMMC')) or n in edited:dropped+=1;continue
                a=t.GetPosition() if isinstance(t,P.PCB_VIA) else t.GetStart();z=t.GetPosition() if isinstance(t,P.PCB_VIA) else t.GetEnd()
                ay,zy=P.ToMM(a.y),P.ToMM(z.y)
                if (ay>=64.8)!=(zy>=64.8):dropped+=1;continue
                clone=t.Duplicate();clone=P.Cast_to_PCB_VIA(clone) if isinstance(t,P.PCB_VIA) else P.Cast_to_PCB_TRACK(clone)
                clone.Move(MM(0,20 if ay>=64.8 else 0))
                bb=clone.GetBoundingBox();tb=[P.ToMM(bb.GetX()),P.ToMM(bb.GetY()),P.ToMM(bb.GetRight()),P.ToMM(bb.GetBottom())]
                if any(intersects(tb,r,gap=.25) for r in new_boxes+changed_lands):dropped+=1;continue
                b.Add(clone);clone.SetNet(netobjs[n]);kept+=1
                carried[str(clone.m_Uuid.AsString())]={'donor_uuid':str(t.m_Uuid.AsString()),'net':n,'y_translation_mm':20 if ay>=64.8 else 0}
        # Dedicated internal reference plane. No GND thermal via is placed under
        # the SY7636A exposed pad. Outer-layer power stage remains to be routed.
        ordered_data_links=route_ordered_data_necks(b,ordered_layout) if name=='Core' else []
        for layer in [P.F_Cu,P.In1_Cu,P.B_Cu]:
            zone=P.ZONE(b);zone.SetLayer(layer);zone.SetNetCode(netobjs['GND'].GetNetCode());zone.SetLocalClearance(P.FromMM(.2));zone.SetMinThickness(P.FromMM(.15));zone.SetPadConnection(P.ZONE_CONNECTION_THERMAL);zone.SetThermalReliefGap(P.FromMM(.2));zone.SetThermalReliefSpokeWidth(P.FromMM(.25))
            chain=P.SHAPE_LINE_CHAIN()
            for x,y in outline:chain.Append(MM(x,y))
            chain.SetClosed(True);zone.AddPolygon(chain);b.Add(zone)
        from pico47_native import stitch_reference_planes
        ep_ground_vias=add_mcu_ground_vias(b,ordered_layout) if name=='Core' else []
        display_return_via=add_display_ground_return(b,ordered_layout) if name=='Display' else None
        stitch_report=stitch_reference_planes(b,outline)
        b.BuildConnectivity();P.ZONE_FILLER(b).Fill(b.Zones())
        title=b.GetTitleBlock();title.SetTitle('PANDA47 '+name+' / E0 UNROUTED / DO NOT ORDER OR POWER');title.SetRevision('E0')
        pcb=out/(name+'.kicad_pcb');P.SaveBoard(str(pcb),b)
        # SaveBoard can write defaults; restore the actual donor rules afterwards.
        (out/(name+'.kicad_pro')).write_bytes((donor/(name+'.kicad_pro')).read_bytes())
        run(['sch','erc','--severity-all','--format','json','--output',out/(name+'-erc.json'),out/(name+'.kicad_sch')],out/(name+'-erc.log'))
        run(['pcb','drc','--refill-zones','--save-board','--severity-all','--all-track-errors','--schematic-parity','--format','json','--output',out/(name+'-drc.json'),pcb],out/(name+'-drc.log'))
        saved=P.LoadBoard(str(pcb));saved_tracks={str(t.m_Uuid.AsString()):str(t.GetNetname()) for t in saved.GetTracks()}
        require(len(carried)==kept and all(saved_tracks.get(u)==entry['net'] for u,entry in carried.items()),'Retained copper changed net during native round-trip')
        (out/(name+'-CARRIED-COPPER.json')).write_text(json.dumps(carried,indent=2)+'\n')
        drc=json.loads((out/(name+'-drc.json')).read_text());erc=json.loads((out/(name+'-erc.json')).read_text())
        counts={'drc':len(drc['violations']),'open':len(drc['unconnected_items']),'parity':len(drc.get('schematic_parity',[])),'erc':sum(len(s.get('violations',[])) for s in erc['sheets'])}
        report['boards'][name]={'counts':counts,'pending_placement':pending,'retained_copper_items':kept,'deliberately_invalidated_copper_items':dropped,'ground_stitch_vias':stitch_report,'mcu_ep_ground_vias':ep_ground_vias,'ordered_data_links':ordered_data_links,'display_ground_return_via':display_return_via,'physical_refs':len(fps[name]),'pcb_sha256':sha(pcb),'schematic_sha256':sha(out/(name+'.kicad_sch'))}
        print(name,json.dumps(report['boards'][name]),flush=True)
    require(all(sha(p)==h for p,h in before.items()),'Donor unexpectedly changed')
    (out/'NEW-PART-REVIEW.json').write_text(json.dumps(specs,indent=2)+'\n')
    (out/'PARTS-INTENT.json').write_text(json.dumps(parts,indent=2)+'\n')
    (out/'E0-STATUS.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'DO-NOT-ORDER-OR-POWER.txt').write_text('E0 is an incomplete redesign. All opens are real and reported. The former D all-zero checks do not qualify this version. Exact Pico battery and complete screen assembly are NOT verified. Do not manufacture, enable charging or power the panel. See E0-STATUS.json.\n')
    print('REAL_NATIVE_CANDIDATE',out,'NOT_FOR_FABRICATION',flush=True)
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--donor',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--routing-checkpoint',type=Path,help='External, source-bound partial route to resume; never grants fabrication approval')
    a=ap.parse_args();create(a.output,a.donor)
    if a.routing_checkpoint:
        from pico47_checkpoint import restore
        restore(a.output,a.routing_checkpoint,a.donor)
