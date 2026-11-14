"""Netlist-style (flat) schematic for Panda47 v0.2.0, the input of readable_schematic.py.

usage: make_flat_sch_v020.py netlist_v020.json out.kicad_sch
Every part gets its own symbol (Panda7:<ref>) with a global label on each connected pin and a
no-connect flag on the others. Pin names and electrical types come from the v0.1.3 / v0.1.2 symbol
libraries where the part is kept, and from the datasheets for the new parts.
"""
import json
import os
import re
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIBS = [HERE.parent / 'v0.1.3/Panda7.kicad_sym', HERE.parent / 'v0.1.2/Panda7.kicad_sym']
PROJECT = 'Panda47-v020'
ROOT = str(uuid.uuid5(uuid.NAMESPACE_URL, 'panda47-v020-root'))


def uid(*a):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'panda47-v020/' + '/'.join(map(str, a))))


def lib_pins(path):
    t = path.read_text()
    out = {}
    for m in re.finditer(r'\(symbol "([A-Z]+\d+)" ', t):
        ref = m.group(1)
        end = t.find('\n(symbol "', m.end())
        seg = t[m.start(): end if end > 0 else len(t)]
        pins = {}
        for p in re.finditer(r'\(pin (\w+) \w+ \(at [^)]*\) \(length [\d.]+\)(?: hide)? \(name "([^"]*)".*?\(number "([^"]*)"', seg):
            pins[p.group(3)] = (p.group(2), p.group(1))
        out.setdefault(ref, pins)
    return out


KNOWN = {}
for lib in LIBS:
    for ref, pins in lib_pins(lib).items():
        KNOWN.setdefault(lib.parent.name, {})[ref] = pins

NEW = {
    'U302': {'1': ('OSCI', 'input'), '2': ('OSCO', 'output'), '3': ('~{INT}', 'open_collector'), '4': ('VSS', 'power_in'),
             '5': ('SDA', 'bidirectional'), '6': ('SCL', 'input'), '7': ('CLKOUT', 'open_collector'), '8': ('VDD', 'power_in')},
    'U503': {'1': ('SDO_SA0', 'bidirectional'), '2': ('SDA', 'bidirectional'), '3': ('VDDIO', 'power_in'), '4': ('NC', 'passive'),
             '5': ('INT1', 'output'), '6': ('INT2', 'output'), '7': ('VDD', 'power_in'), '8': ('GNDIO', 'power_in'),
             '9': ('GND', 'power_in'), '10': ('CS', 'input'), '11': ('NC', 'passive'), '12': ('SCL', 'input')},
    'U902': {'1': ('EN', 'input'), '2': ('GND', 'power_in'), '3': ('LX', 'passive'), '4': ('IN', 'power_in'), '5': ('FB', 'input')},
    'U905': {'1': ('SW', 'passive'), '2': ('GND', 'power_in'), '3': ('FB', 'input'), '4': ('CTRL', 'input'),
             '5': ('VOUT', 'passive'), '6': ('VIN', 'power_in')},
    'Y301': {'1': ('1', 'passive'), '2': ('2', 'passive')},
}


def pins_for(ref, part):
    if ref in NEW:
        return NEW[ref]
    if ref == 'U810':
        return KNOWN['v0.1.2']['U810']
    if ref == 'U601':          # TSSOP names re-numbered to the QFN package
        tssop = KNOWN['v0.1.3']['U601']
        q = {('22', '23', '24')[int(n) - 1] if int(n) <= 3 else str(int(n) - 3): v for n, v in tssop.items()}
        q['25'] = ('EP', 'power_in')
        return q
    if ref in ('Q901', 'Q902'):
        return KNOWN['v0.1.3']['Q907']
    if ref == 'TP19':
        return KNOWN['v0.1.3']['TP18']
    src = KNOWN['v0.1.3'].get(ref)
    if src and set(src) >= set(part['pins']):
        return src
    return {n: (n, 'passive') for n in part['pins']}


KICAD_FP = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')


def fp_excluded(part):
    lib = HERE.parent / 'v0.1.3/Panda47.pretty' if part['lib'] == 'Panda47' else KICAD_FP / f"{part['lib']}.pretty"
    fp_dir = os.environ.get('PANDA47_FP_DIR')            # v0.2.2 parts that exist only in the project library
    if part['lib'] == 'Panda47v2' and fp_dir:
        lib = Path(fp_dir)
    text = (lib / f"{part['footprint']}.kicad_mod").read_text()
    m = re.search(r'\(attr ([^)]*)\)', text)
    return bool(m and 'exclude_from_bom' in m.group(1))


