#!/usr/bin/env python3
"""Revision-B pin migration check against actual schematic AND native pads.

No claim of flashed firmware, timing or production approval. Kept separate from
revision-A host_gpio so the immutable electrical donor stays reproducible.
"""
from pathlib import Path
import argparse,copy,hashlib,json,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
HEADER=ROOT.parents[1]/'firmware/seven_mm/quality_board_pins.h'
EXPECTED={
    '43':('EPD_D0',38,'DISPLAY_SCLK'), '22':('I2C_SCL',16,'I2C_SCL'),
    '21':('I2C_SDA',15,'I2C_SDA'), '12':('SDMMC_CLK',7,'SDMMC_CLK'),
    '13':('SDMMC_CMD',8,'SDMMC_CMD'), '11':('SDMMC_D0',6,'SDMMC_D0'),
    '10':('SDMMC_D1',5,'SDMMC_D1'), '15':('SDMMC_D2',10,'SDMMC_D2'),
    '14':('SDMMC_D3',9,'SDMMC_D3'), '7':('HW_ARM_GPIO',2,'HARDWARE_ARM'),
    '25':('USB_DM_MCU',19,'USB_DM'), '26':('USB_DP_MCU',20,'USB_DP')}
PRESERVED={'29':'VDD_SPI','30':'SPIHD_SOC','31':'SPIWP_SOC','32':'SPICS0_SOC','33':'SPICLK_SOC','34':'SPIQ_SOC','35':'SPID_SOC'}

def require(ok,message):
    if not ok:raise ValueError(message)

def netlist(path):
    root=ET.parse(path).getroot()
    return {(n.get('ref'),n.get('pin')):v.get('name') for v in root.findall('./nets/net') for n in v.findall('node')}

def validate(nets,macros,source_nets):
    for pin,(net,gpio,macro) in EXPECTED.items():
        require(nets.get(('U501',pin))==net,'Wrong revision-B native GPIO pin '+pin)
        require(macros.get('PANDA7B_'+macro+'_GPIO')==gpio,'Wrong firmware macro '+macro)
    for pin,net in PRESERVED.items():require(nets.get(('U501',pin))==net,'Flash supply/pin changed '+pin)
    for pin in ['19','27','38','39','40','41','42']:
        require(nets.get(('U501',pin),'').startswith('unconnected-'),'Reserved/released GPIO used '+pin)
    for pin in ['5','8','51','52']:
        require(nets.get(('U501',pin))==source_nets.get(('U501',pin)),'Strapping pin net changed '+pin)
    changed={k for k in set(nets)|set(source_nets) if k[0]=='U501' and nets.get(k)!=source_nets.get(k)}
    require(changed=={('U501',p) for p in ['10','11','12','13','14','15','19','22','27','43']},'Unreviewed MCU mapping change')
    require(macros.get('PANDA7B_FLASH_MB')==16 and macros.get('PANDA7B_OCTAL_PSRAM_MB')==8,'Memory requirement changed')
    return True

def verify(candidate,donor):
    candidate,donor=Path(candidate),Path(donor)
    n=netlist(candidate/'Core-netlist.xml');old=netlist(donor/'Core-netlist.xml')
    macros={k:int(v) for k,v in re.findall(r'^#define\s+(PANDA7B_\w+)\s+(\d+)\s*$',HEADER.read_text(),re.M)}
    validate(n,macros,old)
    import wx
    app=wx.GetApp() or wx.App(False)
    import pcbnew as P
    b=P.LoadBoard(str(candidate/'Core.kicad_pcb'));mcu=b.FindFootprintByReference('U501')
    require(mcu is not None,'Missing host')
    require(next(f.GetText() for f in mcu.GetFields() if f.GetName()=='MPN')=='ESP32-S3R8','Wrong host memory/voltage variant')
    for pad in mcu.Pads():
        if pad.GetNumber():require(str(pad.GetNetname())==n[('U501',pad.GetNumber())],'PCB/schematic pin mismatch '+pad.GetNumber())
    rejected=0
    for pin in EXPECTED:
        bad=dict(n);bad[('U501',pin)]='WRONG'
        try:validate(bad,macros,old)
        except ValueError:rejected+=1
        else:raise AssertionError('Accepted incorrect pin '+pin)
    badmac=dict(macros);badmac['PANDA7B_SDMMC_CLK_GPIO']=6
    try:validate(n,badmac,old)
    except ValueError:rejected+=1
    else:raise AssertionError('Accepted wrong target GPIO')
    return {'revision':'B','native_schematic_pcb_gpio_parity':True,'header_sha256':hashlib.sha256(HEADER.read_bytes()).hexdigest(),'negative_controls_rejected':rejected,'target_firmware_tested':False,'manufacturing_release':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--donor',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.candidate,a.donor),indent=2))
