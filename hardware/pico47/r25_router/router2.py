"""Negotiated-congestion grid router with windowed rip-up for the Pico47 Core continuation.

spec JSON: {"nets": {"NET": "all" | [[x0,y0,x1,y1], ...]}, "iterations": 60}
Every TARGET net is routed. A spec net loses its tracks/vias that touch its windows ("all" = whole net);
its remaining copper and pads form components that are reconnected into one tree.
Protected nets may never appear in the spec. Copper of nets outside the spec is a hard obstacle.
usage: router2.py geom.json spec.json out.json
"""
import ctypes, json, sys, time
import numpy as np
from PIL import Image, ImageDraw
import shapely
from shapely.geometry import Polygon, LineString, Point, box
from shapely.strtree import STRtree
from scipy.ndimage import binary_dilation

PITCH = 0.025
X0, Y0, X1, Y1 = 1.5, 1.5, 73.5, 131.5
LAYERS = ['F.Cu', 'In2.Cu', 'B.Cu']
LCOST = [1300, 1000, 1150]
W, CLR, VIA_D, VIA_DR = 0.15, 0.15, 0.4, 0.2
HOLE_CLR, H2H, EDGE, M = 0.25, 0.25, 0.2, 0.0  # exact raster; boundary (= rule distance) is legal, as in KiCad DRC
PAD_EPS = 0.002                     # pad outlines were exported ERROR_INSIDE (<= 2 um undersized)
ZONE_CLR, SPOKE_W, SPOKE_L = 0.2, 0.25, 0.5   # GND pour: zone clearance, thermal spoke width, spoke + minimum pour reach
SPOKE_BOX = None                    # set by prepare(): area where new routing must leave two thermal spokes per GND pad
FORCE_SPOKES = set()                # (ref, pad) GND pads that need spokes even though they have GND copper (KiCad flagged)
VIA_COST = 500 * 40
BEND_COST = 150                     # per 45-degree change of direction (0.3 of a grid step)
SEARCH_MAX_EXPAND = 60_000_000       # 每次 A* 搜索的默认展开上限，可由实验 spec 缩小
TARGET = ['P47_D1_SRC', 'SDMMC_CLK', 'P47_MUX3', 'P47_MUX5', 'P47_D10_SRC', 'P47_D11_SRC', 'P47_D14_SRC',
          'P47_XLE_SRC', 'SDMMC_D2', 'SDMMC_D1', 'SDMMC_D0', 'UART0_RX', 'UART0_TX', 'P47_D0_SRC',
          'P47_D7_SRC', 'P47_D6_SRC']
PROTECTED_PREFIX = ('GND', '3V3', 'VSYS', 'VBUS', 'BAT', 'VDD', 'USB', 'XTAL', 'LNA', 'RF_', 'FLASH', 'SPI',
                    'HW_ARM_GPIO', 'FL_HWEN')
NX, NY = int(round((X1 - X0) / PITCH)) + 1, int(round((Y1 - Y0) / PITCH)) + 1
NL = len(LAYERS)
NLAYER = NX * NY
LIB = ctypes.CDLL(__file__.rsplit('/', 1)[0] + '/libastar3.dylib')
P8, P32, PD = ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_double)
LIB.astar.argtypes = [ctypes.c_int] * 3 + [P8, P8, P32, P32, P32, ctypes.c_int32, P32, ctypes.c_int, P8,
                                           PD, PD, PD, ctypes.c_int, P32, ctypes.c_int, ctypes.c_int64,
                                           ctypes.c_int32]
LIB.astar_w.argtypes = LIB.astar.argtypes + [ctypes.c_int] * 4
WINDOW_MARGIN = 8.0                 # mm around the terminals' bounding box before falling back to the whole board
REGION = box(X0 - 1, Y0 - 1, X1 + 1, Y1 + 1)


