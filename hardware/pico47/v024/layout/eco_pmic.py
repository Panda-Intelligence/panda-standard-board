"""eco_pmic.py in out fp_dir: VN reservoir C817 at the rectifier D802 (U810 inverting converter).
C817 (0603) lands directly above the D802 anode pad with a GND via in its pad 2. R801 turns to lie under R802 to make
room. The sense / drive nets that crossed the spot (VEE_FB, VEE_BASE, VGH_FB, VGH, XOE) are re-laid by the grid
router afterwards (layout/spec_pmic.json)."""
import sys, pcbnew as P
from ecolib import trk, via, move
MM = P.FromMM
b = P.LoadBoard(sys.argv[1])
f = P.FootprintLoad(sys.argv[3], 'C_0603_1608Metric')
f.SetReference('C817'); f.SetValue('4.7u/25V/0603'); b.Add(f)
f.SetPosition(P.VECTOR2I(MM(29.9), MM(93.18))); f.SetOrientationDegrees(0)
for p in f.Pads(): p.SetNet(b.FindNet({'1': 'P47_VN', '2': 'GND'}[p.GetNumber()]))
move(b, 'R801', 30.9, 91.4, 180)
trk(b, 'P47_VN', 'F.Cu', 0.45, [(28.85, 94.65), (29.125, 94.375), (29.125, 93.18)])
via(b, 'GND', 30.675, 93.18)
for p in b.FindFootprintByReference('C817').Pads(): print('C817', p.GetNumber(), p.GetNetname(), P.ToMM(p.GetPosition().x), P.ToMM(p.GetPosition().y))
for r in ('R801',):
    for p in b.FindFootprintByReference(r).Pads(): print(r, p.GetNumber(), p.GetNetname(), round(P.ToMM(p.GetPosition().x), 3), round(P.ToMM(p.GetPosition().y), 3))
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
