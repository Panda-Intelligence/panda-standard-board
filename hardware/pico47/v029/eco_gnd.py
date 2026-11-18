"""eco_gnd.py in.kicad_pcb out.kicad_pcb: ground returns after routing (KiCad Python).
- ground vias with a short link where the pour does not reach a pad (gndvia.gnd_via finds a spot that clears all layers),
Pads the pour reaches with one spoke only are handled by fix_thermals.py afterwards."""
import sys, pcbnew as P
from gndvia import gnd_via
T = P.ToMM
b = P.LoadBoard(sys.argv[1])
def pad(ref, num):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == num: return p
for ref, num, rmin, rmax in (('C510', '2', 0.7, 2.5), ('R602', '2', 0.6, 2.5), ('R402', '2', 0.6, 2.5), ('U903', '13', 0.0, 1.0), ('U906', '7', 0.0, 0.45),
                             ('U905', '7', 0.0, 0.45)):
    p = pad(ref, num); assert p.GetNetname() == 'GND', (ref, num, p.GetNetname())
    try: r = gnd_via(b, T(p.GetPosition().x), T(p.GetPosition().y), rmin=rmin, rmax=rmax); print(ref, num, 'ground via', r)
    except AssertionError as e: print(ref, num, 'no via spot: left to the pour')
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
