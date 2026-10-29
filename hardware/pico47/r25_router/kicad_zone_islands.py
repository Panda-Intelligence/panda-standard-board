"""Report GND zone-fill islands that are not joined to the main GND copper cluster (KiCad board, after refill).
usage: kicad_zone_islands.py board.kicad_pcb [NET]
"""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); net = sys.argv[2] if len(sys.argv) > 2 else 'GND'
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
nodes, par = [], {}
def f(i):
    while par[i] != i:
        par[i] = par[par[i]]; i = par[i]
    return i
def add(x):
    nodes.append(x); par[len(nodes) - 1] = len(nodes) - 1; return len(nodes) - 1
def uni(a, c): par[f(a)] = f(c)
fills = []
for z in b.Zones():
    if z.GetNetname() != net: continue
    for ly in CU:
        if z.IsOnLayer(ly):
            ps = z.GetFilledPolysList(ly)
            for i in range(ps.OutlineCount()):
                sp = pcbnew.SHAPE_POLY_SET(); sp.AddOutline(ps.Outline(i))
                for h in range(ps.HoleCount(i)): sp.AddHole(ps.Hole(i, h))
                fills.append((add(('fill', ly, i)), ly, sp, ps.Outline(i).BBox()))
items = []
for t in b.GetTracks():
    if t.GetNetname() != net: continue
    n = add(('via' if t.GetClass() == 'PCB_VIA' else 'track', t.m_Uuid.AsString()))
    lys = CU if t.GetClass() == 'PCB_VIA' else [t.GetLayer()]
    items.append((n, lys, t.GetEffectiveShape()))
for p in b.GetPads():
    if p.GetNetname() != net: continue
    n = add(('pad', p.GetParentFootprint().GetReference() + '.' + p.GetNumber()))
    for ly in CU:
        if p.IsOnLayer(ly):
            items.append((n, [ly], p.GetEffectiveShape(ly)))
for n, lys, shp in items:
    for fn, ly, sp, bb in fills:
        if ly in lys and sp.Collide(shp, 0):
            uni(n, fn)
for i in range(len(items)):
    for j in range(i + 1, len(items)):
        a, c = items[i], items[j]
        if a[0] != c[0] and set(a[1]) & set(c[1]) and a[2].Collide(c[2], 0):
            uni(a[0], c[0])
groups = {}
for i in range(len(nodes)):
    groups.setdefault(f(i), []).append(i)
gs = sorted(groups.values(), key=len, reverse=True)
print(net, 'clusters', len(gs), [len(x) for x in gs[:6]])
for grp in gs[1:]:
    for i in grp:
        if nodes[i][0] == 'fill':
            bb = next(x[3] for x in fills if x[0] == i)
            print('  isolated', b.GetLayerName(nodes[i][1]), 'fill', nodes[i][2], 'bbox', bb.GetLeft() / 1e6, bb.GetTop() / 1e6, bb.GetRight() / 1e6, bb.GetBottom() / 1e6)
        else:
            print('  isolated', nodes[i])
