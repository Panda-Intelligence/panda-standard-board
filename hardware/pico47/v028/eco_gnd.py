"""eco_gnd.py in.kicad_pcb out.kicad_pcb: after routing, two ground pads that the pour reaches with a single thermal
spoke get a solid pour connection instead (KiCad Python): TH801 pad 2 and the J501 shell pad at the detect corner.
A via with a link was tried first; no spot clears the neighbouring vias."""
import sys, pcbnew as P
T = P.ToMM
b = P.LoadBoard(sys.argv[1]); n = 0
for ref, num, at in (('TH801', '2', None), ('J501', 'SH', (14.8, 92.745))):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == num and (at is None or (abs(T(p.GetPosition().x) - at[0]) < 0.05 and abs(T(p.GetPosition().y) - at[1]) < 0.05)):
            assert p.GetNetname() == 'GND'; p.SetLocalZoneConnection(P.ZONE_CONNECTION_FULL); n += 1
assert n == 2, n
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2]); print('solid ground connection on', n, 'pads')
