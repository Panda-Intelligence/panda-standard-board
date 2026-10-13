#!/usr/bin/env python3
"""Verify the GPIO21 display-clock ECO against real schematic, PCB and header.

This verifies electrical identity/connectivity, not on-device firmware, SI or
mechanical acceptance. The60-position board link retains its original signals.
"""
from pathlib import Path
import argparse,copy,hashlib,json,re,subprocess,tempfile,xml.etree.ElementTree as ET
from _split_c1_common import ROOT,REPO,kicad_cli

CONTRACT=ROOT/'seven_mm_host_gpio.json'
HEADER=REPO/'firmware/seven_mm/board_pins.h'

def require(value,message):
    if not value:raise ValueError(message)

def normalized(net):
    return '' if not net or net.startswith('unconnected-') else net

def other_pin_hash(pins):
    rows=sorted((pin,normalized(pins.get(pin,''))) for pin in map(str,range(1,58)) if pin not in {'27','43'})
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

def verify_records(contract,fields,pins,clock_nodes,pcb_pins,clamp_pose,header):
    require(contract['schema']=='panda-seven-mm-host-gpio-v1','Wrong GPIO contract')
    require(fields.get('MPN')=='ESP32-S3R8' and fields.get('Manufacturer')=='Espressif','Wrong MCU variant')
    c=contract['display_clock']
    require((c['new_gpio'],c['new_physical_pin'],c['old_gpio'],c['old_physical_pin'])==(21,'27',38,'43'),'Unreviewed GPIO reassignment')
    require(c['core_net']=='EPD_D0' and c['display_net']=='HOST_SCLK','Display function changed')
    require(pins['27']=='EPD_D0' and not normalized(pins['43']),'Clock is not on GPIO21 exclusively')
    require(set(clock_nodes)=={('U501','27'),('J601','1')},'Display-clock load/source nodes changed')
    require(other_pin_hash(pins)==contract['unchanged_mcu_pin_net_sha256'],'Another MCU function changed')
    for pin,net in contract['preserved_mcu_pins'].items():require(pins[pin]==net,'Protected MCU pin changed: '+pin)
    for pin in contract['octal_psram_reserved_physical_pins']:require(not normalized(pins[pin]),'Octal PSRAM pin assigned externally: '+pin)
    require({p:normalized(v) for p,v in pins.items()}=={p:normalized(v) for p,v in pcb_pins.items()},'Schematic/PCB MCU pin mismatch')
    require(clamp_pose==[30.5,102.75,90.0],'USB clamp has not received the reviewed placement')
    for macro,value in [('PANDA7_DISPLAY_SCLK_GPIO',21),('PANDA7_DISPLAY_SCLK_PACKAGE_PIN',27),('PANDA7_HARDWARE_ARM_GPIO',2),('PANDA7_USB_DM_GPIO',19),('PANDA7_USB_DP_GPIO',20)]:
        require(re.search(r'^#define\s+'+macro+r'\s+'+str(value)+r'\s*$',header,re.M) is not None,'Firmware contract differs: '+macro)
    require(c['gpio_matrix_required'] is True and c['firmware_gpio_required']==21,'Firmware SPI routing contract differs')
    return {'static_gpio_eco_verified':True,'all_other_mcu_nets_preserved':True,'display_sclk_gpio':21,'display_sclk_physical_pin':27,'firmware_header_matches':True,'firmware_target_qualification':False,'manufacturing_release':False}

def inspect(candidate):
    import wx
    app=wx.GetApp() or wx.App(False)
    import pcbnew as P
    candidate=Path(candidate).resolve();sch=candidate/'Core.kicad_sch';before=hashlib.sha256(sch.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='panda-gpio-') as temp:
        out=Path(temp)/'netlist.xml'
        subprocess.run([kicad_cli(),'sch','export','netlist','--format','kicadxml','--output',str(out),str(sch)],check=True,cwd=candidate,stdout=subprocess.DEVNULL,timeout=60)
        xml=ET.parse(out)
    comps={c.get('ref'):{f.get('name'):f.text or '' for f in c.findall('fields/field')} for c in xml.findall('components/comp')}
    pins={n.get('pin'):net.get('name') for net in xml.findall('nets/net') for n in net.findall('node') if n.get('ref')=='U501'}
    nodes=[(n.get('ref'),n.get('pin')) for net in xml.findall('nets/net') if net.get('name')=='EPD_D0' for n in net.findall('node')]
    b=P.LoadBoard(str(candidate/'Core.kicad_pcb'));u=b.FindFootprintByReference('U501');clamp=b.FindFootprintByReference('D201')
    require(u is not None and clamp is not None,'Missing MCU or clamp')
    pcp={p.GetNumber():str(p.GetNetname()) for p in u.Pads() if p.GetNumber()}
    pose=[round(P.ToMM(clamp.GetPosition().x),6),round(P.ToMM(clamp.GetPosition().y),6),round(clamp.GetOrientationDegrees()%360,6)]
    data=(json.loads(CONTRACT.read_text()),comps['U501'],pins,nodes,pcp,pose,HEADER.read_text())
    result=verify_records(*data)
    require(hashlib.sha256(sch.read_bytes()).hexdigest()==before,'GPIO inspection altered schematic')
    return result,data

def negative_controls(data):
    cases=[]
    for pin,net in [('27',''),('43','EPD_D0'),('7','EPD_D0'),('38','EPD_D0'),('22','OTHER_FUNCTION')]:
        d=copy.deepcopy(data);d[2][pin]=net;cases.append(d)
    d=copy.deepcopy(data);d[4]['27']='';cases.append(d)
    d=list(copy.deepcopy(data));d[5]=[71.5,57,180];cases.append(d)
    d=list(copy.deepcopy(data));d[6]=d[6].replace('#define PANDA7_DISPLAY_SCLK_GPIO 21','#define PANDA7_DISPLAY_SCLK_GPIO 38');cases.append(d)
    d=copy.deepcopy(data);d[3].append(('J601','2'));cases.append(d)
    for d in cases:
        try:verify_records(*d)
        except (ValueError,KeyError):continue
        raise AssertionError('Invalid GPIO contract accepted')
    return len(cases)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--negative-controls',action='store_true');a=p.parse_args()
    result,data=inspect(a.candidate)
    if a.negative_controls:result['negative_controls_rejected']=negative_controls(data)
    print(json.dumps(result,indent=2))
