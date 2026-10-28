"""PathFinder with pin-swappable groups (ESP32-S3 GPIO matrix / SGM330A channel freedom).

Group members are pseudo-nets: each source pad must connect to exactly one sink pad of its group.
Every few iterations a congestion-aware source x sink cost matrix is solved (Hungarian) to choose the
pairing; between re-assignments all pairs and ordinary nets are negotiated as usual.
usage: router5.py geom.json spec.json design.json out.json
"""
import json, sys, time
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.ndimage import binary_dilation
sys.path.insert(0, sys.path[0])
import router2 as R
from u501_fanout import fanout

g = json.load(open(sys.argv[1]))
spec = json.load(open(sys.argv[2]))
design = json.load(open(sys.argv[3]))
out = sys.argv[4]
R.SEARCH_MAX_EXPAND = int(spec.get('max_expand', getattr(R, 'SEARCH_MAX_EXPAND', 60_000_000)))
if 'layer_cost' in spec:
    R.LCOST[:] = [int(x) for x in spec['layer_cost']]
t0 = time.time()
pad = {(p['ref'], p['num']): p for p in g['pads']}
gp_pin = {int(k): str(v['package_pin']) for k, v in design['gpio'].items()}
TRI = design['mux']['source_terminal_pins']
CH = [(ref, tri) for ref in ('U710', 'U711') for tri in TRI]
uart_common = {gp_pin[43], gp_pin[44]}
# channels whose common currently lands on GPIO43/44 stay UART channels (fixed)
ch_common_net = {i: pad[(ref, str(tri[2]))]['net'] for i, (ref, tri) in enumerate(CH)}
u501_net = {p['num']: p['net'] for p in g['pads'] if p['ref'] == 'U501'}
uart_ch = {i for i in range(8) if any(u501_net[x] == ch_common_net[i] for x in uart_common)}
sd_ch = [i for i in range(8) if i not in uart_ch]
groups = {
    'A': ([(CH[i][0], str(CH[i][1][1])) for i in range(8)], [('R' + str(710 + b), '1') for b in range(8)]),
    'B': ([('U501', gp_pin[x]) for x in (14, 17, 18, 21, 38, 39, 40)], [('R' + str(710 + b), '1') for b in range(9, 16)]),
}
if spec.get('group_b_ext'):
    # GPIO-matrix functions that may also trade pins with the direct display bits (strapping GPIO45 excluded).
    # The B group has fourteen physical endpoints; derive the sink set explicitly so
    # E26's current pad nets cannot add duplicate sinks (the same display net can be
    # visible on more than one GPIO source after the approved pin permutation).
    ext_gpio = (11, 12, 13, 41, 42, 47, 48)
    b_sinks = [('R' + str(710 + b), '1') for b in range(9, 16)]
    b_sinks += [('R726', '1'), ('R727', '1'), ('R729', '1'), ('R730', '1'),
                ('U904', '2'), ('U904', '3'), ('U904', '4')]
    b_sources = [('U501', gp_pin[x]) for x in (14, 17, 18, 21, 38, 39, 40) + ext_gpio]
    groups['B'] = (b_sources, b_sinks)
groups.update({
    'C': ([(CH[i][0], str(CH[i][1][0])) for i in sd_ch], [('R517', '1'), ('R518', '1'), ('R519', '1'), ('R520', '1'), ('R521', '1'), ('R522', '1')]),
    'D': ([(CH[i][0], str(CH[i][1][2])) for i in sd_ch], [('U501', gp_pin[x]) for x in (5, 6, 7, 8, 9, 10)]),
})
print('UART channels', sorted(uart_ch), 'SD channels', sd_ch, flush=True)
keep = set(spec.get('keep_uuids', []))
orig_net = {}
pseudo = {}
old_names = set()
for gname, (srcs, snks) in groups.items():
    for role, keys in (('S', srcs), ('K', snks)):
        for k in keys:
            p = pad[k]
            name = f'{gname}{role}:{k[0]}.{k[1]}'
            orig_net[name] = p['net']
            old_names.add(p['net'])
            if role == 'K' and k[0] != 'U501':
                # copper still attached to the far end (e.g. a windowed remainder) belongs to the sink
                for t in g['tracks'] + g['vias']:
                    if t['net'] == p['net'] and t['uuid'] not in keep:
                        t['net'] = name
            if k[0] == 'U501':
                for u in fanout(g, p, p['net']):
                    for t in g['tracks'] + g['vias']:
                        if t['uuid'] == u:
                            t['net'] = name
            p['net'] = name
            pseudo[name] = k
# drop all remaining copper of fully ripped nets (escape copper was renamed above or is kept)
full = {n for n, w in spec['nets'].items() if w == 'all'} | old_names
g['tracks'] = [t for t in g['tracks'] if t['net'] not in full or t['uuid'] in keep]
g['vias'] = [v for v in g['vias'] if v['net'] not in full or v['uuid'] in keep]
alive = {p['net'] for p in g['pads']}
spec2 = dict(spec)
spec2['nets'] = {n: w for n, w in spec['nets'].items() if n in alive and n not in pseudo}
for n in pseudo:
    spec2['nets'][n] = 'all'
