"""eco_lanyard.py in out: board cut-out at the bottom-right corner for the enclosure's lanyard channel.
The R4 corner becomes a 2.1 x 6.8 mm step: right edge down to y 108.6, in to x 61.4, down to an R1 corner at
(60.4, 114.4). J820 (courtyard to x 61.38) and SW202 (courtyard to y 108.30) stay where they are."""
import sys, pcbnew as P
MM, T = P.FromMM, P.ToMM
b = P.LoadBoard(sys.argv[1])
def near(p, x, y): return abs(T(p.x) - x) < 0.01 and abs(T(p.y) - y) < 0.01
old = [((63.5, 67.4), (63.5, 111.4)), ((63.5, 111.4), (59.5, 115.4)), ((59.5, 115.4), (36.62, 115.4))]
rm = [d for d in b.GetDrawings() if d.GetLayer() == P.Edge_Cuts and any(
      (near(d.GetStart(), *a) and near(d.GetEnd(), *c)) or (near(d.GetStart(), *c) and near(d.GetEnd(), *a)) for a, c in old)]
assert len(rm) == 3, len(rm)
w = rm[0].GetWidth()
for d in rm: b.Remove(d)
def line(a, c):
    s = P.PCB_SHAPE(b); s.SetShape(P.SHAPE_T_SEGMENT); s.SetLayer(P.Edge_Cuts); s.SetWidth(w)
    s.SetStart(P.VECTOR2I(MM(a[0]), MM(a[1]))); s.SetEnd(P.VECTOR2I(MM(c[0]), MM(c[1]))); b.Add(s)
line((63.5, 67.4), (63.5, 108.6)); line((63.5, 108.6), (61.4, 108.6)); line((61.4, 108.6), (61.4, 114.4)); line((60.4, 115.4), (36.62, 115.4))
a = P.PCB_SHAPE(b); a.SetShape(P.SHAPE_T_ARC); a.SetLayer(P.Edge_Cuts); a.SetWidth(w)
m = 0.70710678
a.SetArcGeometry(P.VECTOR2I(MM(61.4), MM(114.4)), P.VECTOR2I(MM(60.4 + m), MM(114.4 + m)), P.VECTOR2I(MM(60.4), MM(115.4))); b.Add(a)
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
