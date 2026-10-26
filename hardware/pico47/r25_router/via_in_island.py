"""Legal GND via spots (all layers, exact clearances) inside given zone-fill island polygons.
usage: via_in_island.py geom.json islands.json
"""
import json, sys
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree
CLR, HOLE, H2H, EDGE, VD, VDR, ZCLR = 0.15, 0.25, 0.25, 0.2, 0.4, 0.2, 0.2
g = json.load(open(sys.argv[1])); isl = json.load(open(sys.argv[2])); net = 'GND'
objs, holes = [], []
for t in g['tracks']:
    if t['net'] != net:
        a, b2 = (t['x1'], t['y1']), (t['x2'], t['y2'])
        objs.append((LineString([a, b2]) if a != b2 else Point(a)).buffer(t['w'] / 2, 16))
for v in g['vias']:
    c = Point(v['x'], v['y']); holes.append(c.buffer(v['drill'] / 2, 16))
    if v['net'] != net:
        objs.append(c.buffer(v['d'] / 2, 16))
for p in g['pads']:
    if p['drill']:
        holes.append(Point(p['x'], p['y']).buffer(max(p['drill']) / 2, 16))
    if p['net'] != net:
        for ly, q in p['polys'].items():
            if len(q[0]) > 2 and ly != 'In1.Cu':
                objs.append(Polygon(q[0]))
            elif len(q[0]) > 2:
                objs.append(Polygon(q[0]))
ko = [Polygon(z['outline'][0]) for z in g.get('zones', []) if z.get('no_vias')]
tree = STRtree(objs); htree = STRtree(holes)
for o in isl:
    poly = Polygon(o['pts']); x0, y0, x1, y1 = poly.bounds; res = []
    x = x0
    while x <= x1:
        y = y0
        while y <= y1:
            pv = Point(round(x / 0.025) * 0.025, round(y / 0.025) * 0.025)
            if poly.contains(pv) and not any(k.distance(pv) < VD / 2 for k in ko):
                via, hole = pv.buffer(VD / 2, 16), pv.buffer(VDR / 2, 16)
                ok = all(objs[k].distance(via) >= CLR - 1e-6 and objs[k].distance(hole) >= HOLE - 1e-6 for k in tree.query(via.buffer(HOLE)))
                ok = ok and all(holes[k].distance(hole) >= H2H - 1e-6 for k in htree.query(hole.buffer(H2H)))
                if ok:
                    res.append((round(-poly.exterior.distance(pv), 3), round(pv.x, 3), round(pv.y, 3)))
            y += 0.025
        x += 0.025
    res.sort(); print(o['layer'], 'area', round(poly.area, 3), 'candidates', len(res), res[:5])
