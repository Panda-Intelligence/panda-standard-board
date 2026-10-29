"""Connected components of one net's copper (pads, tracks, vias) by geometric overlap per layer.
usage: net_islands.py geom.json NET [NET ...]
"""
import json, sys
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

g = json.load(open(sys.argv[1]))
for net in sys.argv[2:]:
    items = []
    for p in g['pads']:
        if p['net'] == net:
            for ly, q in p['polys'].items():
                if len(q[0]) > 2:
                    items.append((ly, Polygon(q[0]).buffer(1e-4), f"pad {p['ref']}.{p['num']}", p.get('drill') is not None and p['drill'] is not None))
    for t in g['tracks']:
        if t['net'] == net:
            a, b = (t['x1'], t['y1']), (t['x2'], t['y2'])
            items.append((t['layer'], (LineString([a, b]) if a != b else Point(a)).buffer(t['w'] / 2 + 1e-4),
                          f"track {t['layer']} ({a[0]:.2f},{a[1]:.2f})", False))
    for v in g['vias']:
        if v['net'] == net:
            for ly in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'):
                items.append((ly, Point(v['x'], v['y']).buffer(v['d'] / 2 + 1e-4), f"via ({v['x']:.2f},{v['y']:.2f})", True))
    par = list(range(len(items)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    tree = STRtree([it[1] for it in items])
    for i, (ly, s, lab, _) in enumerate(items):
        for j in tree.query(s):
            if j != i and items[j][0] == ly and items[j][1].intersects(s):
                par[f(i)] = f(j)
    # vias / through-hole pads tie their layers together (same label, different layer entries)
    by_lab = {}
    for i, it in enumerate(items):
        if it[3]:
            by_lab.setdefault(it[2], []).append(i)
    for idx in by_lab.values():
        for i in idx[1:]:
            par[f(i)] = f(idx[0])
    comps = {}
    for i in range(len(items)):
        comps.setdefault(f(i), []).append(items[i][2])
    comps = sorted(comps.values(), key=len, reverse=True)
    print(f'{net}: {len(comps)} islands; sizes {[len(c) for c in comps[:8]]}')
    for c in comps[1:]:
        pads = [x for x in c if x.startswith('pad')]
        print('   island', len(c), 'items; pads', pads[:6], 'e.g.', c[0])