def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def main(netlist_path, out):
    nl = json.load(open(netlist_path))
    parts = nl['parts']
    syms, insts, labels = [], [], []
    col_w, x0, y0 = 60.96, 25.4, 25.4
    x, y, row_h = x0, y0, 0.0
    for ref in sorted(parts, key=lambda r: (re.match(r'[A-Z]+', r).group(0), int(re.sub(r'\D', '', r) or 0))):
        p = parts[ref]
        pins = pins_for(ref, p)
        nums = sorted(pins, key=lambda n: (len(n), n))
        left, right = nums[: (len(nums) + 1) // 2], nums[(len(nums) + 1) // 2:]
        h = 2.54 * max(len(left), len(right), 1)
        w = 10.16
        fpid = f"Panda47v2:{p['footprint']}"
        pin_txt = []
        for i, n in enumerate(left):
            name, typ = pins[n]
            pin_txt.append(f'(pin {typ} line (at {-w/2 - 2.54:.2f} {h/2 - 1.27 - 2.54*i:.2f} 0) (length 2.54) '
                           f'(name {q(name)} (effects (font (size 0.85 0.85)))) (number {q(n)} (effects (font (size 0.85 0.85)))))')
        for i, n in enumerate(right):
            name, typ = pins[n]
            pin_txt.append(f'(pin {typ} line (at {w/2 + 2.54:.2f} {h/2 - 1.27 - 2.54*i:.2f} 180) (length 2.54) '
                           f'(name {q(name)} (effects (font (size 0.85 0.85)))) (number {q(n)} (effects (font (size 0.85 0.85)))))')
        props = [('Reference', ref), ('Value', p['value']), ('Footprint', fpid)]
        f = p['fields']
        for k in ('Datasheet', 'Manufacturer', 'MPN', 'LCSC', 'Description'):
            if f.get(k):
                props.append((k, f[k]))
        syms.append(f'(symbol "Panda7:{ref}" (pin_names (offset 0.5)) (in_bom {"no" if fp_excluded(p) else "yes"}) (on_board yes) '
                    + ' '.join(f'(property {q(k)} {q(v)} (at 0 0 0) (effects (font (size 0.85 0.85)) (hide yes)))' for k, v in props)
                    + f' (symbol "{ref}_0_1" (rectangle (start {-w/2} {h/2}) (end {w/2} {-h/2}) (stroke (width 0.254) (type default)) (fill (type background))))'
                    + f' (symbol "{ref}_1_1" ' + ' '.join(pin_txt) + '))')
        if y + h + 10 > 1100:
            x, y = x + col_w, y0
        cx, cy = x + 12.7, y + h / 2 + 5.08
        bom = 'no' if fp_excluded(p) else 'yes'
        insts.append(f'(symbol (lib_id "Panda7:{ref}") (at {cx:.2f} {cy:.2f} 0) (unit 1) (in_bom {bom}) (on_board yes) '
                     f'(dnp {"yes" if p["dnp"] else "no"}) (uuid {q(uid("sym", ref))}) '
                     + ' '.join(f'(property {q(k)} {q(v)} (at {cx:.2f} {cy:.2f} 0) (effects (font (size 0.85 0.85)) (hide {"no" if k == "Reference" else "yes"})))' for k, v in props)
                     + f' (instances (project {q(PROJECT)} (path {q("/" + ROOT)} (reference {q(ref)}) (unit 1)))))')
        for i, n in enumerate(left + right):
            side = -1 if n in left else 1
            k = left.index(n) if n in left else right.index(n)
            px = cx + side * (w / 2 + 2.54)
            py = cy - (h / 2 - 1.27 - 2.54 * k)
            net = p['pins'].get(n, '')
            if net:
                labels.append(f'(global_label {q(net)} (shape passive) (at {px:.2f} {py:.2f} {0 if side > 0 else 180}) '
                              f'(effects (font (size 0.85 0.85)) (justify {"left" if side > 0 else "right"})) (uuid {q(uid("lbl", ref, n))}))')
            else:
                labels.append(f'(no_connect (at {px:.2f} {py:.2f}) (uuid {q(uid("nc", ref, n))}))')
        y += h + 12.7
    # power flags (ERC drivers) on supplies without a power-output pin; readable_schematic adds the rest
    syms.append('(symbol "Panda7:POWER_SOURCE" (power) (pin_names (offset 0)) (in_bom no) (on_board no) '
                '(property "Reference" "#FLG" (at 0 1 0) (effects (font (size 0.85 0.85)))) '
                '(property "Value" "POWER_SOURCE" (at 0 2 0) (effects (font (size 0.85 0.85)))) '
                '(symbol "POWER_SOURCE_0_1" (polyline (pts (xy 0 0) (xy 0 2)) (stroke (width 0.254) (type default)) (fill (type none)))) '
                '(symbol "POWER_SOURCE_1_1" (pin power_out line (at 0 0 90) (length 0) (name "pwr" (effects (font (size 0.85 0.85)))) '
                '(number "1" (effects (font (size 0.85 0.85)))))))')
    used = {n for p in parts.values() for n in p['pins'].values()}       # v0.2.4 has no cell-protection nets
    for k, net in enumerate([n for n in ('GND', 'VBUS_USB', 'BAT_PROT_VDD', 'BAT_CELL_N', 'FUEL_VDD') if n in used], 1):
        fx, fy = x0 + 12.7 * k, 15.24
        insts.append(f'(symbol (lib_id "Panda7:POWER_SOURCE") (at {fx:.2f} {fy:.2f} 0) (unit 1) (in_bom no) (on_board no) (dnp no) '
                     f'(uuid {q(uid("flg", net))}) (property "Reference" "#FLG{k}" (at {fx:.2f} {fy:.2f} 0) (effects (font (size 0.85 0.85)) (hide yes))) '
                     f'(property "Value" "POWER_SOURCE" (at {fx:.2f} {fy:.2f} 0) (effects (font (size 0.85 0.85)) (hide yes))) '
                     f'(instances (project {q(PROJECT)} (path {q("/" + ROOT)} (reference "#FLG{k}") (unit 1)))))')
        labels.append(f'(global_label {q(net)} (shape passive) (at {fx:.2f} {fy:.2f} 0) (effects (font (size 0.85 0.85)) (justify left)) '
                      f'(uuid {q(uid("flglbl", net))}))')
    text = ('(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") '
            f'(uuid {q(ROOT)}) (paper "A0") (lib_symbols ' + '\n'.join(syms) + ')\n' + '\n'.join(insts) + '\n'
            + '\n'.join(labels) + '\n(sheet_instances (path "/" (page "1"))) (embedded_fonts no))\n')
    Path(out).write_text(text)
    print(len(insts), 'symbols', len(labels), 'labels/no-connects ->', out)


if __name__ == '__main__':
    main(*sys.argv[1:3])
