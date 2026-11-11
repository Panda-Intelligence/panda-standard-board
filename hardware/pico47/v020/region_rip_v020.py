"""Clear a window for a local Freerouting pass (KiCad Python).

usage: region_rip_v020.py in.kicad_pcb x0,y0,x1,y1[;x0,y0,x1,y1...] out.kicad_pcb
Deletes every non-GND track/via touching the window, then locks all remaining copper so the DSN
exports it as fixed wiring; Freerouting re-routes only what was removed (with its net-class widths).
"""
import sys

import pcbnew as P

MM, TO = P.FromMM, P.ToMM
board = P.LoadBoard(sys.argv[1])
wins = []
for w in sys.argv[2].split(';'):
    x0, y0, x1, y1 = map(float, w.split(','))
    wins.append(P.BOX2I(P.VECTOR2I(MM(x0), MM(y0)), P.VECTOR2I(MM(x1 - x0), MM(y1 - y0))))
n = 0
for t in list(board.GetTracks()):
    if t.GetNetname() != 'GND' and any(t.GetBoundingBox().Intersects(w) for w in wins):
        board.Delete(t)
        n += 1
for t in board.GetTracks():
    t.SetLocked(True)
board.Save(sys.argv[3])
print('removed', n, 'items in window; remaining copper locked')
