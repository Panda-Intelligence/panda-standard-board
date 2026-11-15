"""eco_keys.py in out: OK key to the top of the right edge (user, 2026-11-15, thumb position when held).
- SW201 (KEY_POWER, the OK / power key) moves from (61.6, 95.2) to (61.6, 71.3): 87.9 mm from the top of the
  133.7 mm body instead of 111.8 mm. Its GND pad joins the F.Cu GND fill; KEY_POWER runs on F.Cu straight down to
  its pull-up R528 (62.51, 80.6), whose branch already reaches the KEY_POWER trunk via (60.604, 96.972).
- The old SW201 stub on F.Cu is removed; the trunk via stays (it joins the In2 trunk and the B.Cu branch).
- FID2 and its keep-out move from (60.95, 70.1) to (52.5, 69.1), still in the top-right corner.
- SW202 (BQ_QON, reset) stays at (61.6, 105.2); only its key cap in the shell becomes small and recessed."""
import sys, pcbnew as P
from ecolib import remove, trk, move
MM = P.FromMM
b = P.LoadBoard(sys.argv[1])

K = 'KEY_POWER'
remove(b, [(K, (61.6, 97.65), (61.6, 97.158)), (K, (61.414, 96.972), (61.6, 97.158)), (K, (60.604, 96.972), (61.414, 96.972))])
move(b, 'SW201', 61.6, 71.3, 90)
trk(b, K, 'F.Cu', 0.2, [(61.6, 73.75), (61.6, 74.6), (62.51, 75.51), (62.51, 80.6)])

f = b.FindFootprintByReference('FID2'); old = f.GetPosition(); new = P.VECTOR2I(MM(52.5), MM(69.1)); f.SetPosition(new)
for z in b.Zones():
    if z.GetZoneName().startswith('FID2'): z.Move(P.VECTOR2I(new.x - old.x, new.y - old.y))

P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
