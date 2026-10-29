"""Width-aware connection router for power/ground pads of moved parts.

Each connection runs from a pad to any existing copper of its net (or, for kind "via", to a new
via into the In1 ground plane next to the pad), at its own width, against all other copper with exact
clearances. Results are added to the geometry as fixed copper of the net.
usage: power_connect.py geom.json conns.json out_geom.json out_added.json
conns.json: [{"ref": "L507", "pad": "2", "width": 0.4, "kind": "net" | "via", "layers": ["F.Cu", "In2.Cu", "B.Cu"]}]
"""
import json, sys, uuid
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
sys.path.insert(0, sys.path[0])
import router2 as R

g = json.load(open(sys.argv[1]))
conns = json.load(open(sys.argv[2]))
out_geom, out_added = sys.argv[3], sys.argv[4]
added = []


def build_block(net, w):
    """Track-centre and via-centre forbidden rasters for copper of width w on `net`."""
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
        if t['net'] == net or t['layer'] not in R.LAYERS:
            continue
        s = R.seg_geom(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2)
        T[R.LAYERS.index(t['layer'])].geom(s.buffer(rT, 12))
        V.geom(s.buffer(rV, 12))
    for v in g['vias']:
        c = Point(v['x'], v['y'])
        if v['net'] != net:
            for cv in T:
                cv.geom(c.buffer(max(v['d'] / 2 + rT, v['drill'] / 2 + R.HOLE_CLR + w / 2), 24))
        V.geom(c.buffer(max(v['d'] / 2 + rV if v['net'] != net else 0, v['drill'] / 2 + R.H2H + R.VIA_DR / 2), 24))
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
                V.geom(pg.buffer(R.VIA_D / 2 + 0.05, 12))      # no via in own pads either
        if p['drill']:
            c = Point(p['x'], p['y'])
            for cv in T:
                cv.geom(c.buffer(max(p['drill']) / 2 + R.HOLE_CLR + w / 2, 24))
            V.geom(c.buffer(max(p['drill']) / 2 + R.H2H + R.VIA_DR / 2, 24))
    for z in g['zones']:
        if z['rule'] and z['no_vias']:
            V.geom(Polygon(z['outline'][0]).buffer(R.VIA_D / 2, 12))
    return np.stack([c.arr() for c in T]).reshape(-1), V.arr().reshape(-1)


def target_nodes(net, exclude_pad):
    """Grid nodes lying inside existing copper of `net` (other than the source pad)."""
    res = set()
    cores = []
    for t in g['tracks']:
        if t['net'] == net and t['layer'] in R.LAYERS:
            cores.append((R.LAYERS.index(t['layer']), R.seg_geom(t['x1'], t['y1'], t['x2'], t['y2'], max(t['w'] / 2 - 0.05, 0.01))))
    for v in g['vias']:
        if v['net'] == net:
            for li in range(R.NL):
                cores.append((li, Point(v['x'], v['y']).buffer(v['d'] / 2 - 0.1, 12)))
    for p in g['pads']:
        if p['net'] == net and (p['ref'], p['num']) != exclude_pad:
            for ly, q in p['polys'].items():
                if ly in R.LAYERS and len(q[0]) > 2:
                    cores.append((R.LAYERS.index(ly), Polygon(q[0]).buffer(-0.05)))
    for li, s in cores:
        if s.is_empty:
            continue
        minx, miny, maxx, maxy = s.bounds
        for i in R.irange(minx, maxx, R.NX):
            for j in R.irange(miny, maxy, R.NY, R.Y0):
                if s.contains(Point(R.X0 + i * R.PITCH, R.Y0 + j * R.PITCH)):
                    res.add(li * R.NLAYER + j * R.NX + i)
    return res


