"""Write router_v020.py output into a board (KiCad Python).

usage: apply_router_v020.py in.kicad_pcb routed.json out.kicad_pcb [extra.json] [ALIAS=NET ...]
routed.json: {"nets": {NET: {"tracks": [[layer, x1, y1, x2, y2], ...], "vias": [[x, y], ...], "removed": [uuid, ...]}}}
extra.json (optional): {"remove_uuids": [...], "tracks": [[net, layer, x1, y1, x2, y2, w], ...], "vias": [[net, x, y], ...]}
"""
import json
import sys

import pcbnew as P

MM = P.FromMM
W, VIA_D, VIA_DR = 0.127, 0.55, 0.3

board = P.LoadBoard(sys.argv[1])
res = json.load(open(sys.argv[2]))
extra = json.load(open(sys.argv[4])) if len(sys.argv) > 4 and sys.argv[4] != '-' else {}
alias = dict(a.split('=') for a in sys.argv[5:])
layer = {n: board.GetLayerID(n) for n in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')}

remove = set(extra.get('remove_uuids', []))
adds = []                                   # (net, layer, x1, y1, x2, y2, w)
vias = []                                   # (net, x, y)
for net, r in res.get('nets', {}).items():
    net = alias.get(net, net)
    remove |= set(r['removed'])
    adds += [(net, *t, W) for t in r['tracks']]
    vias += [(net, *v) for v in r['vias']]
adds += [tuple(t) for t in extra.get('tracks', [])]
vias += [tuple(v) for v in extra.get('vias', [])]

n_rm = 0
for t in list(board.GetTracks()):
    if t.m_Uuid.AsString() in remove:
        board.Delete(t)
        n_rm += 1
for net, ly, x1, y1, x2, y2, w in adds:
    t = P.PCB_TRACK(board)
    t.SetStart(P.VECTOR2I(MM(x1), MM(y1)))
    t.SetEnd(P.VECTOR2I(MM(x2), MM(y2)))
    t.SetWidth(MM(w))
    t.SetLayer(layer[ly])
    t.SetNet(board.FindNet(net))
    board.Add(t)
for net, x, y in vias:
    v = P.PCB_VIA(board)
    v.SetPosition(P.VECTOR2I(MM(x), MM(y)))
    v.SetWidth(MM(VIA_D))
    v.SetDrill(MM(VIA_DR))
    v.SetNet(board.FindNet(net))
    board.Add(v)
P.ZONE_FILLER(board).Fill(board.Zones())
board.Save(sys.argv[3])
print(f'removed {n_rm}, added {len(adds)} tracks, {len(vias)} vias')
