#!/usr/bin/env python3
"""Bind tested control constants to current native pins, not historical IC labels."""
import argparse
import copy
import json
import re
import subprocess
from pathlib import Path
from _split_c1_common import ROOT, REPO, REL, STEM, kicad_cli, repo_entry, sha
from _split_c1_sourcing import blocks, property_value
from verify_split_c1_power_integrity import parse_netlist, check

HEADER = REPO/'firmware/split_c1/board_control.hpp'
EXPECTED_BINDINGS = {
    'kExpander':0x20, 'kCharger':0x1A, 'kFrontlight':0x36, 'kImu':0x6A,
    'kDirection0':0xD0, 'kDirection1':0x1F, 'kQuiescent0':0x20, 'kQuiescent1':0,
    'kPowerGoodMask':0x10, 'kFrontlightEnable':0x20, 'kFrontlightPwm':0x40,
    'kFrontlightMode':1, 'kFrontlightVoltage':0xA1, 'kFrontlightFrequency':0x2B,
    'kBusMaxHz':100000, 'kTransferTimeoutMs':10, 'kServiceDeadlineMs':1000,
    'kFrontlightSettleMs':10, 'kFrontlightStartDeadlineMs':100,
}
# These maps were independently checked against primary pin tables/board intent.
# A copied vendor-compatible symbol name is not evidence of its supply identity.
EXPECTED_PINS = {
    'U601': {'1':'EXP_INT','2':'GND','3':'GND','4':'EN_3V3_SD','5':'EN_3V3_TOUCH',
             '6':'EN_3V3_EPD_LOGIC','7':'EN_VSYS_AUDIO','8':'FUEL_GPOUT','9':'BQ_CE',
             '10':'BQ_INT','11':'BQ_STAT','12':'GND','13':'BQ_PG','14':'KEY_FN',
             '15':'IMU_INT1','16':'SD_CD','17':'PG_3V3_MAIN','18':'FL_HWEN','19':'FL_PWM',
             '20':'TOUCH_RST','21':'GND','22':'I2C_SCL','23':'I2C_SDA','24':'3V3_AON'},
    'U901': {'2':'SGM41513_PSEL','5':'I2C_SCL','6':'I2C_SDA','9':'BQ_CE','22':'SGM41513_REGN'},
    'U905': {'1':'I2C_SDA','2':'I2C_SCL','5':'GND','19':'FL_HWEN','20':'FL_PWM'},
    'U503': {'1':'3V3_AON','12':'3V3_AON','13':'I2C_SCL','14':'I2C_SDA'},
    'U906': {'1':'GND','2':'PG_3V3_MAIN','3':'3V3_AON'},
    'U501': {'8':'I2C_SDA','22':'I2C_SCL'},
    'U302': {'1':'I2C_SCL','8':'I2C_SDA'},
    'R607': {'1':'BQ_CE','2':'GND'},
    'R601': {'1':'FL_HWEN','2':'GND'},
    'R922': {'1':'FL_PWM','2':'GND'},
    'R604': {'1':'EN_3V3_SD','2':'GND'},
    'R605': {'1':'EN_3V3_TOUCH','2':'GND'},
    'R606': {'1':'EN_3V3_EPD_LOGIC','2':'GND'},
    'R507': {'1':'EN_VSYS_AUDIO','2':'GND'},
}
EXACT_MPN = {'U601':'XL9535','U901':'SGM41513YTQF24G/TR',
             'U905':'SGM37601YTRL20G/TR','U503':'QMI8658A','U906':'SGM809B-TXN3LG/TR',
             'U501':'ESP32-S3-WROOM-1U-N16R8','U302':'SD3078','R607':'RC-02K1003FT'}


def header_bindings(text):
    matches = re.findall(r'inline constexpr std::uint(?:8|32)_t\s+(k\w+)\s*=\s*(0x[0-9A-Fa-f]+|[0-9]+)\s*;', text)
    check(len(matches)==len({k for k,v in matches}), 'Duplicate control constant')
    return {key:int(value,0) for key,value in matches}


