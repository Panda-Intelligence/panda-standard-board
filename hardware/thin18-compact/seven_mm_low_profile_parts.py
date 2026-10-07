"""Reviewed low-profile electrical/land definitions for a NEW 7mm candidate.

This module never claims supplier acceptance, stock, RF qualification or finished
PCB routing. Source pin functions come from the current Split-C1 native design.
The legacy R2 branch is not imported. Preserve all 60 interconnect positions.
"""
import json
from pathlib import Path

ESP_DOC='https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf'
ESP_GUIDE='https://documentation.espressif.com/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html'
USB_DOC='https://mupconn.com/uploads/products/USB%20Type%20C/U22401-17/PDF/U22401-17.pdf'
FFC_DOC='https://atta.szlcsc.com/upload/public/pdf/source/20260728/26BC46881D4A63071423AF10299E60A3.pdf'
MODULE_GPIO={4:4,5:5,6:6,7:7,8:15,9:16,10:17,11:18,12:8,13:19,14:20,15:3,16:46,17:9,18:10,19:11,20:12,21:13,22:14,23:21,24:47,25:48,26:45,27:0,28:35,29:36,30:37,31:38,32:39,33:40,34:41,35:42,36:44,37:43,38:2,39:1}
GPIO_PIN={0:5,1:6,2:7,3:8,4:9,5:10,6:11,7:12,8:13,9:14,10:15,11:16,12:17,13:18,14:19,15:21,16:22,17:23,18:24,19:25,20:26,21:27,33:38,34:39,35:40,36:41,37:42,38:43,39:44,40:45,41:47,42:48,43:49,44:50,45:51,46:52,47:36,48:37}


def bare_host(module_nets):
    nets={str(i):'' for i in range(1,58)}
    pins={str(i):{'name':'PIN'+str(i),'type':'bidirectional'} for i in range(1,58)}
    for module_pin,gpio in MODULE_GPIO.items():
        pin=str(GPIO_PIN[gpio]);pins[pin]['name']='GPIO'+str(gpio)
        old=module_nets.get(str(module_pin),'')
        nets[pin]='' if old.startswith('unconnected-') else old
    for gpio in range(33,38):nets[str(GPIO_PIN[gpio])]=''
    power={2:('VDD3P3','3V3_RF'),3:('VDD3P3','3V3_RF'),20:('VDD3P3_RTC','3V3_AON'),46:('VDD3P3_CPU','3V3_AON'),55:('VDDA','3V3_AON'),56:('VDDA','3V3_AON'),57:('GND','GND')}
    for pin,(name,net) in power.items():pins[str(pin)]={'name':name,'type':'power_in'};nets[str(pin)]=net
    for pin,name,typ,net in [(1,'LNA_IN','bidirectional','LNA_IN'),(4,'CHIP_PU','input',module_nets['3']),(28,'SPICS1','bidirectional',''),(29,'VDD_SPI','power_out','VDD_SPI'),(30,'SPIHD','bidirectional','SPIHD_SOC'),(31,'SPIWP','bidirectional','SPIWP_SOC'),(32,'SPICS0','bidirectional','SPICS0_SOC'),(33,'SPICLK','bidirectional','SPICLK_SOC'),(34,'SPIQ','bidirectional','SPIQ_SOC'),(35,'SPID','bidirectional','SPID_SOC'),(53,'XTAL_N','output','XTAL_N'),(54,'XTAL_P','input','XTAL_P_SOC')]:
        pins[str(pin)]={'name':name,'type':typ};nets[str(pin)]=net
    # These six retained labels have no second endpoint in the current two-board
    # design: the obsolete parallel-panel circuitry was already removed. Explicit
    # NC on the bare chip preserves every currently functional pin/net.
    for pin,net in list(nets.items()):
        if net in {'EPD_CKH','EPD_CKV','EPD_STH','EPD_STV','EPD_D6','EPD_D7'}:nets[pin]=''
    assert nets['7']=='HW_ARM_GPIO' and nets['25']=='USB_DM_MCU' and nets['26']=='USB_DP_MCU'
    assert not any(nets[str(GPIO_PIN[g])] for g in range(33,38))
    return nets,pins


