"""anchors_v023.json: the v0.2.2 placement with the hand-laid blocks of design_v023.py.

usage: make_anchors_v023.py placement_v022.json anchors_v022.json hand.json sizes.json out.json
Hand poses replace the old ones. Any other anchored part that now overlaps a hand part or hand copper is released to
the placer, which puts it next to its owner again."""
import json, math, sys
pl = json.load(open(sys.argv[1])); an = json.load(open(sys.argv[2])); hand = json.load(open(sys.argv[3])); sizes = json.load(open(sys.argv[4]))
M = 0.2


def rect(ref, x, y, rot):
    b = sizes[ref]['bbox']; a = math.radians(rot)
    pts = [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])]
    rp = [(x + u * math.cos(a) + v * math.sin(a), y - u * math.sin(a) + v * math.cos(a)) for u, v in pts]
    return (min(p[0] for p in rp) - M, min(p[1] for p in rp) - M, max(p[0] for p in rp) + M, max(p[1] for p in rp) + M)


def hit(a, b): return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


parts = {r: list(v) for r, v in an['parts'].items()}
EXTRA = {'U506': [55.8, 96.8, 0, 'F'], 'U904': [55.6, 104.0, 0, 'F']}
KEEP = {'SW201', 'SW202', 'J201', 'J501', 'J820', 'J803', 'J804', 'D203', 'D803', 'J302'}      # mechanical positions never move
parts.update(EXTRA)
fixed = [rect(r, *p[:3]) for r, p in hand['pose'].items() if not r.startswith('TP')] + [tuple(k) for k in hand['keepout']] + [rect(r, *p[:3]) for r, p in EXTRA.items()]
released = []
for r in list(parts):
    if r in hand['pose'] or r in EXTRA or r in KEEP or r.startswith('TP'):
        continue
    side = parts[r][3] if len(parts[r]) > 3 else 'F'
    if side == 'F' and any(hit(rect(r, *parts[r][:3]), f) for f in fixed):
        del parts[r]; released.append(r)
for r, p in hand['pose'].items():
    parts[r] = [p[0], p[1], p[2], 'B' if r.startswith('TP') else 'F']
out = dict(an, parts=parts, keepout=hand['keepout'])
out.setdefault('allow_edge', {}).update({'D905': True})
json.dump(out, open(sys.argv[5], 'w'), indent=0)
print(len(parts), 'anchors; released:', released)
