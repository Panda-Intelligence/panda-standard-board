"""Hand-layout helper for v0.2.3 (plain Python + shapely).

A Design holds part poses and hand-drawn copper (tracks, vias). Pads are addressed as "REF.PIN"; a track is a list of
pad names or [x, y] points. check() reports clearance problems between hand copper, pads and part bodies; svg() draws a
preview; export() writes poses and copper for the placer and the board builder. Device-cavity mm, y down.
KiCad rotation convention: world = (x + lx cos a + ly sin a, y - lx sin a + ly cos a).
"""
import json
import math

from shapely.geometry import LineString, Point, box

CLR = 0.127


class Design:
    def __init__(self, padlib, sizes):
        self.lib = json.load(open(padlib))
        self.sizes = json.load(open(sizes))
        self.pose = {}
        self.tracks = []        # (net, layer, width, [(x, y), ...])
        self.vias = []          # (net, x, y)
        self.keepouts = []      # (x0, y0, x1, y1) on F for the placer

    def place(self, ref, x, y, rot=0):
        self.pose[ref] = (x, y, rot)

    def load_others(self, placement):
        """Parts placed by the placer: their pads take part in the copper checks, but they are not exported."""
        self.hand = set(self.pose)
        for ref, v in json.load(open(placement))['parts'].items():
            if ref not in self.pose:
                self.pose[ref] = (v[0], v[1], v[2])

    def raw(self, tracks, vias):
        for net, layer, w, pts in tracks:
            self.tracks.append((net, layer, w, [tuple(p) for p in pts]))
        for v in vias:
            self.vias.append(tuple(v))

    def _tf(self, ref, lx, ly):
        x, y, rot = self.pose[ref]
        a = math.radians(rot)
        return x + lx * math.cos(a) + ly * math.sin(a), y - lx * math.sin(a) + ly * math.cos(a)

    def pads(self, ref):
        rot = self.pose[ref][2]
        out = []
        for num, lx, ly, w, h, drill, net, side in self.lib[ref]['pads']:
            x, y = self._tf(ref, lx, ly)
            if rot % 180 == 90:
                w, h = h, w
            out.append(dict(ref=ref, num=num, x=x, y=y, w=w, h=h, net=net, side=side, drill=drill))
        return out

    def pad(self, name):
        ref, num = name.split('.')
        ps = [p for p in self.pads(ref) if p['num'] == num]
        return ps[0]

    def pt(self, p):
        if isinstance(p, str):
            q = self.pad(p)
            return (q['x'], q['y'])
        return (float(p[0]), float(p[1]))

    def track(self, net, width, pts, layer='F.Cu'):
        self.tracks.append((net, layer, width, [self.pt(p) for p in pts]))

    def via(self, net, x, y):
        self.vias.append((net, x, y))

    def body(self, ref):
        b = self.sizes[ref]['bbox']
        cs = [self._tf(ref, lx, ly) for lx, ly in ((b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3]))]
        return box(min(c[0] for c in cs), min(c[1] for c in cs), max(c[0] for c in cs), max(c[1] for c in cs))

    def check(self):
        issues = []
        refs = list(self.pose)
        hand = sorted(getattr(self, 'hand', refs))
        hand = [r for r in hand if self.lib[r]['pads'][0][7] != 'B']
        for i, a in enumerate(hand):
            for b in hand[i + 1:]:
                if self.body(a).intersection(self.body(b)).area > 1e-6:
                    issues.append(f'courtyard {a} / {b}')
        pads = [(p, box(p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)) for r in refs for p in self.pads(r)]
        cu = []
        for net, layer, w, pts in self.tracks:
            for a, b in zip(pts, pts[1:]):
                if a != b:
                    cu.append((net, layer, LineString([a, b]).buffer(w / 2), f'{net} {layer} ({a[0]:.2f},{a[1]:.2f})-({b[0]:.2f},{b[1]:.2f})'))
        for net, x, y in self.vias:
            for layer in ('F.Cu', 'In2.Cu', 'B.Cu'):
                cu.append((net, layer, Point(x, y).buffer(0.275), f'via {net} ({x:.2f},{y:.2f})'))
        for net, layer, g, desc in cu:
            for p, pg in pads:
                on = (layer == 'F.Cu' and p['side'] == 'F') or (layer == 'B.Cu' and p['side'] == 'B') or p['drill']
                if on and p['net'] != net and g.distance(pg) < CLR - 1e-6:
                    issues.append(f'{desc} vs pad {p["ref"]}.{p["num"]} [{p["net"]}] {g.distance(pg):.3f}')
            if desc.startswith('via'):
                for p, pg in pads:      # no via in a pad of the same net unless it is centred on purpose (thermal)
                    if p['net'] == net and p['side'] == 'F' and layer == 'F.Cu' and 0 < g.distance(pg) < 0.05:
                        issues.append(f'{desc} grazes own pad {p["ref"]}.{p["num"]}')
        for i, (n1, l1, g1, d1) in enumerate(cu):
            for n2, l2, g2, d2 in cu[i + 1:]:
                if n1 != n2 and l1 == l2 and g1.distance(g2) < CLR - 1e-6:
                    issues.append(f'{d1} vs {d2} {g1.distance(g2):.3f}')
        return issues

    def svg(self, path, x0, y0, x1, y1, k=40):
        o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{(x1 - x0) * k:.0f}" height="{(y1 - y0) * k:.0f}" style="background:white">']
        X = lambda x: (x - x0) * k
        Y = lambda y: (y - y0) * k
        col = {'F.Cu': '#c33', 'B.Cu': '#36c', 'In2.Cu': '#c90'}
        for r in self.pose:
            if self.lib[r]['pads'] and self.lib[r]['pads'][0][7] == 'B':
                continue
            b = self.body(r).bounds
            o.append(f'<rect x="{X(b[0]):.1f}" y="{Y(b[1]):.1f}" width="{(b[2] - b[0]) * k:.1f}" height="{(b[3] - b[1]) * k:.1f}" fill="none" stroke="#aaa"/>')
        for net, layer, w, pts in sorted(self.tracks, key=lambda t: t[1] != 'B.Cu'):
            d = ' '.join(f'{X(x):.1f},{Y(y):.1f}' for x, y in pts)
            o.append(f'<polyline points="{d}" fill="none" stroke="{col[layer]}" stroke-opacity="0.75" stroke-width="{w * k:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
        for r in self.pose:
            for p in self.pads(r):
                o.append(f'<rect x="{X(p["x"] - p["w"] / 2):.1f}" y="{Y(p["y"] - p["h"] / 2):.1f}" width="{p["w"] * k:.1f}" height="{p["h"] * k:.1f}" fill="#444" fill-opacity="0.8"/>')
                if p['w'] * k > 14 or p['h'] * k > 14:
                    o.append(f'<text x="{X(p["x"]):.1f}" y="{Y(p["y"]) + 3:.1f}" font-size="8" fill="white" text-anchor="middle" font-family="Helvetica">{p["net"][-7:]}</text>')
            b = self.body(r).bounds
            o.append(f'<text x="{X(b[0]) + 2:.1f}" y="{Y(b[1]) + 9:.1f}" font-size="10" fill="#060" font-family="Helvetica">{r}</text>')
        for net, x, y in self.vias:
            o.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{0.275 * k:.1f}" fill="#fc0" stroke="black"/>')
        o.append('</svg>')
        open(path, 'w').write('\n'.join(o))

    def export(self, path):
        keep = list(self.keepouts)
        for net, layer, w, pts in self.tracks:
            if layer == 'F.Cu':
                for a, b in zip(pts, pts[1:]):
                    keep.append([min(a[0], b[0]) - w / 2, min(a[1], b[1]) - w / 2, max(a[0], b[0]) + w / 2, max(a[1], b[1]) + w / 2])
        for net, x, y in self.vias:
            keep.append([x - 0.3, y - 0.3, x + 0.3, y + 0.3])
        hand = getattr(self, 'hand', set(self.pose))
        json.dump(dict(pose={r: list(v) for r, v in self.pose.items() if r in hand},
                       tracks=[[n, l, w, [list(p) for p in pts]] for n, l, w, pts in self.tracks],
                       vias=[list(v) for v in self.vias], keepout=keep), open(path, 'w'), indent=0)