def custom_land(name,pads,body,description):
    """Pads: (number,x,y,width,height[,drill_x,drill_y]). mm."""
    q=lambda v:json.dumps(str(v))
    x0,y0,x1,y1=body
    s=f'(footprint {q(name)} (version 20241229) (generator "pcbnew") (layer "F.Cu") (descr {q(description)}) (attr smd)\n'
    s+=f'(property "Reference" "REF**" (at 0 {y0-1} 0) (layer "F.Fab") (hide yes) (effects (font (size .6 .6) (thickness .1))))\n'
    s+=f'(property "Value" {q(name)} (at 0 {y1+1} 0) (layer "F.Fab") (hide yes) (effects (font (size .6 .6) (thickness .1))))\n'
    s+=f'(fp_rect (start {x0} {y0}) (end {x1} {y1}) (stroke (width .1) (type solid)) (fill none) (layer "F.Fab"))\n'
    a=min([x0]+[p[1]-p[3]/2 for p in pads])-.25;b=min([y0]+[p[2]-p[4]/2 for p in pads])-.25
    c=max([x1]+[p[1]+p[3]/2 for p in pads])+.25;d=max([y1]+[p[2]+p[4]/2 for p in pads])+.25
    s+=f'(fp_rect (start {a} {b}) (end {c} {d}) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))\n'
    for p in pads:
        num,x,y,w,h=p[:5]
        if len(p)==7:
            dx,dy=p[5:];drill=f'(drill oval {dx} {dy})' if dx!=dy else f'(drill {dx})'
            kind='thru_hole';layers='"*.Cu" "*.Mask"';shape='oval'
        else:drill='';kind='smd';layers='"F.Cu" "F.Paste" "F.Mask"';shape='rect'
        s+=f'(pad {q(num)} {kind} {shape} (at {x} {y}) (size {w} {h}) {drill} (layers {layers}))\n'
    return s+')\n'


