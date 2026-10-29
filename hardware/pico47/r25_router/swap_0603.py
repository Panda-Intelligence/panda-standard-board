"""Give C501 and C525 a 0603 land pattern (pads and courtyard copied from C511) in a geometry and a courtyard
file, keeping each part's centre, orientation and pad nets. Study/ECO helper for the 22uF 0805 -> 0603 change.
Pad centres follow the part's own pad axis scaled to the 0603 pitch; pad and courtyard shapes are turned by the
pose difference (a multiple of 90 degrees).
usage: swap_0603.py geom.json courtyards.json out_geom.json out_courtyards.json
"""
import copy, json, math, sys
g = json.load(open(sys.argv[1])); cy = json.load(open(sys.argv[2]))
TEMPLATE, PARTS = 'C511', ('C501', 'C525')
tpl = {p['num']: p for p in g['pads'] if p['ref'] == TEMPLATE}
t0 = cy[TEMPLATE]
half = math.hypot(tpl['1']['x'] - t0['x'], tpl['1']['y'] - t0['y'])
def turn(x, y, k):          # rotate (x, y) by k quarter turns
    for _ in range(k % 4):
        x, y = -y, x
    return x, y
for ref in PARTS:
    c = cy[ref]
    k = int(round((c['rot'] - t0['rot']) / 90.0))
    old = {p['num']: p for p in g['pads'] if p['ref'] == ref}
    for i, p in enumerate(g['pads']):
        if p['ref'] != ref:
            continue
        ux, uy = p['x'] - c['x'], p['y'] - c['y']; n = math.hypot(ux, uy)
        nx, ny = c['x'] + ux / n * half, c['y'] + uy / n * half
        t = tpl[p['num']]
        q = copy.deepcopy(t)
        q['polys'] = {ly: [[[nx + a, ny + b] for a, b in (turn(x - t['x'], y - t['y'], k) for x, y in ring)] for ring in rings]
                      for ly, rings in t['polys'].items()}
        q.update(ref=ref, num=p['num'], net=p['net'], x=nx, y=ny)
        g['pads'][i] = q
    nc = copy.deepcopy(c)
    nc['courtyard'] = {s: [[[c['x'] + a, c['y'] + b] for a, b in (turn(x - t0['x'], y - t0['y'], k) for x, y in ring)] for ring in rings]
                       for s, rings in t0['courtyard'].items()}
    for pd in nc['pads']:
        n = math.hypot(pd['dx'], pd['dy']); pd['dx'], pd['dy'] = pd['dx'] / n * half, pd['dy'] / n * half
    cy[ref] = nc
json.dump(g, open(sys.argv[3], 'w')); json.dump(cy, open(sys.argv[4], 'w'))
print('0603 land pattern for', PARTS)
