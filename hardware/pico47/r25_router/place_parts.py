"""Place removed passives back onto a finalized geometry without disturbing existing copper.

For each part (in order) every 0.1 mm / 90-degree pose within RADIUS of its original position is tested:
courtyard must not overlap other courtyards, pads must clear all other-net copper by CLR and stay off the
board-edge keepout. Score = sum over pads of the distance to the nearest same-net copper (GND pads: to the
nearest legal via site) plus a small displacement penalty and an optional anchor pull.
usage: place_parts.py final_geom.json courtyards.json orig_geom.json parts.json out_geom.json out_moves.json [orig_courtyards.json]
(courtyards.json: current courtyards of the other parts; orig_courtyards.json: r24 frame matching orig_geom pads)
parts.json: [{"ref": "R606", "anchor": [x, y] (optional), "radius": 8}, ...]
"""
import json, sys, math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point
from shapely import affinity
from shapely.strtree import STRtree
from shapely.ops import unary_union

CLR, EDGE, VIA_D = 0.15, 0.2, 0.4
g = json.load(open(sys.argv[1]))
cy = json.load(open(sys.argv[2]))
orig = json.load(open(sys.argv[3]))
parts = json.load(open(sys.argv[4]))
out_geom, out_moves = sys.argv[5], sys.argv[6]
board = Polygon(g['outline'][0]).buffer(-EDGE)
placing = {p['ref'] for p in parts}
# copper of everything currently on the board, per layer, with its net
items = []
for t in g['tracks']:
    s = LineString([(t['x1'], t['y1']), (t['x2'], t['y2'])]).buffer(t['w'] / 2, 8) if (t['x1'], t['y1']) != (t['x2'], t['y2']) \
        else Point(t['x1'], t['y1']).buffer(t['w'] / 2, 8)
    items.append((t['layer'], t['net'], s))
for v in g['vias']:
    for ly in ('F.Cu', 'In2.Cu', 'B.Cu'):
        items.append((ly, v['net'], Point(v['x'], v['y']).buffer(v['d'] / 2, 16)))
for p in g['pads']:
    for ly, q in p['polys'].items():
        if len(q[0]) > 2:
            items.append((ly, p['net'], Polygon(q[0])))
F_items = [(n, s) for ly, n, s in items if ly == 'F.Cu']
tree = STRtree([s for n, s in F_items])
cy_polys = {ref: Polygon(v['courtyard']['F'][0]) for ref, v in cy.items()
            if ref not in placing and v['side'] == 'F' and v['courtyard'].get('F')}
cy_tree_refs = list(cy_polys)
cy_tree = STRtree([cy_polys[r] for r in cy_tree_refs])
# drilled holes (PTH and NPTH) of other footprints may not sit inside a courtyard (npth/pth_inside_courtyard)
holes = [Point(p['x'], p['y']).buffer(max(p['drill']) / 2, 16) for p in g['pads'] if p['drill'] and p['ref'] not in placing]
net_shapes = {}
for ly, n, s in items:
    net_shapes.setdefault(n, []).append(s)
net_union = {n: unary_union(v) for n, v in net_shapes.items()}
gnd_vias = [Point(v['x'], v['y']) for v in g['vias'] if v['net'] == 'GND']


def legal_via(x, y, placed_shapes):
    c = Point(x, y).buffer(VIA_D / 2, 16)
    if not c.within(board.buffer(-VIA_D / 2)):
        return False
    for ly, n, s in items:
        pass
    q = c.buffer(CLR)
    for i in tree.query(q):
        n, s = F_items[i]
        if n != 'GND' and s.intersects(q):
            return False
    for ly, n, s in items:
        if ly in ('In2.Cu', 'B.Cu') and n != 'GND' and s.intersects(q):
            return False
    for s, n in placed_shapes:
        if n != 'GND' and s.intersects(q):
            return False
    return True


moves = {}
placed_extra = []   # (shape, net) of pads placed in this run
fp_pads = {}
for p in orig['pads']:
    fp_pads.setdefault(p['ref'], []).append(p)
