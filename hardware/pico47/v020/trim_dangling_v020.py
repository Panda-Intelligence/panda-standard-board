"""Trim dangling track ends back to the last same-net junction on the segment (KiCad Python).

usage: trim_dangling_v020.py in.kicad_pcb drc.json out.kicad_pcb
For every track that DRC reports as dangling, each end that touches no other copper of its net is moved back
along the segment to the nearest point where other same-net copper (track, via, pad) meets it. Ends without
such a point are left for the pruner.
"""
import json
import math
import sys

import pcbnew as P

MM, TO = P.FromMM, P.ToMM
board = P.LoadBoard(sys.argv[1])
drc = json.load(open(sys.argv[2]))
spots = [(i['pos']['x'], i['pos']['y'], i['description'])
         for v in drc['violations'] if v['type'] == 'track_dangling' for i in v['items']]


def pt(v):
    return TO(v.x), TO(v.y)


def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(a[0] + u * dx - p[0], a[1] + u * dy - p[1])


tracks = [t for t in board.GetTracks() if t.GetClass() == 'PCB_TRACK']
vias = [t for t in board.GetTracks() if t.GetClass() == 'PCB_VIA']
pads = [p for fp in board.GetFootprints() for p in fp.Pads()]


def others(t):
    """(kind, geometry, half-width) of same-net copper that can meet track t on its layer."""
    n, lay = t.GetNetname(), t.GetLayer()
    out = []
    for o in tracks:
        if o is not t and o.GetNetname() == n and o.GetLayer() == lay:
            out.append(('seg', (pt(o.GetStart()), pt(o.GetEnd())), TO(o.GetWidth()) / 2))
    for v in vias:
        if v.GetNetname() == n:
            out.append(('pt', pt(v.GetPosition()), TO(v.GetWidth(lay)) / 2))
    for p in pads:
        if p.GetNetname() == n and p.IsOnLayer(lay):
            out.append(('pad', p, 0))
    return out


def touches(e, w2, ob):
    kind, g, h = ob
    if kind == 'seg':
        return seg_dist(e, *g) <= w2 + h + 1e-4
    if kind == 'pt':
        return math.hypot(e[0] - g[0], e[1] - g[1]) <= h + 1e-4
    return g.HitTest(P.VECTOR2I(MM(e[0]), MM(e[1])))


done = 0
for t in tracks:
    a, b = pt(t.GetStart()), pt(t.GetEnd())
    if not any(f'[{t.GetNetname()}]' in d and min(math.hypot(x - a[0], y - a[1]), math.hypot(x - b[0], y - b[1])) < 2e-3
               for x, y, d in spots):
        continue
    w2 = TO(t.GetWidth()) / 2
    obs = others(t)
    for end, other, setter in ((a, b, t.SetStart), (b, a, t.SetEnd)):
        if any(touches(end, w2, o) for o in obs):
            continue
        L = math.hypot(other[0] - end[0], other[1] - end[1])
        if L < 1e-3:
            continue
        # walk from the open end towards the other end; stop at the first point that touches other copper
        steps = int(L / 0.005) + 1
        for k in range(1, steps):
            s = k * L / steps
            q = (end[0] + (other[0] - end[0]) * s / L, end[1] + (other[1] - end[1]) * s / L)
            if any(touches(q, w2, o) for o in obs):
                setter(P.VECTOR2I(MM(q[0]), MM(q[1])))
                done += 1
                break
P.ZONE_FILLER(board).Fill(board.Zones())
board.Save(sys.argv[3])
print('dangling ends trimmed', done)
