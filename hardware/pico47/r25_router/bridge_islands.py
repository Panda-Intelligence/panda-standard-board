"""Repair a power net split by moved parts: delete pad-less islands, and bridge every island that carries
pads to the main island with a power-width route (any copper layer, through vias as needed).
Obstacles: all other-net copper except the nets being rerouted (spec), plus reserved escape vias.
usage: bridge_islands.py geom.json spec.json NET width out_geom.json out_record.json
"""
import json, sys, uuid
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.strtree import STRtree
sys.path.insert(0, sys.path[0])
import router2 as R

g = json.load(open(sys.argv[1]))
spec = json.load(open(sys.argv[2]))
net, w = sys.argv[3], float(sys.argv[4])
MIN_W = 0.3                         # bridge endpoints: tracks at least this wide, vias and pads
out_geom, out_rec = sys.argv[5], sys.argv[6]
route = set(spec['nets']) | set(R.TARGET)
keep = set(spec.get('keep_uuids', []))


def islands():
    items = []
    for p in g['pads']:
        if p['net'] == net:
            for ly, q in p['polys'].items():
                if len(q[0]) > 2:
                    items.append((ly, Polygon(q[0]).buffer(1e-4), ('pad', p['ref'] + '.' + p['num']), bool(p['drill'])))
    for t in g['tracks']:
        if t['net'] == net:
            a, b = (t['x1'], t['y1']), (t['x2'], t['y2'])
            items.append((t['layer'], (LineString([a, b]) if a != b else Point(a)).buffer(t['w'] / 2 + 1e-4), ('track', t['uuid']), False))
    for v in g['vias']:
        if v['net'] == net:
            for ly in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'):
                items.append((ly, Point(v['x'], v['y']).buffer(v['d'] / 2 + 1e-4), ('via', v['uuid']), True))
    par = list(range(len(items)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    tree = STRtree([it[1] for it in items])
    for i, it in enumerate(items):
        for j in tree.query(it[1]):
            if j != i and items[j][0] == it[0] and items[j][1].intersects(it[1]):
                par[f(i)] = f(j)
    multi = {}
    for i, it in enumerate(items):
        if it[3]:
            multi.setdefault(it[2], []).append(i)
    for idx in multi.values():
        for i in idx[1:]:
            par[f(i)] = f(idx[0])
    comps = {}
    for i in range(len(items)):
        comps.setdefault(f(i), []).append(items[i])
    return sorted(comps.values(), key=len, reverse=True)


comps = islands()
print(f'{net}: {len(comps)} islands {[len(c) for c in comps]}')
record = dict(deleted=[], added=[])
# 1. delete pad-less islands
dead = {it[2][1] for c in comps[1:] if not any(i[2][0] == 'pad' for i in c) for it in c}
g['tracks'] = [t for t in g['tracks'] if t['uuid'] not in dead]
g['vias'] = [v for v in g['vias'] if v['uuid'] not in dead]
record['deleted'] = sorted(dead)
print('deleted pad-less island copper:', len(dead))
comps = islands()
main = comps[0]
for isl in comps[1:]:
    # obstacles at this width
    rT = R.CLR + w / 2
    rV = R.CLR + R.VIA_D / 2
    T = [R.Canvas() for _ in R.LAYERS]
    V = R.Canvas()
    board = Polygon(g['outline'][0])
    outer = box(R.X0 - 5, R.Y0 - 5, R.X1 + 5, R.Y1 + 5)
    for cv in T:
        cv.geom(outer.difference(board.buffer(-(R.EDGE + w / 2))))
    V.geom(outer.difference(board.buffer(-(R.EDGE + R.VIA_D / 2))))
    for t in g['tracks']:
        if t['net'] == net or t['layer'] not in R.LAYERS or (t['net'] in route and t['uuid'] not in keep):
            continue
        s = R.seg_geom(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2)
        T[R.LAYERS.index(t['layer'])].geom(s.buffer(rT, 12))
        V.geom(s.buffer(rV, 12))
    for v in g['vias']:
        if v['net'] == net or (v['net'] in route and v['uuid'] not in keep):
            continue
        c = Point(v['x'], v['y'])
        for cv in T:
            cv.geom(c.buffer(max(v['d'] / 2 + rT, v['drill'] / 2 + R.HOLE_CLR + w / 2), 24))
        V.geom(c.buffer(max(v['d'] / 2 + rV, v['drill'] / 2 + R.HOLE_CLR + R.VIA_D / 2), 24))
    for p in g['pads']:
        for ly, q in p['polys'].items():
            if len(q[0]) < 3:
                continue
            pg = Polygon(q[0])
            if p['net'] != net:
                if ly in R.LAYERS:
                    T[R.LAYERS.index(ly)].geom(pg.buffer(rT + R.PAD_EPS, 12))
                if ly in R.LAYERS or (ly == 'In1.Cu' and p['net'] != 'GND'):
                    V.geom(pg.buffer(rV + R.PAD_EPS, 12))
            elif ly in R.LAYERS:
                V.geom(pg.buffer(R.VIA_D / 2 + 0.05, 12))
        if p['drill']:
            c = Point(p['x'], p['y'])
            for cv in T:
                cv.geom(c.buffer(max(p['drill']) / 2 + R.HOLE_CLR + w / 2, 24))
            V.geom(c.buffer(max(p['drill']) / 2 + R.HOLE_CLR + R.VIA_D / 2, 24))
    for kb in spec.get('bridge_keepout', []):          # areas the repaired power route must leave free
        for cv in T:
            cv.geom(box(*kb).buffer(w / 2 + R.CLR, 8))
        V.geom(box(*kb).buffer(R.VIA_D / 2 + R.CLR, 8))
    blk = np.stack([cv.arr() for cv in T]).reshape(-1).copy()
    vblk = V.arr().reshape(-1).copy()

    wide = {t['uuid'] for t in g['tracks'] if t['net'] == net and t['w'] >= MIN_W}

    def nodes_of(comp):
        res = set()
        for ly, s, ident, _ in comp:
            if ly not in R.LAYERS:
                continue
            if ident[0] == 'track' and ident[1] not in wide:
                continue          # the bridge must start/end on real power copper, never on a thin stub
            core = s.buffer(-min(0.05, w / 2))
            if core.is_empty:
                continue
            li = R.LAYERS.index(ly)
            minx, miny, maxx, maxy = core.bounds
            for i in R.irange(minx, maxx, R.NX):
                for j in R.irange(miny, maxy, R.NY, R.Y0):
                    if core.contains(Point(R.X0 + i * R.PITCH, R.Y0 + j * R.PITCH)):
                        res.add(li * R.NLAYER + j * R.NX + i)
        return np.array(sorted(res), np.int64)
    st, gl = nodes_of(isl), nodes_of(main)
    blk[st] = 0
    blk[gl] = 0
    goal = np.zeros(R.NL * R.NLAYER, np.uint8)
    goal[gl] = 1
    c0 = isl[0][1].centroid
    gx = np.array([(c0.x - R.X0) / R.PITCH]); gy = np.array([(c0.y - R.Y0) / R.PITCH]); gr = np.array([1e9])
    zero = np.zeros(R.NL * R.NLAYER, np.int32); zv = np.zeros(R.NLAYER, np.int32)
    out = np.zeros(2_000_000, np.int32)
    lc = np.array(R.LCOST, np.int32)
    s32 = st.astype(np.int32)
    L = R.search(blk.astype(np.uint8), vblk.astype(np.uint8), zero, zv, s32, goal, gl, gx, gy, gr, out, lc)
    if L <= 0:
        print('  island with pads', [i[2][1] for i in isl if i[2][0] == 'pad'][:4], ': NO BRIDGE PATH')
        continue
    path = out[:L][::-1].tolist()
    tr, vi = R.path_to_copper(path, None, None)
    for ly, x1, y1, x2, y2 in tr:
        it = dict(x1=x1, y1=y1, x2=x2, y2=y2, w=w, layer=ly, net=net, uuid='bridge-' + str(uuid.uuid4()))
        g['tracks'].append(it); record['added'].append(it)
    for x, y in vi:
        it = dict(x=x, y=y, d=R.VIA_D, drill=R.VIA_DR, net=net, uuid='bridge-' + str(uuid.uuid4()))
        g['vias'].append(it); record['added'].append(it)
    print('  bridged island with pads', [i[2][1] for i in isl if i[2][0] == 'pad'][:4],
          f': {len(tr)} segs {sum(np.hypot(t[3]-t[1], t[4]-t[2]) for t in tr):.2f} mm w{w}, {len(vi)} vias')
json.dump(g, open(out_geom, 'w'))
json.dump(record, open(out_rec, 'w'), indent=1)
print('after:', [len(c) for c in islands()])
