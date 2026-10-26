"""Search a GPIO-matrix / mux-channel pin assignment that minimises routed length and path crossings.

Free choices (all firmware-remappable through the ESP32-S3 GPIO matrix):
  * which SD/UART signal and which display data bit share each of the 8 SGM330A channels;
  * which of GPIO5..10 drives each SD channel common (UART TX/RX commons stay on GPIO43/44);
  * which 8 data bits are direct, and which direct GPIO (3,14,17,18,21,38,39,40) drives each.
Fixed: strapping roles, USB, I2C, I2S, controls, panel bit -> R7xx -> FFC.
usage: pinswap_opt.py geom.json spec.json design.json out.json
"""
import json, sys, time, random, math, itertools
import numpy as np
from shapely.geometry import LineString
from shapely.strtree import STRtree
sys.path.insert(0, sys.path[0])
import router2 as R

g = json.load(open(sys.argv[1]))
spec = json.load(open(sys.argv[2]))
design = json.load(open(sys.argv[3]))
out = sys.argv[4]
t0 = time.time()
pad = {(p['ref'], p['num']): p for p in g['pads']}
gpio_pin = {int(k): v['package_pin'] for k, v in design['gpio'].items()}
MUX_TRIPLES = design['mux']['source_terminal_pins']          # per channel: S0, S1, common
CHANNELS = [(ref, tri) for ref in ('U710', 'U711') for tri in MUX_TRIPLES]
SD_SIGNALS = {'SDMMC_D0': ('R519', '1'), 'SDMMC_D1': ('R520', '1'), 'SDMMC_D2': ('R521', '1'),
              'SDMMC_D3': ('R522', '1'), 'SDMMC_CLK': ('R517', '1'), 'SDMMC_CMD': ('R518', '1'),
              'UART0_TX': ('J503', '5'), 'UART0_RX': ('J503', '3')}
UART_GPIO = {'UART0_TX': 43, 'UART0_RX': 44}
SD_GPIOS = [5, 6, 7, 8, 9, 10]
# GPIO3 (strapping) keeps data bit 8 together with its R512 network; it is outside the swap pool
DIRECT_GPIOS = [14, 17, 18, 21, 38, 39, 40]
BITS = [b for b in range(16) if b != 8]
bit_pad = {k: ('R' + str(710 + k), '1') for k in BITS}

# ---- candidate single-net paths -------------------------------------------------------------
c = R.prepare(g, spec)
N = R.NL * R.NLAYER
zero = np.zeros(N, np.int32)
zv = np.zeros(R.NLAYER, np.int32)
pad_cache = {}


def pad_raster(key):
    if key not in pad_cache:
        p = pad[key]
        sh = {ly: R.Polygon(q[0]) for ly, q in p['polys'].items()}
        it = R.Item('pad', p, sh)
        T, V = R.raster_items([it], R.CLR + R.W / 2 + R.M, R.CLR + R.VIA_D / 2 + R.M)
        own = R.Canvas()
        for ly, s in sh.items():
            if ly in R.LAYERS:
                own.geom(s.buffer(R.VIA_D / 2 + 0.05, 12))
        pad_cache[key] = (np.flatnonzero(np.stack([cv.arr() for cv in T])), np.flatnonzero(V.arr()),
                          np.flatnonzero(own.arr()), R.terminal_nodes([it]))
    return pad_cache[key]


