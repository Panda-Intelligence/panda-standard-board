"""Deterministic C301 round-PTH ECO after the prior hardware-finish replay.

Preserves exact part,20mm pin centers,body courtyard,netlist and every track/via.
Only two C301 lands/drills and their engineering descriptions change.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path
from _split_c1_common import REL, STEM, kicad_python
from _split_c1_sourcing import blocks, property_value
from _split_c1_domestic_eco import set_prop

MPN='SE-5R5-D105VYH3C'
DESCRIPTION=('KAMCAP SE-5R5-D105VYH3C/C2894294,1F5.5V horizontal rechargeable RTC backup. '
    '2026-10-04 engineering round-PTH ECO:20mm pitch,1.9mm nominal finished round holes,'
    '2.3mm round lands,0.20mm nominal annular ring; replaces short1.8x1.4mm slots. '
    'Original2020.6 p4 leads:width1.0+/-0.1,thickness0.20+/-0.05,pitch20+/-0.5mm. '
    'Pin1positive RTC_VBACKUP,pin2negative GND. Post-SMT manual assembly; no reflow. '
    'Body support,solder fill,manufacturing tolerance and physical fit remain EVT checks.')


def patch_lands(text):
    pads=list(blocks(text,r'\(pad\s'))
    if len(pads)!=2:raise ValueError('C301 must retain exactly two PTH lands')
    seen=set()
    for a,b,pad in reversed(pads):
        n=re.match(r'\(pad\s+"([^"]+)"',pad)[1]
        if n not in {'1','2'} or n in seen:raise ValueError('Wrong C301 pad numbering')
        seen.add(n)
        if not all(s in pad for s in ['thru_hole oval','(size 2.4 2.0)','(drill oval 1.8 1.4)',f'(at {"-10" if n=="1" else "10"} 0)']):
            raise ValueError('C301 hole/land predecessor differs; no repeat application')
        pad=pad.replace('thru_hole oval','thru_hole circle').replace('(size 2.4 2.0)','(size 2.3 2.3)').replace('(drill oval 1.8 1.4)','(drill 1.9)')
        text=text[:a]+pad+text[b:]
    text=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)',lambda m:'(descr '+json.dumps(DESCRIPTION)+')',text,count=1)
    if property_value(text,'Reference')=='C301':text=set_prop(text,'Description',DESCRIPTION)
    return text


def apply_structure(candidate):
    candidate=Path(candidate);folder=candidate/REL
    pcb=folder/(STEM+'.kicad_pcb');s=pcb.read_text()
    a,b,part=next(x for x in blocks(s,r'\(footprint\s') if property_value(x[2],'Reference')=='C301')
    if property_value(part,'MPN')!=MPN or '(at 59.4 43.5)' not in part:raise ValueError('C301 identity/pose changed')
    new=patch_lands(part);pcb.write_text(s[:a]+new+s[b:])
    library=candidate/'lib/panda-standard.pretty/KAMCAP_SE5R5_D105VYH3C.kicad_mod'
    library.write_text(patch_lands(library.read_text()))
    seen=0
    for sch in folder.glob('*.kicad_sch'):
        s=sch.read_text()
        for a,b,part in blocks(s,r'\(symbol\s+\(lib_id\s'):
            if property_value(part,'Reference')!='C301':continue
            if property_value(part,'MPN')!=MPN:raise ValueError('C301 schematic identity changed')
            part=set_prop(part,'Description',DESCRIPTION);sch.write_text(s[:a]+part+s[b:]);seen+=1
    if seen!=1:raise ValueError('Missing/duplicate C301 schematic instance')


def apply_cap_drill_eco(candidate):
    subprocess.run([kicad_python(),str(Path(__file__).resolve()),'--candidate',str(Path(candidate).resolve())],check=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True)
    args=parser.parse_args();apply_structure(args.candidate)
    import wx
    app=wx.App(False)
    from _split_c1_power_integrity_eco import refill_zones
    refill_zones(args.candidate/REL/(STEM+'.kicad_pcb'))
