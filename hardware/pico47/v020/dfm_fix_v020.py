"""JLC assembly DFM fixes for Panda47 v0.2.0 (plain Python, text edit of the board and Panda47v2.pretty).

usage: dfm_fix_v020.py project_dir

Fixes reported by JLC on the earlier board (order Y4 SMT2611090608) and present on v0.2.0 too:
- U907 XB7608AJ CPC5: pad pitch and pin order per the XySemi datasheet (REV0.1 p.2/p.11). Top view, narrow
  leads 1 VDD / 2 GND / 3 GND at x = -0.795 / -0.265 / +0.795 (e1 0.53, e 1.06), wide leads 5 / 4 VM at
  x = -0.53 / +0.53 on the opposite side. The land is drawn rotated 180 deg so the narrow row stays at
  y = -1.65: pin 1 x = +0.795, pin 2 +0.265, pin 3 -0.795, pin 4 -0.53, pin 5 +0.53 (y = +1.65).
- SW201 / SW202 TS-1186E: two 0.75 mm NPTH holes for the locating posts at (0, +/-0.9) (XKB drawing
  PCB layout 2-0.75, posts 1.80 apart).
- J820 X05A10L40G: hold-down pads 1.91 mm behind the housing edge, 1.15 mm long (XKB drawing,
  recommended layout); pad drawn 0.3 x 1.3 at y = +0.565 to cover both readings of the drawing.
- Pin-1 silkscreen dots (0.3 mm) on parts whose footprint had no pin-1 silk.
- Track detours: 3V3_AON (F.Cu) and FL_C_N (B.Cu) pass between the new switch holes; the U907 VDD and
  cell-negative stubs follow the new pads.
"""
import math
import re
import sys
import uuid
from pathlib import Path

proj = Path(sys.argv[1])
pcb_path = proj / 'Panda47-v020.kicad_pcb'
lib = proj / 'Panda47v2.pretty'
t = pcb_path.read_text()


def uid():
    return str(uuid.uuid4())


def split_fps(text):
    """[(start, end, ref)] of top-level footprint blocks."""
    out = []
    for m in re.finditer(r'\n\t\(footprint ', text):
        i, depth = m.start() + 2, 0
        for j in range(i, len(text)):
            c = text[j]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    break
        blk = text[i:j + 1]
        out.append((i, j + 1, re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)))
    return out


def edit_fp(ref, fn):
    global t
    for i, j, r in split_fps(t):
        if r == ref:
            t = t[:i] + fn(t[i:j]) + t[j:]
            return
    raise SystemExit(f'{ref} not found')


def edit_lib(name, fn):
    p = lib / f'{name}.kicad_mod'
    p.write_text(fn(p.read_text()))


def sub1(pat, rep, s, count=1):
    s2, n = re.subn(pat, rep, s, count=count)
    if n != count:
        raise SystemExit(f'pattern {pat!r}: {n} matches, expected {count}')
    return s2


# ---------------------------------------------------------------- U907 pads
U907 = {'1': (0.795, -1.65), '2': (0.265, -1.65), '3': (-0.795, -1.65), '4': (-0.53, 1.65), '5': (0.53, 1.65)}


def u907(s):
    for n, (x, y) in U907.items():
        s = sub1(r'(\(pad "%s" smd rect\s*\(at )[-\d.]+ [-\d.]+' % n, r'\g<1>%g %g' % (x, y), s)
    return sub1(r'\(descr "[^"]*"\)',
                '(descr "XySemi XB7608AJ CPC5, datasheet REV0.1 p.2/p.11. Top view rotated 180 deg: narrow row '
                'pin1 VDD x+0.795, pin2 GND x+0.265, pin3 GND x-0.795 (e1 0.53 / e 1.06); wide row pin4 VM '
                'x-0.53, pin5 VM x+0.53. Corrected after JLC DFM (Y4).")', s)


edit_fp('U907', u907)
edit_lib('U907_Core', u907)

# ---------------------------------------------------------------- SW201 / SW202 locating holes


