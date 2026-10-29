"""Split a track wherever a same-net, same-layer track end or via lands on its interior centerline,
so KiCad's connectivity (anchor-based) sees the T-junction.
usage: kicad_split_tees.py board.kicad_pcb   (modified in place; run on a copy)
"""
import sys, pcbnew

TOL = 2000          # nm off the centerline
b = pcbnew.LoadBoard(sys.argv[1])
n = 0
while True:
    tracks = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
    vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
    anchors = {}
    for t in tracks:
        for p in (t.GetStart(), t.GetEnd()):
            anchors.setdefault((t.GetNetCode(), t.GetLayer()), []).append((p.x, p.y))
    for v in vias:
        for ly in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
            anchors.setdefault((v.GetNetCode(), ly), []).append((v.GetPosition().x, v.GetPosition().y))
    done = False
    for t in tracks:
        s, e = t.GetStart(), t.GetEnd()
        dx, dy = e.x - s.x, e.y - s.y
        L2 = dx * dx + dy * dy
        if L2 == 0:
            continue
        for (x, y) in anchors.get((t.GetNetCode(), t.GetLayer()), []):
            u = ((x - s.x) * dx + (y - s.y) * dy) / L2
            if u <= 1e-6 or u >= 1 - 1e-6:
                continue
            px, py = s.x + u * dx, s.y + u * dy
            if (px - x) ** 2 + (py - y) ** 2 > TOL * TOL:
                continue
            if (x, y) in ((s.x, s.y), (e.x, e.y)):
                continue
            t2 = pcbnew.PCB_TRACK(b)
            t2.SetLayer(t.GetLayer()); t2.SetWidth(t.GetWidth()); t2.SetNetCode(t.GetNetCode())
            t2.SetStart(pcbnew.VECTOR2I(int(x), int(y))); t2.SetEnd(e)
            t.SetEnd(pcbnew.VECTOR2I(int(x), int(y)))
            b.Add(t2)
            n += 1
            done = True
            break
        if done:
            break
    if not done:
        break
b.Save(sys.argv[1])
print('split', n, 'tracks at tee junctions')
