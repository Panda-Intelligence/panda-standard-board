"""tp_find.py board NET...: vias of each net ranked by free B.Cu radius (other-net copper, holes, board edge, test pads)."""
import sys, math, pcbnew as P
T = P.ToMM
b = P.LoadBoard(sys.argv[1])
def dseg(p, a, c):
    dx, dy = c[0]-a[0], c[1]-a[1]; L = dx*dx+dy*dy
    t = 0 if L == 0 else max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/L)); return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)
obs = []   # (net, fn(p) -> distance to copper edge)
for t in b.GetTracks():
    n = t.GetNetname()
    if t.GetClass() == 'PCB_VIA':
        c = (T(t.GetPosition().x), T(t.GetPosition().y)); obs.append((n, lambda p, c=c: math.hypot(p[0]-c[0], p[1]-c[1]) - 0.3))
    elif t.GetLayer() == P.B_Cu:
        a = (T(t.GetStart().x), T(t.GetStart().y)); c = (T(t.GetEnd().x), T(t.GetEnd().y)); w = T(t.GetWidth())/2
        obs.append((n, lambda p, a=a, c=c, w=w: dseg(p, a, c) - w))
for f in b.GetFootprints():
    for pad in f.Pads():
        if pad.IsOnLayer(P.B_Cu):
            bb = pad.GetBoundingBox(); r = (T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom()))
            obs.append((pad.GetNetname() if not f.GetReference().startswith('TP') else '#tp', lambda p, r=r: math.hypot(max(r[0]-p[0], 0, p[0]-r[2]), max(r[1]-p[1], 0, p[1]-r[3]))))
edge = b.GetBoardEdgesBoundingBox()
for net in sys.argv[2:]:
    best = []
    for t in b.GetTracks():
        if t.GetClass() != 'PCB_VIA' or t.GetNetname() != net: continue
        p = (T(t.GetPosition().x), T(t.GetPosition().y))
        if not (2.5 < p[0] < 61.5 and 69.5 < p[1] < 113.0) or (p[0] < 18.6 and p[1] < 81): continue
        if 26 < p[0] < 38 and p[1] > 107.5: continue
        d = min(fn(p) for n, fn in obs if n != net)
        best.append((round(d, 2), round(p[0], 2), round(p[1], 2)))
    print(net, sorted(best, reverse=True)[:6])
