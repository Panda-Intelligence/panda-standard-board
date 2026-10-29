"""Find the existing U501 per-pin fanout copper (connected to the pad, within RADIUS of it).
Used to relabel escapes with swapped pins and to keep them out of the rip-up."""
from shapely.geometry import LineString, Point, Polygon

RADIUS = 1.3


def _shapes(item, kind):
    if kind == 't':
        g = LineString([(item['x1'], item['y1']), (item['x2'], item['y2'])]).buffer(item['w'] / 2) \
            if (item['x1'], item['y1']) != (item['x2'], item['y2']) else Point(item['x1'], item['y1']).buffer(item['w'] / 2)
        return {item['layer']: g}
    c = Point(item['x'], item['y']).buffer(item['d'] / 2)
    return {ly: c for ly in ('F.Cu', 'In2.Cu', 'B.Cu')}


def fanout(g, pad, net):
    """uuids of `net` copper reachable from `pad` without leaving the RADIUS disc around the pad centre."""
    centre = Point(pad['x'], pad['y'])
    disc = centre.buffer(RADIUS)
    items = [('t', t) for t in g['tracks'] if t['net'] == net] + [('v', v) for v in g['vias'] if v['net'] == net]
    items = [(k, it, _shapes(it, k)) for k, it in items]
    items = [x for x in items if all(s.within(disc) for s in x[2].values())]
    frontier = [{ly: Polygon(q[0]) for ly, q in pad['polys'].items() if len(q[0]) > 2}]
    found, seen = [], set()
    while frontier:
        cur = frontier.pop()
        for k, it, sh in items:
            if it['uuid'] in seen:
                continue
            if any(ly in cur and cur[ly].intersects(s) for ly, s in sh.items()):
                seen.add(it['uuid'])
                found.append(it['uuid'])
                frontier.append(sh)
    return found
