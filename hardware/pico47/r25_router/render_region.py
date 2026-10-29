"""Render a board region of a final geometry to PNG (F red, In2 green, B blue, pads grey, labels refs).
usage: render_region.py geom.json x0 y0 x1 y1 out.png [scale_px_per_mm] [highlight_net ...]
"""
import json, sys
from PIL import Image, ImageDraw
g = json.load(open(sys.argv[1])); x0, y0, x1, y1 = map(float, sys.argv[2:6]); out = sys.argv[6]
k = float(sys.argv[7]) if len(sys.argv) > 7 else 40; hl = set(sys.argv[8:])
im = Image.new('RGB', (int((x1 - x0) * k), int((y1 - y0) * k)), 'white'); d = ImageDraw.Draw(im, 'RGBA')
P = lambda x, y: ((x - x0) * k, (y - y0) * k)
col = {'F.Cu': (220, 40, 40, 150), 'In2.Cu': (40, 170, 40, 150), 'B.Cu': (40, 80, 230, 150)}
for p in g['pads']:
    for ly, q in p['polys'].items():
        if ly in ('F.Cu', 'B.Cu') and len(q[0]) > 2:
            d.polygon([P(*pt) for pt in q[0]], fill=(120, 120, 120, 120) if p['net'] != 'GND' else (230, 200, 60, 160))
for t in g['tracks']:
    if t['layer'] in col:
        c = (0, 0, 0, 255) if t['net'] in hl else col[t['layer']]
        d.line([P(t['x1'], t['y1']), P(t['x2'], t['y2'])], fill=c, width=max(1, int(t['w'] * k)))
for v in g['vias']:
    x, y = P(v['x'], v['y']); r = v['d'] / 2 * k
    d.ellipse([x - r, y - r, x + r, y + r], fill=(0, 0, 0, 200) if v['net'] in hl else (160, 120, 0, 200))
refs = {}
for p in g['pads']:
    refs.setdefault(p['ref'], []).append((p['x'], p['y']))
for r, pts in refs.items():
    cx = sum(a for a, _ in pts) / len(pts); cy = sum(b for _, b in pts) / len(pts)
    if x0 < cx < x1 and y0 < cy < y1:
        d.text(P(cx, cy), r, fill=(0, 0, 0, 255))
for i in range(int(x0), int(x1) + 1):
    if i % 5 == 0: d.line([P(i, y0), P(i, y1)], fill=(0, 0, 0, 40)); d.text(P(i, y0), str(i), fill=(0, 0, 0, 255))
for j in range(int(y0), int(y1) + 1):
    if j % 5 == 0: d.line([P(x0, j), P(x1, j)], fill=(0, 0, 0, 40)); d.text(P(x0, j), str(j), fill=(0, 0, 0, 255))
im.save(out)
