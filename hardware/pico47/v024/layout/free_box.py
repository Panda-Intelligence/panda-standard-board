"""free_spots.py board R: grid points whose circle of radius R is free of non-GND copper on every layer, of pads,
holes and courtyards, and inside the board (candidates for mounting / locating holes)."""
import sys, math, pcbnew as P
T = P.ToMM
b = P.LoadBoard(sys.argv[1]); R = float(sys.argv[2]); BX = [float(v) for v in sys.argv[3].split(',')]; SKIP = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else set()
def dseg(p, a, c):
    dx, dy = c[0]-a[0], c[1]-a[1]; L = dx*dx+dy*dy
    t = 0 if L == 0 else max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/L)); return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)
def drect(p, r): return math.hypot(max(r[0]-p[0], 0, p[0]-r[2]), max(r[1]-p[1], 0, p[1]-r[3]))
segs, circs, rects = [], [], []
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        circs.append((T(t.GetPosition().x), T(t.GetPosition().y), 0.3 if t.GetNetname() != 'GND' else 0.3))
    elif t.GetNetname() != 'GND':
        segs.append(((T(t.GetStart().x), T(t.GetStart().y)), (T(t.GetEnd().x), T(t.GetEnd().y)), T(t.GetWidth())/2))
    else:
        segs.append(((T(t.GetStart().x), T(t.GetStart().y)), (T(t.GetEnd().x), T(t.GetEnd().y)), T(t.GetWidth())/2))
for f in b.GetFootprints():
    if f.GetReference() in SKIP: continue
    for pad in f.Pads():
        bb = pad.GetBoundingBox(); rects.append((T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())))
    cy = f.GetCourtyard(P.F_CrtYd)
    if cy.OutlineCount() and not f.GetReference().startswith('TP'):
        bb = cy.BBox(); rects.append((T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())))
def inside(p): return True
out = []
y = BX[1]
while y < BX[3]:
    x = BX[0]
    while x < BX[2]:
        p = (x, y)
        if inside(p):
            d = min([dseg(p, a, c) - w for a, c, w in segs] + [math.hypot(x-cx, y-cy) - r for cx, cy, r in circs] + [drect(p, r) for r in rects])
            if d >= R: out.append((round(d, 2), x, y))
        x += 0.1
    y += 0.1
# cluster: keep best per 4 mm cell
best = {}
for d, x, y in out:
    k = (int(x // 1.5), int(y // 1.5))
    if k not in best or d > best[k][0]: best[k] = (d, x, y)
for k in sorted(best, key=lambda k: (k[1], k[0])): print('free r %.2f at (%.2f, %.2f)' % best[k])
