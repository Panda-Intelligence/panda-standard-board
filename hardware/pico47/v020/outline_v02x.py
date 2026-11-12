"""Board outline helpers for the v0.2.x scripts.

An outline is a list of corner points [x, y] (device-cavity mm, y down). An entry may instead be
{"arc": [cx, cy, r, a0, a1]}: a circular arc from angle a0 to a1 (degrees, measured in the y-down
frame, so 90 points to +y). Arcs join the neighbouring points with straight edges.
"""
import math


def arc_points(cx, cy, r, a0, a1, step=0.25):
    n = max(2, int(math.ceil(abs(math.radians(a1 - a0)) * r / step)))
    return [[cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))] for i in range(n + 1)]


def expand(outline, step=0.25):
    """Outline as a plain polygon (arcs sampled every `step` mm)."""
    pts = []
    for e in outline:
        if isinstance(e, dict):
            pts += arc_points(*e['arc'], step=step)
        else:
            pts.append(list(e))
    return pts


def edges(outline):
    """Edge.Cuts primitives: ('line', a, b) and ('arc', start, mid, end), closed."""
    items = []
    for e in outline:
        if isinstance(e, dict):
            cx, cy, r, a0, a1 = e['arc']
            p = arc_points(cx, cy, r, a0, a1, step=1e9)
            am = math.radians((a0 + a1) / 2)
            items.append(('arc', p[0], [cx + r * math.cos(am), cy + r * math.sin(am)], p[-1]))
    pts = []
    for e in outline:
        if isinstance(e, dict):
            cx, cy, r, a0, a1 = e['arc']
            p = arc_points(cx, cy, r, a0, a1, step=1e9)
            pts.append(('arc_start', p[0]))
            pts.append(('arc_end', p[-1]))
        else:
            pts.append(('pt', list(e)))
    # straight edges between consecutive outline vertices, skipping the arc interiors
    for i in range(len(pts)):
        k0, a = pts[i]
        k1, b = pts[(i + 1) % len(pts)]
        if k0 == 'arc_start' and k1 == 'arc_end':
            continue
        if math.dist(a, b) > 1e-6:
            items.append(('line', a, b))
    return items
