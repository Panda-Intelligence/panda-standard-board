"""Remove dangling copper from a final geometry: track segments with a free end and vias touching nothing
of their own net, repeated to a fixed point. Supply/ground nets are left alone (their copper may end in a pour).
usage: prune_geom.py final_geom.json out_geom.json
"""
import json, sys
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

PROTECTED = ('GND', '3V3', 'VSYS', 'VBUS', 'BAT', 'VDD')
g = json.load(open(sys.argv[1]))
pads_by_net = {}
for p in g['pads']:
    for ly, q in p['polys'].items():
        if len(q[0]) > 2:
            pads_by_net.setdefault(p['net'], []).append((ly, Polygon(q[0])))
removed = 0
while True:
    by_net = {}
    for t in g['tracks']:
        by_net.setdefault(t['net'], []).append(('t', t))
    for v in g['vias']:
        by_net.setdefault(v['net'], []).append(('v', v))
    drop = set()
    for net, items in by_net.items():
        if not net or net.startswith(PROTECTED):
            continue
        shapes = []
        for k, it in items:
            if k == 't':
                a, b = (it['x1'], it['y1']), (it['x2'], it['y2'])
                shapes.append((k, it, it['layer'], (LineString([a, b]) if a != b else Point(a)).buffer(it['w'] / 2)))
            else:
                c = Point(it['x'], it['y']).buffer(it['d'] / 2)
                for ly in ('F.Cu', 'In2.Cu', 'B.Cu'):
                    shapes.append((k, it, ly, c))
        for ly, pg in pads_by_net.get(net, []):
            shapes.append(('p', None, ly, pg))
        tree = STRtree([s[3] for s in shapes])

        def touches(pt, layer, me):
            q = Point(pt).buffer(1e-4)
            return any(shapes[j][1] is not me and shapes[j][2] == layer and shapes[j][3].intersects(q)
                       for j in tree.query(q))
        for k, it in items:
            if k == 't':
                if not touches((it['x1'], it['y1']), it['layer'], it) or not touches((it['x2'], it['y2']), it['layer'], it):
                    drop.add(it['uuid'])
            else:
                c = Point(it['x'], it['y']).buffer(it['d'] / 2)
                if not any(shapes[j][1] is not it and shapes[j][3].intersects(c) for j in tree.query(c)):
                    drop.add(it['uuid'])
    if not drop:
        break
    g['tracks'] = [t for t in g['tracks'] if t['uuid'] not in drop]
    g['vias'] = [v for v in g['vias'] if v['uuid'] not in drop]
    removed += len(drop)
json.dump(g, open(sys.argv[2], 'w'))
print('pruned', removed, 'dangling items')
