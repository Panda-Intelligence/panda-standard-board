"""spot_0402.py board x y rmax 0402|0201 [own nets]: free places for one more 0402 near (x, y) (KiCad Python).
A place is free when the 1.9 x 1.0 mm courtyard (either orientation) keeps clear of every other courtyard and pad,
of vias on any layer and of front-layer tracks of other nets (GND and the listed own nets may pass). Nearest first."""
import sys, math, pcbnew as P
T = P.ToMM
b = P.LoadBoard(sys.argv[1]); x0, y0, rmax = map(float, sys.argv[2:5]); SIZE = sys.argv[5]; own = set(sys.argv[6:]) | {'GND'}
HW, HH = {'0402': (0.95, 0.5), '0201': (0.7, 0.38)}[SIZE]
rects = []
for f in b.GetFootprints():
    for pad in f.Pads():
        if pad.IsOnLayer(P.F_Cu):
            bb = pad.GetBoundingBox(); rects.append((T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())))
    cy = f.GetCourtyard(P.F_CrtYd)
    if cy.OutlineCount():
        bb = cy.BBox(); rects.append((T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())))
segs = [(T(t.GetStart().x), T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y), T(t.GetWidth()) / 2) for t in b.GetTracks()
        if t.GetClass() != 'PCB_VIA' and t.GetLayer() == P.F_Cu and t.GetNetname() not in own]
vias = [(T(t.GetPosition().x), T(t.GetPosition().y)) for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
edge = b.GetBoardEdgesBoundingBox()
def seg_rect(s, r):                       # distance from a segment to a rectangle (sampled)
    n = max(2, int(math.hypot(s[2] - s[0], s[3] - s[1]) / 0.05))
    return min(math.hypot(max(r[0] - px, 0, px - r[2]), max(r[1] - py, 0, py - r[3]))
               for px, py in ((s[0] + (s[2] - s[0]) * i / n, s[1] + (s[3] - s[1]) * i / n) for i in range(n + 1)))
out = []
for i in range(int(-rmax / 0.1), int(rmax / 0.1) + 1):
    for j in range(int(-rmax / 0.1), int(rmax / 0.1) + 1):
        x, y = x0 + i * 0.1, y0 + j * 0.1; d = math.hypot(x - x0, y - y0)
        if d > rmax: continue
        for rot, (hw, hh) in ((0, (HW, HH)), (90, (HH, HW))):
            r = (x - hw, y - hh, x + hw, y + hh)
            if r[0] < 0.9 or r[2] > 63.1 or r[1] < 67.8 or r[3] > 115.0 or (r[0] < 17.0 and r[1] < 79.4): continue   # v0.2.4 outline, speaker notch
            if any(r[0] < q[2] and q[0] < r[2] and r[1] < q[3] and q[1] < r[3] for q in rects): continue
            if any(r[0] - 0.42 < vx < r[2] + 0.42 and r[1] - 0.42 < vy < r[3] + 0.42 for vx, vy in vias): continue
            near = [s for s in segs if min(s[0], s[2]) - 1 < r[2] and max(s[0], s[2]) + 1 > r[0] and min(s[1], s[3]) - 1 < r[3] and max(s[1], s[3]) + 1 > r[1]]
            if any(seg_rect(s, r) < s[4] + 0.1 for s in near): continue
            out.append((round(d, 2), round(x, 2), round(y, 2), rot))
seen = set()
for d, x, y, rot in sorted(out):
    k = (int(x // 0.6), int(y // 0.6), rot)
    if k in seen: continue
    seen.add(k); print(d, x, y, rot)
    if len(seen) >= 12: break
