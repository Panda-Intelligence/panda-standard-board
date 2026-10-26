"""Plan a conflict-free U501 escape (fanout) for every rerouted QFN pin with CP-SAT.

Candidates per pin: a 45-degree dogleg stub from the pad's inner or outer end to a via, or an outward
F.Cu stub. Legality uses router2's exact rasters; pairwise conflicts use its occupancy model.
Output: geom with the chosen escape copper injected (new uuids) + spec with those uuids kept.
usage: escape_plan.py geom.json spec.json out_geom.json out_spec.json
"""
import json, sys, time, uuid, math
import numpy as np
from shapely.geometry import Polygon
from ortools.sat.python import cp_model
sys.path.insert(0, sys.path[0])
import router2 as R
from u501_fanout import fanout

g = json.load(open(sys.argv[1]))
spec = json.load(open(sys.argv[2]))
spec.pop('keep_uuids', None)
t0 = time.time()
c = R.prepare(g, spec)
route = set(c.nets)
EP = (62.5, 96.5)
pins = [p for p in g['pads'] if p['ref'] == 'U501' and p['net'] in route and p['num'] != '57']
print(f'{len(pins)} U501 pins to escape', flush=True)
N = R.NL * R.NLAYER


def pad_fix(p):
    sh = {ly: Polygon(q[0]) for ly, q in p['polys'].items()}
    it = R.Item('pad', p, sh)
    T, V = R.raster_items([it], R.CLR + R.W / 2 + R.M, R.CLR + R.VIA_D / 2 + R.M)
    return np.flatnonzero(np.stack([cv.arr() for cv in T])), np.flatnonzero(V.arr()), sh['F.Cu']


def cells_of_polyline(pts, layer):
    out = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        n = max(2, int(math.hypot(x2 - x1, y2 - y1) / (R.PITCH / 2)) + 1)
        for k in range(n + 1):
            x, y = x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n
            out.append(layer * R.NLAYER + int(round((y - R.Y0) / R.PITCH)) * R.NX + int(round((x - R.X0) / R.PITCH)))
    return np.unique(np.array(out, np.int64))