def route_pads(ka, kb):
    ta, va, oa, terma = pad_raster(ka)
    tb, vb, ob, termb = pad_raster(kb)
    fixT, fixV = c.fixT.astype(np.int16), c.fixV.astype(np.int16)
    fixT[ta] -= 1; fixT[tb] -= 1; fixV[va] -= 1; fixV[vb] -= 1
    blk = (c.sTf | (fixT > 0)).astype(np.uint8)
    vblk = (c.sVf | (fixV > 0)).astype(np.uint8)
    vblk[oa] = 1; vblk[ob] = 1
    goal = np.zeros(N, np.uint8)
    goal[list(termb)] = 1
    starts = np.array(list(terma), np.int32)
    pb = pad[kb]
    gx = np.array([(pb['x'] - R.X0) / R.PITCH]); gy = np.array([(pb['y'] - R.Y0) / R.PITCH]); gr = np.array([0.5 / R.PITCH])
    L = R.LIB.astar(R.NX, R.NY, R.NL, blk.ctypes.data_as(R.P8), vblk.ctypes.data_as(R.P8), zero.ctypes.data_as(R.P32),
                    zv.ctypes.data_as(R.P32), c.lc.ctypes.data_as(R.P32), R.VIA_COST, starts.ctypes.data_as(R.P32),
                    len(starts), goal.ctypes.data_as(R.P8), gx.ctypes.data_as(R.PD), gy.ctypes.data_as(R.PD),
                    gr.ctypes.data_as(R.PD), 1, c.outbuf.ctypes.data_as(R.P32), len(c.outbuf), 60_000_000, R.BEND_COST)
    if L <= 0:
        return None
    path = c.outbuf[:L][::-1].tolist()
    tr, vi = R.path_to_copper(path, pa_xy(ka), pa_xy(kb))
    pts = [(R.node_xyl(n)[1], R.node_xyl(n)[2]) for n in path]
    length = sum(math.hypot(t[3] - t[1], t[4] - t[2]) for t in tr) + len(vi) * 1.0
    return dict(len=length, vias=len(vi), line=pts[::4] + [pts[-1]])


def pa_xy(k):
    return (pad[k]['x'], pad[k]['y'])


cands = {}
def cand(ka, kb):
    key = (ka, kb)
    if key not in cands:
        cands[key] = route_pads(ka, kb)
    return cands[key]


u501 = lambda gp: ('U501', str(gpio_pin[gp]))
for ci, (ref, (s0, s1, cm)) in enumerate(CHANNELS):
    for gp in SD_GPIOS + list(UART_GPIO.values()):
        cand(u501(gp), (ref, str(cm)))
    for sig, k in SD_SIGNALS.items():
        cand((ref, str(s0)), k)
    for b in BITS:
        cand((ref, str(s1)), bit_pad[b])
for gp in DIRECT_GPIOS:
    for b in BITS:
        cand(u501(gp), bit_pad[b])
bad = [k for k, v in cands.items() if v is None]
print(f'{len(cands)} candidate paths in {time.time() - t0:.0f}s; unroutable {len(bad)}', flush=True)
keys = [k for k, v in cands.items() if v is not None]
idx = {k: i for i, k in enumerate(keys)}
lines = [LineString(cands[k]['line']).simplify(0.6) for k in keys]
tree = STRtree(lines)
X = {}
for i, ln in enumerate(lines):
    for j in tree.query(ln):
        if j <= i:
            continue
        a, b = keys[i], keys[j]
        if set(a) & set(b):
            continue
        inter = ln.intersection(lines[j])
        # count transversal crossings only; shared corridors (overlaps) are not crossings
        n = sum(1 for gm in getattr(inter, 'geoms', [inter]) if gm.geom_type == 'Point') if not inter.is_empty else 0
        if n:
            X[(i, j)] = n
print(f'crossing table {len(X)} pairs {time.time() - t0:.0f}s', flush=True)

# ---- assignment search ------------------------------------------------------------------------
LAMBDA = 6.0          # mm-equivalent penalty per crossing
FAIL = 1000.0


def conns(a):
    """a = (sd_of_ch[8], bit_of_ch[8], gpio_of_ch[8], direct_bit_of_gpio{gp: bit})"""
    sd, bit, gp, direct = a
    res = []
    for ci, (ref, (s0, s1, cm)) in enumerate(CHANNELS):
        res.append((u501(gp[ci]), (ref, str(cm))))
        res.append(((ref, str(s0)), SD_SIGNALS[sd[ci]]))
        res.append(((ref, str(s1)), bit_pad[bit[ci]]))
    for g_, b in direct.items():
        res.append((u501(g_), bit_pad[b]))
    return res


