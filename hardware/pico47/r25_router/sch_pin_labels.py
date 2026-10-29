"""Locate the global label attached to each pin of given symbols in a generated KiCad schematic, and
optionally rewrite label texts (pin-swap ECO).
usage: sch_pin_labels.py Core.kicad_sch REFS [newnets.json out.kicad_sch]
  without newnets: print ref.pin -> label text (verification);
  newnets.json: {"U501.13": "P47_MUX6", ...} rewrites exactly those labels and writes out.kicad_sch.
"""
import json, re, sys, math

sch = open(sys.argv[1]).read()
refs = sys.argv[2].split(',')


def balanced(s, i):
    d = 0
    for j in range(i, len(s)):
        if s[j] == '(':
            d += 1
        elif s[j] == ')':
            d -= 1
            if d == 0:
                return j + 1
    raise ValueError


lib = {}
i0 = sch.index('(lib_symbols')
lib_txt = sch[i0:balanced(sch, i0)]
for m in re.finditer(r'\(symbol "([^"]+)"', lib_txt):
    name = m.group(1)
    if name.count('_') >= 2 and re.search(r'_\d+_\d+$', name):
        continue
    blk = lib_txt[m.start():balanced(lib_txt, m.start())]
    pins = {}
    for pm in re.finditer(r'\(pin \w+ \w+ \(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\) \(length ([-\d.]+)\).*?\(number "([^"]+)"', blk, re.S):
        pins[pm.group(5)] = (float(pm.group(1)), float(pm.group(2)))
    lib[name] = pins
inst = {}
for m in re.finditer(r'\(symbol\s*\(lib_id "([^"]+)"\)\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)', sch):
    blk = sch[m.start():balanced(sch, m.start())]
    r = re.search(r'\(property "Reference" "([^"]+)"', blk)
    if r and r.group(1) in refs:
        inst[r.group(1)] = (m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4)), 'mirror' in blk[:200])
labels = []
for m in re.finditer(r'\(global_label "([^"]*)" \(shape \w+\)\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)', sch):
    labels.append((float(m.group(2)), float(m.group(3)), m.group(1), m.start(1), m.end(1)))
result = {}
for ref, (lid, x, y, ang, mir) in inst.items():
    a = math.radians(ang)
    for num, (px, py) in lib[lid].items():
        # library y is up, schematic y is down; rotation is counter-clockwise in the library frame
        rx = px * math.cos(a) - py * math.sin(a)
        ry = px * math.sin(a) + py * math.cos(a)
        X, Y = round(x + rx, 4), round(y - ry, 4)
        hit = [l for l in labels if abs(l[0] - X) < 1e-3 and abs(l[1] - Y) < 1e-3]
        result[f'{ref}.{num}'] = hit[0] if hit else None
if len(sys.argv) == 3:
    print(json.dumps({k: (v[2] if v else None) for k, v in result.items()}))
    sys.exit(0)
new = json.load(open(sys.argv[3]))
edits = []
for key, net in new.items():
    lab = result.get(key)
    if lab is None:
        raise SystemExit(f'no label at {key}')
    if lab[2] != net:
        edits.append((lab[3], lab[4], net, key, lab[2]))
out = sch
for s0, s1, net, key, old in sorted(edits, reverse=True):
    out = out[:s0] + net + out[s1:]
open(sys.argv[4], 'w').write(out)
print(json.dumps({'relabelled': [(k, o, n) for _, _, n, k, o in sorted(edits, key=lambda e: e[3])]}, indent=1))
