"""eco_d11.py in out: open an escape for U501 pin 21 (P47_D11) below the pin row.
C504's GND via moves into its pad 2 (via-in-pad, same filled process as the QFN pads), a P47_D11 via takes the
freed spot, and P47_D9 on In2 turns 0.5 mm later to clear both."""
import sys, pcbnew as P
MM, T = P.FromMM, P.ToMM
b = P.LoadBoard(sys.argv[1])
def near(p, x, y): return abs(T(p.x) - x) < 0.003 and abs(T(p.y) - y) < 0.003
RM = [('GND', (44.530, 100.695), None), ('GND', (44.530, 101.400), (44.530, 100.695)),
      ('P47_D9', (43.465, 98.799), (43.465, 100.787)), ('P47_D9', (43.465, 100.787), (45.599, 102.920))]
hit = []
for t in b.GetTracks():
    for k, (net, a, c) in enumerate(RM):
        if t.GetNetname() != net: continue
        if c is None:
            ok = t.GetClass() == 'PCB_VIA' and near(t.GetPosition(), *a)
        else:
            ok = t.GetClass() != 'PCB_VIA' and ((near(t.GetStart(), *a) and near(t.GetEnd(), *c)) or (near(t.GetStart(), *c) and near(t.GetEnd(), *a)))
        if ok: hit.append((k, t))
assert sorted(k for k, _ in hit) == list(range(len(RM))), [k for k, _ in hit]
for _, t in hit: b.Remove(t)
def trk(net, layer, w, pts):
    for a, c in zip(pts, pts[1:]):
        t = P.PCB_TRACK(b); t.SetNet(b.FindNet(net)); t.SetLayer(b.GetLayerID(layer)); t.SetWidth(MM(w))
        t.SetStart(P.VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(P.VECTOR2I(MM(c[0]), MM(c[1]))); b.Add(t)
def via(net, x, y):
    v = P.PCB_VIA(b); v.SetNet(b.FindNet(net)); v.SetPosition(P.VECTOR2I(MM(x), MM(y))); v.SetWidth(P.F_Cu, MM(0.55)); v.SetDrill(MM(0.3)); b.Add(v)
via('GND', 44.5, 101.3)
trk('P47_D9', 'In2.Cu', 0.127, [(43.465, 98.799), (43.465, 101.3), (45.085, 102.92), (45.599, 102.92)])
trk('P47_D11', 'F.Cu', 0.127, [(43.8, 99.75), (43.8, 100.25), (44.1, 100.62)])
via('P47_D11', 44.1, 100.62)
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