def holes(angle, ind):
    def f(s):
        a = f' {angle:g}' if angle else ''
        i, k = '\t' * ind, '\t' * (ind + 1)
        new = ''.join(f'{i}(pad "" np_thru_hole circle\n{k}(at 0 {y:g}{a})\n{k}(size 0.75 0.75)\n{k}(drill 0.75)\n'
                      f'{k}(layers "*.Cu" "*.Mask")\n{k}(uuid "{uid()}")\n{i})\n' for y in (-0.9, 0.9))
        s = sub1(r'(\n\s*)\(embedded_fonts no\)', '\n' + new + r'\g<1>(embedded_fonts no)', s)
        return s.replace('without locating posts', 'two 0.75 mm NPTH for the locating posts at (0,+/-0.9) '
                         '(JLC DFM Y4: parts are supplied with posts)')
    return f


for ref in ('SW201', 'SW202'):     # both placed at 90 deg; board pad angles include the footprint rotation
    edit_fp(ref, holes(90, 2))
    edit_lib(f'{ref}_Core', holes(0, 1))


# ---------------------------------------------------------------- J820 hold-down pads
def j820(s):
    for x in ('-10.635', '10.635'):
        s = sub1(r'(\(pad "MP" smd rect\s*\(at %s )-0.39(\)\s*\(size 0.3 )1.15\)' % re.escape(x), r'\g<1>0.565\g<2>1.3)', s)
    return sub1(r'\(descr "[^"]*"\)',
                '(descr "XKB X05A10L40G; exact LCSC C21261162; 0.5 mm pitch, bottom contact, right angle. '
                'Hold-down pads per XKB recommended layout: 1.91 mm behind the housing edge, 1.15 mm long '
                '(drawn 0.3 x 1.3 at y+0.565). Corrected after JLC DFM (Y4).")', s)


edit_fp('J820', j820)
edit_lib('J820_Display', j820)

# ---------------------------------------------------------------- pin-1 dots
DOT_R, PAD_GAP, EDGE_GAP = 0.15, 0.15, 0.3
TARGETS = ['U501', 'U810', 'U904', 'U907', 'Q901', 'Q902', 'J820', 'J803', 'J804']


def fp_info(blk):
    at = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', blk)
    fx, fy, th = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0)
    pads = []
    for p in re.finditer(r'\(pad "([^"]*)" (\w+) (\w+)\s*\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)\s*\(size ([\d.]+) ([\d.]+)\)', blk):
        n, _, _, x, y, a, w, h = p.groups()
        pads.append((n, float(x), float(y), float(a or 0) - th, float(w), float(h)))
    fab = [tuple(map(float, m.groups())) for m in re.finditer(
        r'\(fp_(?:line|rect)\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)[\s\S]*?\(layer "F\.Fab"\)', blk)]
    return fx, fy, th, pads, fab


def to_global(fx, fy, th, x, y):
    c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
    return fx + x * c + y * s, fy - x * s + y * c


def pad_box(x, y, a, w, h):
    if round(a) % 180 == 90:
        w, h = h, w
    elif round(a) % 90:
        w = h = math.hypot(w, h)
    return x - w / 2, y - h / 2, x + w / 2, y + h / 2


fps = []
for i, j, ref in split_fps(t):
    blk = t[i:j]
    fx, fy, th, pads, fab = fp_info(blk)
    back = '(layer "B.Cu")' in blk[:300]
    for n, x, y, a, w, h in pads:
        gx, gy = to_global(fx, fy, th, x, y)
        fps.append((ref, back, pad_box(gx, gy, a + th, w, h)))
vias = [(float(m.group(1)), float(m.group(2)), float(m.group(3)))
        for m in re.finditer(r'\(via\s+\(at ([-\d.]+) ([-\d.]+)\)\s*\(size ([\d.]+)\)', t)]
edges = [tuple(map(float, m.groups())) for m in re.finditer(
    r'\(gr_line\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)[\s\S]{0,120}?\(layer "Edge.Cuts"\)', t)]
edges.append((0.5, 82, 52, 82))


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(x1 + u * dx - px, y1 + u * dy - py)