def search(blk, vblk, extra, vextra, starts, goal, goal_nodes, gx, gy, gr, outbuf, lc, max_expand=None):
    """A* inside a window around starts+goals (fast path), retrying on the whole board when it fails."""
    if max_expand is None:
        max_expand = SEARCH_MAX_EXPAND
    cells = np.concatenate([np.asarray(starts, np.int64) % NLAYER, np.asarray(goal_nodes, np.int64) % NLAYER])
    xs, ys = cells % NX, cells // NX
    m = int(WINDOW_MARGIN / PITCH)
    win = (max(int(xs.min()) - m, 0), max(int(ys.min()) - m, 0), min(int(xs.max()) + m, NX - 1), min(int(ys.max()) + m, NY - 1))
    args = (NX, NY, NL, blk.ctypes.data_as(P8), vblk.ctypes.data_as(P8), extra.ctypes.data_as(P32),
            vextra.ctypes.data_as(P32), lc.ctypes.data_as(P32), VIA_COST, starts.ctypes.data_as(P32), len(starts),
            goal.ctypes.data_as(P8), gx.ctypes.data_as(PD), gy.ctypes.data_as(PD), gr.ctypes.data_as(PD), len(gx),
            outbuf.ctypes.data_as(P32), len(outbuf), max_expand, BEND_COST)
    L = LIB.astar_w(*args, *win)
    if L <= 0 and win != (0, 0, NX - 1, NY - 1):
        L = LIB.astar(*args)
    return L


class Canvas:
    """Boolean raster; cell (i, j) centre is world (X0 + i*PITCH, Y0 + j*PITCH).

    A cell is set exactly when its centre lies inside the drawn shape (vectorised point-in-polygon),
    so keepouts equal the rule distance instead of over-covering by up to half a cell.
    """

    def __init__(self):
        self.a = np.zeros((NY, NX), bool)

    def geom(self, gm):
        if gm.is_empty:
            return
        minx, miny, maxx, maxy = gm.bounds
        i0 = max(int(np.ceil((minx - X0) / PITCH)), 0)
        i1 = min(int(np.floor((maxx - X0) / PITCH)), NX - 1)
        j0 = max(int(np.ceil((miny - Y0) / PITCH)), 0)
        j1 = min(int(np.floor((maxy - Y0) / PITCH)), NY - 1)
        if i1 < i0 or j1 < j0:
            return
        xs = X0 + np.arange(i0, i1 + 1) * PITCH
        ys = Y0 + np.arange(j0, j1 + 1) * PITCH
        X, Y = np.meshgrid(xs, ys)
        self.a[j0:j1 + 1, i0:i1 + 1] |= shapely.contains_xy(gm, X, Y)

    def arr(self):
        return self.a


def seg_geom(x1, y1, x2, y2, r):
    if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
        return Point(x1, y1).buffer(r, 24)
    return LineString([(x1, y1), (x2, y2)]).buffer(r, 24)


def pad_polys(p, layer):
    return [Polygon(q) for q in p['polys'].get(layer, []) if len(q) > 2]


def cell(x, y):
    return int(round((y - Y0) / PITCH)) * NX + int(round((x - X0) / PITCH))


class Item:
    """One piece of copper of a routed net: kind pad/track/via with per-layer shapes."""

    def __init__(self, kind, src, shapes):
        self.kind, self.src, self.shapes = kind, src, shapes


