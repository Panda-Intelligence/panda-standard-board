#!/usr/bin/env python3
"""Independently check actual pins, exact variants and the PG/PSEL migration.

A matching schematic/PCB can share an incorrect circuit, so these functional
contracts are separate from native parity. No physical pass is inferred.
"""
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from _split_c1_common import ROOT, REPO, REL, STEM, repo_entry
from _split_c1_sourcing import blocks, property_value

EXPECTED_PINS = {
    'U906': {'1':'GND','2':'PG_3V3_MAIN','3':'3V3_AON'},
    'C204': {'1':'3V3_AON','2':'GND'},
    'R201': {'1':'SGM41513_PSEL','2':'GND'},
    'R204': {'1':'SGM41513_PSEL','2':'SGM41513_REGN'},
}
EXACT_PARTS = {
    'U906': ('SGMICRO','SGM809B-TXN3LG/TR','panda-standard:SGM809B_SOT23_TX00031',''),
    'U901': ('SGMICRO','SGM41513YTQF24G/TR','panda-standard:SGM41513_YTQF24_4x4_P0.5_EP2.7','C5153778'),
    'U902': ('SGMICRO','SGM62125AXG/TR','panda-standard:SGM62125_XG_WLCSP15_1.46x2.3_P0.4',''),
    'R201': ('FH (Fenghua Advanced)','RS-03K5601FT','panda-standard:R201_ILIM_0603_SEED','C99891'),
    'R204': ('FH (Fenghua Advanced)','RS-03K1201FT','panda-standard:R204_ILIM_RC_0603_SEED','C118396'),
    'C204': ('FH (Fenghua Advanced)','0603B334K500NT','panda-standard:C204_ILIM_RC_0603_SEED','C188679'),
}
REQUIRED_IC_MPN = {
    'U302':'SD3078', 'U402':'SGM2578SDYG/TR','U403':'SGM2578SDYG/TR',
    'U404':'SGM2578SDYG/TR','U405':'SGM2578SDYG/TR',
    'U501':'ESP32-S3-WROOM-1U-N16R8','U503':'QMI8658A','U601':'XL9535',
    'U901':'SGM41513YTQF24G/TR','U902':'SGM62125AXG/TR','U903':'CW2217BAAD',
    'U904':'NS4168','U905':'SGM37601YTRL20G/TR','U906':'SGM809B-TXN3LG/TR',
}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def parse_netlist(path):
    root = ET.parse(path).getroot()
    fields = {c.get('ref'):{f.get('name'):f.text or '' for f in c.findall('./fields/field')}
              for c in root.findall('./components/comp')}
    pins, nets = {}, {}
    for net in root.findall('./nets/net'):
        name = net.get('name'); nodes = []
        for node in net.findall('node'):
            key = (node.get('ref'),node.get('pin'))
            check(key not in pins,'A pin appears on multiple nets')
            pins[key] = name; nodes.append(key)
        nets[name] = set(nodes)
    return fields, pins, nets


def verify_contract(fields, pins, nets):
    for ref, expected in EXACT_PARTS.items():
        check(ref in fields,'Missing required circuit part '+ref)
        actual = tuple(fields[ref].get(k,'') for k in ['Manufacturer','MPN','Footprint','LCSC'])
        check(actual == expected,'Unreviewed exact identity '+ref)
    for ref, mapping in EXPECTED_PINS.items():
        actual = {p:n for (r,p),n in pins.items() if r == ref}
        check(actual == mapping,'Wrong reviewed pin map '+ref)
    check(pins.get(('U901','2')) == 'SGM41513_PSEL','PSEL is not pre-AON biased')
    check(pins.get(('U901','22')) == 'SGM41513_REGN','REGN output source missing')
    check(nets.get('SGM41513_PSEL') == {('U901','2'),('R201','1'),('R204','1')},
          'Unexpected PSEL source, capacitor or load')
    check(nets.get('PG_3V3_MAIN') == {('U906','2'),('U601','17'),('TP16','1')},
          'PG must come from U906 and must not drive MCU reset')
    check(not ({'BQ_ILIM','BQ_ILIM_RC'} & set(nets)),'Obsolete BQ control nets remain')
    # SGM809B is push-pull. P14 input-only is a required firmware contract,
    # not something static PCB/ERC can verify.
    return True