def inside(px, py):
    return (0.5 < px < 63.5 and 82 < py < 114.8 and not (27.38 < px < 36.62 and py > 109.25)) or \
        (52 < px < 63.5 and 4 < py <= 82)


def box_dist(px, py, b):
    return math.hypot(max(b[0] - px, 0, px - b[2]), max(b[1] - py, 0, py - b[3]))


placed = []


def place_dot(ref, fixed=None):
    blk = [t[i:j] for i, j, r in split_fps(t) if r == ref][0]
    fx, fy, th, pads, fab = fp_info(blk)
    p1 = [p for p in pads if p[0] == '1'][0]
    _, x1, y1, a1, w1, h1 = p1
    body = (min(min(f[0], f[2]) for f in fab), min(min(f[1], f[3]) for f in fab),
            max(max(f[0], f[2]) for f in fab), max(max(f[1], f[3]) for f in fab)) if fab else None
    pb = pad_box(x1, y1, a1, w1, h1)
    best = None
    if fixed:
        cands = [fixed]
    else:
        cands = []
        for k in range(48):
            ang = 2 * math.pi * k / 48
            ux, uy = math.cos(ang), math.sin(ang)
            hx, hy = (pb[2] - pb[0]) / 2, (pb[3] - pb[1]) / 2
            sc = min(hx / abs(ux) if ux else 1e9, hy / abs(uy) if uy else 1e9)
            for ring in (0.0, 0.2, 0.4):
                r = PAD_GAP + DOT_R + 0.05 + ring
                cands.append((x1 + ux * (sc + r), y1 + uy * (sc + r)))
    for lx, ly in cands:
        if True:
            if body and body[0] - 0.05 < lx < body[2] + 0.05 and body[1] - 0.05 < ly < body[3] + 0.05:
                continue
            gx, gy = to_global(fx, fy, th, lx, ly)
            if not inside(gx, gy) or min(seg_dist(gx, gy, *e) for e in edges) < EDGE_GAP + DOT_R:
                continue
            if any(not back and box_dist(gx, gy, b) < PAD_GAP + DOT_R for _, back, b in fps):
                continue
            if any(math.hypot(gx - vx, gy - vy) < 0.2 + DOT_R for vx, vy, vs in vias):   # tented vias; keep off the drill
                continue
            if any(math.hypot(gx - px, gy - py) < 2 * DOT_R + 0.2 for px, py in placed):
                continue
            d1 = box_dist(lx, ly, pb)
            # unambiguous: pad 1 must be clearly the nearest pad of this part
            if any(box_dist(lx, ly, pad_box(x, y, a, w, h)) < d1 + 0.15 for n, x, y, a, w, h in pads if n not in ('1', '')):
                continue
            if best is None or d1 < best[0]:
                best = (d1, lx, ly, gx, gy)
    if best is None:
        raise SystemExit(f'no pin-1 dot position for {ref}')
    placed.append(best[3:])
    return best[1], best[2], best[3], best[4]


def dot(x, y, indent):
    i = '\t' * indent
    return (f'{i}(fp_circle\n{i}\t(center {x:.3f} {y:.3f})\n{i}\t(end {x + DOT_R:.3f} {y:.3f})\n'
            f'{i}\t(stroke\n{i}\t\t(width 0.1)\n{i}\t\t(type solid)\n{i}\t)\n{i}\t(fill yes)\n'
            f'{i}\t(layer "F.SilkS")\n{i}\t(uuid "{uid()}")\n{i})\n')


done = {}
for ref in TARGETS:
    fpid = re.search(r'\(footprint "Panda47v2:([^"]+)"', [t[i:j] for i, j, r in split_fps(t) if r == ref][0]).group(1)
    lx, ly, gx, gy = place_dot(ref, done.get(fpid))
    edit_fp(ref, lambda s: sub1(r'(\n\t\t)\(pad ', '\n' + dot(lx, ly, 2) + r'\g<1>(pad ', s))
    if fpid not in done:      # one library footprint per FPID (Q901 / Q902 share Q907_Core)
        edit_lib(fpid, lambda s: sub1(r'(\n\t)\(pad ', '\n' + dot(lx, ly, 1) + r'\g<1>(pad ', s))
        done[fpid] = (lx, ly)
    print(f'pin-1 dot {ref}: local ({lx:.3f}, {ly:.3f}) board ({gx:.3f}, {gy:.3f})')

