"""anchors_v024.json: the v0.2.3 placement with the v0.2.4 changes.
usage: make_anchors_v024.py anchors_v023.json hand.json sizes.json netlist_v024.json out.json
- board outline with the 16.1 x 11.6 mm speaker notch (board 63 x 48 mm) at the top-left corner;
- removed parts dropped; parts inside the notch or overlapping hand parts / hand copper released to the placer."""
import json, math, sys
an = json.load(open(sys.argv[1])); hand = json.load(open(sys.argv[2])); sizes = json.load(open(sys.argv[3])); net = json.load(open(sys.argv[4]))['parts']
M = 0.2
NX, NY = 16.6, 79.0


def rect(ref, x, y, rot):
    b = sizes[ref]['bbox']; a = math.radians(rot)
    pts = [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])]
    rp = [(x + u * math.cos(a) + v * math.sin(a), y - u * math.sin(a) + v * math.cos(a)) for u, v in pts]
    return (min(p[0] for p in rp) - M, min(p[1] for p in rp) - M, max(p[0] for p in rp) + M, max(p[1] for p in rp) + M)


def hit(a, b): return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


parts = {r: list(v) for r, v in an['parts'].items() if r in net}
KEEP = {'SW201', 'SW202', 'J201', 'J501', 'J820', 'J803', 'J804', 'D203', 'D803'}
fixed = [rect(r, *p[:3]) for r, p in hand['pose'].items() if not r.startswith('TP')] + [tuple(k) for k in hand['keepout']]
notch = (0.0, 60.0, NX + 0.3, NY + 0.3)
released = []
for r in list(parts):
    if r in hand['pose'] or r in KEEP:
        continue
    side = parts[r][3] if len(parts[r]) > 3 else 'F'
    rc = rect(r, *parts[r][:3])
    if hit(rc, notch) or (side == 'F' and any(hit(rc, f) for f in fixed)):
        del parts[r]; released.append(r)
for r, p in hand['pose'].items():
    parts[r] = [p[0], p[1], p[2], 'B' if r.startswith('TP') else 'F']
W, T, B, R4 = 0.5, 67.4, 115.4, 4.0       # 63 x 48 mm: 5 mm added at the top (user, 2026-11-13)
# bottom-right: a 2.1 x 6.8 mm step for the enclosure's lanyard channel (user, 2026-11-13), R1 at its lower corner
outline = [[NX, T], [63.5, T], [63.5, 108.6], [61.4, 108.6], [61.4, B - 1.0], {'arc': [60.4, B - 1.0, 1.0, 0, 90]},
           [36.62, B], [36.62, 109.85], [27.38, 109.85], [27.38, B],
           {'arc': [W + R4, B - R4, R4, 90, 180]}, [W, NY], [NX, NY]]
out = dict(an, parts=parts, keepout=hand['keepout'], outline=outline)
out['target'] = {k: v for k, v in an.get('target', {}).items() if k in net}
json.dump(out, open(sys.argv[5], 'w'), indent=0)
print(len(parts), 'anchors; released:', released)
