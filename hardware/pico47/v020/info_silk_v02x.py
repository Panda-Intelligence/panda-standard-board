"""Add board-level printed information (product, revision, test-point names) to the silkscreen (KiCad Python).

usage: info_silk_v02x.py in.kicad_pcb spec.json out.kicad_pcb
spec: {"texts": [{"text": str, "layer": "F"|"B", "x": mm, "y": mm, "h": mm, "w": line mm, "justify": ...},
                 {"text": str, "layer": "B", "near": "TP3", "h": 1.0},
                 {"text": str, "layer": "B", "area": [x0, y0, x1, y1]}, ...]}
A text with "near" is put next to that footprint: the first of the positions around it (sides, then corners, at
0.3 / 0.8 / 1.4 mm) whose box keeps
0.15 mm from pads, holes, other footprints' courtyards on that side, earlier texts and 0.3 mm from the
board edge. Fixed texts are checked the same way. Text on B.SilkS is mirrored. Any text that does not fit
is reported and left out (exit code 1).
"""
import json
import sys

import pcbnew as P

MM, TO = P.FromMM, P.ToMM
CLR, EDGE_CLR = 0.15, 0.3
board = P.LoadBoard(sys.argv[1])
spec = json.load(open(sys.argv[2]))
LAYER = {'F': P.F_SilkS, 'B': P.B_SilkS}
CU = {'F': P.F_Cu, 'B': P.B_Cu}
CRT = {'F': P.F_CrtYd, 'B': P.B_CrtYd}
JUST = {'left': P.GR_TEXT_H_ALIGN_LEFT, 'center': P.GR_TEXT_H_ALIGN_CENTER, 'right': P.GR_TEXT_H_ALIGN_RIGHT}

for d in list(board.GetDrawings()):                    # re-runnable: drop texts this spec owns
    if d.GetClass() == 'PCB_TEXT' and d.GetText() in {t['text'] for t in spec['texts']}:
        board.Remove(d)


def rect(bb, grow=0.0):
    return (TO(bb.GetX()) - grow, TO(bb.GetY()) - grow, TO(bb.GetRight()) + grow, TO(bb.GetBottom()) + grow)


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


obst = {'F': [], 'B': []}
for fp in board.GetFootprints():
    for pad in fp.Pads():
        for s in 'FB':
            if pad.IsOnLayer(CU[s]) or pad.GetDrillSizeX() > 0:
                obst[s].append((fp.GetReference(), rect(pad.GetBoundingBox(), CLR)))
    for s in 'FB':
        for g in fp.GraphicalItems():
            if g.GetLayer() == CRT[s]:
                obst[s].append((fp.GetReference(), rect(g.GetBoundingBox(), 0.0)))
edge = board.GetBoardEdgesBoundingBox()
outline = P.SHAPE_POLY_SET()
board.GetBoardPolygonOutlines(outline, True)


def inside(r):
    for x, y in ((r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])):
        p = P.VECTOR2I(MM(x), MM(y))
        if not outline.Contains(p) or outline.COutline(0).SquaredDistance(p, True) < MM(EDGE_CLR) ** 2:
            return False
    return True


def make(t, x, y, just):
    g = P.PCB_TEXT(board)
    g.SetText(t['text'])
    g.SetLayer(LAYER[t['layer']])
    h = t.get('h', 1.0)
    g.SetTextSize(P.VECTOR2I(MM(h), MM(h)))
    g.SetTextThickness(MM(t.get('w', 0.15)))
    g.SetHorizJustify(JUST[just])
    g.SetVertJustify(P.GR_TEXT_V_ALIGN_CENTER)
    g.SetPosition(P.VECTOR2I(MM(x), MM(y)))
    if t['layer'] == 'B':
        g.SetMirrored(True)
    return g


def fits(g, side, ignore=None):
    r = rect(g.GetBoundingBox())
    if not inside(r):
        return False
    return not any(hit(r, o) for ref, o in obst[side] if ref != ignore)


failed = []
for t in spec['texts']:
    side = t['layer']
    if 'near' in t:
        fp = board.FindFootprintByReference(t['near'])
        b = rect(fp.GetBoundingBox(False, False))
        cx, cy, h = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, t.get('h', 1.0)
        cands = []
        for gap in (0.3, 0.8, 1.4):
            cands += [(b[2] + gap, cy, 'left'), (b[0] - gap, cy, 'right'), (cx, b[1] - gap - h / 2, 'center'),
                      (cx, b[3] + gap + h / 2, 'center'), (b[2] + gap, b[1] - gap, 'left'), (b[0] - gap, b[1] - gap, 'right'),
                      (b[2] + gap, b[3] + gap, 'left'), (b[0] - gap, b[3] + gap, 'right')]
        if side == 'B':                         # mirrored: left/right justification runs the other way
            cands = [(x, y, {'left': 'right', 'right': 'left'}.get(j, j)) for x, y, j in cands]
        g = next((g for g in (make(t, *c) for c in cands) if fits(g, side, t['near'])), None)
    elif 'area' in t:                               # first fitting spot in the area, scanned row by row
        x0, y0, x1, y1 = t['area']
        g = None
        for j in range(int((y1 - y0) / 0.25) + 1):
            for i in range(int((x1 - x0) / 0.5) + 1):
                c = make(t, x0 + 0.5 * i, y0 + 0.25 * j, 'center')
                if fits(c, side):
                    g = c
                    break
            if g:
                break
    else:
        g = make(t, t['x'], t['y'], t.get('justify', 'center'))
        g = g if fits(g, side) else None
    if g is None:
        failed.append(t['text'])
        continue
    board.Add(g)
    obst[side].append(('_text', rect(g.GetBoundingBox(), CLR)))
board.Save(sys.argv[3])
print('silkscreen info texts', len(spec['texts']) - len(failed), 'placed; not placed:', failed)
sys.exit(1 if failed else 0)
