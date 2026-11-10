"""Relabel a few GND pads (plus the copper already tied to one anchor pad) as a temporary net so router_v020
can join pads that the pour and the via stitcher could not reach.

usage: gnd_local_v020.py geom.json REF pin,pin,... anchor_pin out_geom.json out_spec.json
Apply the result with apply_router_v020.py and the alias TMPNET=GND.
"""
import json
import math
import sys

g = json.load(open(sys.argv[1]))
ref, pins, anchor = sys.argv[2], sys.argv[3].split(','), sys.argv[4]
TMP = 'TMPGND_' + ref
anc = next(p for p in g['pads'] if p['ref'] == ref and p['num'] == anchor)
for p in g['pads']:
    if p['ref'] == ref and p['num'] in pins + [anchor]:
        p['net'] = TMP
# copper touching the anchor pad (stub + via), followed transitively over GND items within 3 mm
pts = [(anc['x'], anc['y'])]
moved = True
while moved:
    moved = False
    for t in g['tracks']:
        if t['net'] == 'GND' and any(math.hypot(t['x1'] - x, t['y1'] - y) < 0.06 or math.hypot(t['x2'] - x, t['y2'] - y) < 0.06 for x, y in pts) \
                and math.hypot(t['x1'] - anc['x'], t['y1'] - anc['y']) < 3:
            t['net'] = TMP
            pts += [(t['x1'], t['y1']), (t['x2'], t['y2'])]
            moved = True
    for v in g['vias']:
        if v['net'] == 'GND' and any(math.hypot(v['x'] - x, v['y'] - y) < 0.06 for x, y in pts):
            v['net'] = TMP
            pts.append((v['x'], v['y']))
            moved = True
json.dump(g, open(sys.argv[5], 'w'))
json.dump({'nets': {TMP: 'all'}, 'target_nets': [], 'iterations': 20}, open(sys.argv[6], 'w'))
print(TMP, 'pads', pins + [anchor], 'copper points', len(pts))