def write_custom_lands(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    order=[('A1',-3.35),('B12',-3.05),('A4',-2.55),('B9',-2.25),('B8',-1.75),('A5',-1.25),('B7',-.75),('A6',-.25),('A7',.25),('B6',.75),('A8',1.25),('B5',1.75),('B4',2.25),('A9',2.55),('B1',3.05),('A12',3.35)]
    pads=[(n,x,-.55,.30,1.10) for n,x in order]
    for x in [-5.62,5.62]:pads.extend([('SH',x,.6,1.,1.8,.6,1.4),('SH',x,4.6,1.,2.,.6,1.8)])
    (folder/'MUP_U22401_17.kicad_mod').write_text(custom_land('MUP_U22401_17',pads,[-6.12,-1.1,6.12,6.5],'MUP U22401-17 DWG-U22401-XX-01 Rev2; 0.8mm PCB; 9.24mm recess. Source geometry reviewed, physical acceptance pending.'))
    # Use exact stocked 40P + 20P parts rather than extrapolating a 60P SKU.
    # XKB's A1 family drawing gives the same 0.5mm/1.0mm-bottom-contact land
    # construction and the N-based body/support dimensions for both parts.
    for n,mpn,code in [(40,'X05A10L40G','C21261162'),(20,'X05A10L20G','C2880915')]:
        a=n*.5+1.77;d=n*.5+1.27
        pads=[(str(i+1),(i-(n-1)/2)*.5,-2.30,.30,.65) for i in range(n)]
        pads.extend([('MP',-d/2,-.39,.30,1.15),('MP',d/2,-.39,.30,1.15)])
        name=f'XKB_{mpn}'
        desc=f'XKB {mpn}; exact LCSC {code};0.5mm pitch,bottom-contact,right-angle,1.0mm body family. Exact cable/contact-side and assembly acceptance remain open.'
        (folder/(name+'.kicad_mod')).write_text(custom_land(name,pads,[-a/2,-1.92,a/2,1.42],desc))
    # XySemi XB7608A CPC5 package, derived conservatively from the primary
    # REV0.1 package outline: body2.5..2.7mm; bottom pitch0.53mm,top1.06mm;
    # narrow leads0.16..0.26mm,broad leads0.69..0.79mm. Exact JLC C669688
    # EasyEDA/CAM land acceptance is still required before manufacturing release.
    pads=[('1',-.53,-1.65,.30,1.00),('2',0,-1.65,.30,1.00),('3',.53,-1.65,.30,1.00),('5',-.53,1.65,.80,1.00),('4',.53,1.65,.80,1.00)]
    (folder/'XB7608A_CPC5.kicad_mod').write_text(custom_land('XB7608A_CPC5',pads,[-1.35,-1.35,1.35,1.35],'XySemi XB7608A CPC5 primary package outline REV0.1; pins1VDD,2/3 cell negative GND,4/5 protected pack negative VM; derived engineering lands, JLC C669688 acceptance required.'))
    # Manual CR1216 tab/lead assembly. The coin cell itself is NOT reflowed.

    # Body envelope is 12.5x1.6mm; pads accept pre-welded insulated leads/tabs.
    pads=[('1',-5.0,0,2.0,2.0),('2',5.0,0,2.0,2.0)]
    s=custom_land('RTC_CR1216_LeadAssembly',pads,[-6.4,-6.4,6.4,6.4],'Power Glory CR1216 primary-cell manual lead assembly; cell max 12.5x1.6mm. Hardware Schottky isolates SD3078 charge path; NEVER reflow the cell.')
    s=s.replace('(attr smd)','(attr smd exclude_from_pos_files)')
    (folder/'RTC_CR1216_LeadAssembly.kicad_mod').write_text(s)
    pads=[('1',0,0,1.,1.4),('2',-1.4,0,1.,1.8),('2',1.4,0,1.,1.8)]
    s=custom_land('RF_CoaxLanding',pads,[-2,-1.2,2,1.2],'Controlled-impedance RF coax solder termination; exact low-profile antenna/harness assembly and strain relief pending.')
    s=s.replace('(attr smd)','(attr smd exclude_from_pos_files exclude_from_bom)')
    (folder/'RF_CoaxLanding.kicad_mod').write_text(s)
    for n in [2,3]:
        pads=[(str(i+1),(i-(n-1)/2)*2,0,1.3,2.) for i in range(n)]
        # PCB copper terminals are excluded from purchased-component BOM;
        # the wire assembly is separately required, never called a stocked part.
        s=custom_land('WireLanding_'+str(n),pads,[-n,-1.2,n,1.2],'PCB solder landing, NOT a purchasable connector; exact pre-tinned insulated harness/strain relief acceptance required.')
        s=s.replace('(attr smd)','(attr smd exclude_from_pos_files exclude_from_bom)')
        (folder/('WireLanding_'+str(n)+'.kicad_mod')).write_text(s)

def split_60_interconnect(core_nets, display_nets):
    """Map donor logical positions onto exact 40P+20P opposite-facing FFCs."""
    numbered=[str(i) for i in range(1,61)]
    assert all(i in core_nets and i in display_nets for i in numbered)
    # Donor shell/support pads are not part of the60 logical-position contract;
    # the new XKB mechanical tabs are explicitly bonded to GND on both boards.
    core40={str(i):core_nets[str(i)] for i in range(1,41)}
    core20={str(i):core_nets[str(40+i)] for i in range(1,21)}
    display40={str(41-i):display_nets[str(i)] for i in range(1,41)}
    display20={str(21-i):display_nets[str(40+i)] for i in range(1,21)}
    for row in [core40,core20,display40,display20]:
        row['MP']='GND'
    cable=[]
    for logical in range(1,61):
        if logical<=40:
            cable.append({'logical_position':logical,'core_ref':'J601','core_pin':logical,
                          'display_ref':'J1','display_pin':41-logical,'cable':'FFC40',
                          'core_net':core_nets[str(logical)],'display_net':display_nets[str(logical)]})
        else:
            p=logical-40
            cable.append({'logical_position':logical,'core_ref':'J602','core_pin':p,
                          'display_ref':'J4','display_pin':21-p,'cable':'FFC20',
                          'core_net':core_nets[str(logical)],'display_net':display_nets[str(logical)]})
    assert len(cable)==60 and len({x['logical_position'] for x in cable})==60
    return {'Core':{'J601':core40,'J602':core20},
            'Display':{'J1':display40,'J4':display20},'cable':cable}
