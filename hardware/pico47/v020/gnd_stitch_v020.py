"""Give every top-side GND pad its own short stub and through via to the In1 ground plane (KiCad Python).

usage: gnd_stitch_v020.py in.kicad_pcb out.kicad_pcb report.json [REF.PIN,... only these pads]
Exposed pads get a small grid of vias inside the pad (these need resin fill + cap, listed in the report).
All added items are locked so the autorouter keeps them.
"""
import json
import math
import sys

import pcbnew as P

MM, TO = P.FromMM, P.ToMM
VIA_D, VIA_DRILL, STUB_W = 0.55, 0.3, 0.25
CLR = 0.127                    # via/track copper to other-net copper (board rule)
VIA_PITCH = 0.70               # via centre to via centre
EDGE = 0.48                    # via centre to board edge (0.25 copper-edge + radius)
EP_VIAS = {'U501.57': (3, 3), 'U901.25': (2, 2), 'U904.9': (1, 2), 'U601.25': (1, 1), 'U903.13': (1, 1)}

board = P.LoadBoard(sys.argv[1])
ONLY = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else None
gnd = board.FindNet('GND')

SEGS = []
for d in board.GetDrawings():
    if d.GetLayer() == P.Edge_Cuts:
        s, e = d.GetStart(), d.GetEnd()
        SEGS.append(((TO(s.x), TO(s.y)), (TO(e.x), TO(e.y))))


def _sd(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy or 1)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def in_board(x, y, margin):
    c = False
    for (x1, y1), (x2, y2) in SEGS:
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c and all(_sd((x, y), a, b) >= margin for a, b in SEGS)


obst = []                      # (x0, y0, x1, y1) other-net copper on any layer the via touches
for fp in board.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetname() == 'GND' or pad.GetNumber() == '' or not pad.IsOnCopperLayer():
            continue
        bb = pad.GetBoundingBox()
        obst.append((TO(bb.GetX()), TO(bb.GetY()), TO(bb.GetRight()), TO(bb.GetBottom())))
vias = []                      # existing via centres (x, y)
for t in board.GetTracks():
    if t.GetNetname() == 'GND':
        if t.GetClass() == 'PCB_VIA':
            vias.append((TO(t.GetPosition().x), TO(t.GetPosition().y)))
        continue
    if t.GetClass() == 'PCB_VIA':
        p, r = t.GetPosition(), TO(t.GetWidth(P.F_Cu)) / 2
        obst.append((TO(p.x) - r, TO(p.y) - r, TO(p.x) + r, TO(p.y) + r))
    else:
        a, b, hw = t.GetStart(), t.GetEnd(), TO(t.GetWidth()) / 2
        n = max(1, int(TO((b - a).EuclideanNorm()) / 0.1))
        for i in range(n + 1):
            x = TO(a.x) + (TO(b.x) - TO(a.x)) * i / n
            y = TO(a.y) + (TO(b.y) - TO(a.y)) * i / n
            obst.append((x - hw, y - hw, x + hw, y + hw))


def rect_dist(x, y, r):
    dx = max(r[0] - x, 0, x - r[2])
    dy = max(r[1] - y, 0, y - r[3])
    return math.hypot(dx, dy)


def seg_ok(a, b, half):
    n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05))
    for i in range(n + 1):
        x = a[0] + (b[0] - a[0]) * i / n
        y = a[1] + (b[1] - a[1]) * i / n
        if any(rect_dist(x, y, r) < half + CLR for r in obst):
            return False
    return True


def via_ok(x, y):
    if not in_board(x, y, EDGE):
        return False
    if any(rect_dist(x, y, r) < VIA_D / 2 + CLR for r in obst):
        return False
    return all(math.hypot(x - vx, y - vy) >= VIA_PITCH for vx, vy in vias)


def add_via(x, y):
    v = P.PCB_VIA(board)
    v.SetPosition(P.VECTOR2I(MM(x), MM(y)))
    v.SetWidth(MM(VIA_D))
    v.SetDrill(MM(VIA_DRILL))
    v.SetNet(gnd)
    v.SetLocked(True)
    board.Add(v)
    vias.append((x, y))


