"""prune_stubs.py in.kicad_pcb out.kicad_pcb NET...: remove dead-end copper of the named nets (KiCad Python).
Track ends, vias and pads of a net are grouped into junctions. A track goes when one of its ends is alone in its
junction (nothing else there) and no other track ends on its body (T-junction): a track that carries a T always
stays, also when its own end overshoots the junction. A via goes when it touches fewer than two items; a via that only joins tracks on one layer is replaced by
direct links between those tracks (v0.2.7: the earlier "fewer than two layers" rule cut a live SD_CD path).
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
total = 0; joined = 0
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
        touch = [o for o in trk if o.GetNetname() == v.GetNetname() and pseg(x, y, *xy(o)) < r + T(o.GetWidth()) / 2 - EPS]
        npad = sum(1 for p in pads if p.GetNetname() == v.GetNetname() and p.HitTest(v.GetPosition(), int(P.FromMM(r))))
        if len(touch) + npad <= 1: dv.append(v); continue
        if len({o.GetLayer() for o in touch}) == 1 and npad == 0:
            # A via used only as a junction of tracks on one layer (the router leaves these): join the tracks at its
            # centre first, then the via can go. Never drop it without the link: the tracks may meet only on its pad.
            for o in touch:
                s_ = xy(o); e = (s_[0], s_[1]) if math.hypot(s_[0] - x, s_[1] - y) <= math.hypot(s_[2] - x, s_[3] - y) else (s_[2], s_[3])
                if math.hypot(e[0] - x, e[1] - y) > 0.001:
                    t = P.PCB_TRACK(b); t.SetNet(o.GetNet()); t.SetLayer(o.GetLayer()); t.SetWidth(o.GetWidth())
                    t.SetStart(P.VECTOR2I(P.FromMM(e[0]), P.FromMM(e[1]))); t.SetEnd(v.GetPosition()); b.Add(t)
            dv.append(v); joined += 1
    for v in dv: b.Remove(v); KEEP.append(v)
    total += len(dead) + len(dv)
    if not dead and not dv: break
# Last pass: a kept track whose loose end overshoots its outermost T-junction is cut back to that junction.
def proj(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    return 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
trimmed = 0
trk = [t for t in b.GetTracks() if t.GetNetname() in nets and t.GetClass() != 'PCB_VIA']
via = [t for t in b.GetTracks() if t.GetNetname() in nets and t.GetClass() == 'PCB_VIA']
for t in trk:
    s, w, n, ly = xy(t), T(t.GetWidth()), t.GetNetname(), t.GetLayer()
    js = []                                   # junction positions along the track, 0 = start, 1 = end
    for o in trk:
        if o is t or o.GetNetname() != n or o.GetLayer() != ly: continue
        so = xy(o)
        for ox, oy in ((so[0], so[1]), (so[2], so[3])):
            if pseg(ox, oy, *s) < (w + T(o.GetWidth())) / 2 - EPS: js.append(proj(ox, oy, *s))
    for v in via:
        vx, vy = T(v.GetPosition().x), T(v.GetPosition().y)
        if v.GetNetname() == n and pseg(vx, vy, *s) < T(v.GetWidth(P.F_Cu)) / 2 + w / 2 - EPS: js.append(proj(vx, vy, *s))
    for p in pads:
        if p.GetNetname() == n and p.IsOnLayer(ly):
            for k in range(21):
                if p.HitTest(P.VECTOR2I(P.FromMM(s[0] + (s[2] - s[0]) * k / 20), P.FromMM(s[1] + (s[3] - s[1]) * k / 20)), t.GetWidth() // 2): js.append(k / 20)
    if len(js) < 2: continue
    L = math.hypot(s[2] - s[0], s[3] - s[1]); lo, hi = min(js), max(js)
    if lo * L > 0.15:
        t.SetStart(P.VECTOR2I(P.FromMM(s[0] + (s[2] - s[0]) * lo), P.FromMM(s[1] + (s[3] - s[1]) * lo))); trimmed += 1
    if (1 - hi) * L > 0.15:
        t.SetEnd(P.VECTOR2I(P.FromMM(s[0] + (s[2] - s[0]) * hi), P.FromMM(s[1] + (s[3] - s[1]) * hi))); trimmed += 1
print('overshooting ends cut back:', trimmed)
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2]); print('removed', total, 'dead-end items of', sorted(nets), '; single-layer junction vias replaced by links:', joined)
