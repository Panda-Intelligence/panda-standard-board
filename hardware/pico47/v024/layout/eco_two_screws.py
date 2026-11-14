"""eco_two_screws.py in out: drop the nut H1 left of USB-C (user, 2026-11-14: two screws and two shell lips).
The board keeps H2 and H3 at the top edge. D203, R208 and the 3V3 trunk stay where eco_mount.py put them."""
import sys, pcbnew as P
b = P.LoadBoard(sys.argv[1]); f = b.FindFootprintByReference('H1'); b.Remove(f); KEEP = [f]
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
