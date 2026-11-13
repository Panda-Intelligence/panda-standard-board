"""eco_final.py in out: three hand fixes after the finishing pipeline.
1. I2C_SDA on In2 at U601: restore the run to the via at (12.586, 83.618) that the dangling-end trim removed
   (the router had left a T-junction 4 um off the segment, so the trim saw a loose end).
2. BAT_CONN_P sense stub at U903 pin 8: 0.127 -> 0.12 mm (it was 1.4 um short of clearance to BQ_TS).
3. U904 pin 7 (amplifier GND) was fenced in by VSYS and SPK_P: GND via in the pad (filled, like the QFN pad vias)."""
import sys, pcbnew as P
MM, T = P.FromMM, P.ToMM
b = P.LoadBoard(sys.argv[1])
def near(p, x, y): return abs(T(p.x) - x) < 0.003 and abs(T(p.y) - y) < 0.003
n = 0
for t in b.GetTracks():
    if t.GetClass() != 'PCB_VIA' and t.GetNetname() == 'BAT_CONN_P' and (near(t.GetStart(), 41.4, 74.008) or near(t.GetEnd(), 41.4, 74.008)) and T(t.GetWidth()) < 0.13:
        t.SetWidth(MM(0.12)); n += 1
assert n == 2, n
def trk(net, layer, w, pts):
    for a, c in zip(pts, pts[1:]):
        t = P.PCB_TRACK(b); t.SetNet(b.FindNet(net)); t.SetLayer(b.GetLayerID(layer)); t.SetWidth(MM(w))
        t.SetStart(P.VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(P.VECTOR2I(MM(c[0]), MM(c[1]))); b.Add(t)
trk('I2C_SDA', 'In2.Cu', 0.127, [(12.575, 89.475), (12.575, 89.1), (11.775, 88.3), (11.775, 84.729), (12.586, 83.918), (12.586, 83.618)])
v = P.PCB_VIA(b); v.SetNet(b.FindNet('GND')); v.SetPosition(P.VECTOR2I(MM(3.565), MM(80.6))); v.SetWidth(P.F_Cu, MM(0.55)); v.SetDrill(MM(0.3)); b.Add(v)
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