cands = []      # (pin index, cost, tracks, vias, centre-cells, via-cells)
for pi, p in enumerate(pins):
    ta, va, poly = pad_fix(p)
    fixT = c.fixT.astype(np.int16); fixT[ta] -= 1
    fixV = c.fixV.astype(np.int16); fixV[va] -= 1
    blk = c.sTf | (fixT > 0)
    vblk = c.sVf | (fixV > 0)
    minx, miny, maxx, maxy = poly.bounds
    vertical = (maxy - miny) > (maxx - minx)
    cx, cy = p['x'], p['y']
    if vertical:
        sgn = 1 if EP[1] > cy else -1
        ends = {'in': (cx, cy + sgn * (maxy - miny) / 2), 'out': (cx, cy - sgn * (maxy - miny) / 2)}
        dirs = {'in': (0, sgn), 'out': (0, -sgn)}
        perp = (1, 0)
    else:
        sgn = 1 if EP[0] > cx else -1
        ends = {'in': (cx + sgn * (maxx - minx) / 2, cy), 'out': (cx - sgn * (maxx - minx) / 2, cy)}
        dirs = {'in': (sgn, 0), 'out': (-sgn, 0)}
        perp = (0, 1)
    own = poly.buffer(R.VIA_D / 2 + 0.05)
    n0 = len(cands)
    for side, smax in (('in', 1.0), ('out', 1.6)):
        ex, ey = ends[side]
        dx, dy = dirs[side]
        for s in np.arange(0.25, smax + 1e-9, 0.05):
            for t in np.arange(-1.0, 1.0 + 1e-9, 0.05):
                if abs(t) > s + 1e-9:
                    continue
                bend = (ex + dx * (s - abs(t)), ey + dy * (s - abs(t)))
                end = (bend[0] + perp[0] * t, bend[1] + perp[1] * t)
                end = (round(round((end[0] - R.X0) / R.PITCH) * R.PITCH + R.X0, 4),
                       round(round((end[1] - R.Y0) / R.PITCH) * R.PITCH + R.Y0, 4))
                pts = [(cx, cy), (ex, ey), bend, end]
                cl = cells_of_polyline(pts, 0)
                if blk[cl].any():
                    continue
                ec = int(round((end[1] - R.Y0) / R.PITCH)) * R.NX + int(round((end[0] - R.X0) / R.PITCH))
                length = math.hypot(ex - cx, ey - cy) + (s - abs(t)) + abs(t) * math.sqrt(2)
                tracks = [('F.Cu', a[0], a[1], b[0], b[1]) for a, b in zip(pts, pts[1:])
                          if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6]
                from shapely.geometry import Point
                if not vblk[ec] and not own.contains(Point(end)) and not any(blk[l * R.NLAYER + ec] for l in range(R.NL)):
                    cands.append((pi, 10 + length + (0 if side == 'in' else 0.5), tracks, [end], cl, np.array([ec]), None))
                if side == 'out' and s >= 0.6 and t == 0:
                    cands.append((pi, 25 + length, tracks, [], cl, np.zeros(0, np.int64), None))
    # the pin's existing escape copper (relabelled with the pin when swapped) is always a candidate
    orig = set(fanout(g, p, p['net']))
    # an existing "escape" must actually leave the pad: end in a via or reach >= 0.3 mm beyond it
    if orig and not any(v['uuid'] in orig for v in g['vias']):
        reach = max((Polygon(poly.exterior).distance(R.Point(x, y)) if not poly.contains(R.Point(x, y)) else 0.0)
                    for t in g['tracks'] if t['uuid'] in orig for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2'])))
        if reach < 0.3:
            orig = set()
    if orig:
        otr = [t for t in g['tracks'] if t['uuid'] in orig]
        ovi = [v for v in g['vias'] if v['uuid'] in orig]
        cl = np.unique(np.concatenate([cells_of_polyline([(t['x1'], t['y1']), (t['x2'], t['y2'])], R.LAYERS.index(t['layer']))
                                       for t in otr]))
        vcs = np.array([int(round((v['y'] - R.Y0) / R.PITCH)) * R.NX + int(round((v['x'] - R.X0) / R.PITCH)) for v in ovi], np.int64)
        tr = [(t['layer'], t['x1'], t['y1'], t['x2'], t['y2']) for t in otr]
        cands.append((pi, 8.0, tr, [(v['x'], v['y']) for v in ovi], cl, vcs, sorted(orig)))
    print(f'pin {p["num"]:>2} {p["net"]:16s} candidates {len(cands) - n0}{" (incl. existing)" if orig else ""}', flush=True)

print(f'{len(cands)} candidates {time.time() - t0:.0f}s; building conflicts', flush=True)
occT, occV = [], []
for k, (pi, cost, tr, vi, cl, vc, ou) in enumerate(cands):
    o = R.occupancy(tr, vi)
    occT.append(o[0]); occV.append(o[1])
# conflict if one candidate's centre/via cells fall in another pin's candidate occupancy
cell_owner = {}
for k in range(len(cands)):
    for cc in occT[k]:
        cell_owner.setdefault(int(cc), []).append(k)
vowner = {}
for k in range(len(cands)):
    for cc in occV[k]:
        vowner.setdefault(int(cc), []).append(k)
conf = set()
for k, (pi, cost, tr, vi, cl, vc, ou) in enumerate(cands):
    hits = set()
    for cc in cl:
        hits.update(cell_owner.get(int(cc), ()))
    for l in range(R.NL):
        for cc in vc:
            hits.update(cell_owner.get(int(l * R.NLAYER + cc), ()))
    for cc in vc:
        hits.update(vowner.get(int(cc), ()))
    for h in hits:
        # two untouched r24 escapes already coexist legally (r24 native DRC), whatever the raster says
        if cands[h][0] != pi and not (ou and cands[h][6]):
            conf.add((min(k, h), max(k, h)))
print(f'{len(conf)} conflicts {time.time() - t0:.0f}s', flush=True)
m = cp_model.CpModel()
miss = []
x = [m.NewBoolVar(f'x{k}') for k in range(len(cands))]
for pi in range(len(pins)):
    ks = [k for k in range(len(cands)) if cands[k][0] == pi]
    m.AddAtMostOne([x[k] for k in ks])
    miss.append((pi, 1 - sum(x[k] for k in ks)))
for a, b in conf:
    m.AddBoolOr([x[a].Not(), x[b].Not()])
m.Minimize(sum(int(cands[k][1] * 100) * x[k] for k in range(len(cands))) + sum(1_000_000 * e for _, e in miss))
sol = cp_model.CpSolver()
sol.parameters.max_time_in_seconds = 300
sol.parameters.num_workers = 8
st = sol.Solve(m)
print('solver', sol.StatusName(st), f'{time.time() - t0:.0f}s', flush=True)
unescaped = [pins[pi]['num'] + ':' + pins[pi]['net'] for pi, e in miss if st in (cp_model.OPTIMAL, cp_model.FEASIBLE) and sol.Value(e)]
print('UNESCAPED', unescaped, flush=True)
if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    sys.exit(1)
keep = []
for k in range(len(cands)):
    if sol.Value(x[k]):
        pi, cost, tr, vi, cl, vc, ou = cands[k]
        net = pins[pi]['net']
        if ou:
            keep += ou
            print(f'  pin {pins[pi]["num"]:>2} {net:16s} existing escape', flush=True)
            continue
        for ly, x1, y1, x2, y2 in tr:
            u = str(uuid.uuid4())
            g['tracks'].append(dict(x1=x1, y1=y1, x2=x2, y2=y2, w=R.W, layer=ly, net=net, uuid=u))
            keep.append(u)
        for vx, vy in vi:
            u = str(uuid.uuid4())
            g['vias'].append(dict(x=vx, y=vy, d=R.VIA_D, drill=R.VIA_DR, net=net, uuid=u))
            keep.append(u)
        print(f'  pin {pins[pi]["num"]:>2} {net:16s} {"via " + str(vi[0]) if vi else "F stub"}', flush=True)
spec['keep_uuids'] = keep
json.dump(g, open(sys.argv[3], 'w'))
json.dump(spec, open(sys.argv[4], 'w'), indent=1)