def add_track(a, b, w=STUB_W):
    t = P.PCB_TRACK(board)
    t.SetStart(P.VECTOR2I(MM(a[0]), MM(a[1])))
    t.SetEnd(P.VECTOR2I(MM(b[0]), MM(b[1])))
    t.SetWidth(MM(w))
    t.SetLayer(P.F_Cu)
    t.SetNet(gnd)
    t.SetLocked(True)
    board.Add(t)


report = dict(stitched=[], via_in_pad=[], failed=[], reused=[])
pads = []
for fp in board.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetname() == 'GND' and pad.IsOnLayer(P.F_Cu):
            if ONLY and f'{fp.GetReference()}.{pad.GetNumber()}' not in ONLY:
                continue
            pads.append((fp, pad))

# exposed pads first: vias inside the pad
for fp, pad in pads:
    key = f'{fp.GetReference()}.{pad.GetNumber()}'
    if key not in EP_VIAS:
        continue
    bb = pad.GetBoundingBox()
    cx, cy = TO(bb.GetCenter().x), TO(bb.GetCenter().y)
    nx, ny = EP_VIAS[key]
    sx = min(1.0, (TO(bb.GetWidth()) - VIA_D) / max(nx - 1, 1))
    sy = min(1.0, (TO(bb.GetHeight()) - VIA_D) / max(ny - 1, 1))
    for i in range(nx):
        for j in range(ny):
            x = cx + (i - (nx - 1) / 2) * sx
            y = cy + (j - (ny - 1) / 2) * sy
            if any(rect_dist(x, y, r) < VIA_D / 2 + CLR for r in obst):
                report.setdefault('ep_skipped', []).append([key, round(x, 3), round(y, 3)])
                continue
            add_via(x, y)
            report['via_in_pad'].append([key, round(x, 3), round(y, 3)])

for fp, pad in pads:
    key = f'{fp.GetReference()}.{pad.GetNumber()}'
    if key in EP_VIAS:
        continue
    bb = pad.GetBoundingBox()
    cx, cy = TO(bb.GetCenter().x), TO(bb.GetCenter().y)
    hx, hy = TO(bb.GetWidth()) / 2, TO(bb.GetHeight()) / 2
    fc = fp.GetPosition()
    away = math.atan2(cy - TO(fc.y), cx - TO(fc.x)) if (abs(cx - TO(fc.x)) + abs(cy - TO(fc.y))) > 0.05 else 0.0
    # fine-pitch pins: leave straight out along the pad's long axis with a narrower stub
    sw = 0.15 if min(hx, hy) * 2 < 0.3 else STUB_W
    if hx != hy:
        if hy > hx:
            away = math.pi / 2 if cy > TO(fc.y) else -math.pi / 2
        else:
            away = 0.0 if cx > TO(fc.x) else math.pi
    # reuse a GND via that is already close and reachable
    near = sorted(vias, key=lambda v: math.hypot(v[0] - cx, v[1] - cy))
    if near and math.hypot(near[0][0] - cx, near[0][1] - cy) < max(hx, hy) + 0.9 and seg_ok((cx, cy), near[0], STUB_W / 2):
        add_track((cx, cy), near[0])
        report['reused'].append(key)
        continue
    best = None
    for k in range(16):
        ang = away + (k // 2 + 1) // 2 * (math.pi / 8) * (1 if k % 2 else -1) if k else away
        ux, uy = math.cos(ang), math.sin(ang)
        # distance from the centre to the pad boundary along (ux, uy)
        reach = min(hx / abs(ux) if abs(ux) > 1e-6 else 1e9, hy / abs(uy) if abs(uy) > 1e-6 else 1e9)
        for step in range(0, 30):
            d = reach + VIA_D / 2 + 0.12 + step * 0.1
            x, y = round(cx + ux * d, 3), round(cy + uy * d, 3)
            if via_ok(x, y) and seg_ok((cx + ux * reach, cy + uy * reach), (x, y), sw / 2):
                best = (d, x, y)
                break
        if best:
            break
    if not best:
        report['failed'].append(key)
        continue
    _, x, y = best
    add_via(x, y)
    add_track((cx, cy), (x, y), sw)
    report['stitched'].append(key)

board.Save(sys.argv[2])
json.dump(report, open(sys.argv[3], 'w'), indent=1)
print({k: len(v) for k, v in report.items()}, 'failed:', report['failed'])
