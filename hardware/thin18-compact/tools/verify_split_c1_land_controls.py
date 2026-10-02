#!/usr/bin/env python3
"""In-memory negative controls; never alter PCB files or physical EVT evidence."""
from pathlib import Path
import sys,json
from copy import deepcopy
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from _split_c1_sourcing import blocks,property_value
from _split_c1_land_guards import verify_20261002_lands
from _split_c1_enclosure_study import side_battery_budget
core=next((ROOT/'core-c1-96x68-split/eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16').glob('*.kicad_pcb')).read_text()
display=(ROOT/'display-c1-45x36-production-bom/PANDA-EPD0426-SPI-EVT.kicad_pcb').read_text()
verify_20261002_lands(core,display)
inputs=json.loads((ROOT/'split-c1-mechanical-inputs.json').read_text())
side_battery_budget(inputs,[38,30,83,66],.8,1.5,.8)
def change(text,ref,old,new):
    a,b,f=next((a,b,f) for a,b,f in blocks(text,r'\(footprint\s') if property_value(f,'Reference')==ref)
    if old not in f:raise ValueError('Test predecessor absent')
    return text[:a]+f.replace(old,new,1)+text[b:]
cases=[
 ('microSD wrong row height',change(core,'J501','(size 0.6 1.6)','(size 0.6 1.5)'),display),
 ('microSD swapped supply/command',change(core,'J501','(net "3V3_SD")','(net "SDMMC_CMD_CARD")'),display),
 ('microSD reversed entry',change(core,'J501','(at 81.75 17.315 90)','(at 81.75 17.315 -90)'),display),
 ('microSD missing locating drill',change(core,'J501','(drill 1)','(drill .8)'),display),
 ('undocumented inductor B01 variant',change(core,'L402','MWSA0402S-1R0MT','MWSA0402S-1R0MTB01'),display),
 ('battery wrong pitch',change(core,'J301','(at -1 -2.21 90)','(at -.625 -2.21 90)'),display),
 ('battery reversed polarity',change(core,'J301','(net "BAT_CONN_P")','(net "GND")'),display),
 ('battery grounded anchors',change(core,'J301','(at -3.2 5.39 90)','(at -3.2 5.39 90) (net "GND")'),display),
 ('ESD symmetric ground lands',change(core,'D201','(size 0.575 0.45)','(size 0.7 0.45)'),display),
 ('panel swapped gate/sense',core,change(display,'J2','(net "/GDR")','(net "/RESE")')),
 ('panel obsolete support width',core,change(display,'J2','(size 0.3 0.76)','(size 0.8 0.76)'))]
results=[]
for name,c,d in cases:
    try:verify_20261002_lands(c,d)
    except ValueError as e:results.append({'name':name,'rejected':True,'error':str(e)})
    else:raise ValueError('Incorrect primary footprint accepted: '+name)
for name,mutate in [
 ('battery overlaps Display',lambda s:s.update(battery_rect_xyxy_mm=[3,6,39,60])),
 ('unsupported5.95mm case',lambda s:s.update(proposed_outer_xyz_mm=[112,75,5.95]))]:
    wrong=deepcopy(inputs);mutate(wrong['side_battery_study'])
    try:side_battery_budget(wrong,[38,30,83,66],.8,1.5,.8)
    except ValueError as e:results.append({'name':name,'rejected':True,'error':str(e)})
    else:raise ValueError('Incorrect enclosure budget accepted: '+name)
print(json.dumps({'current_primary_lands_passed':True,'negative_controls':results,
 'physical_measurements_added':0,'manufacturing_release':False},indent=2))
