"""Add three 1 mm fiducials (2 mm mask opening) for pick-and-place (KiCad Python).
usage: fiducials_v023.py in.kicad_pcb out.kicad_pcb
For each of three board corners, takes the free spot nearest the corner: 1.3 mm clear of front copper pads, tracks and
courtyards, 2.5 mm from the board edge. A round keep-out stops the copper pour inside the mask opening.
The footprints are board-only (not in the schematic, BOM or placement file)."""
import math, sys
import pcbnew as P
MM, T = P.FromMM, P.ToMM
LIB = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Fiducial.pretty'
b = P.LoadBoard(sys.argv[1])
for fp in list(b.GetFootprints()):
    if fp.GetReference().startswith('FID'):
        b.Remove(fp)
for z in list(b.Zones()):
    if z.GetZoneName().startswith('FID'):
        b.Remove(z)
bb = b.GetBoardEdgesBoundingBox(); X0, Y0, X1, Y1 = T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())
outline = P.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(outline, True)
rects = []
for fp in b.GetFootprints():
    if not fp.IsFlipped():
        r = fp.GetBoundingBox(False, False); rects.append((T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom())))
    for p in fp.Pads():
        if p.GetDrillSizeX() > 0:
            r = p.GetBoundingBox(); rects.append((T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom())))
segs = [(T(t.GetStart().x), T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y), T(t.GetWidth()) / 2) for t in b.GetTracks()
        if t.GetClass() != 'PCB_VIA' and t.GetLayer() == P.F_Cu]
vias = [(T(t.GetPosition().x), T(t.GetPosition().y)) for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']


def dseg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1; l2 = dx * dx + dy * dy
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / l2)) if l2 else 0
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)


def free(x, y, r=1.3, edge=2.5):
    pt = P.VECTOR2I(MM(x), MM(y))
    if not outline.Contains(pt) or outline.COutline(0).SquaredDistance(pt, True) < MM(edge) ** 2:
        return False
    if any(a - r < x < c + r and bq - r < y < d + r for a, bq, c, d in rects):
        return False
    if any(dseg(x, y, a, bq, c, d) < r + w for a, bq, c, d, w in segs):
        return False
    return not any(math.hypot(x - vx, y - vy) < r + 0.3 for vx, vy in vias)


placed = []
for i, (cx, cy) in enumerate(((X0, Y0), (X1, Y0), (X0, Y1))):
    best = None
    for gx in range(int((X1 - X0) / 0.25)):
        for gy in range(int((Y1 - Y0) / 0.25)):
            x, y = X0 + gx * 0.25, Y0 + gy * 0.25
            d = math.hypot(x - cx, y - cy)
            if (best is None or d < best[0]) and all(math.hypot(x - px, y - py) > 15 for px, py in placed) and free(x, y):
                best = (d, x, y)
    if best is None:
        print('no free spot near corner', i); continue
    _, x, y = best
    fp = P.FootprintLoad(LIB, 'Fiducial_1mm_Mask2mm')
    fp.SetReference(f'FID{i + 1}'); fp.SetValue('Fiducial'); fp.SetPosition(P.VECTOR2I(MM(x), MM(y)))
    fp.SetAttributes(P.FP_BOARD_ONLY | P.FP_EXCLUDE_FROM_POS_FILES | P.FP_EXCLUDE_FROM_BOM | P.FP_SMD)
    for f in fp.GetFields():
        f.SetVisible(False)
    b.Add(fp)
    z = P.ZONE(b); z.SetIsRuleArea(True); z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False); z.SetLayer(P.F_Cu); z.SetZoneName(f'FID{i + 1} keep-out')
    ch = P.SHAPE_LINE_CHAIN()
    for k in range(24):
        ch.Append(MM(x + 1.1 * math.cos(2 * math.pi * k / 24)), MM(y + 1.1 * math.sin(2 * math.pi * k / 24)))
    ch.SetClosed(True); z.Outline().AddOutline(ch); b.Add(z)
    placed.append((x, y)); print(f'FID{i + 1} at {x:.2f}, {y:.2f}')
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
