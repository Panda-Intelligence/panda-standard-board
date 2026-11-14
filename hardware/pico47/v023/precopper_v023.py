"""Add the hand-drawn copper of design_v023.py to a board as locked tracks and vias (KiCad Python).
usage: precopper_v023.py in.kicad_pcb hand.json out.kicad_pcb"""
import json, sys
import pcbnew as P
MM = P.FromMM
b = P.LoadBoard(sys.argv[1]); h = json.load(open(sys.argv[2]))
L = {n: b.GetLayerID(n) for n in ('F.Cu', 'In2.Cu', 'B.Cu')}
n = 0
for net, layer, w, pts in h['tracks']:
    ni = b.FindNet(net)
    if ni is None:
        raise SystemExit(f'unknown net {net}')
    for a, c in zip(pts, pts[1:]):
        if a == c:
            continue
        t = P.PCB_TRACK(b); t.SetLayer(L[layer]); t.SetNet(ni); t.SetWidth(MM(w))
        t.SetStart(P.VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(P.VECTOR2I(MM(c[0]), MM(c[1]))); t.SetLocked(True); b.Add(t); n += 1
for net, x, y in h['vias']:
    v = P.PCB_VIA(b); v.SetNet(b.FindNet(net)); v.SetPosition(P.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(0.55)); v.SetDrill(MM(0.3))
    v.SetLayerPair(L['F.Cu'], L['B.Cu']); v.SetLocked(True); b.Add(v); n += 1
b.Save(sys.argv[3]); print('hand copper items', n)
