"""prune_stubs.py in.kicad_pcb out.kicad_pcb NET...: remove dead-end copper of the named nets (KiCad Python).
Track ends, vias and pads of a net are grouped into junctions. A track goes when one of its ends is alone in its
junction (nothing else there) and no other track ends on its body (T-junction): a track that carries a T always
stays, also when its own end overshoots the junction. A via goes when it joins fewer than two layers (a pad counts as one).
Repeats until nothing changes. Used after parts were removed, so that their feed branches do not stay as antennas."""
import math, sys, pcbnew as P
T = P.ToMM
b = P.LoadBoard(sys.argv[1]); nets = set(sys.argv[3:]); KEEP = []; EPS = 0.01
def pseg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)
def xy(t): return (T(t.GetStart().x), T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y))
pads = [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() in nets]
total = 0
while True:
    trk = [t for t in b.GetTracks() if t.GetNetname() in nets and t.GetClass() != 'PCB_VIA']
    via = [t for t in b.GetTracks() if t.GetNetname() in nets and t.GetClass() == 'PCB_VIA']
    ends = [(t, i) for t in trk for i in (0, 1)]                       # i: 0 = start, 1 = end
    pt = {(id(t), i): (xy(t)[2 * i], xy(t)[2 * i + 1]) for t, i in ends}
    alone = {}
    for t, i in ends:
        # something touches this end only if it is at least as close to it as to the track's other end
        x, y = pt[(id(t), i)]; ox_, oy_ = pt[(id(t), 1 - i)]; n, ly, w = t.GetNetname(), t.GetLayer(), T(t.GetWidth()); k = 0
        for o in trk:
            if o is t or o.GetNetname() != n or o.GetLayer() != ly: continue
            d = pseg(x, y, *xy(o))
            if d < (w + T(o.GetWidth())) / 2 - EPS and d <= pseg(ox_, oy_, *xy(o)): k += 1
        for v in via:
            vx, vy = T(v.GetPosition().x), T(v.GetPosition().y); d = math.hypot(vx - x, vy - y)
            if v.GetNetname() == n and d < T(v.GetWidth(P.F_Cu)) / 2 + w / 2 - EPS and d <= math.hypot(vx - ox_, vy - oy_): k += 1
        for p in pads:
            if p.GetNetname() == n and p.IsOnLayer(ly) and p.HitTest(P.VECTOR2I(P.FromMM(x), P.FromMM(y)), t.GetWidth() // 2): k += 1
        alone[(id(t), i)] = k == 0
    dead = []
    for t in trk:
        if not (alone[(id(t), 0)] or alone[(id(t), 1)]): continue
        s, w = xy(t), T(t.GetWidth()); tee = False
        for o in trk:                                                   # another track ending on this one's body
            if o is t or o.GetNetname() != t.GetNetname() or o.GetLayer() != t.GetLayer(): continue
            for i in (0, 1):
                ox, oy = pt[(id(o), i)]; reach = (w + T(o.GetWidth())) / 2 - EPS
                if pseg(ox, oy, *s) < reach and min(math.hypot(ox - s[0], oy - s[1]), math.hypot(ox - s[2], oy - s[3])) >= reach: tee = True
        mid_via = any(v.GetNetname() == t.GetNetname() and pseg(T(v.GetPosition().x), T(v.GetPosition().y), *s) < T(v.GetWidth(P.F_Cu)) / 2 + w / 2 - EPS
                      and min(math.hypot(T(v.GetPosition().x) - s[0], T(v.GetPosition().y) - s[1]), math.hypot(T(v.GetPosition().x) - s[2], T(v.GetPosition().y) - s[3])) >= T(v.GetWidth(P.F_Cu)) / 2 + w / 2 - EPS for v in via)
        if not tee and not mid_via: dead.append(t)
    for t in dead: b.Remove(t); KEEP.append(t)
    trk = [t for t in trk if t not in dead]
    dv = []
    for v in via:
        if v.GetNetname() == 'GND': continue
        x, y, r = T(v.GetPosition().x), T(v.GetPosition().y), T(v.GetWidth(P.F_Cu)) / 2
        k = len({o.GetLayer() for o in trk if o.GetNetname() == v.GetNetname() and pseg(x, y, *xy(o)) < r + T(o.GetWidth()) / 2 - EPS})   # layers joined
        k += sum(1 for p in pads if p.GetNetname() == v.GetNetname() and p.HitTest(v.GetPosition(), int(P.FromMM(r))))
        if k <= 1: dv.append(v)
    for v in dv: b.Remove(v); KEEP.append(v)
    total += len(dead) + len(dv)
    if not dead and not dv: break
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2]); print('removed', total, 'dead-end items of', sorted(nets))