def cost(a):
    cs = conns(a)
    total = 0.0
    ids = []
    for k in cs:
        if k not in idx:
            total += FAIL
            continue
        total += cands[k]['len']
        ids.append(idx[k])
    ids.sort()
    cross = 0
    for x, y in itertools.combinations(ids, 2):
        cross += X.get((x, y), 0)
    return total + LAMBDA * cross, cross


def gpio_for(sd):
    free = iter(SD_GPIOS)
    return [UART_GPIO[s] if s in UART_GPIO else None for s in sd]


def normalise(sd, gp):
    """UART channels must use GPIO43/44; SD channels use GPIO5..10 in the given order list."""
    order = [x for x in gp if x in SD_GPIOS]
    it = iter(order)
    return [UART_GPIO[s] if s in UART_GPIO else next(it) for s in sd]


# current contract as the starting point
cur_sd, cur_bit, cur_gp = [], [], []
for ch in design['mux']['channels']:
    cur_sd.append(ch['select_0_net'])
    cur_bit.append(int(ch['select_1_net'][5:].split('_')[0]))
    cur_gp.append(ch['gpio'])
cur_direct = {}
for gp_, item in design['gpio'].items():
    n = item['net']
    if n.startswith('P47_D') and n.endswith('_SRC') and int(gp_) in DIRECT_GPIOS:
        cur_direct[int(gp_)] = int(n[5:].split('_')[0])
start = (cur_sd, cur_bit, cur_gp, cur_direct)
best = start
bcost = cost(start)
print('contract assignment cost', bcost, flush=True)
random.seed(1)
a = (list(cur_sd), list(cur_bit), list(cur_gp), dict(cur_direct))
acost = bcost[0]
T = 40.0
for step in range(200000):
    sd, bit, gp, direct = list(a[0]), list(a[1]), list(a[2]), dict(a[3])
    m = random.random()
    if m < 0.25:
        i, j = random.sample(range(8), 2); sd[i], sd[j] = sd[j], sd[i]
    elif m < 0.5:
        i, j = random.sample(range(8), 2); bit[i], bit[j] = bit[j], bit[i]
    elif m < 0.65:
        sdch = [i for i in range(8) if sd[i] not in UART_GPIO]
        i, j = random.sample(sdch, 2); gp[i], gp[j] = gp[j], gp[i]
    elif m < 0.85:
        g1, g2 = random.sample(DIRECT_GPIOS, 2); direct[g1], direct[g2] = direct[g2], direct[g1]
    else:  # exchange a muxed bit with a direct bit
        i = random.randrange(8); g1 = random.choice(DIRECT_GPIOS)
        bit[i], direct[g1] = direct[g1], bit[i]
    gp = normalise(sd, gp)
    nb = (sd, bit, gp, direct)
    nc = cost(nb)[0]
    if nc < acost or random.random() < math.exp((acost - nc) / T):
        a, acost = nb, nc
        if nc < bcost[0]:
            best, bcost = nb, cost(nb)
    T = max(0.2, T * 0.99996)
    if step % 20000 == 0:
        print(f'step {step} T {T:.2f} current {acost:.1f} best {bcost}', flush=True)
print('best', bcost, flush=True)
sd, bit, gp, direct = best
json.dump(dict(cost=bcost, contract_cost=cost(start),
               channels=[dict(part=CHANNELS[i][0], terminals=CHANNELS[i][1], select_0_net=sd[i],
                              display_bit=bit[i], gpio=gp[i]) for i in range(8)],
               direct={str(k): v for k, v in direct.items()}), open(out, 'w'), indent=1)