def inspect(candidate, netlist):
    candidate = Path(candidate); pcb = candidate/REL/(STEM+'.kicad_pcb')
    fields, pins, nets = parse_netlist(netlist)
    verify_contract(fields,pins,nets)
    text = pcb.read_text()
    footprints = {property_value(f,'Reference'):f for _,_,f in blocks(text,r'\(footprint\s')}
    ics = {r for r,f in footprints.items() if r and re.fullmatch(r'U\d+',r)
           and not re.search(r'\(dnp\s+yes\)',f)}
    check(ics == set(REQUIRED_IC_MPN),'A required populated Core IC was removed/DNP or an unreviewed IC added')
    for ref,mpn in REQUIRED_IC_MPN.items():
        check(property_value(footprints[ref],'MPN') == mpn,'Wrong populated IC variant '+ref)
        check('(attr exclude_from_bom)' not in footprints[ref], 'Required IC excluded from BOM')
    for ref,expected in EXACT_PARTS.items():
        f=footprints[ref]
        actual=(property_value(f,'Manufacturer'),property_value(f,'MPN'),
                re.match(r'\(footprint\s+("(?:\\.|[^"\\])*")',f).group(1),property_value(f,'LCSC') or '')
        actual=(actual[0],actual[1],json.loads(actual[2]),actual[3])
        check(actual==expected,'PCB exact part differs '+ref)
        found={}
        for _,_,pad in blocks(f,r'\(pad\s'):
            number=re.match(r'\(pad\s+"([^"]*)"',pad).group(1)
            net=re.search(r'\(net\s+(?:\d+\s+)?("(?:\\.|[^"\\])*")',pad)
            if number and net:found[number]=json.loads(net.group(1))
        expected_pins={p:n for (r,p),n in pins.items() if r==ref}
        check(found==expected_pins,'PCB functional pin contract differs '+ref)
    supervisor=footprints['U906']
    check(re.search(r'\(at\s+17\s+18\.75\)',supervisor) is not None,'Unreviewed supervisor pose')
    for _,_,pad in blocks(supervisor,r'\(pad\s'):
        n=re.match(r'\(pad\s+"([^"]+)"',pad).group(1)
        xy=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',pad).groups()))
        size=tuple(map(float,re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)',pad).groups()))
        check(xy=={'1':(-1.145,-.95),'2':(-1.145,.95),'3':(1.145,0)}[n] and size==(.76,.76),
              'Supervisor original-maker land/pin mismatch')
    return {'schema':'panda-split-c1-power-integrity-verification-v1',
            'native_source':repo_entry(pcb),'netlist_semantic_sha256':hashlib.sha256(json.dumps({'fields':fields,'pins':sorted([list(key)+[net] for key,net in pins.items()])},sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'contract':repo_entry(ROOT/'split-c1-power-integrity.json'),
            'checker':repo_entry(Path(__file__)),
            'functional_pin_contract_passed':True,'original_maker_supervisor_lands_passed':True,
            'required_populated_core_ic_refs':len(ics),'exact_variant_checks_passed':True,
            'obsolete_ilim_control_nets_absent':True,'pg_hardware_source_present':True,
            'psel_bias_independent_of_aon':True,'physical_evt_passed':False,
            'firmware_policy_verified':False,'assembly_order_ready':False,'manufacturing_release':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,default=ROOT/'core-c1-96x68-split')
    parser.add_argument('--netlist',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'split-c1-power-integrity-verification.json')
    args=parser.parse_args(argv)
    netlist=args.netlist or args.candidate/'verification/netlist.xml'
    report=inspect(args.candidate,netlist)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['functional_pin_contract_passed','original_maker_supervisor_lands_passed','required_populated_core_ic_refs','manufacturing_release']},indent=2))


if __name__=='__main__':main()
