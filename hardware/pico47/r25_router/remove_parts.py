"""Hypothetical/relocation prep: remove parts' pads and the fixed copper that only served them.
Tracks/vias of the parts' nets that touch a removed pad are deleted, then copper of those nets that became
dangling within RADIUS of the parts is pruned repeatedly (a via counts as anchored if it lands on a pour net).
usage: remove_parts.py geom.json REF,REF,... out_geom.json [radius]
"""
import json, sys
from shapely.geometry import LineString, Point, Polygon
g = json.load(open(sys.argv[1])); refs = set(sys.argv[2].split(',')); out = sys.argv[3]
rad = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0
gone = [p for p in g['pads'] if p['ref'] in refs]
nets = {p['net'] for p in gone}
centers = [(p['x'], p['y']) for p in gone]
g['pads'] = [p for p in g['pads'] if p['ref'] not in refs]
near = lambda x, y: any(abs(x - a) < rad and abs(y - b) < rad for a, b in centers)
def shp(t):
    a, b = (t['x1'], t['y1']), (t['x2'], t['y2'])
    return (LineString([a, b]) if a != b else Point(a)).buffer(t['w'] / 2)
polys = [(ly, Polygon(q[0])) for p in gone for ly, q in p['polys'].items() if len(q[0]) > 2]
drop = set()
for t in g['tracks']:
    if t['net'] in nets and any(ly == t['layer'] and pg.intersects(shp(t)) for ly, pg in polys):
        drop.add(t['uuid'])
for v in g['vias']:
    if v['net'] in nets and any(pg.intersects(Point(v['x'], v['y']).buffer(v['d'] / 2)) for ly, pg in polys):
        drop.add(v['uuid'])
POUR = {'GND'}
while True:
    g['tracks'] = [t for t in g['tracks'] if t['uuid'] not in drop]
    g['vias'] = [v for v in g['vias'] if v['uuid'] not in drop]
    new = set()
    for net in nets:
        items = [('t', t, t['layer'], shp(t)) for t in g['tracks'] if t['net'] == net]
        items += [('v', v, ly, Point(v['x'], v['y']).buffer(v['d'] / 2)) for v in g['vias'] if v['net'] == net for ly in ('F.Cu', 'In2.Cu', 'B.Cu')]
        items += [('p', None, ly, Polygon(q[0])) for p in g['pads'] if p['net'] == net for ly, q in p['polys'].items() if len(q[0]) > 2]
        def touch(pt, ly, me):
            q = Point(pt).buffer(1e-4)
            return any(it[1] is not me and it[2] == ly and it[3].intersects(q) for it in items)
        for k, it, ly, s in items:
            if k == 't' and near(it['x1'], it['y1']):
                if not touch((it['x1'], it['y1']), ly, it) or not touch((it['x2'], it['y2']), ly, it):
                    new.add(it['uuid'])
            elif k == 'v' and net not in POUR and near(it['x'], it['y']):
                if not any(o[1] is not it and o[3].intersects(s) for o in items if o[2] == ly):
                    new.add(it['uuid'])
    if not new:
        break
    drop |= new
print('removed parts', sorted(refs), 'copper items', len(drop))
json.dump(g, open(out, 'w'))
