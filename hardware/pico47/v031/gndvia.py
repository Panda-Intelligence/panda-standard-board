"""gndvia.py: gnd_via(board, x, y) adds a GND via at the nearest spot that clears every other net on all layers and
links it to (x, y) with a straight front-layer track (KiCad Python). Same search as v025/eco_review.py."""
import math, pcbnew as P
from ecolib import trk, via
MM, T = P.FromMM, P.ToMM
def ends(t): return [(T(t.GetPosition().x), T(t.GetPosition().y))] if t.GetClass() == 'PCB_VIA' else [(T(t.GetStart().x), T(t.GetStart().y)), (T(t.GetEnd().x), T(t.GetEnd().y))]
def seg_d(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L)); return math.hypot(px - ax - t * dx, py - ay - t * dy)
def gnd_via(b, x0, y0, w=0.3, rmax=2.5, rmin=0.7):
    VR, DR = 0.275, 0.15
    near = [t for t in b.GetTracks() if min(math.hypot(x - x0, y - y0) for x, y in ends(t)) < rmax + 8]
    padl = [(p, p.GetBoundingBox()) for f in b.GetFootprints() for p in f.Pads() if abs(T(p.GetPosition().x) - x0) < rmax + 4 and abs(T(p.GetPosition().y) - y0) < rmax + 4]
    def box_d(bb, x, y): return math.hypot(max(T(bb.GetX()) - x, 0, x - T(bb.GetRight())), max(T(bb.GetY()) - y, 0, y - T(bb.GetBottom())))
    best = None
    for i in range(-50, 51):
        for j in range(-50, 51):
            x, y = x0 + i * 0.05, y0 + j * 0.05; d = math.hypot(x - x0, y - y0)
            if d > rmax or d < rmin or (best and d >= best[0]): continue
            if x < 1.0 or x > 63.0 or y < 68.0 or y > 114.9 or (x < 17.1 and y < 79.5): continue
            ok = True
            for t in near:
                gnd = t.GetNetname() == 'GND'
                if t.GetClass() == 'PCB_VIA':
                    dd = math.hypot(T(t.GetPosition().x) - x, T(t.GetPosition().y) - y)
                    if dd < 2 * DR + 0.27 or (not gnd and dd < 2 * VR + 0.14): ok = False; break
                    if not gnd and any(math.hypot(T(t.GetPosition().x) - (x0 + (x - x0) * k / 16), T(t.GetPosition().y) - (y0 + (y - y0) * k / 16)) < VR + w / 2 + 0.14 for k in range(17)): ok = False; break   # the link must clear vias too
                elif not gnd:
                    e = ends(t); hw = T(t.GetWidth()) / 2
                    if seg_d(x, y, *e[0], *e[1]) < max(VR + 0.14, DR + 0.26) + hw: ok = False; break
                    if t.GetLayer() == P.F_Cu and any(seg_d(x0 + (x - x0) * k / 16, y0 + (y - y0) * k / 16, *e[0], *e[1]) < w / 2 + hw + 0.14 for k in range(17)): ok = False; break
            if not ok: continue
            for p, bb in padl:
                dd = box_d(bb, x, y)
                if p.GetNetname() == 'GND':
                    if dd < VR + 0.1 and dd > 0: ok = False; break
                    if dd == 0 and math.hypot(T(p.GetPosition().x) - x0, T(p.GetPosition().y) - y0) > 0.01: ok = False; break
                else:
                    if dd < max(VR + 0.14, DR + 0.26): ok = False; break
                    if p.IsOnLayer(P.F_Cu) and any(box_d(bb, x0 + (x - x0) * k / 16, y0 + (y - y0) * k / 16) < w / 2 + 0.14 for k in range(17)): ok = False; break
            if ok: best = (d, round(x, 3), round(y, 3))
    assert best, ('no via spot', x0, y0)
    trk(b, 'GND', 'F.Cu', w, [(x0, y0), best[1:]]); via(b, 'GND', *best[1:]); print('GND via', best[1:], 'for', (x0, y0))

