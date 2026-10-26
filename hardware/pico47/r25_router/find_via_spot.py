"""Find legal spots for a NET via joined by a straight track to a pad, using exact clearances on all layers.
usage: find_via_spot.py geom.json REF PAD [track_w|0] [radius]
"""
import json, sys, math
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree
CLR, HOLE, H2H, EDGE, VD, VDR = 0.15, 0.25, 0.25, 0.2, 0.4, 0.2
g = json.load(open(sys.argv[1])); ref, num = sys.argv[2], sys.argv[3]
w = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25; rad = float(sys.argv[5]) if len(sys.argv) > 5 else 1.5
TRACK = w > 0           # track_w 0: via only (it joins the pad through the zone fill)
pad = next(p for p in g['pads'] if p['ref'] == ref and p['num'] == num); net = pad['net']
padpoly = Polygon(pad['polys']['F.Cu'][0] if 'F.Cu' in pad['polys'] else pad['polys']['B.Cu'][0])
padly = 'F.Cu' if 'F.Cu' in pad['polys'] else 'B.Cu'
objs, holes = [], []
for t in g['tracks']:
    if t['net'] != net:
        a, b2 = (t['x1'], t['y1']), (t['x2'], t['y2'])
        objs.append((t['layer'], (LineString([a, b2]) if a != b2 else Point(a)).buffer(t['w'] / 2, 16)))
for v in g['vias']:
    c = Point(v['x'], v['y'])
    holes.append(c.buffer(v['drill'] / 2, 16))
    if v['net'] != net:
        for ly in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'):
            objs.append((ly, c.buffer(v['d'] / 2, 16)))
for p in g['pads']:
    if p['drill']:
        holes.append(Point(p['x'], p['y']).buffer(max(p['drill']) / 2, 16))
    if p['net'] != net:
        for ly, q in p['polys'].items():
            if len(q[0]) > 2:
                objs.append((ly, Polygon(q[0])))
for z in g.get('zones', []):
    if z.get('no_vias') or z.get('keepout'):
        objs.append(('VIAKO', Polygon(z['outline'][0])))
board = Polygon(g['outline'][0])
tree = STRtree([o[1] for o in objs]); htree = STRtree(holes)
c0 = padpoly.centroid; res = []
for i in range(-int(rad / 0.025), int(rad / 0.025) + 1):
    for j in range(-int(rad / 0.025), int(rad / 0.025) + 1):
        x, y = c0.x + i * 0.025, c0.y + j * 0.025
        pv = Point(x, y)
        if padpoly.distance(pv) < VD / 2 + 0.05:
            continue
        via = pv.buffer(VD / 2, 16); hole = pv.buffer(VDR / 2, 16)
        if board.exterior.distance(pv) < EDGE + VD / 2 or not board.contains(pv):
            continue
        q = padpoly.exterior.interpolate(padpoly.exterior.project(pv))
        trk = LineString([(c0.x, c0.y), (x, y)]).buffer(w / 2, 16)
        ok = True
        for k in tree.query(via.buffer(CLR).union(trk.buffer(CLR))):
            ly, s = objs[k]
            if ly == 'VIAKO':
                if s.intersects(via): ok = False; break
                continue
            if ly.endswith('.Cu') and s.distance(via) < CLR - 1e-6 and not (ly == 'In1.Cu' and False): ok = False; break
            if TRACK and ly == padly and s.distance(trk) < CLR - 1e-6: ok = False; break
            if s.distance(hole) < HOLE - 1e-6: ok = False; break
        if not ok: continue
        for k in htree.query(hole.buffer(H2H)):
            if holes[k].distance(hole) < H2H - 1e-6: ok = False; break
        if ok:
            res.append((math.hypot(x - c0.x, y - c0.y), round(x, 3), round(y, 3)))
res.sort(); print(net, 'pad', ref, num, 'candidates', len(res)); print(res[:10])