# ---------------------------------------------------------------- tracks


def seg(x1, y1, x2, y2, w, layer, net):
    return (f'\t(segment\n\t\t(start {x1:g} {y1:g})\n\t\t(end {x2:g} {y2:g})\n\t\t(width {w:g})\n'
            f'\t\t(layer "{layer}")\n\t\t(net "{net}")\n\t\t(uuid "{uid()}")\n\t)\n')


def drop_segment(x1, y1, x2, y2, net):
    global t
    pat = (r'\t\(segment\s*\(start %s %s\)\s*\(end %s %s\)\s*\(width [\d.]+\)\s*\(layer "[^"]+"\)\s*\(net "%s"\)\s*'
           r'\(uuid "[^"]+"\)\s*\)\n') % tuple(map(re.escape, (x1, y1, x2, y2, net)))
    t = sub1(pat, '', t)


def add(*segs):
    global t
    i = t.index('\t(segment')
    t = t[:i] + ''.join(segs) + t[i:]


# U907: VDD from the new pin 1, cell negative to pins 2 and 3
drop_segment('54.47', '68.85', '54.47', '69.6287', 'BAT_PROT_VDD')
drop_segment('56.2413', '71.4', '54.47', '69.6287', 'BAT_PROT_VDD')
drop_segment('55', '68.85', '55', '68.0713', 'BAT_CELL_N')
drop_segment('55.53', '68.85', '55.53', '68.0713', 'BAT_CELL_N')
drop_segment('55', '68.0713', '55.53', '68.0713', 'BAT_CELL_N')
drop_segment('54.1525', '68.0713', '55', '68.0713', 'BAT_CELL_N')
add(seg(55.795, 68.85, 55.795, 69.6287, 0.3, 'F.Cu', 'BAT_PROT_VDD'),
    seg(55.795, 69.6287, 57.5663, 71.4, 0.3, 'F.Cu', 'BAT_PROT_VDD'),
    seg(57.5663, 71.4, 58.02, 71.4, 0.3, 'F.Cu', 'BAT_PROT_VDD'),
    seg(54.1525, 68.0713, 55.265, 68.0713, 0.3, 'F.Cu', 'BAT_CELL_N'),
    seg(54.205, 68.85, 54.205, 68.0713, 0.3, 'F.Cu', 'BAT_CELL_N'),
    seg(55.265, 68.85, 55.265, 68.0713, 0.3, 'F.Cu', 'BAT_CELL_N'))
drop_segment('58.02', '71.4', '56.2413', '71.4', 'BAT_PROT_VDD')

# SW201: 3V3_AON between the two locating holes
drop_segment('63.0405', '25.2043', '63.0405', '38.234', '3V3_AON')
add(*[seg(*a, *b, 0.225, 'F.Cu', '3V3_AON') for a, b in zip(
    [(63.0405, 25.2043), (63.0405, 28.2), (61.6, 29.6405), (61.6, 30.3595), (63.0405, 31.8)],
    [(63.0405, 28.2), (61.6, 29.6405), (61.6, 30.3595), (63.0405, 31.8), (63.0405, 38.234)])])

# SW202: FL_C_N (B.Cu) between the two locating holes
drop_segment('60.9286', '67.3265', '60.9286', '37.6183', 'FL_C_N')
add(*[seg(*a, *b, 0.127, 'B.Cu', 'FL_C_N') for a, b in zip(
    [(60.9286, 67.3265), (60.9286, 43.6), (61.6, 42.9286), (61.6, 41.0714), (60.9286, 40.4)],
    [(60.9286, 43.6), (61.6, 42.9286), (61.6, 41.0714), (60.9286, 40.4), (60.9286, 37.6183)])])

pcb_path.write_text(t)
print('saved', pcb_path)
