"""eco_tp_silk.py in out: back-silkscreen names for TP5 / TP6 / TPG2, in the style of the existing test-point names."""
import sys, pcbnew as P
MM = P.FromMM
b = P.LoadBoard(sys.argv[1])
ref = next(d for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == P.B_SilkS and d.GetText() == 'SCL')
for text, x, y in (('FLV', 34.84, 72.25), ('SD3V3', 24.96, 102.6), ('GND', 23.41, 74.7)):
    t = P.PCB_TEXT(b); t.SetLayer(P.B_SilkS); t.SetText(text); t.SetAttributes(ref.GetAttributes())
    t.SetPosition(P.VECTOR2I(MM(x), MM(y))); b.Add(t)
b.Save(sys.argv[2])
