#!/usr/bin/env python3
"""Check actual C301 hole/polarity and a conservative documented insertion fit."""
import argparse
import copy
import json
import math
import re
from pathlib import Path
from _split_c1_common import ROOT, REL, STEM, repo_entry
from _split_c1_sourcing import blocks, property_value
from _split_c1_fabrication import require


def fit_screen(hole=1.9,land=2.3):
    # Manufacturer p4: lead width1.0+/-0.1,thickness0.2+/-0.05,pitch20+/-0.5.
    # Fabricator published finished-hole lower tolerance-.08,position+/- .075.
    # Translate the cap midpoint to the two hole centers; no forced lead bending.
    lead_radius=math.hypot(1.1/2,.25/2)
    center_error=math.hypot(.5/2+.075,.075)
    available=(hole-.08)/2
    margin=available-lead_radius-center_error
    annular=(land-hole)/2
    require(margin>0,'No positive worst-corner insertion envelope')
    require(annular>=.2-1e-9,'Annular ring below reviewed0.20mm intent')
    return {'lead_circumradius_mm':lead_radius,'center_offset_bound_mm':center_error,
            'minimum_finished_hole_radius_mm':available,'calculated_radial_fit_margin_mm':margin,
            'nominal_annular_ring_mm':annular,
            'basis':'Documentary envelope only; actual lot,finished drill/plating,solder fill and fit are untested.'}


def check_part(part):
    require(property_value(part,'MPN')=='SE-5R5-D105VYH3C','Wrong capacitor variant')
    require(property_value(part,'LCSC')=='C2894294','Wrong exact capacitor catalog identity')
    require(re.search(r'\(at\s+59\.4\s+43\.5\)',part),'Unreviewed capacitor pose')
    pads=list(blocks(part,r'\(pad\s'));require(len(pads)==2,'Cap pad count changed')
    seen=set()
    for a,b,pad in pads:
        n=re.match(r'\(pad\s+"([^"]+)"',pad)[1]
        require(n in ['1','2'] and n not in seen,'Wrong or duplicate C301 pad number');seen.add(n)
        require('thru_hole circle' in pad and '(drill 1.9)' in pad and '(size 2.3 2.3)' in pad,'Wrong circular hole/land')
        require(f'(at {"-10" if n=="1" else "10"} 0)' in pad,'Cap pitch differs')
        require('(layers "*.Cu" "*.Mask")' in pad,'PTH span/mask differs')
        require('(net "'+('RTC_VBACKUP' if n=='1' else 'GND')+'")' in pad,'Cap polarity differs')
    return fit_screen()


def inspect(candidate):
    candidate=Path(candidate);pcb=candidate/REL/(STEM+'.kicad_pcb')
    part=next(p for a,b,p in blocks(pcb.read_text(),r'\(footprint\s') if property_value(p,'Reference')=='C301')
    fit=check_part(part)
    cases=[part.replace('(drill 1.9)','(drill oval 1.8 1.4)'),part.replace('(size 2.3 2.3)','(size 2.2 2.2)'),
           part.replace('(at -10 0)','(at -9.5 0)'),part.replace('RTC_VBACKUP','GND'),
           part.replace('C2894294','C118887'),part.replace('SE-5R5-D105VYH3C','SE-5R5-D105VYH')]
    for bad in cases:
        try:check_part(bad)
        except ValueError:pass
        else:raise AssertionError('Incorrect cap drill/variant was accepted')
    return {'schema':'panda-split-c1-cap-drill-verification-v1','pcb':repo_entry(pcb),
            'checker':repo_entry(Path(__file__)),'new_round_holes_mm':1.9,'round_lands_mm':2.3,
            'pitch_mm':20,'correct_polarity':True,'negative_cases_rejected':len(cases),'fit_screen':fit,
            'manufacturer_land_pattern_claimed':False,'physical_fit_verified':False,'manufacturing_release':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,default=ROOT/'core-c1-96x68-split');p.add_argument('--output',type=Path,default=ROOT/'split-c1-cap-drill-verification.json');a=p.parse_args()
    r=inspect(a.candidate);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))


if __name__=='__main__':main()
