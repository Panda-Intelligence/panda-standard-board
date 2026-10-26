"""Rebuild a Core board from r24 and a finalized geometry. Run with KiCad python.
usage: apply_final.py r24.kicad_pcb r24_geom.json final_geom.json moves.json out.kicad_pcb
  - pad nets follow final_geom (pin swap), footprints in moves.json get their new pose;
  - r24 copper absent from final_geom is deleted, r24 copper whose net changed is relabelled,
    copper with non-r24 uuids is added at its own width / via size.
"""
import json, sys
import pcbnew

src, g0p, gfp, movesp, dst = sys.argv[1:6]
b = pcbnew.LoadBoard(src)
g0 = json.load(open(g0p))
gf = json.load(open(gfp))
moves = json.load(open(movesp))
mm = pcbnew.FromMM
lay = {n: b.GetLayerID(n) for n in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')}
net = lambda name: b.FindNet(name)

# 1. footprint moves
for ref, m in moves.items():
    fp = b.FindFootprintByReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I(mm(m['x']), mm(m['y'])))
    fp.SetOrientationDegrees(m['rot'])
# 2. pad nets (by reference + number; final geometry is authoritative)
final_pad_net = {(p['ref'], p['num']): p['net'] for p in gf['pads']}
changed_pads = 0
for fp in b.GetFootprints():
    for pd in fp.Pads():
        k = (fp.GetReference(), pd.GetNumber())
        if k in final_pad_net and pd.GetNetname() != final_pad_net[k] and final_pad_net[k]:
            ni = net(final_pad_net[k])
            assert ni is not None, final_pad_net[k]
            pd.SetNet(ni)
            changed_pads += 1
# 3. copper delta
final = {t['uuid']: t for t in gf['tracks'] + gf['vias']}
removed = relabelled = 0
for t in list(b.GetTracks()):
    u = t.m_Uuid.AsString()
    if u not in final:
        b.Remove(t); removed += 1
    elif final[u]['net'] != t.GetNetname():
        t.SetNet(net(final[u]['net'])); relabelled += 1
r24 = {t['uuid'] for t in g0['tracks'] + g0['vias']}
added = 0
for t in gf['tracks']:
    if t['uuid'] in r24:
        continue
    tr = pcbnew.PCB_TRACK(b)
    tr.SetStart(pcbnew.VECTOR2I(mm(t['x1']), mm(t['y1'])))
    tr.SetEnd(pcbnew.VECTOR2I(mm(t['x2']), mm(t['y2'])))
    tr.SetWidth(mm(t['w']))
    tr.SetLayer(lay[t['layer']])
    tr.SetNet(net(t['net']))
    b.Add(tr); added += 1
for v in gf['vias']:
    if v['uuid'] in r24:
        continue
    via = pcbnew.PCB_VIA(b)
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetWidth(mm(v['d']))
    via.SetDrill(mm(v['drill']))
    via.SetPosition(pcbnew.VECTOR2I(mm(v['x']), mm(v['y'])))
    via.SetNet(net(v['net']))
    b.Add(via); added += 1
b.Save(dst)
print(json.dumps(dict(moved=len(moves), pad_net_changes=changed_pads, removed=removed, relabelled=relabelled, added=added)))
