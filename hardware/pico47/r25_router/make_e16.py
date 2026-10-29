"""E16 = E15 with the J601.34 GND escape via moved to the connector's left side (44.225, 102.95), in line with
the pin 36/38 GND vias, so the lane right of the FFC pads stays open for P47_D11_SRC.
usage: make_e16.py geom-E15.json geom-E16.json
"""
import json, sys, uuid
g = json.load(open(sys.argv[1]))
v = next(v for v in g['vias'] if v['net'] == 'GND' and abs(v['x'] - 45.45) < .01 and abs(v['y'] - 102.95) < .01)
t = next(t for t in g['tracks'] if t['net'] == 'GND' and abs(t['y1'] - 102.95) < .01 and abs(t['x2'] - 45.45) < .01)
v['x'] = 44.225; t['x2'] = 44.225
json.dump(g, open(sys.argv[2], 'w'))
print('J601.34 via ->', v['x'], v['y'])
