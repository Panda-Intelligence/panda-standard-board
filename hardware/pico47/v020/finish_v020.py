"""Post-route clean-up for Panda47 v0.2.0 (KiCad Python).

usage: finish_v020.py in.kicad_pcb drc.json out.kicad_pcb
- deletes vias that DRC reports as dangling
- widens tracks narrower than the JLC multilayer minimum (0.09 mm) to 0.0952 mm
- adds one GND via to every outer-layer GND fill piece that holds no GND via
"""
import json
import math
import sys

import pcbnew as P

MM, TO = P.FromMM, P.ToMM
VIA_D, VIA_DRILL, MIN_W = 0.55, 0.3, 0.0952   # JLC multilayer minimum is 0.09 mm

board = P.LoadBoard(sys.argv[1])
drc = json.load(open(sys.argv[2]))

dangling = {(round(i['pos']['x'], 3), round(i['pos']['y'], 3))
            for v in drc['violations'] if v['type'] == 'via_dangling' for i in v['items']}
removed = widened = 0
for t in list(board.GetTracks()):
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition()
        if (round(TO(p.x), 3), round(TO(p.y), 3)) in dangling and not t.IsLocked():
            board.Delete(t)
            removed += 1
    elif TO(t.GetWidth()) < MIN_W - 1e-4:
        t.SetWidth(MM(MIN_W))
        widened += 1

gnd = board.FindNet('GND')
P.ZONE_FILLER(board).Fill(board.Zones())

obst = []                      # other-net copper on inner / opposite layers: (layer, x0, y0, x1, y1)
for fp in board.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetname() != 'GND' and pad.GetNumber() != '' and pad.IsOnCopperLayer():
            bb = pad.GetBoundingBox()
            obst.append((None, TO(bb.GetX()), TO(bb.GetY()), TO(bb.GetRight()), TO(bb.GetBottom())))
segs = []
for t in board.GetTracks():
    if t.GetNetname() != 'GND' and t.GetClass() == 'PCB_TRACK':
        segs.append(((TO(t.GetStart().x), TO(t.GetStart().y)), (TO(t.GetEnd().x), TO(t.GetEnd().y)), TO(t.GetWidth()) / 2))
    if t.GetNetname() != 'GND' and t.GetClass() == 'PCB_VIA':
        p = t.GetPosition()
        segs.append(((TO(p.x), TO(p.y)), (TO(p.x), TO(p.y)), TO(t.GetWidth()) / 2))
gvias = [(TO(t.GetPosition().x), TO(t.GetPosition().y)) for t in board.GetTracks()
         if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND']


def sd(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    u = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy or 1)))
    return math.hypot(p[0] - a[0] - u * dx, p[1] - a[1] - u * dy)


def free(x, y):
    r = VIA_D / 2 + 0.15
    for _, x0, y0, x1, y1 in obst:
        if math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1)) < r:
            return False
    for a, b, hw in segs:
        if sd((x, y), a, b) < r + hw:
            return False
    return all(math.hypot(x - vx, y - vy) >= 0.7 for vx, vy in gvias)


def chain_pts(ch):
    return [(TO(ch.CPoint(i).x), TO(ch.CPoint(i).y)) for i in range(ch.PointCount())]


def inside(pt, poly):
    x, y = pt
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


added = []
for z in board.Zones():
    if z.GetNetname() != 'GND' or z.GetLayer() not in (P.F_Cu, P.B_Cu):
        continue
    fill = z.GetFilledPolysList(z.GetLayer())
    for i in range(fill.OutlineCount()):
        poly = chain_pts(fill.Outline(i))
        if any(inside(v, poly) for v in gvias):
            continue
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        done = False
        gx = min(xs)
        while gx <= max(xs) and not done:
            gy = min(ys)
            while gy <= max(ys) and not done:
                if inside((gx, gy), poly) and all(sd((gx, gy), a, b) >= VIA_D / 2 + 0.02
                                                  for a, b in zip(poly, poly[1:] + poly[:1])) and free(gx, gy):
                    v = P.PCB_VIA(board)
                    v.SetPosition(P.VECTOR2I(MM(gx), MM(gy)))
                    v.SetWidth(MM(VIA_D))
                    v.SetDrill(MM(VIA_DRILL))
                    v.SetNet(gnd)
                    board.Add(v)
                    gvias.append((gx, gy))
                    added.append((round(gx, 2), round(gy, 2)))
                    done = True
                gy += 0.1
            gx += 0.1
P.ZONE_FILLER(board).Fill(board.Zones())
board.Save(sys.argv[3])
print('dangling vias removed', removed, 'tracks widened', widened, 'GND island vias', len(added))
