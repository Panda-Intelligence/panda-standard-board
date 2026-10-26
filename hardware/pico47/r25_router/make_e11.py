"""E11 = E9b + fixed GND copper the router must respect (KiCad trial of E9b-77): a GND escape via for the
pour-fed FFC pin J601.34 and the debug-header GND pin J503.4, a stitching via for a pad-less pour island, and the C710 3V3_AON stub
straightened to clear C710.2 by 0.15 mm.
usage: make_e11.py geom-E9b.json geom-E11.json
"""
import json, sys, uuid
g = json.load(open(sys.argv[1]))
def via(x, y): g['vias'].append(dict(x=x, y=y, d=0.4, drill=0.2, net='GND', uuid='e11-' + str(uuid.uuid4())))
def trk(x1, y1, x2, y2, w, ly, net): g['tracks'].append(dict(x1=x1, y1=y1, x2=x2, y2=y2, w=w, layer=ly, net=net, uuid='e11-' + str(uuid.uuid4())))
via(45.45, 102.95); trk(44.8, 102.95, 45.45, 102.95, 0.2, 'F.Cu', 'GND')
via(34.45, 124.6)
via(51.975, 98.215); trk(52.0, 98.865, 51.975, 98.215, 0.25, 'B.Cu', 'GND')      # J503.4 own escape (pour pocket closes)
n0 = len(g['tracks'])
g['tracks'] = [t for t in g['tracks'] if not (t['net'] == '3V3_AON' and t['layer'] == 'F.Cu' and abs(t['w'] - 0.35) < 1e-6
               and min(t['x1'], t['x2']) >= 60.999 and max(t['x1'], t['x2']) <= 61.626
               and min(t['y1'], t['y2']) >= 83.52 and max(t['y1'], t['y2']) <= 83.951)]
print('C710 stub segments replaced:', n0 - len(g['tracks']))
trk(61.0, 83.525, 61.625, 83.95, 0.35, 'F.Cu', '3V3_AON')
json.dump(g, open(sys.argv[2], 'w'))
