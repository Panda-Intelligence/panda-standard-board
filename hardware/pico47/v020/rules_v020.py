"""Write the v0.2.0 net classes and board rules into a .kicad_pro (plain Python).

Default 0.127/0.127 mm, power 0.3 mm; through vias 0.55/0.3 mm so the order needs no small-hole option.
"""
import json
import sys

POWER = ['GND', 'VSYS_RAW', '3V3_AON', '3V3_RF', '3V3_SD', 'VBUS_USB', 'BAT_*', 'SGM41513_SW', 'SGM41513_PMID',
         'BUCK_LX', 'P47_VP_LX', 'P47_VN_LX', 'P47_VP', 'P47_VN', 'FL_SW', 'FL_VOUT', 'SPK_P', 'SPK_N', 'VDD_SPI']

pro_path = sys.argv[1]
pro = json.load(open(pro_path))
ns = pro['net_settings']
base = dict(ns['classes'][0])
base.update(name='Default', track_width=0.127, clearance=0.127, via_diameter=0.55, via_drill=0.3)
power = dict(base, name='Power', track_width=0.3, clearance=0.127, via_diameter=0.6, via_drill=0.3, priority=0)
ns['classes'] = [base, power]
ns['netclass_patterns'] = [{'netclass': 'Power', 'pattern': p} for p in POWER]
ns['netclass_assignments'] = None
r = pro['board']['design_settings']['rules']
r.update(min_track_width=0.09, min_clearance=0.127, min_via_diameter=0.55, min_through_hole_diameter=0.3,
         min_via_annular_width=0.1, min_hole_clearance=0.25, min_hole_to_hole=0.25, min_copper_edge_clearance=0.2)
json.dump(pro, open(pro_path, 'w'), indent=2)
print('rules written to', pro_path)
