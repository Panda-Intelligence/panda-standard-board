"""Hide reference/value/user text on the silkscreen (the board is too dense to print designators; they stay on
the F.Fab assembly layer) and drop footprint silk graphics that sit on copper (KiCad Python).

usage: silk_v020.py in.kicad_pcb out.kicad_pcb
"""
import sys

import pcbnew as P

board = P.LoadBoard(sys.argv[1])
SILK = (P.F_SilkS, P.B_SilkS)
hidden = 0
for fp in board.GetFootprints():
    for f in fp.GetFields():
        if f.GetLayer() in SILK and f.IsVisible():
            f.SetVisible(False)
            hidden += 1
    for g in fp.GraphicalItems():
        if g.GetClass() == 'PCB_TEXT' and g.GetLayer() in SILK:
            g.SetVisible(False) if hasattr(g, 'SetVisible') else None
            hidden += 1
board.Save(sys.argv[2])
print('silkscreen texts hidden', hidden)
