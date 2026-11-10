"""Small explicit fixes after routing (KiCad Python).

usage: touchup_v020.py in.kicad_pcb fixes.json out.kicad_pcb
fixes.json: {"narrow": [[net, x, y, width_mm], ...]     tracks of net with an end at (x, y) get this width
             "narrow_box": [[net, x0, y0, x1, y1, width_mm], ...]   tracks of net touching the box
             "solid_pads": ["REF.PIN", ...]}            pad-to-zone connection set to solid
"""
import json
import sys

import pcbnew as P

MM, TO = P.FromMM, P.ToMM
board = P.LoadBoard(sys.argv[1])
fx = json.load(open(sys.argv[2]))
n = 0
for net, x, y, w in fx.get('narrow', []):
    for t in board.GetTracks():
        if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == net:
            ends = [(TO(t.GetStart().x), TO(t.GetStart().y)), (TO(t.GetEnd().x), TO(t.GetEnd().y))]
            if any(abs(a - x) < 0.02 and abs(b - y) < 0.02 for a, b in ends):
                t.SetWidth(MM(w))
                n += 1
for net, x0, y0, x1, y1, w in fx.get('narrow_box', []):
    box = P.BOX2I(P.VECTOR2I(MM(x0), MM(y0)), P.VECTOR2I(MM(x1 - x0), MM(y1 - y0)))
    for t in board.GetTracks():
        if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == net and t.GetBoundingBox().Intersects(box):
            t.SetWidth(MM(w))
            n += 1
s = 0
for key in fx.get('solid_pads', []):
    ref, pin = key.split('.')
    for p in board.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == pin:
            p.SetLocalZoneConnection(P.ZONE_CONNECTION_FULL)
            s += 1
P.ZONE_FILLER(board).Fill(board.Zones())
board.Save(sys.argv[3])
print('narrowed', n, 'tracks; solid pads', s)