regular_targets = [n for n in R.TARGET if n in alive and n not in pseudo]
R.TARGET = regular_targets
c = R.prepare(g, spec2)
regular = [n for n in c.nets if n not in pseudo]
sources = {gname: [f'{gname}S:{k[0]}.{k[1]}' for k in srcs] for gname, (srcs, snks) in groups.items()}
sinks = {gname: [f'{gname}K:{k[0]}.{k[1]}' for k in snks] for gname, (srcs, snks) in groups.items()}
print(f'regular nets {len(regular)}: {regular}', flush=True)
N = R.NL * R.NLAYER
HIST_T = spec.get('hist', 3000)
HIST_DIL = spec.get('hist_dilation', 4)
R.BEND_COST = spec.get('bend', R.BEND_COST)


def route_pair(src, snk, extra, vextra):
    """Route src pseudo-net to snk pseudo-net (both fixed obstacles for everyone else)."""
    for n in (src, snk):
        oT, oV = c.fixedR[n]
        c.fixT[oT] -= 1
        c.fixV[oV] -= 1
    np.logical_or(c.sTf, c.fixT > 0, out=c.blk.view(bool))
    np.logical_or(c.sVf, c.fixV > 0, out=c.vblk.view(bool))
    c.vblk[c.ownV[src]] = 1
    c.vblk[c.ownV[snk]] = 1
    for n in (src, snk):
        oT, oV = c.fixedR[n]
        c.fixT[oT] += 1
        c.fixV[oV] += 1
    ta, tb = c.terms[src][0], c.terms[snk][0]
    goal = np.zeros(N, np.uint8)
    goal[list(tb)] = 1
    xs = [R.node_xyl(nd) for nd in tb]
    cx, cy = np.mean([q[1] for q in xs]), np.mean([q[2] for q in xs])
    rad = max(np.hypot(q[1] - cx, q[2] - cy) for q in xs)
    gx = np.array([(cx - R.X0) / R.PITCH]); gy = np.array([(cy - R.Y0) / R.PITCH]); gr = np.array([rad / R.PITCH])
    starts = np.array(list(ta), np.int32)
    L = R.search(c.blk, c.vblk, extra, vextra, starts, goal, list(tb), gx, gy, gr, c.outbuf, c.lc)
    if L <= 0:
        return None
    path = c.outbuf[:L][::-1].tolist()
    tr, vi = R.path_to_copper(path, ta.get(path[0]), tb.get(path[-1]))
    cost = sum(np.hypot(t[3] - t[1], t[4] - t[2]) for t in tr) + len(vi) + float(extra[path].sum()) / 20000.0
    return tr, vi, np.array(path, np.int64), cost


cntT = np.zeros(N, np.uint8)
cntV = np.zeros(R.NLAYER, np.uint8)
histT = np.zeros(N, np.int32)
histV = np.zeros(R.NLAYER, np.int32)
extra = np.empty(N, np.int32)
vextra = np.empty(R.NLAYER, np.int32)
occ, res, paths = {}, {}, {}
assign = {gname: list(range(len(sources[gname]))) for gname in groups}   # source i -> sink assign[i]

def load_assign(st):
    """Adopt a saved pairing; pairs whose pads are no longer group members are skipped and the
    remaining sources take unused sinks, so a changed channel/pin split still loads."""
    key2name = {v: k for k, v in pseudo.items()}
    for gname in groups:
        S, K = sources[gname], sinks[gname]
        new = [None] * len(S)
        used = set()
        for src_key, snk_key in st['assign'].get(gname, []):
            s_n, k_n = key2name.get(tuple(src_key)), key2name.get(tuple(snk_key))
            if s_n in S and k_n in K and K.index(k_n) not in used:
                new[S.index(s_n)] = K.index(k_n)
                used.add(K.index(k_n))
        free = [j for j in range(len(K)) if j not in used]
        assign[gname] = [j if j is not None else free.pop(0) for j in new]

pres = 2000
best = None


def set_costs(skip):
    if skip in occ:
        cntT[occ[skip][0]] -= 1
        cntV[occ[skip][1]] -= 1
    np.multiply(cntT, np.int32(pres), out=extra, casting='unsafe')
    extra[:] += histT
    np.multiply(cntV, np.int32(pres * 4), out=vextra, casting='unsafe')
    vextra[:] += histV


def commit(n, tr, vi, nodes, label):
    res[n] = dict(tracks=tr, vias=vi, pair=label)
    paths[n] = nodes
    occ[n] = R.occupancy(tr, vi)
    cntT[occ[n][0]] += 1
    cntV[occ[n][1]] += 1


