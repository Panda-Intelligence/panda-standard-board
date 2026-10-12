"""Conservative native plane stitching. Requires KiCad's pcbnew Python module."""
import math
import pcbnew as P


def stitch_reference_planes(board, outline):
    """Place GND vias outside component bodies and foreign-copper bounding boxes.

    This geometric prefilter is intentionally conservative. Native DRC must still
    run afterwards. No blind vias, rule changes, or exposed-pad ground vias.
    """
    def mm(p):
        return P.ToMM(p.x), P.ToMM(p.y)

    def box(item):
        b = item.GetBoundingBox()
        return [P.ToMM(b.GetX()), P.ToMM(b.GetY()),
                P.ToMM(b.GetRight()), P.ToMM(b.GetBottom())]

    def inside(x, y):
        odd = False
        for (ax, ay), (bx, by) in zip(outline, outline[1:] + outline[:1]):
            if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
                odd = not odd
        return odd

    def edge_distance(x, y):
        ds = []
        for (ax, ay), (bx, by) in zip(outline, outline[1:] + outline[:1]):
            dx, dy = bx-ax, by-ay
            if dx == 0 and dy == 0:
                raise ValueError('Zero-length outline edge')
            q = min(1, max(0, ((x-ax)*dx + (y-ay)*dy) / (dx*dx + dy*dy)))
            ds.append(math.hypot(x-ax-q*dx, y-ay-q*dy))
        return min(ds)

    barriers, occupied = [], []
    for fp in board.GetFootprints():
        b = fp.GetBoundingBox(False, False)
        barriers.append([P.ToMM(b.GetX()), P.ToMM(b.GetY()),
                         P.ToMM(b.GetRight()), P.ToMM(b.GetBottom())])
    for t in board.GetTracks():
        if isinstance(t, P.PCB_VIA):
            occupied.append(mm(t.GetPosition()))
        if str(t.GetNetname()) != 'GND':
            barriers.append(box(t))
    xmin, ymin = min(p[0] for p in outline), min(p[1] for p in outline)
    xmax, ymax = max(p[0] for p in outline), max(p[1] for p in outline)
    candidates = [(round(xmin+1+i*3, 4), round(ymin+1+j*3, 4))
                  for j in range(int((ymax-ymin-1)/3)+1)
                  for i in range(int((xmax-xmin-1)/3)+1)]
    candidates.sort(key=lambda q: edge_distance(*q))
    coords = []
    limit = 18 if xmax-xmin < 40 else 28
    ground = board.FindNet('GND')
    if ground is None:
        raise ValueError('Missing GND net')
    for x, y in candidates:
        if len(coords) >= limit:
            break
        if not inside(x, y) or edge_distance(x, y) < .65:
            continue
        if any(a-.60 <= x <= c+.60 and b-.60 <= y <= d+.60 for a, b, c, d in barriers):
            continue
        if any(math.hypot(x-a, y-b) < 3 for a, b in occupied+coords):
            continue
        via = P.PCB_VIA(board)
        via.SetViaType(P.VIATYPE_THROUGH)
        via.SetPosition(P.VECTOR2I(P.FromMM(x), P.FromMM(y)))
        via.SetWidth(P.FromMM(.65))
        via.SetDrill(P.FromMM(.30))
        via.SetLayerPair(P.F_Cu, P.B_Cu)
        board.Add(via)
        via.SetNet(ground)
        coords.append((x, y))
    return coords
