#!/usr/bin/env python3
"""Verify the <=7mm RTC primary-cell safety topology in a generated native candidate.

This is a static circuit/identity check, not a claim of retention, leakage,
temperature, or physical assembly qualification.
"""
from pathlib import Path
import argparse, copy, json, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
CONTRACT=ROOT/'seven_mm_rtc_contract.json'

def require(test,message):
    if not test: raise ValueError(message)

def parse_netlist(path):
    root=ET.parse(path).getroot()
    fields={c.get('ref'):{f.get('name'):f.text or '' for f in c.findall('fields/field')}
            for c in root.findall('components/comp')}
    nets={}
    for net in root.findall('nets/net'):
        for n in net.findall('node'):
            nets[(n.get('ref'),n.get('pin'))]=net.get('name')
    return fields,nets

def verify(contract,fields,nets):
    require(contract['schema']=='panda-seven-mm-rtc-v1','Wrong RTC contract')
    rtc=contract['rtc'];cell=contract['primary_cell'];bar=contract['reverse_charge_barrier'];fw=contract['firmware']
    require('C301' not in fields,'Tall rechargeable C301 still populated')
    for item in [rtc,cell,bar]:
        ref=item['ref'];require(ref in fields,'Missing '+ref)
        require(fields[ref].get('MPN')==item['mpn'],'Wrong '+ref+' MPN')
        if item.get('manufacturer'):
            require(fields[ref].get('Manufacturer')==item['manufacturer'],'Wrong '+ref+' manufacturer')
    require(nets[(rtc['ref'],rtc['vbackup_pin'])]==rtc['vbackup_net'],'RTC VBAT net differs')
    require(nets[(cell['ref'],'1')]=='RTC_CELL_P' and nets[(cell['ref'],'2')]=='GND','Primary cell polarity/net differs')
    require(nets[(bar['ref'],'1')]==bar['pin1']['net'] and bar['pin1']['function']=='K','Barrier cathode contract differs')
    require(nets[(bar['ref'],'2')]==bar['pin2']['net'] and bar['pin2']['function']=='A','Barrier anode contract differs')
    require(nets[(bar['ref'],'1')]!=nets[(bar['ref'],'2')],'Primary cell directly tied to RTC backup rail')
    require(cell['reflow_allowed'] is False and cell['direct_cell_soldering_allowed'] is False,'Primary cell assembly safety relaxed')
    require(fw['sd3078_register_18h_charge_enable_required'] is False,'Primary-cell charging incorrectly enabled')
    require(fw['historical_0x82_write_forbidden'] is True and fw['charge_enable_readback_required'] is True,'Firmware charge-disable contract incomplete')
    a=contract['acceptance']
    require(a['isolated_retention_hours_minimum']>=24 and a['end_vbackup_voltage_v_minimum']>=2.3,'RTC retention target relaxed')
    require(all(a[k] is False for k in ['reverse_charge_current_physically_verified','hot_cold_diode_margin_verified','actual_cell_lot_and_tabs_verified','physical_evt_passed','manufacturing_release']),'Unproven RTC evidence marked passed')
    return {'static_rtc_topology_passed':True,'series_diode_orientation_verified':True,'reverse_charge_isolation_verified':False,
            'firmware_charge_enable_required':False,'physical_evt_passed':False,'manufacturing_release':False}

def negative_controls(contract,fields,nets):
    cases=[]
    bad=copy.deepcopy(contract);bad['firmware']['sd3078_register_18h_charge_enable_required']=True;cases.append(('charge_enable',bad,fields,nets))
    bad=copy.deepcopy(contract);bad['primary_cell']['reflow_allowed']=True;cases.append(('reflow',bad,fields,nets))
    swapped=dict(nets);swapped[('D306','1')]='RTC_CELL_P';swapped[('D306','2')]='RTC_VBACKUP';cases.append(('diode_reverse',contract,fields,swapped))
    direct=dict(nets);direct[('D306','1')]='RTC_CELL_P';direct[('D306','2')]='RTC_CELL_P';cases.append(('shorted_barrier',contract,fields,direct))
    wrong=copy.deepcopy(fields);wrong['BT301']=dict(wrong['BT301']);wrong['BT301']['MPN']='ML1216';cases.append(('wrong_cell',contract,wrong,nets))
    for name,c,f,n in cases:
        try: verify(c,f,n)
        except (ValueError,KeyError): continue
        raise AssertionError('Invalid RTC case accepted: '+name)
    return len(cases)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--negative-controls',action='store_true');a=p.parse_args()
    contract=json.loads(CONTRACT.read_text());fields,nets=parse_netlist(a.candidate/'Core-netlist.xml')
    result=verify(contract,fields,nets)
    if a.negative_controls:result['negative_controls_rejected']=negative_controls(contract,fields,nets)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