def verify_logic(bindings, fields, pins):
    check(bindings==EXPECTED_BINDINGS, 'Unreviewed control address/mask/timing constant')
    for ref, mpn in EXACT_MPN.items():
        check(fields.get(ref,{}).get('MPN')==mpn, 'Wrong control component identity '+ref)
    for ref, mapping in EXPECTED_PINS.items():
        for pin, net in mapping.items():
            check(pins.get((ref,pin))==net, 'Control pin contract differs: '+ref+'.'+pin)
    port0 = [pins[('U601',str(i))] for i in range(4,12)]
    port1 = [pins[('U601',str(i))] for i in range(13,21)]
    controlled = {'EN_3V3_SD','EN_3V3_TOUCH','EN_3V3_EPD_LOGIC','EN_VSYS_AUDIO',
                  'BQ_CE','FL_HWEN','FL_PWM','TOUCH_RST'}
    for index, port in enumerate([port0,port1]):
        direction = sum(1<<bit for bit,net in enumerate(port) if net not in controlled)
        reset_latch = sum(1<<bit for bit,net in enumerate(port) if net=='BQ_CE')
        check(bindings['kDirection'+str(index)]==direction, 'GPIO direction derived from actual nets differs')
        check(bindings['kQuiescent'+str(index)]==reset_latch, 'Active-low charge-enable reset differs')
    check(port1[4]=='PG_3V3_MAIN' and bindings['kDirection1']&0x10, 'P14 must be input')
    check(pins.get(('U503','10'),'').startswith('unconnected-'), 'QMI reserved pin10 contract changed')
    check(pins.get(('U503','11'),'').startswith('unconnected-'), 'QMI reserved pin11 contract changed')
    return {'port0_nets':port0,'port1_nets':port1,'pg_input_bit':4,
            'host_scl_gpio':14,'host_sda_gpio':15,'shared_bus_max_hz':100000}


def negative_controls(bindings, fields, pins):
    cases = []
    for key,value in [('kCharger',0x6B),('kImu',0x6B),('kExpander',0x21),
                      ('kDirection1',0x0F),('kQuiescent0',0),('kBusMaxHz',400000),
                      ('kFrontlightVoltage',0xE9),('kFrontlightFrequency',0x24)]:
        bad=bindings.copy();bad[key]=value;cases.append((bad,fields,pins))
    for key,value in [(('U601','17'),'FL_HWEN'),(('U503','1'),'GND'),
                      (('U905','5'),'3V3_AON'),(('U901','2'),'3V3_AON'),
                      (('R607','2'),'3V3_AON')]:
        bad=pins.copy();bad[key]=value;cases.append((bindings,fields,bad))
    for ref,value in [('U901','SGM41513AYTQF24G/TR'),('U905','SGM37601YTG24G/TR'),('U503','LSM6DSO32XTR')]:
        bad=copy.deepcopy(fields);bad[ref]['MPN']=value;cases.append((bindings,bad,pins))
    for test in cases:
        try:verify_logic(*test)
        except ValueError:pass
        else:raise AssertionError('Incorrect control mapping was accepted')
    return len(cases)


