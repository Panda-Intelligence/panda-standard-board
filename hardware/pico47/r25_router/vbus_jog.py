"""Reroute the VBUS_USB In2 stretch between (64.8,99.6) and its via (55.25,106) at its own 0.35 mm width,
keeping the planned U501 escape vias free. In2 only, no new vias.
usage: vbus_jog.py geom.json escaped_geom.json spec.json out_geom.json out_record.json
  geom.json         - swapped geometry with the original VBUS copper
  escaped_geom.json - same plus injected escape copper (their vias are reserved)
"""
import json, sys, uuid
import numpy as np
from shapely.geometry import LineString, Point, Polygon
sys.path.insert(0, sys.path[0])
import router2 as R

g = json.load(open(sys.argv[1]))
ge = json.load(open(sys.argv[2]))
spec = json.load(open(sys.argv[3]))
A, B = (64.8, 99.6), (55.25, 106.0)
WV = 0.35
L2 = R.LAYERS.index('In2.Cu')
route = set(spec['nets']) | set(R.TARGET)
old = [t for t in g['tracks'] if t['net'] == 'VBUS_USB' and t['layer'] == 'In2.Cu'
       and LineString([(t['x1'], t['y1']), (t['x2'], t['y2'])]).within(Polygon([(55.2, 99.5), (64.85, 99.5), (64.85, 106.05), (55.2, 106.05)]))]
ids = {t['uuid'] for t in old}
cv = R.Canvas()
r = R.CLR + WV / 2 + R.M
for t in g['tracks']:
    if t['layer'] == 'In2.Cu' and t['net'] not in route and t['uuid'] not in ids and t['net'] != 'VBUS_USB':
        cv.geom(R.seg_geom(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2).buffer(r, 12))
for v in g['vias']:
    if v['net'] not in route and v['net'] != 'VBUS_USB':
        cv.geom(Point(v['x'], v['y']).buffer(max(v['d'] / 2 + r, v['drill'] / 2 + R.HOLE_CLR + WV / 2 + R.M), 24))
for p in g['pads']:
    for ly, q in p['polys'].items():
        if ly == 'In2.Cu' and p['net'] != 'VBUS_USB':
            cv.geom(Polygon(q[0]).buffer(r, 12))
    if p['drill']:
        cv.geom(Point(p['x'], p['y']).buffer(max(p['drill']) / 2 + R.HOLE_CLR + WV / 2 + R.M, 24))
esc_vias = [v for v in ge['vias'] if v['uuid'] in set(json.load(open(sys.argv[3].replace('.json', '.json')))['keep_uuids'])] \
    if 'keep_uuids' in spec else []
for v in ge['vias']:
    if v['uuid'] in set(spec.get('keep_uuids', [])) and v['net'] != 'VBUS_USB':
        cv.geom(Point(v['x'], v['y']).buffer(v['d'] / 2 + r, 24))
for kb in spec.get('vbus_keepout', []):
    cv.geom(R.box(*kb).buffer(WV / 2 + R.CLR, 8))      # leave room for the U501 bottom-row escapes
board = Polygon(g['outline'][0])
cv.geom(R.box(R.X0 - 5, R.Y0 - 5, R.X1 + 5, R.Y1 + 5).difference(board.buffer(-(R.EDGE + WV / 2 + R.M))))
blk2 = cv.arr().reshape(-1)
blk = np.ones(R.NL * R.NLAYER, np.uint8)
blk[L2 * R.NLAYER:(L2 + 1) * R.NLAYER] = blk2
vblk = np.ones(R.NLAYER, np.uint8)
zero = np.zeros(R.NL * R.NLAYER, np.int32); zv = np.zeros(R.NLAYER, np.int32)
s = np.array([L2 * R.NLAYER + R.cell(*A)], np.int32)
goal = np.zeros(R.NL * R.NLAYER, np.uint8); goal[L2 * R.NLAYER + R.cell(*B)] = 1
print('start blocked', blk[s[0]], 'goal blocked', blk[L2 * R.NLAYER + R.cell(*B)])
blk[s[0]] = 0; blk[L2 * R.NLAYER + R.cell(*B)] = 0
out = np.zeros(1_000_000, np.int32)
gx = np.array([(B[0] - R.X0) / R.PITCH]); gy = np.array([(B[1] - R.Y0) / R.PITCH]); gr = np.array([0.0])
lc = np.array(R.LCOST, np.int32)
L = R.LIB.astar(R.NX, R.NY, R.NL, blk.ctypes.data_as(R.P8), vblk.ctypes.data_as(R.P8), zero.ctypes.data_as(R.P32),
                zv.ctypes.data_as(R.P32), lc.ctypes.data_as(R.P32), R.VIA_COST, s.ctypes.data_as(R.P32), 1,
                goal.ctypes.data_as(R.P8), gx.ctypes.data_as(R.PD), gy.ctypes.data_as(R.PD), gr.ctypes.data_as(R.PD), 1,
                out.ctypes.data_as(R.P32), len(out), 50_000_000, R.BEND_COST)
if L <= 0:
    sys.exit('no VBUS path')
path = out[:L][::-1].tolist()
tr, vi = R.path_to_copper(path, None, None)
assert not vi
oldlen = sum(LineString([(t['x1'], t['y1']), (t['x2'], t['y2'])]).length for t in old)
newlen = sum(LineString([(t[1], t[2]), (t[3], t[4])]).length for t in tr)
print(f'old {len(old)} segs {oldlen:.2f} mm -> new {len(tr)} segs {newlen:.2f} mm')
for gg in (g, ge):
    gg['tracks'] = [t for t in gg['tracks'] if t['uuid'] not in ids]
    for ly, x1, y1, x2, y2 in tr:
        gg['tracks'].append(dict(x1=x1, y1=y1, x2=x2, y2=y2, w=WV, layer=ly, net='VBUS_USB', uuid='vbus-' + str(uuid.uuid4())))
json.dump(ge, open(sys.argv[4], 'w'))
json.dump(dict(removed=sorted(ids), added=tr, width=WV, old_len=oldlen, new_len=newlen), open(sys.argv[5], 'w'), indent=1)