def net_items(g, net, removed):
    items = []
    for p in g['pads']:
        if p['net'] == net:
            sh = {ly: Polygon(q) for ly, qs in p['polys'].items() for q in qs[:1] if len(q) > 2}
            items.append(Item('pad', p, sh))
    for t in g['tracks']:
        if t['net'] == net and t['uuid'] not in removed:
            items.append(Item('track', t, {t['layer']: seg_geom(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2)}))
    for v in g['vias']:
        if v['net'] == net and v['uuid'] not in removed:
            c = Point(v['x'], v['y']).buffer(v['d'] / 2, 24)
            items.append(Item('via', v, {ly: c for ly in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')}))
    return items


def components(items):
    par = list(range(len(items)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            for ly, s in items[i].shapes.items():
                o = items[j].shapes.get(ly)
                if o is not None and s.intersects(o):
                    par[f(i)] = f(j)
                    break
    comps = {}
    for i, it in enumerate(items):
        comps.setdefault(f(i), []).append(it)
    return list(comps.values())


def irange(lo, hi, n, origin=X0):
    """Grid indices covering [lo, hi], clipped to the routing grid (one cell inside its border)."""
    return range(max(int(np.ceil((lo - origin) / PITCH)), 1), min(int(np.floor((hi - origin) / PITCH)) + 1, n - 1))


def terminal_nodes(comp):
    """node -> anchor (x, y) for pad stubs, or None when the node already lies inside track/via copper."""
    res = {}
    for it in comp:
        if it.kind == 'pad':
            p = it.src
            for ly, pg in it.shapes.items():
                if ly not in LAYERS:
                    continue
                li = LAYERS.index(ly)
                inner = pg.buffer(-W / 2 - 0.002)
                if inner.is_empty:
                    continue
                shrunk = pg.buffer(-W / 2 + 0.001)
                minx, miny, maxx, maxy = inner.bounds
                for i in irange(minx, maxx, NX):
                    for j in irange(miny, maxy, NY, Y0):
                        x, y = X0 + i * PITCH, Y0 + j * PITCH
                        if inner.contains(Point(x, y)) and LineString([(p['x'], p['y']), (x, y)]).within(shrunk):
                            res[li * NLAYER + j * NX + i] = (p['x'], p['y'])
        elif it.kind == 'track':
            t = it.src
            li = LAYERS.index(t['layer'])
            core = seg_geom(t['x1'], t['y1'], t['x2'], t['y2'], max(t['w'] / 2 - 0.06, 0.01))
            minx, miny, maxx, maxy = core.bounds
            for i in irange(minx, maxx, NX):
                for j in irange(miny, maxy, NY, Y0):
                    if core.contains(Point(X0 + i * PITCH, Y0 + j * PITCH)):
                        res[li * NLAYER + j * NX + i] = None
        else:
            v = it.src
            core = Point(v['x'], v['y']).buffer(max(v['d'] / 2 - 0.1, 0.05), 16)
            minx, miny, maxx, maxy = core.bounds
            for i in irange(minx, maxx, NX):
                for j in irange(miny, maxy, NY, Y0):
                    if core.contains(Point(X0 + i * PITCH, Y0 + j * PITCH)):
                        for li in range(NL):
                            res[li * NLAYER + j * NX + i] = None
    return res


def raster_items(items, rT, rV, T=None, V=None):
    T = T or [Canvas() for _ in LAYERS]
    V = V or Canvas()
    for it in items:
        eps = PAD_EPS if it.kind == 'pad' else 0.0
        for ly, s in it.shapes.items():
            if ly in LAYERS:
                T[LAYERS.index(ly)].geom(s.buffer(rT + eps, 12))
            if ly in LAYERS or (it.kind == 'pad' and ly == 'In1.Cu'):
                V.geom(s.buffer(rV + eps, 12))
        if it.kind in ('pad', 'via'):
            src = it.src
            dr = (max(src['drill']) if it.kind == 'pad' else src['drill']) if (it.kind == 'via' or src['drill']) else None
            if dr:
                c = Point(src['x'], src['y'])
                for cv in T:
                    cv.geom(c.buffer(dr / 2 + HOLE_CLR + W / 2 + M, 24))
                # via hole-to-hole spacing, and via copper to the hole edge (KiCad hole clearance)
                V.geom(c.buffer(max(dr / 2 + H2H + VIA_DR / 2, dr / 2 + HOLE_CLR + VIA_D / 2) + M, 24))
    return T, V


def reserve_spokes(g, T, V):
    """Keep the two least obstructed thermal-spoke paths of every GND SMD pad inside SPOKE_BOX clear."""
    if SPOKE_BOX is None:
        return 0
    n = 0
    sig_polys = [Polygon(q[0]) for p in g['pads'] if p['net'] not in ('GND', '') and Point(p['x'], p['y']).within(SPOKE_BOX.buffer(2))
                 for ly, q in p['polys'].items() if ly in ('F.Cu', 'B.Cu') and len(q[0]) > 2]
    sig_tree = STRtree(sig_polys) if sig_polys else None
    gnd_cu = [(t['layer'], seg_geom(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2)) for t in g['tracks'] if t['net'] == 'GND']
    gnd_cu += [(ly, Point(v['x'], v['y']).buffer(v['d'] / 2, 12)) for v in g['vias'] if v['net'] == 'GND' for ly in ('F.Cu', 'B.Cu')]
    gnd_wired = set()
    for p in g['pads']:
        if p['net'] == 'GND' and Point(p['x'], p['y']).within(SPOKE_BOX):
            for ly, q in p['polys'].items():
                if ly in ('F.Cu', 'B.Cu') and len(q[0]) > 2 and any(l == ly and s.intersects(Polygon(q[0])) for l, s in gnd_cu):
                    gnd_wired.add((p['ref'], p['num']))
    for p in g['pads']:
        # two-terminal passives only (IC exposed pads have via fields, connector pins keep their r24 escapes),
        # and only pads that reach GND through the pour alone -- unless KiCad flagged the pad (FORCE_SPOKES)
        forced = (p['ref'], p['num']) in FORCE_SPOKES
        if p['net'] != 'GND' or p['drill'] or (p['ref'][:1] not in 'RCL' and not forced) or not (forced or Point(p['x'], p['y']).within(SPOKE_BOX)):
            continue
        if (p['ref'], p['num']) in gnd_wired and not forced:
            continue
        for ly in ('F.Cu', 'B.Cu'):
            q = p['polys'].get(ly)
            if not q or len(q[0]) < 3:
                continue
            pg = Polygon(q[0])
            minx, miny, maxx, maxy = pg.bounds
            cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
            h = SPOKE_W / 2
            rects = [box(maxx, cy - h, maxx + SPOKE_L, cy + h), box(minx - SPOKE_L, cy - h, minx, cy + h),
                     box(cx - h, maxy, cx + h, maxy + SPOKE_L), box(cx - h, miny - SPOKE_L, cx + h, miny)]
            li = LAYERS.index(ly)
            cur = T[li].arr()
            def blocked(r):
                a, b_, c_, d = r.bounds
                i0, i1 = int((a - X0) / PITCH), int((c_ - X0) / PITCH) + 1
                j0, j1 = int((b_ - Y0) / PITCH), int((d - Y0) / PITCH) + 1
                return cur[max(j0, 0):j1, max(i0, 0):i1].mean() if j1 > j0 and i1 > i0 else 1.0
            # never let a spoke path crowd a signal pad (it must keep its own escape)
            free = [r for r in rects if not sig_tree or not any(
                sig_polys[i].distance(r) < ZONE_CLR + 0.3 for i in sig_tree.query(r.buffer(ZONE_CLR + 0.3)))]
            # a KiCad-flagged pad boxed in by signal pins on every side still gets its spokes
            rects = free if free or not forced else rects
            for r in sorted(rects, key=blocked)[:2]:
                T[li].geom(r.buffer(ZONE_CLR + W / 2, 8))
                V.geom(r.buffer(ZONE_CLR + VIA_D / 2, 8))
                n += 1
    return n


def build_static(g, routed, removed):
    """Hard obstacles from every item not belonging to a routed net."""
    rT, rV = CLR + W / 2 + M, CLR + VIA_D / 2 + M
    items = []
    for t in g['tracks']:
        if t['net'] in routed or t['layer'] not in LAYERS:
            continue
        sg = seg_geom(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2)
        if sg.intersects(REGION):
            items.append(Item('track', t, {t['layer']: sg}))
    for v in g['vias']:
        if v['net'] in routed or not Point(v['x'], v['y']).buffer(1).intersects(REGION):
            continue
        c = Point(v['x'], v['y']).buffer(v['d'] / 2, 24)
        items.append(Item('via', v, {ly: c for ly in LAYERS}))
    for p in g['pads']:
        if p['net'] in routed or not Point(p['x'], p['y']).buffer(3).intersects(REGION):
            continue
        sh = {}
        for ly, qs in p['polys'].items():
            if ly in LAYERS or (ly == 'In1.Cu' and p['net'] != 'GND'):
                sh[ly] = Polygon(qs[0]) if len(qs) == 1 else Polygon(qs[0]).union(Polygon(qs[1]))
        items.append(Item('pad', p, sh))
    # edge keepout first: its board-shaped hole is drawn with fill 0 and would erase earlier obstacles
    T = [Canvas() for _ in LAYERS]
    V = Canvas()
    board = Polygon(g['outline'][0])
    outer = box(X0 - 5, Y0 - 5, X1 + 5, Y1 + 5)
    for cv in T:
        cv.geom(outer.difference(board.buffer(-(EDGE + W / 2 + M))))
    V.geom(outer.difference(board.buffer(-(EDGE + VIA_D / 2 + M))))
    raster_items(items, rT, rV, T, V)
    reserve_spokes(g, T, V)
    for z in g['zones']:
        if not z['rule']:
            continue
        pg = Polygon(z['outline'][0])
        if z['no_vias']:
            V.geom(pg.buffer(VIA_D / 2 + M, 12))
        if z['no_tracks']:
            for ly in z['layers']:
                if ly in LAYERS:
                    T[LAYERS.index(ly)].geom(pg.buffer(W / 2 + M, 12))
    return np.stack([c.arr() for c in T]), V.arr()


def node_xyl(n):
    l, c = divmod(n, NLAYER)
    j, i = divmod(c, NX)
    return l, X0 + i * PITCH, Y0 + j * PITCH


def path_to_copper(path, anchor_a, anchor_b):
    pts = [node_xyl(n) for n in path]
    tracks, vias = [], []
    runs, cur = [], [pts[0]]
    for q in pts[1:]:
        if q[0] != cur[-1][0]:
            runs.append(cur)
            vias.append((q[1], q[2]))
            cur = [q]
        else:
            cur.append(q)
    runs.append(cur)
    if anchor_a:
        runs[0].insert(0, (runs[0][0][0], anchor_a[0], anchor_a[1]))
    if anchor_b:
        runs[-1].append((runs[-1][-1][0], anchor_b[0], anchor_b[1]))
    for run in runs:
        simp = [run[0]]
        for k in range(1, len(run) - 1):
            a, b, c = simp[-1], run[k], run[k + 1]
            if abs((b[1] - a[1]) * (c[2] - b[2]) - (b[2] - a[2]) * (c[1] - b[1])) > 1e-9:
                simp.append(b)
        simp.append(run[-1])
        for a, b in zip(simp, simp[1:]):
            if abs(a[1] - b[1]) > 1e-9 or abs(a[2] - b[2]) > 1e-9:
                tracks.append((LAYERS[a[0]], a[1], a[2], b[1], b[2]))
    return tracks, vias


def occupancy(tracks, vias):
    T = [Canvas() for _ in LAYERS]
    V = Canvas()
    for ly, x1, y1, x2, y2 in tracks:
        sg = seg_geom(x1, y1, x2, y2, W / 2)
        T[LAYERS.index(ly)].geom(sg.buffer(CLR + W / 2 + M, 12))
        V.geom(sg.buffer(CLR + VIA_D / 2 + M, 12))
    for x, y in vias:
        c = Point(x, y)
        for cv in T:
            cv.geom(c.buffer(VIA_D / 2 + CLR + W / 2 + M, 24))
        V.geom(c.buffer(VIA_D + CLR + M, 24))
    return np.flatnonzero(np.stack([c.arr() for c in T])), np.flatnonzero(V.arr())


class Ctx:
    pass


def prepare(g, spec):
    """Remove windowed copper, build static/fixed rasters and per-net terminals."""
    c = Ctx()
    t0 = time.time()
    windows = dict(spec.get('nets', {}))
    for n in TARGET:
        windows.setdefault(n, 'all')
    for n in windows:
        if n.startswith(PROTECTED_PREFIX):
            raise SystemExit(f'protected net in spec: {n}')
    c.nets = list(windows)
    global SPOKE_BOX, FORCE_SPOKES
    FORCE_SPOKES = {tuple(x.split('.')) for x in spec.get('force_spokes', [])}
    wins = [b for w in windows.values() if w != 'all' for b in w]
    SPOKE_BOX = box(min(b[0] for b in wins), min(b[1] for b in wins), max(b[2] for b in wins), max(b[3] for b in wins)) if wins else None
    keep = set(spec.get('keep_uuids', []))
    c.removed = {}
    for n, win in windows.items():
        rem = []
        boxes = None if win == 'all' else [box(*b) for b in win]
        for t in g['tracks']:
            if t['net'] == n and (boxes is None or any(LineString([(t['x1'], t['y1']), (t['x2'], t['y2'])]).buffer(t['w'] / 2).intersects(bx) for bx in boxes)):
                rem.append(t['uuid'])
        for v in g['vias']:
            if v['net'] == n and (boxes is None or any(Point(v['x'], v['y']).buffer(v['d'] / 2).intersects(bx) for bx in boxes)):
                rem.append(v['uuid'])
        c.removed[n] = set(rem) - keep
    allrem = set().union(*c.removed.values())
    sT, sV = build_static(g, set(c.nets), allrem)
    c.comps, c.fixedR, c.terms, c.ownV = {}, {}, {}, {}
    for n in c.nets:
        items = net_items(g, n, c.removed[n])
        c.comps[n] = components(items)
        T, V = raster_items(items, CLR + W / 2 + M, CLR + VIA_D / 2 + M)
        c.fixedR[n] = (np.flatnonzero(np.stack([cv.arr() for cv in T])), np.flatnonzero(V.arr()))
        c.terms[n] = [terminal_nodes(cp) for cp in c.comps[n]]
        ov = Canvas()
        for it in items:
            if it.kind == 'pad':
                for ly, sh in it.shapes.items():
                    if ly in LAYERS:
                        ov.geom(sh.buffer(VIA_D / 2 + 0.05, 12))
        c.ownV[n] = np.flatnonzero(ov.arr())
        for k, tn in enumerate(c.terms[n]):
            if not tn:
                raise SystemExit(f'{n}: component {k} has no terminal nodes')
    print(f'setup {time.time() - t0:.1f}s nets {len(c.nets)} comps ' +
          ' '.join(f'{n}:{len(cp)}' for n, cp in c.comps.items() if len(cp) != 2), flush=True)
    c.fixT = np.zeros(NL * NLAYER, np.uint8)
    c.fixV = np.zeros(NLAYER, np.uint8)
    for n in c.nets:
        c.fixT[c.fixedR[n][0]] += 1
        c.fixV[c.fixedR[n][1]] += 1
    c.sTf, c.sVf = sT.reshape(-1), sV.reshape(-1)
    c.blk = np.empty(NL * NLAYER, np.uint8)
    c.vblk = np.empty(NLAYER, np.uint8)
    c.outbuf = np.zeros(4_000_000, np.int32)
    c.lc = np.array(LCOST, np.int32)
    return c


def route_net(c, n, extra, vextra):
    """Grow one net's tree from component 0 over the given soft costs. Returns (tracks, vias, nodes) or None."""
    oT, oV = c.fixedR[n]
    c.fixT[oT] -= 1
    c.fixV[oV] -= 1
    np.logical_or(c.sTf, c.fixT > 0, out=c.blk.view(bool))
    np.logical_or(c.sVf, c.fixV > 0, out=c.vblk.view(bool))
    c.vblk[c.ownV[n]] = 1
    c.fixT[oT] += 1
    c.fixV[oV] += 1
    tree = dict(c.terms[n][0])
    pending = list(range(1, len(c.comps[n])))
    tr_all, vi_all, nodes_all = [], [], []
    while pending:
        goal = np.zeros(NL * NLAYER, np.uint8)
        owner = {}
        gpts = []
        for k in pending:
            for nd in c.terms[n][k]:
                goal[nd] = 1
                owner[nd] = k
            xs = [node_xyl(nd) for nd in c.terms[n][k]]
            cx, cy = np.mean([q[1] for q in xs]), np.mean([q[2] for q in xs])
            rad = max(np.hypot(q[1] - cx, q[2] - cy) for q in xs)
            gpts.append(((cx - X0) / PITCH, (cy - Y0) / PITCH, rad / PITCH))
        gx = np.array([q[0] for q in gpts]); gy = np.array([q[1] for q in gpts]); gr = np.array([q[2] for q in gpts])
        starts = np.array(list(tree), np.int32)
        L = search(c.blk, c.vblk, extra, vextra, starts, goal, list(owner), gx, gy, gr, c.outbuf, c.lc)
        if L <= 0:
            return None
        path = c.outbuf[:L][::-1].tolist()
        k = owner[path[-1]]
        tr, vi = path_to_copper(path, tree.get(path[0]), c.terms[n][k].get(path[-1]))
        tr_all += tr
        vi_all += vi
        nodes_all += path
        for nd in path:
            tree.setdefault(nd, None)
        tree.update(c.terms[n][k])
        pending.remove(k)
    return tr_all, vi_all, np.array(nodes_all, np.int64)


def main():
    """PathFinder negotiation over all routed nets."""
    g = json.load(open(sys.argv[1]))
    spec = json.load(open(sys.argv[2]))
    out = sys.argv[3]
    global SEARCH_MAX_EXPAND
    SEARCH_MAX_EXPAND = int(spec.get('max_expand', SEARCH_MAX_EXPAND))
    t0 = time.time()
    c = prepare(g, spec)
    nets = c.nets
    extra = np.empty(NL * NLAYER, np.int32)
    vextra = np.empty(NLAYER, np.int32)
    cntT = np.zeros(NL * NLAYER, np.uint8)
    cntV = np.zeros(NLAYER, np.uint8)
    histT = np.zeros(NL * NLAYER, np.int32)
    histV = np.zeros(NLAYER, np.int32)
    occ, res, paths = {}, {}, {}
    pres = 2000
    best = None
    for it in range(spec.get('iterations', 60)):
        for n in nets:
            if n in occ:
                cntT[occ[n][0]] -= 1
                cntV[occ[n][1]] -= 1
            np.multiply(cntT, np.int32(pres), out=extra, casting='unsafe')
            extra += histT
            np.multiply(cntV, np.int32(pres * 4), out=vextra, casting='unsafe')
            vextra += histV
            r = route_net(c, n, extra, vextra)
            if r is None:
                print(f'it{it} {n}: FAILED', flush=True)
                occ.pop(n, None); res.pop(n, None); paths.pop(n, None)
                continue
            tr_all, vi_all, paths[n] = r
            res[n] = dict(tracks=tr_all, vias=vi_all, removed=sorted(c.removed[n]))
            occ[n] = occupancy(tr_all, vi_all)
            cntT[occ[n][0]] += 1
            cntV[occ[n][1]] += 1
        overT = np.zeros(cntT.size, bool)
        overV = np.zeros(cntV.size, bool)
        bad_nets = []
        for n, r in res.items():
            pn = paths[n]
            mine = np.isin(pn, occ[n][0])
            bad = pn[cntT[pn].astype(np.int32) - mine > 0]
            vc = np.array([cell(x, y) for x, y in r['vias']], np.int64)
            vbad = vc[cntV[vc].astype(np.int32) - np.isin(vc, occ[n][1]) > 0] if len(vc) else vc
            if len(bad) or len(vbad):
                bad_nets.append(n)
                overT[bad] = True
                overV[vbad] = True
        failed = [n for n in nets if n not in res]
        lens = sum(np.hypot(t[3] - t[1], t[4] - t[2]) for r in res.values() for t in r['tracks'])
        print(f'it{it}: routed {len(res)}/{len(nets)} conflicted {len(bad_nets)} over {int(overT.sum())}/{int(overV.sum())} len {lens:.1f}mm '
              f'vias {sum(len(r["vias"]) for r in res.values())} {time.time() - t0:.0f}s fail={failed} bad={bad_nets[:10]}',
              flush=True)
        json.dump(dict(nets=res, iteration=it, conflicted=bad_nets, failed=failed,
                       overT=np.flatnonzero(overT).tolist()[:200000]), open(out + '.last', 'w'))
        score = len(failed) * 100 + len(bad_nets)
        if best is None or score <= best[0]:
            best = (score, it)
            json.dump(dict(nets=res, spec=spec, iteration=it, conflicted=bad_nets, failed=failed,
                           complete=(not failed and not bad_nets)), open(out, 'w'))
        if not failed and not bad_nets:
            break
        histT += binary_dilation(overT.reshape(NL, NY, NX), iterations=4).reshape(-1).astype(np.int32) * 3000
        histV += binary_dilation(overV.reshape(NY, NX), iterations=4).reshape(-1).astype(np.int32) * 6000
        pres = min(int(pres * 1.5), 2_000_000)


if __name__ == '__main__':
    main()