def legalize(src_state):
    """Rip-up-and-reroute from a near-solution, keeping the committed set conflict-free."""
    from collections import deque, Counter
    st = json.load(open(src_state))
    load_assign(st)
    owner_of = {}
    for gname in groups:
        for i, s in enumerate(sources[gname]):
            owner_of[s] = (s, sinks[gname][assign[gname][i]])
    live = set(regular) | {x for g_ in groups for x in sources[g_]}
    queue_stale = []
    for n, rr in st['nets'].items():
        if n not in live:
            continue
        tr = [tuple(t) for t in rr['tracks']]
        vi = [tuple(v) for v in rr['vias']]
        res[n] = dict(tracks=tr, vias=vi, pair=rr.get('pair'))
        occ[n] = R.occupancy(tr, vi)
    # conflict graph on the loaded state
    def conflicts_of(n, tr, vi, nodes=None):
        if nodes is None:
            nodes = []
            for ly, x1, y1, x2, y2 in tr:
                k = max(2, int(np.hypot(x2 - x1, y2 - y1) / (R.PITCH / 2)) + 1)
                for q in range(k + 1):
                    x, y = x1 + (x2 - x1) * q / k, y1 + (y2 - y1) * q / k
                    nodes.append(R.LAYERS.index(ly) * R.NLAYER + R.cell(x, y))
            nodes = np.unique(np.array(nodes, np.int64))
        vc = np.array([R.cell(x, y) for x, y in vi], np.int64)
        hit = {}
        for m, o in occ.items():
            if m == n or m not in committed:
                continue
            h = nodes[np.isin(nodes, o[0])]
            vh = vc[np.isin(vc, o[1])] if len(vc) else vc
            if len(h) or len(vh):
                hit[m] = h
        return hit
    committed = set(res)
    # nets of a state made on another geometry may cross copper that is now fixed: reroute them
    stale = spec.get('static_stale', {})
    for n in list(res):
        hT = int(c.sTf[occ[n][0]].sum()); hV = int(c.sVf[occ[n][1]].sum()) if len(occ[n][1]) else 0
        if hT + hV > stale.get(n, 0):
            print(f'legalize: {n} crosses fixed copper ({hT} track / {hV} via cells), rerouting', flush=True)
            committed.discard(n); queue_stale.append(n)
    graph = {n: set(conflicts_of(n, res[n]['tracks'], res[n]['vias'])) for n in res if n in committed}
    for n in graph:
        for m in list(graph[n]):
            graph.setdefault(m, set()).add(n)
    queue = deque()
    # 采用确定性的贪心顶点覆盖，避免大型 CP-SAT 原生库成为后台路由运行时依赖。
    # 每次移除当前度数最高的网络，直到剩余图无边；后续 legalize 会逐项重路由。
    cover = {n: set(edges) for n, edges in graph.items()}
    while True:
        candidates = [(len(edges), n) for n, edges in cover.items() if edges]
        if not candidates:
            break
        _, victim = max(candidates, key=lambda item: (item[0], item[1]))
        committed.discard(victim)
        queue.append(victim)
        for peer in cover.get(victim, set()):
            cover.get(peer, set()).discard(victim)
        cover[victim].clear()
    queue.extend(queue_stale)
    queue.extend(sorted(x for x in live if x not in res and x not in queue))      # never-routed nets of the state too
    for n in list(res):
        if n not in committed:
            res.pop(n); occ.pop(n)
    for n in committed:
        cntT[occ[n][0]] += 1
        cntV[occ[n][1]] += 1
    print(f'legalize: committed {len(committed)} conflict-free, rerouting {len(queue)}: {list(queue)}', flush=True)
    BIG = 2_000_000
    rips = Counter()
    tries = Counter()
    expected = len(regular) + sum(len(s) for s in sources.values())
    best_n = -1
    step = 0
    while queue and step < spec.get('max_steps', 3000):
        n = queue.popleft()
        step += 1
        np.multiply(cntT, np.int32(BIG), out=extra, casting='unsafe')
        np.minimum(extra + histT.astype(np.int64), 2_000_000_000, out=extra, casting='unsafe')
        np.multiply(cntV, np.int32(BIG * 4), out=vextra, casting='unsafe')
        np.minimum(vextra + histV.astype(np.int64), 2_000_000_000, out=vextra, casting='unsafe')
        if n in owner_of:
            r = route_pair(owner_of[n][0], owner_of[n][1], extra, vextra)
            r = None if r is None else r[:3]
        else:
            r = R.route_net(c, n, extra, vextra)
        if r is None:
            print(f'step{step} {n}: no path', flush=True)
            continue
        tr, vi, nodes = r
        hits = conflicts_of(n, tr, vi, nodes)
        if hits and tries[n] < spec.get('patience', 3):
            # do not displace committed nets yet: make the contested cells dearer and retry later
            tries[n] += 1
            for h in hits.values():
                hh = np.zeros(N, bool); hh[h] = True
                histT[:] += binary_dilation(hh.reshape(R.NL, R.NY, R.NX), iterations=3).reshape(-1).astype(np.int32) * (BIG // 16)
            queue.append(n)
            continue
        tries[n] = 0
        for m, h in hits.items():
            cntT[occ[m][0]] -= 1
            cntV[occ[m][1]] -= 1
            committed.discard(m)
            res.pop(m); occ.pop(m)
            queue.append(m)
            rips[m] += 1
            hh = np.zeros(N, bool); hh[h] = True
            histT[:] += binary_dilation(hh.reshape(R.NL, R.NY, R.NX), iterations=3).reshape(-1).astype(np.int32) * (BIG // 8)
        res[n] = dict(tracks=tr, vias=vi, pair=[pseudo[x] for x in owner_of[n]] if n in owner_of else None)
        occ[n] = R.occupancy(tr, vi)
        cntT[occ[n][0]] += 1
        cntV[occ[n][1]] += 1
        committed.add(n)
        if len(committed) > best_n or not queue:
            best_n = max(best_n, len(committed))
            json.dump(dict(nets=res, assign={gname: [[pseudo[sources[gname][i]], pseudo[sinks[gname][assign[gname][i]]]]
                                                     for i in range(len(sources[gname]))] for gname in groups},
                           legal=True, committed=sorted(committed), pending=sorted(set(queue)), step=step,
                           complete=(len(committed) == expected), spec=spec2), open(out, 'w'))
        if step % 10 == 0 or not queue:
            print(f'step{step}: committed {len(committed)}/{expected} queue {len(queue)} best {best_n} '
                  f'top-rips {rips.most_common(4)} {time.time() - t0:.0f}s', flush=True)
    print(f'legalize done: committed {len(committed)}/{expected} pending {sorted(set(queue))}', flush=True)


def polish(src_state):
    """Transactional completion from a legal partial state; never loses a committed net."""
    from collections import deque
    st = json.load(open(src_state))
    load_assign(st)
    owner_of = {s: (s, sinks[gname][assign[gname][i]]) for gname in groups for i, s in enumerate(sources[gname])}
    live = set(regular) | {x for g_ in groups for x in sources[g_]}
    for n in [n for n in st['committed'] if n in live]:
        rr = st['nets'][n]
        tr = [tuple(t) for t in rr['tracks']]; vi = [tuple(v) for v in rr['vias']]
        res[n] = dict(tracks=tr, vias=vi, pair=rr.get('pair'))
        occ[n] = R.occupancy(tr, vi)
        cntT[occ[n][0]] += 1
        cntV[occ[n][1]] += 1
    allnets = regular + [s for g_ in groups for s in sources[g_]]
    pending = [n for n in allnets if n not in res]
    BIG = 2_000_000

    def attempt(n):
        np.multiply(cntT, np.int32(BIG), out=extra, casting='unsafe')
        np.minimum(extra + histT.astype(np.int64), 2_000_000_000, out=extra, casting='unsafe')
        np.multiply(cntV, np.int32(BIG * 4), out=vextra, casting='unsafe')
        np.minimum(vextra + histV.astype(np.int64), 2_000_000_000, out=vextra, casting='unsafe')
        if n in owner_of:
            r = route_pair(owner_of[n][0], owner_of[n][1], extra, vextra)
            r = None if r is None else r[:3]
        else:
            r = R.route_net(c, n, extra, vextra)
        if r is None:
            return None
        tr, vi, nodes = r
        vc = np.array([R.cell(x, y) for x, y in vi], np.int64)
        hits = {}
        for m, o in occ.items():
            h = nodes[np.isin(nodes, o[0])]
            vh = vc[np.isin(vc, o[1])] if len(vc) else vc
            if len(h) or len(vh):
                hits[m] = h
        return tr, vi, hits

    def drop(m):
        cntT[occ[m][0]] -= 1; cntV[occ[m][1]] -= 1
        res.pop(m); occ.pop(m)

    def add(n, tr, vi):
        res[n] = dict(tracks=tr, vias=vi, pair=[pseudo[x] for x in owner_of[n]] if n in owner_of else None)
        occ[n] = R.occupancy(tr, vi)
        cntT[occ[n][0]] += 1; cntV[occ[n][1]] += 1

    def save():
        json.dump(dict(nets=res, assign={gname: [[pseudo[sources[gname][i]], pseudo[sinks[gname][assign[gname][i]]]]
                                                 for i in range(len(sources[gname]))] for gname in groups},
                       legal=True, committed=sorted(res), pending=sorted(n for n in allnets if n not in res),
                       complete=all(n in res for n in allnets), spec=spec2), open(out, 'w'))

    save()
    print(f'polish: {len(res)}/{len(allnets)} legal, pending {pending}', flush=True)
    for rnd, budget in enumerate(spec.get('budgets', [2, 4, 8, 16, 32, 64, 128, 256])):
        for tgt in list(pending):
            snap = {n: (res[n]['tracks'], res[n]['vias']) for n in res}
            queue = deque([tgt]); used = 0; ok = True
            while queue:
                n = queue.popleft(); used += 1
                if used > budget:
                    ok = False; break
                r = attempt(n)
                if r is None:
                    ok = False; break
                tr, vi, hits = r
                if tgt in hits and n != tgt:
                    ok = False; break
                for m, h in hits.items():
                    drop(m); queue.append(m)
                    hh = np.zeros(N, bool); hh[h] = True
                    histT[:] += binary_dilation(hh.reshape(R.NL, R.NY, R.NX), iterations=2).reshape(-1).astype(np.int32) * (BIG // 32)
                add(n, tr, vi)
            if ok:
                pending.remove(tgt)
                save()
            else:
                for n in list(res):
                    drop(n)
                for n, (tr, vi) in snap.items():
                    add(n, tr, vi)
            print(f'round{rnd} budget{budget} {tgt}: {"OK" if ok else "rollback"} used {used} '
                  f'[{len(res)}/{len(allnets)} legal] {time.time() - t0:.0f}s', flush=True)
        if not pending:
            print('POLISH COMPLETE', flush=True)
            break
    print(f'polish done: pending {pending}', flush=True)


def diagnose(src_state):
    st = json.load(open(src_state))
    load_assign(st)
    owner_of = {s: (s, sinks[gname][assign[gname][i]]) for gname in groups for i, s in enumerate(sources[gname])}
    live = set(regular) | {x for g_ in groups for x in sources[g_]}
    for n in [n for n in st['committed'] if n in live]:
        rr = st['nets'][n]
        occ[n] = R.occupancy([tuple(t) for t in rr['tracks']], [tuple(v) for v in rr['vias']])
        cntT[occ[n][0]] += 1; cntV[occ[n][1]] += 1
    for n in sorted(x for x in live if x not in st['committed']):
        np.multiply(cntT, np.int32(50_000_000), out=extra, casting='unsafe')
        np.multiply(cntV, np.int32(50_000_000), out=vextra, casting='unsafe')
        if n in owner_of:
            r = route_pair(owner_of[n][0], owner_of[n][1], extra, vextra); r = None if r is None else r[:3]
            ends = [pseudo[x] for x in owner_of[n]]
        else:
            r = R.route_net(c, n, extra, vextra); ends = n
        if r is None:
            print(n, 'NO PATH at all'); continue
        tr, vi, nodes = r
        vc = np.array([R.cell(x, y) for x, y in vi], np.int64)
        for m, o in occ.items():
            h = nodes[np.isin(nodes, o[0])]
            vh = vc[np.isin(vc, o[1])] if len(vc) else vc
            if len(h) or len(vh):
                pts = [R.node_xyl(int(q)) for q in (h if len(h) else vh)]
                print(f'{n} {ends}: hits {m} x{len(h)}+{len(vh)} at ({np.mean([p[1] for p in pts]):.2f},{np.mean([p[2] for p in pts]):.2f}) {R.LAYERS[pts[0][0]]}')


def finalize(src_state, out_geom):
    """Write the final geometry with real net names: kept copper + routed copper, pads renamed."""
    with open(src_state) as state_file:
        st = json.load(state_file)
    real = {}
    for gname in groups:
        for src_key, snk_key in st['assign'][gname]:
            src_key, snk_key = tuple(src_key), tuple(snk_key)
            if gname in 'ABC':
                net = orig_net[f'{gname}K:{snk_key[0]}.{snk_key[1]}']
            else:
                # 沿用已交换通道的实际公共端网络，避免与固定 UART 通道重名。
                net = orig_net[f'{gname}S:{src_key[0]}.{src_key[1]}']
            real[f'{gname}S:{src_key[0]}.{src_key[1]}'] = net
            real[f'{gname}K:{snk_key[0]}.{snk_key[1]}'] = net
    gf = json.loads(json.dumps(g))
    for p in gf['pads']:
        if p['net'] in real:
            p['net'] = real[p['net']]
    removed_all = set().union(*c.removed.values())
    for coll in ('tracks', 'vias'):
        keepers = []
        for t in gf[coll]:
            if t['uuid'] in removed_all:
                continue
            if t['net'] in real:
                t['net'] = real[t['net']]
            keepers.append(t)
        gf[coll] = keepers
    k = 0
    live = set(regular) | {x for g_ in groups for x in sources[g_]}
    for n in [n for n in st['committed'] if n in live]:
        rr = st['nets'][n]
        net = real.get(n, n)
        for ly, x1, y1, x2, y2 in rr['tracks']:
            gf['tracks'].append(dict(x1=x1, y1=y1, x2=x2, y2=y2, w=R.W, layer=ly, net=net, uuid=f'route-{k}')); k += 1
        for x, y in rr['vias']:
            gf['vias'].append(dict(x=x, y=y, d=R.VIA_D, drill=R.VIA_DR, net=net, uuid=f'route-{k}')); k += 1
    with open(out_geom, 'w') as geometry_file:
        json.dump(gf, geometry_file)
    pend = [real.get(n, n) for n in st.get('pending', [])]
    print(f'finalized {len(st["committed"])} routed nets, {k} new copper items; pending {pend}', flush=True)
    with open(out_geom.replace('.json', '-pins.json'), 'w') as pins_file:
        json.dump(dict(pin_nets={f'{p["ref"]}.{p["num"]}': p['net'] for p in gf['pads'] if p['ref'] in ('U501', 'U710', 'U711')},
                       pending=pend, pseudo_to_real=real), pins_file, indent=1)


def region(src_state):
    """For each pending net: rip the committed nets near its best path and negotiate that subset locally."""
    from shapely.geometry import LineString as LS
    st = json.load(open(src_state))
    load_assign(st)
    owner_of = {s: (s, sinks[gname][assign[gname][i]]) for gname in groups for i, s in enumerate(sources[gname])}
    allnets = regular + [s for g_ in groups for s in sources[g_]]
    live = set(regular) | {x for g_ in groups for x in sources[g_]}
    committed = {n: (st['nets'][n]['tracks'], st['nets'][n]['vias']) for n in st['committed'] if n in live}
    base_sT, base_sV = c.sTf.copy(), c.sVf.copy()

    def route_any(n, ex, vx):
        if n in owner_of:
            r = route_pair(owner_of[n][0], owner_of[n][1], ex, vx)
            return None if r is None else r[:3]
        return R.route_net(c, n, ex, vx)

    def save():
        json.dump(dict(nets={n: dict(tracks=[list(t) for t in tr], vias=[list(v) for v in vi],
                                     pair=[pseudo[x] for x in owner_of[n]] if n in owner_of else None)
                             for n, (tr, vi) in committed.items()},
                       assign={gname: [[pseudo[sources[gname][i]], pseudo[sinks[gname][assign[gname][i]]]]
                                       for i in range(len(sources[gname]))] for gname in groups},
                       legal=True, committed=sorted(committed), pending=sorted(n for n in allnets if n not in committed),
                       complete=all(n in committed for n in allnets), spec=spec2), open(out, 'w'))

    for attempt in range(spec.get('region_attempts', 3)):
        pending = [n for n in allnets if n not in committed]
        if not pending:
            break
        for p in pending:
            # best path of p against all committed copper
            cT = np.zeros(N, np.uint8); cV = np.zeros(R.NLAYER, np.uint8)
            occs = {n: R.occupancy(tr, vi) for n, (tr, vi) in committed.items()}
            for o in occs.values():
                cT[o[0]] += 1; cV[o[1]] += 1
            ex = (cT.astype(np.int32) * 50_000_000); vx = (cV.astype(np.int32) * 50_000_000)
            r = route_any(p, ex, vx)
            if r is None:
                print(f'region {p}: no path', flush=True); continue
            tr, vi, nodes = r
            pts = [(t[1], t[2]) for t in tr] + [(tr[-1][3], tr[-1][4])] if tr else [(v[0], v[1]) for v in vi]
            band = LS(pts).buffer(spec.get('region_radius', 1.5)) if len(pts) > 1 else None
            subset = [p]
            for n, (ntr, nvi) in committed.items():
                if band is not None and any(LS([(t[1], t[2]), (t[3], t[4])]).intersects(band) for t in ntr if (t[1], t[2]) != (t[3], t[4])):
                    subset.append(n)
            # everything outside the subset becomes a hard obstacle
            c.sTf[:] = base_sT; c.sVf[:] = base_sV
            for n, o in occs.items():
                if n not in subset:
                    c.sTf[o[0]] = True; c.sVf[o[1]] = True
            lres, locc = {}, {}
            lT = np.zeros(N, np.uint8); lV = np.zeros(R.NLAYER, np.uint8)
            hT = np.zeros(N, np.int32); hV = np.zeros(R.NLAYER, np.int32)
            pr = 2000
            ok = False
            for it in range(spec.get('region_iterations', 40)):
                for n in subset:
                    if n in locc:
                        lT[locc[n][0]] -= 1; lV[locc[n][1]] -= 1
                    exl = (lT.astype(np.int32) * pr + hT); vxl = (lV.astype(np.int32) * pr * 4 + hV)
                    rr = route_any(n, exl, vxl)
                    if rr is None:
                        lres.pop(n, None); locc.pop(n, None); continue
                    lres[n] = rr; locc[n] = R.occupancy(rr[0], rr[1])
                    lT[locc[n][0]] += 1; lV[locc[n][1]] += 1
                bad = 0; oT = np.zeros(N, bool)
                for n, (ntr, nvi, nn) in lres.items():
                    mine = np.isin(nn, locc[n][0])
                    b = nn[lT[nn].astype(np.int32) - mine > 0]
                    vc = np.array([R.cell(x, y) for x, y in nvi], np.int64)
                    vb = vc[lV[vc].astype(np.int32) - np.isin(vc, locc[n][1]) > 0] if len(vc) else vc
                    if len(b) or len(vb):
                        bad += 1; oT[b] = True
                if bad == 0 and len(lres) == len(subset):
                    ok = True
                    break
                hT += binary_dilation(oT.reshape(R.NL, R.NY, R.NX), iterations=4).reshape(-1).astype(np.int32) * spec.get('hist', 6000)
                pr = min(int(pr * 1.5), 2_000_000)
            c.sTf[:] = base_sT; c.sVf[:] = base_sV
            if ok:
                for n in subset:
                    committed[n] = (lres[n][0], lres[n][1])
                save()
            print(f'attempt{attempt} region {p}: subset {len(subset)} {"OK" if ok else "no"} after {it + 1} its '
                  f'[{len(committed)}/{len(allnets)} legal] {time.time() - t0:.0f}s', flush=True)
    save()
    print(f'region done: {len(committed)}/{len(allnets)}; pending {[n for n in allnets if n not in committed]}', flush=True)


SURG_BEST = 0


def surgery(src_state, order, keepouts):
    """Rip `order` nets from a legal state and reroute them in that order against everything else as walls;
    keepouts: {net: [[x0,y0,x1,y1,layer|None], ...]} forbids those boxes for that net. Commit only if all clean."""
    from shapely.geometry import box as sbox
    st = json.load(open(src_state))
    load_assign(st)
    owner_of = {s: (s, sinks[gname][assign[gname][i]]) for gname in groups for i, s in enumerate(sources[gname])}
    live = set(regular) | {x for g_ in groups for x in sources[g_]}
    committed = {n: (st['nets'][n]['tracks'], st['nets'][n]['vias']) for n in st['committed'] if n in live and n not in order}
    occs = {n: R.occupancy(tr, vi) for n, (tr, vi) in committed.items()}
    cT = np.zeros(N, np.uint8); cV = np.zeros(R.NLAYER, np.uint8)
    for o in occs.values():
        cT[o[0]] += 1; cV[o[1]] += 1
    base = c.sTf.copy()
    done = {}
    for n in order:
        c.sTf[:] = base
        for kb in keepouts.get(n, []):
            cv = [R.Canvas() for _ in R.LAYERS]
            for li, ly in enumerate(R.LAYERS):
                if kb[4] in (None, ly):
                    cv[li].geom(sbox(*kb[:4]))
            c.sTf[:] |= np.stack([x.arr() for x in cv]).reshape(-1)
        ex = (cT.astype(np.int32) * 50_000_000); vx = (cV.astype(np.int32) * 50_000_000)
        if n in owner_of:
            r = route_pair(owner_of[n][0], owner_of[n][1], ex, vx); r = None if r is None else r[:3]
        else:
            r = R.route_net(c, n, ex, vx)
        c.sTf[:] = base
        if r is None:
            print(f'surgery {n}: no path', flush=True)
            if not spec.get('best_effort'):
                return False
            continue
        tr, vi, nodes = r
        vc = np.array([R.cell(x, y) for x, y in vi], np.int64)
        hit = int((cT[nodes] > 0).sum()) + (int((cV[vc] > 0).sum()) if len(vc) else 0)
        print(f'surgery {n}: {"clean" if hit == 0 else f"{hit} conflict cells"}', flush=True)
        if hit:
            new_occ = R.occupancy(tr, vi)
            conflict_nets = [m for m, o in occs.items()
                             if np.intersect1d(new_occ[0], o[0]).size
                             or np.intersect1d(new_occ[1], o[1]).size]
            print(f'surgery {n}: conflict nets {sorted(conflict_nets)}', flush=True)
        if hit:
            if not spec.get('best_effort'):
                return False
            continue                      # best effort: leave this net pending

        done[n] = (tr, vi)
        o = R.occupancy(tr, vi); occs[n] = o
        cT[o[0]] += 1; cV[o[1]] += 1
    committed.update(done)
    global SURG_BEST
    if spec.get('best_effort') and len(committed) <= SURG_BEST:
        print(f'surgery: {len(committed)}/{len(live)} (not better than {SURG_BEST})', flush=True)
        return False
    SURG_BEST = len(committed)
    json.dump(dict(nets={n: dict(tracks=[list(t) for t in tr], vias=[list(v) for v in vi],
                                 pair=[pseudo[x] for x in owner_of[n]] if n in owner_of else None)
                         for n, (tr, vi) in committed.items()},
                   assign={gname: [[pseudo[sources[gname][i]], pseudo[sinks[gname][assign[gname][i]]]]
                                   for i in range(len(sources[gname]))] for gname in groups},
                   legal=True, committed=sorted(committed),
                   pending=sorted(x for x in live if x not in committed),
                   complete=all(x in committed for x in live), spec=spec2), open(out, 'w'))
    print(f'surgery OK: {len(committed)}/{len(live)} legal', flush=True)
    return True


if spec.get('surgery_from'):
    import random
    rng = random.Random(spec.get('seed', 1))
    first, rest = spec.get('surgery_first', []), list(spec['surgery_order'])
    for trial in range(spec.get('surgery_trials', 1)):
        order = first + (rest if trial == 0 else rng.sample(rest, len(rest)))
        print(f'trial {trial}: {order}', flush=True)
        if surgery(spec['surgery_from'], order, spec.get('surgery_keepouts', {})) and not spec.get('best_effort'):
            break
        if spec.get('best_effort') and SURG_BEST >= len(regular) + sum(len(v) for v in sources.values()):
            break
    sys.exit(0)

if spec.get('region_from'):
    region(spec['region_from'])
    sys.exit(0)

if spec.get('finalize_from'):
    finalize(spec['finalize_from'], spec['finalize_to'])
    sys.exit(0)

if spec.get('diagnose_from'):
    diagnose(spec['diagnose_from'])
    sys.exit(0)

if spec.get('polish_from'):
    polish(spec['polish_from'])
    sys.exit(0)

if spec.get('legalize_from'):
    legalize(spec['legalize_from'])
    sys.exit(0)

if spec.get('warm_from'):
    ws = json.load(open(spec['warm_from']))
    load_assign(ws)
    live = set(regular) | {x for g_ in groups for x in sources[g_]}
    for n in [n for n in ws.get('committed', ws['nets']) if n in live]:
        rr = ws['nets'][n]
        tr = [tuple(t) for t in rr['tracks']]; vi = [tuple(v) for v in rr['vias']]
        res[n] = dict(tracks=tr, vias=vi, pair=rr.get('pair'))
        occ[n] = R.occupancy(tr, vi)
        cntT[occ[n][0]] += 1; cntV[occ[n][1]] += 1
        pts = []
        for ly, x1, y1, x2, y2 in tr:
            k = max(2, int(np.hypot(x2 - x1, y2 - y1) / (R.PITCH / 2)) + 1)
            pts += [R.LAYERS.index(ly) * R.NLAYER + R.cell(x1 + (x2 - x1) * q / k, y1 + (y2 - y1) * q / k) for q in range(k + 1)]
        paths[n] = np.unique(np.array(pts, np.int64))
    pres = spec.get('warm_pres', 200_000)
    print(f'warm start: {len(res)} nets from {spec["warm_from"]}', flush=True)

for it in range(spec.get('iterations', 150)):
    if (not spec.get('warm_from') or spec.get('warm_reassign')) and it % spec.get('reassign_every', 4) == 0 and (it > 0 or not spec.get('warm_from')):
        allowed_reassign = set(spec.get('reassign_groups', groups))
        for gname in groups:
            if gname not in allowed_reassign:
                continue
            S, K = sources[gname], sinks[gname]
            M = np.full((len(S), len(K)), 1e9)
            for i, s in enumerate(S):
                set_costs(s)
                for j, k in enumerate(K):
                    r = route_pair(s, k, extra, vextra)
                    if r is not None:
                        M[i, j] = r[3]
                if s in occ:
                    cntT[occ[s][0]] += 1
                    cntV[occ[s][1]] += 1
            rows, cols = linear_sum_assignment(M)
            new = [0] * len(S)
            for i, j in zip(rows, cols):
                new[i] = j
            if new != assign[gname]:
                print(f'it{it} group {gname} reassigned cost {M[rows, cols].sum():.0f}', flush=True)
            assign[gname] = new
    for n in regular:
        set_costs(n)
        r = R.route_net(c, n, extra, vextra)
        if r is None:
            print(f'it{it} {n}: FAILED', flush=True)
            occ.pop(n, None); res.pop(n, None); paths.pop(n, None)
            continue
        commit(n, *r, None)
    for gname in groups:
        for i, s in enumerate(sources[gname]):
            k = sinks[gname][assign[gname][i]]
            set_costs(s)
            r = route_pair(s, k, extra, vextra)
            if r is None:
                print(f'it{it} {s}->{k}: FAILED', flush=True)
                occ.pop(s, None); res.pop(s, None); paths.pop(s, None)
                continue
            commit(s, r[0], r[1], r[2], [pseudo[s], pseudo[k]])
    overT = np.zeros(N, bool)
    overV = np.zeros(R.NLAYER, bool)
    bad = []
    for n, rr in res.items():
        pn = paths[n]
        mine = np.isin(pn, occ[n][0])
        b = pn[cntT[pn].astype(np.int32) - mine > 0]
        vc = np.array([R.cell(x, y) for x, y in rr['vias']], np.int64)
        vb = vc[cntV[vc].astype(np.int32) - np.isin(vc, occ[n][1]) > 0] if len(vc) else vc
        if len(b) or len(vb):
            bad.append(n)
            overT[b] = True
            overV[vb] = True
    expected = len(regular) + sum(len(s) for s in sources.values())
    lens = sum(np.hypot(t[3] - t[1], t[4] - t[2]) for rr in res.values() for t in rr['tracks'])
    print(f'it{it}: routed {len(res)}/{expected} conflicted {len(bad)} over {int(overT.sum())}/{int(overV.sum())} '
          f'len {lens:.0f}mm {time.time() - t0:.0f}s bad={bad[:8]}', flush=True)
    state = dict(nets=res, assign={gname: [[pseudo[sources[gname][i]], pseudo[sinks[gname][assign[gname][i]]]]
                                          for i in range(len(sources[gname]))] for gname in groups},
                 iteration=it, conflicted=bad, complete=(not bad and len(res) == expected), spec=spec2)
    json.dump(state, open(out + '.last', 'w'))
    score = (expected - len(res)) * 1000 + int(overT.sum())
    if best is None or score <= best:
        best = score
        json.dump(state, open(out, 'w'))
    if not bad and len(res) == expected:
        print('CONVERGED', flush=True)
        break
    histT += binary_dilation(overT.reshape(R.NL, R.NY, R.NX), iterations=HIST_DIL).reshape(-1).astype(np.int32) * HIST_T
    histV += binary_dilation(overV.reshape(R.NY, R.NX), iterations=HIST_DIL).reshape(-1).astype(np.int32) * HIST_T * 2
    pres = min(int(pres * 1.5), 2_000_000)
