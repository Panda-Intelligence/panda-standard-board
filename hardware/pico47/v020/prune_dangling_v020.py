"""Delete tracks that KiCad DRC reports as dangling, but only when the deletion keeps every connection
(some reported tracks still join copper mid-segment and must stay). KiCad Python.

usage: prune_dangling_v020.py in.kicad_pcb drc.json out.kicad_pcb
"""
import json
import sys

import pcbnew as P

TO = P.ToMM
board = P.LoadBoard(sys.argv[1])
drc = json.load(open(sys.argv[2]))
spots = [(i['pos']['x'], i['pos']['y'], i['description'])
         for v in drc['violations'] if v['type'] == 'track_dangling' for i in v['items']]


def unconnected():
    board.BuildConnectivity()
    return board.GetConnectivity().GetUnconnectedCount(True)


base = unconnected()
kept = removed = 0
for t in list(board.GetTracks()):
    if t.GetClass() != 'PCB_TRACK' or t.IsLocked():
        continue
    ends = [(TO(t.GetStart().x), TO(t.GetStart().y)), (TO(t.GetEnd().x), TO(t.GetEnd().y))]
    if not any(f'[{t.GetNetname()}]' in d and any(abs(x - p[0]) < 2e-3 and abs(y - p[1]) < 2e-3 for p in ends)
               for x, y, d in spots):
        continue
    copy = t.Duplicate()
    board.Delete(t)
    if unconnected() > base:
        board.Add(copy)
        kept += 1
    else:
        removed += 1
P.ZONE_FILLER(board).Fill(board.Zones())
board.Save(sys.argv[3])
print(f'dangling reports {len(spots)}: removed {removed}, kept {kept} (needed for connectivity); unconnected {base} -> {unconnected()}')