def verify_fresh(report):
    check(report.get('schema')=='panda-split-c1-control-verification-v1', 'Wrong control report schema')
    for entry in report['inputs'].values():
        check(sha(REPO/entry['path'])==entry['sha256'], 'Stale control input: '+entry['path'])
    check(report['native_bindings_verified'] and report['host_tests_passed'], 'Control validation missing')
    for flag in ['target_firmware_integration_verified','physical_evt_passed',
                 'pre_firmware_charging_inhibit_proven','manufacturing_release']:
        check(report[flag] is False, 'Unproven control release flag: '+flag)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-target-integration',action='store_true')
    args=parser.parse_args(argv)
    output=ROOT/'split-c1-control-verification.json';output.unlink(missing_ok=True)
    candidate=ROOT/'core-c1-96x68-split';pcb=candidate/REL/(STEM+'.kicad_pcb')
    sources=[pcb,HEADER,Path(__file__).resolve(),ROOT/'test_split_c1_control.py',
             ROOT/'split-c1-control-contract.json',REPO/'firmware/split_c1/README.md',
             REPO/'firmware/split_c1/board_control.cpp',REPO/'firmware/split_c1/tests/board_control_test.cpp',
             ROOT/'SPLIT-C1-RTC-FIRMWARE.md',candidate/'frontlight-firmware-contract.json']
    sources+=sorted(pcb.parent.glob('*.kicad_sch'))
    inputs={p.relative_to(REPO).as_posix():repo_entry(p) for p in sources}
    host_path=ROOT/'split-c1-control-host-tests.json'
    host=json.loads(host_path.read_text())
    for entry in host['inputs'].values():
        check(sha(REPO/entry['path'])==entry['sha256'], 'Host control tests are stale')
    check(host['passed'] and host['compiled_and_executed'], 'Host control tests failed')
    check(host['physical_hardware_tested'] is False, 'Mock tests must not claim hardware testing')
    inputs['host_tests']=repo_entry(host_path)
    work=REPO/'.work/split-c1-control';work.mkdir(parents=True,exist_ok=True)
    netlist=work/'control-netlist.xml'
    subprocess.run([kicad_cli(),'sch','export','netlist','--format','kicadxml','--output',str(netlist),
                    str(pcb.with_suffix('.kicad_sch'))],check=True,capture_output=True,timeout=60)
    fields,pins,nets=parse_netlist(netlist)
    bindings=header_bindings(HEADER.read_text())
    contract=json.loads((ROOT/'split-c1-control-contract.json').read_text())
    check(contract['bindings']==bindings and contract['expected_native_pin_nets']==EXPECTED_PINS and contract['exact_control_mpns']==EXACT_MPN, 'Documented control contract differs from code/native checker')
    derived=verify_logic(bindings,fields,pins)
    controls=negative_controls(bindings,fields,pins)
    footprints={property_value(f,'Reference'):f for _,_,f in blocks(pcb.read_text(),r'\(footprint\s')}
    for ref,mapping in EXPECTED_PINS.items():
        fp=footprints[ref];check(not re.search(r'\(dnp\s+yes\)',fp),'Required control part is DNP')
        found={}
        for _,_,pad in blocks(fp,r'\(pad\s'):
            n=re.match(r'\(pad\s+"([^"]*)"',pad).group(1)
            net=re.search(r'\(net\s+(?:\d+\s+)?("(?:\\.|[^"\\])*")',pad)
            if n and net:found[n]=json.loads(net.group(1))
        for pin,net in mapping.items():check(found.get(pin)==net,'PCB control pin differs: '+ref+'.'+pin)
        if ref in EXACT_MPN:check(property_value(fp,'MPN')==EXACT_MPN[ref],'PCB control MPN differs')
    for entry in inputs.values():check(sha(REPO/entry['path'])==entry['sha256'],'Concurrent control source change')
    report={'schema':'panda-split-c1-control-verification-v1','design_target':'split-c1','inputs':inputs,
            'native_bindings_verified':True,'derived_control':derived,'compiled_header_bindings':bindings,
            'checked_native_component_refs':sorted(EXPECTED_PINS),'host_tests_passed':True,
            'host_test_groups':host['test_groups'],'single_transfer_fault_cases':host['single_transfer_fault_cases'],
            'incorrect_binding_cases_rejected':controls,'pre_firmware_charging_inhibit_proven':False,
            'open_hardware_findings':[{'id':'R607_PRE_FIRMWARE_CHARGING',
              'netlist_evidence':sorted([list(n) for n in nets['BQ_CE']]),
              'bias':'R607 100k to GND; XL9535 reset directions are inputs',
              'effect':'Software inhibit only exists after firmware runs. Autonomous charging before MCU initialization or after XL/charger resets is not excluded.',
              'status':'OPEN; review a hardware inhibit ECO or a batteryless/current-limited commissioning fixture before connecting an unqualified cell'},
             {'id':'PERSISTENT_BUS_LOSS','status':'OPEN','effect':'XL9535 outputs may retain frontlight ON when every shutdown transaction fails; software reports UNKNOWN, not physically OFF.'}],
            'target_firmware_integration_verified':False,'physical_evt_passed':False,'manufacturing_release':False}
    verify_fresh(report)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['native_bindings_verified','host_test_groups',
        'single_transfer_fault_cases','incorrect_binding_cases_rejected','pre_firmware_charging_inhibit_proven',
        'target_firmware_integration_verified','manufacturing_release']},indent=2))
    return 2 if args.require_target_integration else 0


if __name__=='__main__':raise SystemExit(main())
