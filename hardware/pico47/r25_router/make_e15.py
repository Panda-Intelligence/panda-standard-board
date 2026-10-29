"""E15 = E12 minus bare GND stitching vias inside the U710/U711 -> U501 routing corridor (they joined no pad or
track; the pours they stitched are re-checked for islands in the KiCad trial).
usage: make_e15.py geom-E12.json geom-E15.json
"""
import json, sys
g = json.load(open(sys.argv[1]))
DROP = [(57.0, 69.0), (57.0, 72.0), (57.0, 75.0), (60.0, 75.0), (58.7, 93.38)]
n0 = len(g['vias'])
g['vias'] = [v for v in g['vias'] if not (v['net'] == 'GND' and any(abs(v['x'] - x) < 0.02 and abs(v['y'] - y) < 0.02 for x, y in DROP))]
print('dropped', n0 - len(g['vias']), 'stitching vias')
json.dump(g, open(sys.argv[2], 'w'))
