#!/usr/bin/env python3
"""2026-11-06 Claude：把网表式 Single 原理图重排为带连线、按功能分块的可读原理图。

输入原理图每个引脚各挂一个全局标签、元件按位号排成网格。本工具保持全部元件实例
（UUID、库符号、字段、引脚、实例路径）和电气连接不变，只改元件位置并重画连接：

* 元件按位号百位分块（2xx USB/充电、3xx 电池/RTC、…），每块一个带标题的框；
* 块内的网络用导线相连：引脚横向短线接入相邻通道中该网络专用的竖线，跨通道时
  在块顶部用该网络专用的横线汇合；所有导线只在端点相接，交叉处不相连；
* 跨块网络在每块内先连成一组，再挂一个全局标签；GND 等多引脚电源网络直接在
  引脚挂全局标签；未用引脚保留“不连接”标记。

相邻两列元件错开 1.27 mm、每个网络在通道内独占一条竖线、每个汇合横线独占一行，
因此不同网络的导线端点不会落在一起。输出须再经网表比对、ERC 与 PCB 原理图一致性
检查确认（见 --check）。
usage: readable_schematic.py IN.kicad_sch NETLIST.xml OUT.kicad_sch
"""
from __future__ import annotations

import re
import sys
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict

G = 1.27                     # schematic grid
PITCH = 2.54                 # track pitch inside a routing channel
LABEL_NETS = {'GND', '3V3_AON', 'VSYS_RAW', 'I2C_SDA', 'I2C_SCL'}
MAX_LABEL_PINS = 10          # nets with more pins than this are labelled at every pin
COL_HEIGHT = 190.5           # target column height inside a block (mm)
BLOCK_NAMES = {
    '2': 'USB-C 输入与充电路径', '3': '电池、电量计与 RTC', '4': '3V3 电源与负载开关',
    '5': 'ESP32-S3、Flash、SD 卡、音频', '6': 'IO 扩展与上拉', '7': '屏幕数据 / SD 多路开关与串联电阻',
    '8': '墨水屏电源 SY7636A 与面板接口', '9': '充电、电量计与前光', 'X': '测试点与电源标志',
}


def snap(v, g=G):
    return round(round(v / g) * g, 4)


def uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'panda47-readable/' + '/'.join(map(str, parts))))


def balanced(text, i):
    depth = 0
    for j in range(i, len(text)):
        if text[j] == '(':
            depth += 1
        elif text[j] == ')':
            depth -= 1
            if depth == 0:
                return j + 1
    raise ValueError('unbalanced s-expression')


def top_items(text):
    """Top-level items of (kicad_sch ...) as (head, start, end)."""
    i = text.index('(kicad_sch') + 1
    out = []
    while True:
        i = text.find('(', i)
        if i < 0:
            break
        j = balanced(text, i)
        head = re.match(r'\((\w+)', text[i:i + 40]).group(1)
        out.append((head, i, j))
        i = j
    return out