cy_r24 = json.load(open(sys.argv[7])) if len(sys.argv) > 7 else cy   # the placed part's own frame must match orig pads
for spec in parts:
    ref = spec['ref']
    info = cy_r24[ref]
    ox, oy, orot = info['x'], info['y'], info['rot']
    court = Polygon(info['courtyard']['F'][0])
    pads = fp_pads[ref]
    best = None
    R = spec.get('radius', 8.0)
    cx0, cy0 = spec.get('center', (ox, oy))      # search around a target (e.g. the IC pin it serves)
    anchor = spec.get('anchor')
    for drot in (0, 90, 180, 270):
        c_rot = affinity.rotate(court, -drot, origin=(ox, oy))
        p_rot = [(pd, affinity.rotate(Polygon(pd['polys']['F.Cu'][0]), -drot, origin=(ox, oy))) for pd in pads]
        for ddx in np.arange(-R, R + 1e-9, 0.1):
            for ddy in np.arange(-R, R + 1e-9, 0.1):
                if ddx * ddx + ddy * ddy > R * R:
                    continue
                dx, dy = cx0 - ox + ddx, cy0 - oy + ddy
                cpoly = affinity.translate(c_rot, dx, dy)
                if not cpoly.within(board.buffer(EDGE)):
                    continue
                if any(cy_polys[cy_tree_refs[i]].intersects(cpoly) and cy_polys[cy_tree_refs[i]].intersection(cpoly).area > 1e-4
                       for i in cy_tree.query(cpoly)):
                    continue
                if any(s.intersects(cpoly) for s, n in placed_extra if s.geom_type == 'Polygon' and n == '__court__'):
                    continue
                if any(h.intersects(cpoly) for h in holes):
                    continue
                ok = True
                score = 0.0
                shapes = []
                for pd, pp in p_rot:
                    sh = affinity.translate(pp, dx, dy)
                    if not sh.within(board):
                        ok = False; break
                    q = sh.buffer(CLR)
                    for i in tree.query(q):
                        n, s = F_items[i]
                        if n != pd['net'] and s.intersects(q):
                            ok = False; break
                    if not ok:
                        break
                    if any(n != pd['net'] and s.intersects(q) for s, n in placed_extra if n != '__court__'):
                        ok = False; break
                    shapes.append((pd, sh))
                    if pd['net'] == 'GND':
                        score += 0.4
                    else:
                        u = net_union.get(pd['net'])
                        score += sh.distance(u) if u is not None else 10.0
                if not ok:
                    continue
                score += 0.05 * math.hypot(dx, dy)
                if anchor:
                    cx = sum(sh.centroid.x for _, sh in shapes) / len(shapes); cyy = sum(sh.centroid.y for _, sh in shapes) / len(shapes)
                    score += spec.get('anchor_weight', 0.5) * math.hypot(cx - anchor[0], cyy - anchor[1])
                if best is None or score < best[0]:
                    best = (score, drot, dx, dy, shapes, cpoly)
    if best is None:
        print(f'{ref}: NO LEGAL POSE within {R} mm', flush=True)
        continue
    score, drot, dx, dy, shapes, cpoly = best
    moves[ref] = dict(x=round(ox + dx, 4), y=round(oy + dy, 4), rot=(orot + drot) % 360, drot=drot, score=round(score, 3))
    for pd, sh in shapes:
        placed_extra.append((sh, pd['net']))
        newp = dict(pd)
        newp['polys'] = {'F.Cu': [list(map(list, sh.exterior.coords))]}
        newp['x'], newp['y'] = sh.centroid.x, sh.centroid.y
        g['pads'].append(newp)
    placed_extra.append((cpoly, '__court__'))
    print(f'{ref}: placed at ({ox + dx:.2f},{oy + dy:.2f}) rot {(orot + drot) % 360:.0f} (moved {math.hypot(dx, dy):.2f} mm) score {score:.2f}', flush=True)
json.dump(g, open(out_geom, 'w'))
json.dump(moves, open(out_moves, 'w'), indent=1)
