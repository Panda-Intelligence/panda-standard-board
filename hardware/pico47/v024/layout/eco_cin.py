"""eco_cin.py in out fp_dir: input capacitor C818 (0402) at U810 pin 24, the supply pin of the inverting converter.
L802 turns 180 deg and moves 0.3 mm down: its switch pad now sits straight under the rectifier D802 (1.8 mm of
track instead of a 4 mm diagonal), and its ground pad sits next to C818's ground. The VSYS track that ran under
L802 from C816 is removed (it crossed the new switch track); C816 keeps its feed on the other side. Signals that
crossed the spot (MODE, VEE_BASE) are re-laid by the grid router afterwards (layout/spec_cin.json).
C816 is removed and C506 moves to the audio amplifier."""
import sys, pcbnew as P
from ecolib import remove, trk, via, move
MM = P.FromMM
b = P.LoadBoard(sys.argv[1]); o = b.FindFootprintByReference('C504')
f = P.FootprintLoad(sys.argv[3], 'C_0402_1005Metric')
f.SetReference('C818'); f.SetValue('2.2u/10V/0402'); b.Add(f)
f.SetPosition(P.VECTOR2I(MM(26.9), MM(97.62))); f.SetOrientationDegrees(0)
for p in f.Pads(): p.SetNet(b.FindNet({'1': 'VSYS_RAW', '2': 'GND'}[p.GetNumber()]))
move(b, 'L802', 27.5, 100.4, 180)
V, X = 'VSYS_RAW', 'P47_VN_LX'
remove(b, [(X, (28.85, 96.75), (26.0, 99.6)), (X, (26.0, 99.6), (26.0, 100.1)),
           ('GND', (29.0, 100.1), (30.18, 100.675)),
           (V, (31.2, 98.725), (30.439, 97.964)), (V, (30.439, 97.964), (28.417, 97.964)), (V, (28.417, 97.964), (28.042, 98.338)),
           (V, (28.042, 98.338), (28.042, 100.402)), (V, (28.042, 100.402), (28.042, 100.704)),
           (V, (28.042, 100.704), (27.764, 100.983)), (V, (27.764, 100.983), (27.655, 100.983))])
trk(b, X, 'F.Cu', 0.6, [(28.85, 96.75), (28.85, 98.0), (29.0, 98.6)])
trk(b, V, 'F.Cu', 0.3, [(25.7, 96.45), (25.7, 97.2), (26.12, 97.62), (26.42, 97.62)])
trk(b, 'GND', 'F.Cu', 0.3, [(27.38, 97.62), (27.38, 98.0), (26.5, 98.88)])
via(b, 'GND', 26.0, 99.2); via(b, 'GND', 26.0, 99.9)
# C816 goes (see the netlist note). C506, the amplifier's 10 uF, hung off C816 32 mm from U904: it moves to the VSYS
# track below the amplifier, next to C505.
remove(b, [(V, (31.2, 98.72), (32.24, 98.72)), (V, (32.24, 98.72), (32.6, 99.08)), (V, (32.6, 99.08), (34.15, 99.08)),
           (V, (34.15, 99.08), (35.02, 99.95)), (V, (35.02, 99.95), (35.02, 100.47)), (V, (35.02, 100.47), (36.53, 101.97)),
           (V, (36.53, 101.97), (36.65, 101.97)), ('GND', (31.2, 97.175), (30.33, 97.175))])
c816 = b.FindFootprintByReference('C816'); b.Remove(c816)
move(b, 'C506', 3.1, 88.75, 0)
trk(b, V, 'F.Cu', 0.4, [(2.585, 87.75), (2.325, 88.2), (2.325, 88.75)])
trk(b, 'GND', 'F.Cu', 0.3, [(3.875, 88.75), (4.3, 88.45), (6.33, 88.445)])   # to the existing GND via below C505
for p in b.FindFootprintByReference('C506').Pads():
    if p.GetNumber() == '2': p.SetLocalZoneConnection(P.ZONE_CONNECTION_FULL)
for r in ('C818', 'L802', 'C506'):
    for p in b.FindFootprintByReference(r).Pads(): print(r, p.GetNumber(), p.GetNetname(), round(P.ToMM(p.GetPosition().x), 3), round(P.ToMM(p.GetPosition().y), 3), round(P.ToMM(p.GetSize().x), 2), round(P.ToMM(p.GetSize().y), 2))
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
