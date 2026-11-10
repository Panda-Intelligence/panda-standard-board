"""Build a router_v020 spec that releases every signal net crossing the corridors of the failing nets.

usage: corridor_spec_v020.py geom.json fail_net,... out_spec.json [half_width_mm] [extra_spec.json]
Power-class nets keep their copper (router_v020 lays 0.127 mm tracks only).
"""
import json
import math
import sys

from shapely.geometry import LineString, box

g = json.load(open(sys.argv[1]))
fails = sys.argv[2].split(',')
out = sys.argv[3]
hw = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5
extra = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else {}
KEEP = ('GND', '3V3_AON', '3V3_RF', '3V3_SD', 'VSYS_RAW', 'VBUS_USB', 'BAT_', 'SGM41513_SW', 'SGM41513_PMID',
        'BUCK_LX', 'P47_VP_LX', 'P47_VN_LX', 'P47_VN', 'FL_SW', 'VDD_SPI', 'SPK_', 'XTAL', 'RF_ANT', 'LNA_IN')

wins = []
for n in fails:
    pts = [(p['x'], p['y']) for p in g['pads'] if p['net'] == n]
    used = [0]
    while len(used) < len(pts):
        d, i, j = min((math.dist(pts[i], pts[j]), i, j) for i in used for j in range(len(pts)) if j not in used)
        used.append(j)
        a, b = pts[i], pts[j]
        steps = max(1, int(d / 4))
        for k in range(steps):
            p0 = (a[0] + (b[0] - a[0]) * k / steps, a[1] + (b[1] - a[1]) * k / steps)
            p1 = (a[0] + (b[0] - a[0]) * (k + 1) / steps, a[1] + (b[1] - a[1]) * (k + 1) / steps)
            wins.append([min(p0[0], p1[0]) - hw, min(p0[1], p1[1]) - hw, max(p0[0], p1[0]) + hw, max(p0[1], p1[1]) + hw])
boxes = [box(*w) for w in wins]
nets = {n: 'all' for n in fails}
for t in g['tracks']:
    n = t['net']
    if not n or n in nets or n.startswith(KEEP):
        continue
    seg = LineString([(t['x1'], t['y1']), (t['x2'], t['y2'])])
    if any(seg.intersects(b) for b in boxes):
        nets.setdefault(n, wins)
for n, w in extra.get('nets', {}).items():
    nets.setdefault(n, w)
spec = dict(nets=nets, target_nets=[], iterations=extra.get('iterations', 60))
json.dump(spec, open(out, 'w'))
print(len(wins), 'corridor boxes,', len(nets), 'nets released:', ' '.join(sorted(nets)))
