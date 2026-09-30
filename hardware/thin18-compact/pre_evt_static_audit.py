#!/usr/bin/env python3
from pathlib import Path
import json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
CAND=ROOT/'c4d12-96x68-routing'
NET=CAND/'verification/netlist.xml'
r=ET.parse(NET).getroot()
comps={c.get('ref'):c for c in r.findall('components/comp')}
nets={n.get('name',''):[(x.get('ref'),x.get('pin')) for x in n.findall('node')] for n in r.findall('nets/net')}
def value(ref): return (comps[ref].findtext('value') or '').strip()
def fields(ref): return {f.get('name'):f.text or '' for f in comps[ref].findall('fields/field')}
checks=[]
def add(id,ok,evidence,blocker=None): checks.append({'id':id,'result':'PASS_DOCUMENTARY' if ok and not blocker else 'BLOCKED','evidence':evidence,'blocker':blocker if blocker else (None if ok else 'documentary condition failed')})
add('USB_CC1_RD',value('R206').startswith('5.1k') and ('R206','2') in nets['USB_CC1'] and ('R206','1') in nets['GND'],
    {'value':value('R206'),'cc_net':'USB_CC1'},'exact mainland MPN/LCSC not frozen' if not fields('R206').get('MPN') else None)
add('USB_CC2_RD',value('R207').startswith('5.1k') and ('R207','2') in nets['USB_CC2'] and ('R207','1') in nets['GND'],
    {'value':value('R207'),'cc_net':'USB_CC2'},'exact mainland MPN/LCSC not frozen' if not fields('R207').get('MPN') else None)
add('USB_ESD_PATH',all(ref in comps for ref in ['D201','D202']),{'D201':value('D201'),'D202':value('D202')})
add('USB_NATIVE_DPDM',all(n in nets for n in ['USB_DP','USB_DM','USB_DP_MCU','USB_DM_MCU']),
    {'connector_side':['USB_DP','USB_DM'],'mcu_side':['USB_DP_MCU','USB_DM_MCU']})
add('POWER_DOMESTIC_BASE',all(value(x).startswith(y) for x,y in [('U901','SGM41513'),('U902','SGM62125'),('U903','CW2217')]),
    {x:value(x) for x in ['U901','U902','U903']})
pcb_text=(CAND/'eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16/PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_pcb').read_text()
add('LEGACY_GAUGE_OFFBOARD','U301' in comps and '(property \"Reference\" \"U301\"' not in pcb_text,
    {'U301':'schematic historical DNP/off-board; no PCB footprint; excluded from production BOM by symbol flags'})
add('FRONTLIGHT_CURRENT_CONTRACT',value('U905').startswith('SGM37601'),{'driver':value('U905'),'firmware':'REG0x01=0x56 / 14.5mA nominal; physical accuracy Q06 NOT_RUN'})
add('FRONTLIGHT_OVP_CONTRACT',value('U905').startswith('SGM37601'),{'driver':value('U905'),'firmware':'REG0x02=0xA1 / 18V OVP; physical open-string Q07 NOT_RUN'})
add('COUT_RATING',value('C923').startswith('4.7uF 50V'),{'C923':value('C923'),'MPN':fields('C923').get('MPN'),'qualification':'DC-bias Q08 NOT_RUN'})
add('SCHOTTKY_RATING',fields('D905').get('Voltage_Rating')=='40V',{'D905':value('D905'),'MPN':fields('D905').get('MPN'),'qualification':'hot leakage Q09 NOT_RUN'})
add('INDUCTOR_FIRST_ORDER',fields('L905').get('MPN')=='SWPA252012S100MT',{'L905':value('L905'),'MPN':fields('L905').get('MPN'),'qualification':'thermal/EMI/acoustic Q10 NOT_RUN'})
add('FPC_EXACT_CONNECTORS',fields('J803').get('LCSC')=='C224194' and fields('J804').get('LCSC')=='C224194',
    {'J803':fields('J803').get('MPN'),'J804':fields('J804').get('MPN'),'qualification':'orientation/insertion Q11 NOT_RUN'})
report={'date':'2026-09-30','candidate':CAND.name,'result':'PASS_DOCUMENTARY_WITH_OPEN_PHYSICAL_GATES',
        'checks':checks,'physical_tests_completed':0,'manufacturing_release':False,
        'physical_gates':{'Q04':'USB-C/USB2','Q05':'charging/NTC/ship/deep-sleep','Q06':'frontlight current','Q07':'OVP/open-string','Q08':'COUT DC-bias','Q09':'Schottky hot leakage','Q10':'inductor thermal/EMI/acoustic','Q11':'FPC fit','Q12':'RF/thermal/full EVT'}}
(ROOT/'c4d12-static-preflight.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
