"""Relabel pad nets in an exported geometry according to a pin-swap assignment; emit the pad-net map.
usage: apply_pinswap_geom.py geom.json design.json pinswap.json out_geom.json out_padmap.json
Each mux channel keeps its common-net name P47_MUX<ch>; the channel's S0/S1 pins and the U501 GPIO
pins take the newly assigned nets. Copper of every relabelled net must be rerouted.
"""
import json, sys
sys.path.insert(0, sys.path[0])
from u501_fanout import fanout

g = json.load(open(sys.argv[1]))
design = json.load(open(sys.argv[2]))
ps = json.load(open(sys.argv[3]))
gpio_pin = {int(k): v['package_pin'] for k, v in design['gpio'].items()}
padmap = {}
for ch, c in enumerate(ps['channels']):
    ref = c['part']
    s0, s1, cm = c['terminals']
    padmap[(ref, str(s0))] = c['select_0_net']
    padmap[(ref, str(s1))] = f"P47_D{c['display_bit']}_SRC"
    padmap[(ref, str(cm))] = f'P47_MUX{ch}'
    padmap[('U501', str(gpio_pin[c['gpio']]))] = f'P47_MUX{ch}'
for gp, bit in ps['direct'].items():
    padmap[('U501', str(gpio_pin[int(gp)]))] = f'P47_D{bit}_SRC'
changed = []
relabel_copper = {}
for p in g['pads']:
    k = (p['ref'], p['num'])
    if k in padmap and p['net'] != padmap[k]:
        changed.append(dict(ref=p['ref'], num=p['num'], old=p['net'], new=padmap[k]))
        if p['ref'] == 'U501':   # the pin's existing escape follows the pin to its new net
            for u in fanout(g, p, p['net']):
                relabel_copper[u] = padmap[k]
        p['net'] = padmap[k]
for t in g['tracks'] + g['vias']:
    if t['uuid'] in relabel_copper:
        t['net'] = relabel_copper[t['uuid']]
# every net must still have exactly its original pad count (pure permutation)
from collections import Counter
before = Counter(p['net'] for p in json.load(open(sys.argv[1]))['pads'])
after = Counter(p['net'] for p in g['pads'])
assert before == after, {n: (before[n], after[n]) for n in set(before) | set(after) if before[n] != after[n]}
json.dump(g, open(sys.argv[4], 'w'))
json.dump(dict(changed=changed, relabel_copper=relabel_copper, relabelled_nets=sorted({c['old'] for c in changed} | {c['new'] for c in changed})),
          open(sys.argv[5], 'w'), indent=1)
print(len(changed), 'pads relabelled;', len(relabel_copper), 'escape copper items relabelled;', len({c['new'] for c in changed}), 'nets affected')
