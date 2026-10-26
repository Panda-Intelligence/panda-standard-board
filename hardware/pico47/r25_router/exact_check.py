"""Exact (shapely) clearance check of new copper in a final geometry, mirroring the KiCad copper rules.
usage: exact_check.py final_geom.json r24_geom.json
Reports new tracks/vias closer than 0.15 mm to other-net copper, than 0.25 mm (copper) to holes, or
whose vias are closer than 0.25 mm hole-to-hole, plus same-net via hole spacing.
"""
import json, sys
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

CLR, HOLE, H2H, EDGE = 0.15, 0.25, 0.25, 0.2
gf = json.load(open(sys.argv[1]))
r24 = {t['uuid'] for t in json.load(open(sys.argv[2]))['tracks'] + json.load(open(sys.argv[2]))['vias']}
objs = []        # (layer, net, shape, is_new, label)
for t in gf['tracks']:
    a, b = (t['x1'], t['y1']), (t['x2'], t['y2'])
    s = (LineString([a, b]) if a != b else Point(a)).buffer(t['w'] / 2, 32)
    objs.append((t['layer'], t['net'], s, t['uuid'] not in r24, f"track {t['net']} {t['layer']} ({a[0]:.3f},{a[1]:.3f})-({b[0]:.3f},{b[1]:.3f}) w{t['w']}"))
holes = []
for v in gf['vias']:
    c = Point(v['x'], v['y'])
    for ly in ('F.Cu', 'In2.Cu', 'B.Cu'):
        objs.append((ly, v['net'], c.buffer(v['d'] / 2, 64), v['uuid'] not in r24, f"via {v['net']} ({v['x']:.3f},{v['y']:.3f})"))
    holes.append((v['net'], c.buffer(v['drill'] / 2, 64), v['uuid'] not in r24, f"via-hole {v['net']} ({v['x']:.3f},{v['y']:.3f})"))
for p in gf['pads']:
    for ly, q in p['polys'].items():
        if ly in ('F.Cu', 'In2.Cu', 'B.Cu') and len(q[0]) > 2:
            objs.append((ly, p['net'], Polygon(q[0]), False, f"pad {p['ref']}.{p['num']} {p['net']}"))
    if p['drill']:
        holes.append((p['net'], Point(p['x'], p['y']).buffer(max(p['drill']) / 2, 64), False, f"pad-hole {p['ref']}.{p['num']}"))
tree = STRtree([o[2] for o in objs])
issues = set()
for i, (ly, net, s, new, lab) in enumerate(objs):
    if not new:
        continue
    for j in tree.query(s.buffer(CLR)):
        ly2, net2, s2, new2, lab2 = objs[j]
        if ly2 != ly or net2 == net or (new2 and j < i):
            continue
        d = s.distance(s2)
        if d < CLR - 1e-5:
            issues.add((round(d, 4), 'clearance', lab, lab2))
htree = STRtree([h[1] for h in holes])
for i, (ly, net, s, new, lab) in enumerate(objs):
    if not new:
        continue
    for j in htree.query(s.buffer(HOLE)):
        hnet, hs, hnew, hlab = holes[j]
        if hnet == net:
            continue
        d = s.distance(hs)
        if d < HOLE - 1e-5:
            issues.add((round(d, 4), 'hole_clearance', lab, hlab))
for i, (net, hs, new, lab) in enumerate(holes):
    if not new:
        continue
    for j in htree.query(hs.buffer(H2H)):
        if j == i:
            continue
        d = hs.distance(holes[j][1])
        if d < H2H - 1e-5:
            issues.add((round(d, 4), 'hole_to_hole', lab, holes[j][3]))
for it in sorted(issues):
    print(it)
print(len(issues), 'issues')