def main(inp, netp, outp):
    text = open(inp).read()
    items = top_items(text)
    lib = next(text[a:b] for h, a, b in items if h == 'lib_symbols')
    # library pin geometry: lib name -> {pin number: (x, y)} in symbol units (y up)
    libpins, libext = {}, {}
    for m in re.finditer(r'\(symbol "([^"]+)"', lib):
        name = m.group(1)
        if ':' not in name:
            continue
        body = lib[m.start():balanced(lib, m.start())]
        pins = {}
        for p in re.finditer(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\).*?\(number "([^"]*)"', body):
            pins.setdefault(p.group(4), (float(p.group(1)), float(p.group(2))))
        ys = [y for _, y in pins.values()] or [0]
        rect = re.search(r'\(rectangle\(start ([-\d.]+) ([-\d.]+)\)\(end ([-\d.]+) ([-\d.]+)\)', body)
        top = max([abs(float(rect.group(2))), abs(float(rect.group(4)))] if rect else [max(map(abs, ys)) + 2.54])
        libpins[name], libext[name] = pins, top
    syms = []
    for h, a, b in items:
        if h != 'symbol':
            continue
        s = text[a:b]
        lib_id = re.search(r'\(lib_id "([^"]+)"\)', s).group(1)
        ref = re.search(r'\(property "Reference" "([^"]+)"', s).group(1)
        at = re.search(r'\(lib_id "[^"]+"\)\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)', s)
        assert float(at.group(3)) == 0, ref + ' is rotated'
        syms.append(dict(ref=ref, lib=lib_id, x=float(at.group(1)), y=float(at.group(2)), text=s))
    # pin -> net: the label sitting on each pin end of the input sheet is authoritative (it also covers
    # power flags, which the board netlist omits); the netlist names the no-connect pins
    at_label = {}
    for h, a, b in items:
        if h == 'global_label':
            m = re.match(r'\(global_label "([^"]+)".*?\(at ([-\d.]+) ([-\d.]+)', text[a:b])
            at_label[(round(float(m.group(2)), 3), round(float(m.group(3)), 3))] = m.group(1)
    root = ET.parse(netp).getroot()
    pin_net = {}
    for n in root.iter('net'):
        for x in n.iter('node'):
            pin_net[(x.get('ref'), x.get('pin'))] = n.get('name').lstrip('/')
    for s in syms:
        for num, (px, py) in libpins[s['lib']].items():
            k = (round(s['x'] + px, 3), round(s['y'] - py, 3))
            if k in at_label:
                assert pin_net.get((s['ref'], num), at_label[k]) == at_label[k], (s['ref'], num)
                pin_net[(s['ref'], num)] = at_label[k]
    net_pins = defaultdict(list)
    for k, n in pin_net.items():
        net_pins[n].append(k)
    flags = [s for s in syms if s['ref'].startswith('#')]
    parts = [s for s in syms if not s['ref'].startswith('#')]
    byref = {s['ref']: s for s in syms}

    # ---------------------------------------------------------------- blocks
    def block_of(ref):
        m = re.match(r'([A-Z]+)(\d+)$', ref)
        if not m or m.group(1) in ('TP', 'TPG') or len(m.group(2)) < 3:
            return None
        return m.group(2)[0]
    block = {}
    for s in parts:
        b = block_of(s['ref'])
        if b:
            block[s['ref']] = b
    for s in parts + flags:              # test points and flags follow the block of their net
        if s['ref'] in block:
            continue
        votes = defaultdict(int)
        for (r, p), n in pin_net.items():
            if r == s['ref'] and n not in LABEL_NETS:
                for r2, _ in net_pins[n]:
                    if block.get(r2):
                        votes[block[r2]] += 1
        block[s['ref']] = max(votes, key=votes.get) if votes else 'X'
    members = defaultdict(list)
    for s in parts + flags:
        members[block[s['ref']]].append(s)

    def pins_of(s):
        out = []
        for num, (px, py) in libpins[s['lib']].items():
            out.append((num, px, py, pin_net.get((s['ref'], num))))
        return out

    def is_label_net(n):
        return n in LABEL_NETS or len(net_pins[n]) > MAX_LABEL_PINS

    out_items = []          # new schematic items (strings)
    placed = {}             # ref -> (x, y)
    frames = []

    def place_block(bkey, ox, oy):
        mem = members[bkey]
        big = sorted([s for s in mem if len(libpins[s['lib']]) > 2], key=lambda s: -len(libpins[s['lib']]))
        small = [s for s in mem if len(libpins[s['lib']]) <= 2]
        # order: each multi-pin part followed by the small parts sharing a non-label net with it
        order, used = [], set()
        for s in big:
            order.append(s); used.add(s['ref'])
            nets = {n for _, _, _, n in pins_of(s) if n and not is_label_net(n)}
            for t in small:
                if t['ref'] not in used and any(n in nets for _, _, _, n in pins_of(t)):
                    order.append(t); used.add(t['ref'])
        order += [t for t in small if t['ref'] not in used]
        # columns of bounded height
        cols, cur, h = [], [], 0.0
        for s in order:
            sh = 2 * libext[s['lib']] + 10.16
            if cur and h + sh > COL_HEIGHT:
                cols.append(cur); cur, h = [], 0.0
            cur.append((s, h, sh)); h += sh
        if cur:
            cols.append(cur)
        ncol = len(cols)
        # pin rows: column k is offset by k*1.27 so neighbouring columns never share a pin row
        col_of, local = {}, {}
        for k, col in enumerate(cols):
            for s, y0, sh in col:
                col_of[s['ref']] = k
                local[s['ref']] = snap(y0 + libext[s['lib']] + 5.08, PITCH) + (G if k % 2 else 0.0)
        # which channel each pin uses, per net
        chan_pins = defaultdict(lambda: defaultdict(list))     # net -> channel -> [(ref, pin, side, ly)]
        label_pins, nc_pins = [], []
        nets_here = defaultdict(list)
        for s in [c[0] for col in cols for c in col]:
            for num, px, py, n in pins_of(s):
                if n is None:
                    continue
                nets_here[n].append((s['ref'], num, px, py))
        for n, plist in nets_here.items():
            total = len(net_pins[n])
            if n.startswith('unconnected-') and total == 1:
                nc_pins += plist
            elif is_label_net(n) or (len(plist) == 1):
                label_pins += [(n,) + p for p in plist]
            else:
                for r, num, px, py in plist:
                    k = col_of[r]
                    ch = k if px < 0 else k + 1
                    chan_pins[n][ch].append((r, num, px, py))
        # channel widths
        ch_nets = defaultdict(list)
        for n, chs in chan_pins.items():
            for ch in chs:
                ch_nets[ch].append(n)
        ch_w = [max(2, len(ch_nets[ch]) + 2) * PITCH for ch in range(ncol + 1)]
        # x of channel starts and column centres
        x, ch_x0, col_x = ox, [], []
        for k in range(ncol + 1):
            ch_x0.append(x); x += ch_w[k]
            if k < ncol:
                col_x.append(x + 12.7); x += 25.4
        width = x - ox
        bus_nets = [n for n, chs in chan_pins.items() if len(chs) > 1 or len(net_pins[n]) > sum(len(v) for v in chs.values())]
        bus_y = {n: oy + 12.7 + i * PITCH for i, n in enumerate(sorted(bus_nets))}
        top = oy + 12.7 + len(bus_nets) * PITCH + 7.62
        top = snap(top, PITCH)
        colh = max(sum(sh for _, _, sh in col) for col in cols)
        # place symbols
        for k, col in enumerate(cols):
            for s, y0, sh in col:
                placed[s['ref']] = (snap(col_x[k], PITCH), snap(top + local[s['ref']], G))

        def pin_xy(r, px, py):
            sx, sy = placed[r]
            return round(sx + px, 4), round(sy - py, 4)
        # tracks
        track_x = {}
        for ch in range(ncol + 1):
            for i, n in enumerate(sorted(ch_nets[ch])):
                track_x[(n, ch)] = round(ch_x0[ch] + (i + 1.5) * PITCH, 4)
        wires = []                       # (x1, y1, x2, y2)
        nodes = defaultdict(int)         # endpoint -> count, for junctions
        def wire(a, b):
            if a != b:
                wires.append((a, b)); nodes[a] += 1; nodes[b] += 1
        for n, chs in chan_pins.items():
            xs = []
            for ch, plist in chs.items():
                tx = track_x[(n, ch)]
                ys = []
                for r, num, px, py in plist:
                    p = pin_xy(r, px, py)
                    wire(p, (tx, p[1])); ys.append(p[1])
                if n in bus_y:
                    ys.append(bus_y[n])
                ys = sorted(set(ys))
                for y1, y2 in zip(ys, ys[1:]):
                    wire((tx, y1), (tx, y2))
                xs.append(tx)
            if n in bus_y:
                xs = sorted(set(xs))
                for x1, x2 in zip(xs, xs[1:]):
                    wire((x1, bus_y[n]), (x2, bus_y[n]))
            if len(net_pins[n]) > sum(len(v) for v in chs.values()):          # also used in other blocks
                out_items.append(glabel(n, xs[0], bus_y[n], 180))
            else:                                                             # keep the net name
                ch0 = min(chs); tx = track_x[(n, ch0)]
                ytop = bus_y[n] if n in bus_y else min(pin_xy(r, px, py)[1] for r, _, px, py in chs[ch0])
                # a global label keeps the board's net name (a local label would become "/name")
                out_items.append(glabel(n, tx, ytop, 0))
        for (a, b) in wires:
            out_items.append(f'(wire (pts (xy {a[0]:.4f} {a[1]:.4f}) (xy {b[0]:.4f} {b[1]:.4f})) '
                             f'(stroke (width 0) (type default)) (uuid "{uid("w", a, b)}"))')
        for p, c in nodes.items():
            if c >= 3:
                out_items.append(f'(junction (at {p[0]:.4f} {p[1]:.4f}) (diameter 0) (color 0 0 0 0) (uuid "{uid("j", p)}"))')
        for n, r, num, px, py in label_pins:
            x0, y0 = pin_xy(r, px, py)
            out_items.append(glabel(n, x0, y0, 180 if px < 0 else 0))
        for r, num, px, py in nc_pins:
            x0, y0 = pin_xy(r, px, py)
            out_items.append(f'(no_connect (at {x0:.4f} {y0:.4f}) (uuid "{uid("nc", r, num)}"))')
        height = top - oy + colh + 12.7
        frames.append((bkey, ox, oy, ox + width, oy + height))
        return width, height

    def glabel(n, x0, y0, ang):
        just = 'right' if ang == 180 else 'left'
        return (f'(global_label "{n}" (shape passive) (at {x0:.4f} {y0:.4f} {ang}) '
                f'(effects (font (size 1.27 1.27)) (justify {just})) (uuid "{uid("gl", n, x0, y0)}"))')

    # pack blocks into rows
    order = [b for b in sorted(members) if b != 'X'] + (['X'] if 'X' in members else [])
    x, y, row_h, MAXW = 25.4, 38.1, 0.0, 1650.0
    sizes = {}
    for b in order:            # dry run widths via a scratch placement
        save = (list(out_items), dict(placed), list(frames))
        w, h = place_block(b, 0.0, 0.0)
        out_items[:], frames[:] = save[0], save[2]
        placed.clear(); placed.update(save[1])
        sizes[b] = (w, h)
    for b in order:
        w, h = sizes[b]
        if x > 25.4 and x + max(w, 101.6) > MAXW:
            x, y, row_h = 25.4, y + row_h + 25.4, 0.0
        place_block(b, snap(x, PITCH), snap(y, PITCH))
        x += max(w, 101.6) + 50.8; row_h = max(row_h, h)      # room for the block title
    page_w = snap(max(f[3] for f in frames) + 25.4, PITCH)
    page_h = snap(max(f[4] for f in frames) + 25.4, PITCH)
    for b, x0, y0, x1, y1 in frames:
        out_items.append(f'(rectangle (start {x0 - 5.08:.4f} {y0:.4f}) (end {x1 + 5.08:.4f} {y1:.4f}) '
                         f'(stroke (width 0.3) (type dash)) (fill (type none)) (uuid "{uid("frame", b)}"))')
        out_items.append(f'(text "{b}xx  {BLOCK_NAMES.get(b, "")}" (exclude_from_sim no) (at {x0:.4f} {y0 + 6.35:.4f} 0) '
                         f'(effects (font (size 3.5 3.5) (thickness 0.5) bold) (justify left)) (uuid "{uid("title", b)}"))')

    # moved symbol instances (all their absolute (at ...) shift together)
    new_syms = []
    for s in syms:
        nx, ny = placed[s['ref']]
        dx, dy = nx - s['x'], ny - s['y']
        def shift(m):
            return f'(at {float(m.group(1)) + dx:.4f} {float(m.group(2)) + dy:.4f}{m.group(3)}'
        new_syms.append(re.sub(r'\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?\))', shift, s['text']))
    keep = [text[a:b] for h, a, b in items if h not in ('symbol', 'global_label', 'no_connect', 'paper', 'wire', 'junction', 'label', 'text')]
    head = [k for k in keep if k.startswith(('(version', '(generator', '(uuid'))]
    rest = [k for k in keep if not k.startswith(('(version', '(generator', '(uuid'))]
    body = head + [f'(paper "User" {page_w:.2f} {page_h:.2f})'] + rest + new_syms + out_items
    open(outp, 'w').write('(kicad_sch\n' + '\n'.join(body) + '\n)\n')
    print(f'{len(syms)} symbols in {len(frames)} blocks, {sum(1 for o in out_items if o.startswith("(wire"))} wires, '
          f'{sum(1 for o in out_items if o.startswith("(global_label"))} labels, page {page_w:.0f}x{page_h:.0f} mm')


if __name__ == '__main__':
    main(*sys.argv[1:4])
