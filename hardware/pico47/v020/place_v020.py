"""Placement for Panda47 v0.2.0: hand-placed anchors + greedy placement of passives next to their owner.

usage: place_v020.py netlist.json sizes.json r50.json anchors.json out_placement.json

Coordinates are device-cavity millimetres (y down). The board is an L: an 11.5 mm strip beside the
50 x 80 mm cell and a full-width strip below it.
"""
import json
import math
import sys

from outline_v02x import expand

netlist, sizes, r50, anchors = (json.load(open(p)) for p in sys.argv[1:5])
parts = netlist['parts']
r50c = r50['comps']

OUTLINE_SRC = anchors['outline']
OUTLINE = expand(OUTLINE_SRC)
OUTLINE_CORNERS = [e for e in OUTLINE_SRC if not isinstance(e, dict)]
MARGIN = anchors.get('margin', 0.15)
HALO = anchors.get('halo', 0.0)          # extra clearance kept around hand-placed ICs for fan-out
EDGE = anchors.get('edge', 0.3)


def inside(pt, poly):
    x, y = pt
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy or 1)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def rect_ok(r, poly, edge):
    x0, y0, x1, y1 = r
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if not all(inside(c, poly) for c in corners):
        return False
    for c in corners + [((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1), (x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)]:
        for a, b in zip(poly, poly[1:] + poly[:1]):
            if seg_dist(c, a, b) < edge:
                return False
    # polygon vertices inside the rectangle (notch corners)
    for vx, vy in (OUTLINE_CORNERS if poly is OUTLINE else poly):
        if x0 - edge < vx < x1 + edge and y0 - edge < vy < y1 + edge:
            return False
    return True


def rot_bbox(b, rot):
    x0, y0, x1, y1 = b
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    a = math.radians(rot)
    # KiCad: positive orientation is counter-clockwise on screen (y down) -> x' = x cos + y sin, y' = -x sin + y cos
    rp = [(x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)) for x, y in pts]
    xs, ys = [p[0] for p in rp], [p[1] for p in rp]
    return min(xs), min(ys), max(xs), max(ys)


def placed_rect(ref, x, y, rot):
    b = rot_bbox(sizes[ref]['bbox'], rot)
    return (x + b[0] - MARGIN, y + b[1] - MARGIN, x + b[2] + MARGIN, y + b[3] + MARGIN)


def pad_xy(ref, pin, x, y, rot):
    px, py = sizes[ref]['pads'].get(pin, (0, 0))
    a = math.radians(rot)
    return x + px * math.cos(a) + py * math.sin(a), y - px * math.sin(a) + py * math.cos(a)


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


placed, rects = {}, []
for ref, pose in anchors['parts'].items():
    x, y, rot = pose[:3]
    r = placed_rect(ref, x, y, rot)
    pose = list(pose) + ['F'] * (4 - len(pose))
    if not anchors.get('allow_edge', {}).get(ref) and not rect_ok(r, OUTLINE, EDGE):
        print('WARN anchor outside board:', ref, [round(v, 2) for v in r])
    for other, orc, s in rects:
        if s == pose[3] and overlap(r, orc):
            print('WARN anchor overlap:', ref, other)
    placed[ref] = pose
    hx = HALO if ref[0] in 'UJ' else 0.0
    rects.append((ref, (r[0] - hx, r[1] - hx, r[2] + hx, r[3] + hx), pose[3]))

for i, k in enumerate(anchors.get('keepout', [])):      # hand-drawn copper and reserved areas on the front side
    rects.append((f'_keep{i}', tuple(k), 'F'))

BIG = {'GND', '3V3_AON', 'VSYS_RAW'}
ICS = [r for r in placed if r[0] in 'UJQ' or r.startswith('L') or r.startswith('D') or r.startswith('Y') or r.startswith('SW')]


def owner(ref):
    """Anchor whose pads share a non-power net with ref; ties broken by R50 distance."""
    if ref in anchors.get('owner', {}):
        return anchors['owner'][ref]
    mine = {n for n in parts[ref]['pins'].values() if n and n not in BIG}
    cands = []
    for a in ICS:
        shared = mine & {n for n in parts[a]['pins'].values() if n}
        if shared:
            d = 0
            if ref in r50c and a in r50c:
                d = math.hypot(r50c[ref]['x'] - r50c[a]['x'], r50c[ref]['y'] - r50c[a]['y'])
            cands.append((-len(shared), d, a))
    if cands:
        return min(cands)[2]
    if ref in r50c:
        return min((math.hypot(r50c[ref]['x'] - r50c[a]['x'], r50c[ref]['y'] - r50c[a]['y']), a) for a in ICS if a in r50c)[1]
    return None


def target(ref):
    """Mean position of the owner pads on nets shared with ref (power caps: owner's power pins).
    anchors['target'][ref] = "REF.PIN" pins the target to one pad of a placed part."""
    tp = anchors.get('target', {}).get(ref)
    if tp:
        tr, tn = tp.split('.')
        return pad_xy(tr, tn, *placed[tr][:3])
    own = owner(ref)
    if own is None:
        return None
    ox, oy, orot = placed[own][:3]
    mine = {n for n in parts[ref]['pins'].values() if n}
    focus = mine - {'GND'} or mine
    pts = [pad_xy(own, pin, ox, oy, orot) for pin, n in parts[own]['pins'].items() if n in focus]
    if not pts:
        return ox, oy
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


todo = [r for r in parts if r not in placed]
TGT = list(anchors.get('target', {}))
order = sorted(todo, key=lambda r: (0 if r in TGT else 1, TGT.index(r) if r in TGT else 0,
                                    -(sizes[r]['bbox'][2] - sizes[r]['bbox'][0]) * (sizes[r]['bbox'][3] - sizes[r]['bbox'][1])))
fails = []
STEP = 0.3
for ref in order:
    t = target(ref)
    if t is None:
        fails.append(ref)
        continue
    side = 'B' if ref.startswith('TP') else anchors.get('side', {}).get(ref, 'F')
    best = None
    for ring in range(0, 100):
        rr = ring * STEP
        n = max(1, int(2 * math.pi * rr / STEP))
        for k in range(n):
            a = 2 * math.pi * k / n
            x = round((t[0] + rr * math.cos(a)) / 0.05) * 0.05
            y = round((t[1] + rr * math.sin(a)) / 0.05) * 0.05
            for rot in (0, 90):
                r = placed_rect(ref, x, y, rot)
                if not rect_ok(r, OUTLINE, EDGE):
                    continue
                if any(overlap(r, o) for o_ref, o, s in rects
                       if s == side or (side == 'B' and o_ref[0] in 'UJLY')):
                    continue
                best = (x, y, rot)
                break
            if best:
                break
        if best:
            break
    if not best:
        fails.append(ref)
        continue
    placed[ref] = [best[0], best[1], best[2], side]
    rects.append((ref, placed_rect(ref, *best), side))

json.dump(dict(outline=OUTLINE_SRC, parts=placed), open(sys.argv[5], 'w'), indent=0)
print('placed', len(placed), 'of', len(parts), 'failed', fails)
