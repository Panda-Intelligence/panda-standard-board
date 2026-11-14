"""eco_touch_int.py in out: hand fix at U601 pins 9-11 after the grid-router pass.
TOUCH_INT and P47_PGOOD vias were 0.5 mm apart. Pin 9 (GND) now ties to the exposed pad instead of its own via,
the TOUCH_INT via moves to (11.4, 89.5) and EN_3V3_SD on B.Cu shifts 0.25 mm down to clear it."""
import sys, pcbnew as P
MM = P.FromMM
b = P.LoadBoard(sys.argv[1])
RM = {'2a50bda2', 'af22ea46', '1f697af1', '35f2b919', '378a92c2', '7579f78c', 'e19facce', '27debbf4', '4579769f', '61c547b0', '17c0c239', 'd60c9365'}
n = 0
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString()[:8] in RM: b.Remove(t); n += 1
assert n == len(RM), n
def trk(net, layer, w, pts):
    for a, c in zip(pts, pts[1:]):
        t = P.PCB_TRACK(b); t.SetNet(b.FindNet(net)); t.SetLayer(b.GetLayerID(layer)); t.SetWidth(MM(w))
        t.SetStart(P.VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(P.VECTOR2I(MM(c[0]), MM(c[1]))); b.Add(t)
def via(net, x, y):
    v = P.PCB_VIA(b); v.SetNet(b.FindNet(net)); v.SetPosition(P.VECTOR2I(MM(x), MM(y))); v.SetWidth(P.F_Cu, MM(0.55)); v.SetDrill(MM(0.3)); b.Add(v)
trk('GND', 'F.Cu', 0.15, [(11.05, 88.5625), (11.05, 87.8)])
trk('TOUCH_INT', 'F.Cu', 0.127, [(11.55, 88.5625), (11.55, 89.25), (11.4, 89.5)])
via('TOUCH_INT', 11.4, 89.5)
trk('TOUCH_INT', 'B.Cu', 0.127, [(11.4, 89.5), (11.8, 89.9), (12.325, 89.9)])
trk('EN_3V3_SD', 'B.Cu', 0.127, [(12.0, 90.65), (11.45, 90.1), (10.75, 90.1), (10.5, 89.85)])
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