for cn in conns:
    pad = next(p for p in g['pads'] if p['ref'] == cn['ref'] and p['num'] == cn['pad'])
    net, w = pad['net'], cn['width']
    blk, vblk = build_block(net, w)
    allowed = [R.LAYERS.index(l) for l in cn.get('layers', R.LAYERS)]
    for li in range(R.NL):
        if li not in allowed:
            blk[li * R.NLAYER:(li + 1) * R.NLAYER] = 1
    item = R.Item('pad', pad, {ly: Polygon(q[0]) for ly, q in pad['polys'].items() if len(q[0]) > 2})
    saveW = R.W
    R.W = w
    starts = R.terminal_nodes([item])
    R.W = saveW
    if cn['kind'] == 'via':
        # goal: any node of the pad's layer where a via may stand (the via itself is the connection)
        li = R.LAYERS.index('F.Cu')
        goal = np.zeros(R.NL * R.NLAYER, np.uint8)
        cx, cy = pad['x'], pad['y']
        for i in R.irange(cx - 1.2, cx + 1.2, R.NX):
            for j in R.irange(cy - 1.2, cy + 1.2, R.NY, R.Y0):
                c = j * R.NX + i
                if not vblk[c] and not blk[li * R.NLAYER + c]:
                    goal[li * R.NLAYER + c] = 1
    else:
        goal = np.zeros(R.NL * R.NLAYER, np.uint8)
        tn = list(target_nodes(net, (pad['ref'], pad['num'])))
        goal[tn] = 1
        blk[tn] = 0
    if cn['kind'] == 'via' and cn.get('fallback_net', True):
        tn = list(target_nodes(net, (pad['ref'], pad['num'])))
        goal[tn] = 1
        blk[tn] = 0
    s = np.array([n for n in starts if not blk[n]], np.int32)
    if not len(s) or not goal.any():
        print(f'{cn["ref"]}.{cn["pad"]} {net}: no start/goal ({len(s)} starts)'); continue
    gx = np.array([(pad['x'] - R.X0) / R.PITCH]); gy = np.array([(pad['y'] - R.Y0) / R.PITCH]); gr = np.array([1e9])
    out = np.zeros(1_000_000, np.int32)
    zero = np.zeros(R.NL * R.NLAYER, np.int32); zv = np.zeros(R.NLAYER, np.int32)
    lc = np.array(R.LCOST, np.int32)
    blk8 = blk.astype(np.uint8); vblk8 = vblk.astype(np.uint8)
    L = R.LIB.astar(R.NX, R.NY, R.NL, blk8.ctypes.data_as(R.P8), vblk8.ctypes.data_as(R.P8), zero.ctypes.data_as(R.P32),
                    zv.ctypes.data_as(R.P32), lc.ctypes.data_as(R.P32), R.VIA_COST, s.ctypes.data_as(R.P32), len(s),
                    goal.ctypes.data_as(R.P8), gx.ctypes.data_as(R.PD), gy.ctypes.data_as(R.PD), gr.ctypes.data_as(R.PD), 1,
                    out.ctypes.data_as(R.P32), len(out), 50_000_000, R.BEND_COST)
    if L <= 0:
        print(f'{cn["ref"]}.{cn["pad"]} {net}: NO PATH'); continue
    path = out[:L][::-1].tolist()
    anchor = (pad['x'], pad['y'])
    tr, vi = R.path_to_copper(path, anchor, None)
    if cn['kind'] == 'via':
        l, x, y = R.node_xyl(path[-1])
        vi.append((x, y))
    new = []
    for ly, x1, y1, x2, y2 in tr:
        new.append(('t', dict(x1=x1, y1=y1, x2=x2, y2=y2, w=w, layer=ly, net=net, uuid='pwr-' + str(uuid.uuid4()))))
    for x, y in vi:
        new.append(('v', dict(x=x, y=y, d=R.VIA_D, drill=R.VIA_DR, net=net, uuid='pwr-' + str(uuid.uuid4()))))
    for k, it in new:
        (g['tracks'] if k == 't' else g['vias']).append(it)
        added.append(it)
    length = sum(np.hypot(t[3] - t[1], t[4] - t[2]) for t in tr)
    print(f'{cn["ref"]}.{cn["pad"]} {net}: {len(tr)} segs {length:.2f} mm w{w}, {len(vi)} vias')
json.dump(g, open(out_geom, 'w'))
json.dump(added, open(out_added, 'w'), indent=1)
