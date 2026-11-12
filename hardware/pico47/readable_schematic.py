#!/usr/bin/env python3
"""2026-11-06 Claude：把网表式 Single 原理图重画为常规画法的多页层次原理图。

输入是每个引脚各挂一个全局标签的扁平原理图及其 KiCad 网表；输出一张目录根页和按功能
分的 A4/A3 子页（文件名 OUT-<页>.kicad_sch），并重写同目录的 Panda7.kicad_sym。元件
实例的 UUID、库名、全部字段、引脚编号与电气类型以及网表都不变：

* 芯片与连接器画成方框：电源脚在上、地脚在下，信号脚分两侧并按高度平衡；电阻、电容、
  电感、二极管、晶振、MOS 管、按键、电池、测试点与电源/地符号使用 KiCad 标准库图形
  （坐标嵌在下方 STOCK 表中，不依赖本机库路径）；
* 一端接地或接电源的阻容竖挂在引脚引出线上（每个引脚最多四个）；两端都是电源的去耦
  元件排成一组共用电源线；两端都是信号的串联元件排成一列、两端挂标签；
* 跨元件的连接用同名全局标签，电源与地用电源符号，未用引脚打不连接标记；缺少驱动的
  电源网络补一个电源标志（只为 ERC，不上 PCB、不进网表）；
* 元件归属按 PCB 上的距离：每个阻容归最近的、与它共网络的芯片引脚（同位号百位优先）。

可见的 Spec 字段只显示 Value 中 “/” 前的规格；构建脚本须把它同步到封装（隐藏），并
比对网表、跑 ERC 与 PCB 原理图一致性检查。
usage: readable_schematic.py IN.kicad_sch NETLIST.xml OUT.kicad_sch [BOARD.kicad_pcb]
"""
from __future__ import annotations

import math
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

STOCK = {
    'R' : ( ['(rectangle (start -1.016 -2.54) (end 1.016 2.54) (stroke (width 0.254) (type default)) (fill (type none)))'] , [('1', 0.0, 3.81, 270, 1.27), ('2', 0.0, -3.81, 90, 1.27)] ),
    'C' : ( ['(polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))', '(polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.508) (type default)) (fill (type none)))'] , [('1', 0.0, 3.81, 270, 2.794), ('2', 0.0, -3.81, 90, 2.794)] ),
    'L' : ( ['(arc (start 0 2.54) (mid 0.6323 1.905) (end 0 1.27) (stroke (width 0) (type default)) (fill (type none)))', '(arc (start 0 1.27) (mid 0.6323 0.635) (end 0 0) (stroke (width 0) (type default)) (fill (type none)))', '(arc (start 0 0) (mid 0.6323 -0.635) (end 0 -1.27) (stroke (width 0) (type default)) (fill (type none)))', '(arc (start 0 -1.27) (mid 0.6323 -1.905) (end 0 -2.54) (stroke (width 0) (type default)) (fill (type none)))'] , [('1', 0.0, 3.81, 270, 1.27), ('2', 0.0, -3.81, 90, 1.27)] ),
    'D_Schottky' : ( ['(polyline (pts (xy -1.905 0.635) (xy -1.905 1.27) (xy -1.27 1.27) (xy -1.27 -1.27) (xy -0.635 -1.27) (xy -0.635 -0.635)) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27) (xy -1.27 0) (xy 1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy 1.27 0) (xy -1.27 0)) (stroke (width 0) (type default)) (fill (type none)))'] , [('1', -3.81, 0.0, 0, 2.54), ('2', 3.81, 0.0, 180, 2.54)] ),
    'D_Zener' : ( ['(polyline (pts (xy -1.27 -1.27) (xy -1.27 1.27) (xy -0.762 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy 1.27 0) (xy -1.27 0)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 1.27 -1.27) (xy 1.27 1.27) (xy -1.27 0) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))'] , [('1', -3.81, 0.0, 0, 2.54), ('2', 3.81, 0.0, 180, 2.54)] ),
    'Thermistor_NTC' : ( ['(arc (start -3.175 2.413) (mid -3.0506 2.3165) (end -3.048 2.159) (stroke (width 0) (type default)) (fill (type none)))', '(arc (start -3.048 2.794) (mid -2.9736 2.9736) (end -2.794 3.048) (stroke (width 0) (type default)) (fill (type none)))', '(arc (start -2.794 3.048) (mid -2.6144 2.9736) (end -2.54 2.794) (stroke (width 0) (type default)) (fill (type none)))', '(arc (start -2.794 2.54) (mid -2.9736 2.6144) (end -3.048 2.794) (stroke (width 0) (type default)) (fill (type none)))', '(arc (start -2.794 1.905) (mid -2.9736 1.9794) (end -3.048 2.159) (stroke (width 0) (type default)) (fill (type none)))', '(arc (start -2.54 2.159) (mid -2.6144 1.9794) (end -2.794 1.905) (stroke (width 0) (type default)) (fill (type none)))', '(arc (start -2.159 2.794) (mid -2.434 2.5608) (end -2.794 2.54) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy -2.54 2.159) (xy -2.54 2.794)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy -2.54 -3.683) (xy -2.54 -1.397) (xy -2.794 -2.159) (xy -2.286 -2.159) (xy -2.54 -1.397) (xy -2.54 -1.651)) (stroke (width 0) (type default)) (fill (type outline)))', '(polyline (pts (xy -1.778 2.54) (xy -1.778 1.524) (xy 1.778 -1.524) (xy 1.778 -2.54)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy -1.778 -1.397) (xy -1.778 -3.683) (xy -2.032 -2.921) (xy -1.524 -2.921) (xy -1.778 -3.683) (xy -1.778 -3.429)) (stroke (width 0) (type default)) (fill (type outline)))', '(rectangle (start -1.016 2.54) (end 1.016 -2.54) (stroke (width 0.254) (type default)) (fill (type none)))'] , [('1', 0.0, 3.81, 270, 1.27), ('2', 0.0, -3.81, 90, 1.27)] ),
    'Battery_Cell' : ( ['(rectangle (start -2.286 1.778) (end 2.286 1.524) (stroke (width 0) (type default)) (fill (type outline)))', '(rectangle (start -1.524 1.016) (end 1.524 0.508) (stroke (width 0) (type default)) (fill (type outline)))', '(polyline (pts (xy 0 1.778) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 0 0.762) (xy 0 0)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 0.762 3.048) (xy 1.778 3.048)) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy 1.27 3.556) (xy 1.27 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))'] , [('1', 0.0, 5.08, 270, 2.54), ('2', 0.0, -2.54, 90, 2.54)] ),
    'SW_Push' : ( ['(circle (center -2.032 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 0 1.27) (xy 0 3.048)) (stroke (width 0) (type default)) (fill (type none)))', '(circle (center 2.032 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 2.54 1.27) (xy -2.54 1.27)) (stroke (width 0) (type default)) (fill (type none)))'] , [('1', -5.08, 0.0, 0, 2.54), ('2', 5.08, 0.0, 180, 2.54)] ),
    'TestPoint' : ( ['(circle (center 0 3.302) (radius 0.762) (stroke (width 0) (type default)) (fill (type none)))'] , [('1', 0.0, 0.0, 90, 2.54)] ),
    'Crystal_GND24' : ( ['(polyline (pts (xy -2.54 2.286) (xy -2.54 3.556) (xy 2.54 3.556) (xy 2.54 2.286)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy -2.54 0) (xy -2.032 0)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy -2.54 -2.286) (xy -2.54 -3.556) (xy 2.54 -3.556) (xy 2.54 -2.286)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy -2.032 -1.27) (xy -2.032 1.27)) (stroke (width 0.508) (type default)) (fill (type none)))', '(rectangle (start -1.143 2.54) (end 1.143 -2.54) (stroke (width 0.3048) (type default)) (fill (type none)))', '(polyline (pts (xy 0 -3.81) (xy 0 -3.556)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 2.032 0) (xy 2.54 0)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 2.032 -1.27) (xy 2.032 1.27)) (stroke (width 0.508) (type default)) (fill (type none)))'] , [('1', -3.81, 0.0, 0, 1.27), ('2', 0.0, -5.08, 90, 1.27), ('3', 3.81, 0.0, 180, 1.27), ('4', 0.0, -5.08, 90, 1.27)] ),
    'Q_NMOS' : ( ['(polyline (pts (xy 0.254 1.905) (xy 0.254 -1.905)) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy 0.254 0) (xy -2.54 0)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 0.762 2.286) (xy 0.762 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy 0.762 0.508) (xy 0.762 -0.508)) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy 0.762 -1.27) (xy 0.762 -2.286)) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy 0.762 -1.778) (xy 3.302 -1.778) (xy 3.302 1.778) (xy 0.762 1.778)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 1.016 0) (xy 2.032 0.381) (xy 2.032 -0.381) (xy 1.016 0)) (stroke (width 0) (type default)) (fill (type outline)))', '(circle (center 1.651 0) (radius 2.794) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy 2.54 2.54) (xy 2.54 1.778)) (stroke (width 0) (type default)) (fill (type none)))', '(circle (center 2.54 1.778) (radius 0.254) (stroke (width 0) (type default)) (fill (type outline)))', '(circle (center 2.54 -1.778) (radius 0.254) (stroke (width 0) (type default)) (fill (type outline)))', '(polyline (pts (xy 2.54 -2.54) (xy 2.54 0) (xy 0.762 0)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 2.921 0.381) (xy 3.683 0.381)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 3.302 0.381) (xy 2.921 -0.254) (xy 3.683 -0.254) (xy 3.302 0.381)) (stroke (width 0) (type default)) (fill (type none)))'] , [('D', 2.54, 5.08, 270, 2.54), ('G', -5.08, 0.0, 0, 2.54), ('S', 2.54, -5.08, 90, 2.54)] ),
    'D_Dual_Series_AKC' : ( ['(polyline (pts (xy -3.81 1.27) (xy -1.27 0) (xy -3.81 -1.27) (xy -3.81 1.27) (xy -3.81 1.27) (xy -3.81 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy -3.81 0) (xy 3.81 0)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy -1.27 -1.27) (xy -1.27 1.27) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy 0 0) (xy 0 -2.54)) (stroke (width 0) (type default)) (fill (type none)))', '(circle (center 0 0) (radius 0.254) (stroke (width 0) (type default)) (fill (type outline)))', '(polyline (pts (xy 1.27 1.27) (xy 3.81 0) (xy 1.27 -1.27) (xy 1.27 1.27) (xy 1.27 1.27) (xy 1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy 3.81 1.27) (xy 3.81 -1.27) (xy 3.81 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))', '(polyline (pts (xy 6.35 0) (xy 7.62 0)) (stroke (width 0) (type default)) (fill (type none)))'] , [('1', -7.62, 0.0, 0, 3.81), ('2', 7.62, 0.0, 180, 3.81), ('3', 0.0, -5.08, 90, 2.54)] ),
    'PWR_FLAG' : ( ['(polyline (pts (xy 0 0) (xy 0 1.27) (xy -1.016 1.905) (xy 0 2.54) (xy 1.016 1.905) (xy 0 1.27)) (stroke (width 0) (type default)) (fill (type none)))'] , [('1', 0.0, 0.0, 90, 0.0)] ),
    'GND' : ( ['(polyline (pts (xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27)) (stroke (width 0) (type default)) (fill (type none)))'] , [('1', 0.0, 0.0, 270, 0.0)] ),
    '+3V3' : ( ['(polyline (pts (xy -0.762 1.27) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 0 2.54) (xy 0.762 1.27)) (stroke (width 0) (type default)) (fill (type none)))', '(polyline (pts (xy 0 0) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))'] , [('1', 0.0, 0.0, 90, 0.0)] ),
}

G = 1.27
P = 2.54
CW = 1.25                     # approximate stroke-font advance per character at 1.27 mm
FONT = '(effects (font (size 1.27 1.27)))'
POWER_NETS = ['GND', 'VBUS_USB', 'VSYS_RAW', 'VSYS_AUDIO', '3V3_AON', '3V3_RF', 'VDD_SPI',
              '3V3_SD', '3V3_TOUCH', '3V3_EPD_LOGIC']
SUPPLY = set(POWER_NETS) - {'GND'}
PROJECT = 'Single'
# sheet key -> (file suffix, sheet name, Chinese title); anchors go to the sheet of their designator hundreds
SHEETS = {
    '2': ('usb', 'USB_Input', 'USB-C 接口与 ESD 防护'),
    '3': ('battery', 'Battery_RTC', '电池接口与 RTC（SD3078）'),
    '4': ('switches', 'Load_Switches', '分路负载开关 SGM2578'),
    '5': ('mcu', 'MCU', 'ESP32-S3、IMU、Flash、microSD 与调试'),
    '6': ('io', 'IO_Expander', 'IO 扩展 XL9535'),
    '7': ('mux', 'Panel_SD_Mux', '屏幕数据 / microSD 多路开关'),
    '8': ('epd', 'EPD_PMIC', '墨水屏电源与面板、触摸、前光接口'),
    '9': ('power', 'Charger_Power', '充电、3V3 升降压、电量计、音频与前光驱动'),
}
PAPERS = [('A4', 297.0, 210.0), ('A3', 420.0, 297.0), ('A2', 594.0, 420.0)]


def snap(v, g=G):
    return round(round(v / g) * g, 4)


def snap_up(v, g=P):
    return round(math.ceil(v / g - 1e-6) * g, 4)


def uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'panda47-schematic/' + '/'.join(map(str, parts))))


def q(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def balanced(text, i):
    depth, instr, esc = 0, False, False
    for j in range(i, len(text)):
        c = text[j]
        if instr:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                instr = False
            continue
        if c == '"':
            instr = True
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return j + 1
    raise ValueError('unbalanced s-expression')


def top_items(text):
    i = text.index('(kicad_sch') + 1
    out = []
    while True:
        i = text.find('(', i)
        if i < 0:
            break
        j = balanced(text, i)
        out.append((re.match(r'\((\w+)', text[i:i + 40]).group(1), i, j))
        i = j
    return out


def natural(num):
    m = re.match(r'([A-Za-z]*)(\d*)', num)
    return (0, int(num)) if num.isdigit() else (1, m.group(1), int(m.group(2) or 0), num)


def textw(s, size=1.27):
    return len(s) * CW * size / 1.27


def spec_of(value):
    s = value.split(' / ')[0].strip()
    if len(s) > 18:
        out = ''
        for tok in s.split():
            if out and len(out) + 1 + len(tok) > 18:
                break
            out = (out + ' ' + tok).strip()
        s = out or s[:18]
    return s


# ------------------------------------------------------------------ geometry helpers (lib coords, y up)
def rot(x, y, k):
    for _ in range(k % 4):
        x, y = -y, x
    return round(x, 4) + 0.0, round(y, 4) + 0.0          # + 0.0 turns -0.0 into 0.0


def rot_prim(prim, k):
    def f(m):
        x, y = rot(float(m.group(2)), float(m.group(3)), k)
        return f'({m.group(1)} {x:g} {y:g})'
    return re.sub(r'\((xy|start|end|mid|center) ([-\d.]+) ([-\d.]+)\)', f, prim)


def shift_prim(prim, dx, dy):
    def f(m):
        return f'({m.group(1)} {float(m.group(2)) + dx:g} {float(m.group(3)) + dy:g})'
    return re.sub(r'\((xy|start|end|mid|center) ([-\d.]+) ([-\d.]+)\)', f, prim)


class LibSym:
    """A generated library symbol: graphics + pins in lib coordinates (y up)."""

    def __init__(self, name, props, prims, pins, show_names=False, show_numbers=False, power=False):
        self.name, self.props, self.prims, self.pins = name, props, prims, pins
        self.show_names, self.show_numbers, self.power = show_names, show_numbers, power

    def text(self, full):
        base = self.name
        head = [f'(symbol {q(full)}']
        if self.power:
            head.append('(power)')
        head.append('(pin_numbers (hide yes))' if not self.show_numbers else '')
        head.append('(pin_names (offset 1.016))' if self.show_names else '(pin_names (offset 0) (hide yes))')
        head.append('(exclude_from_sim no)')
        head.append('(in_bom no) (on_board no)' if self.power else '(in_bom yes) (on_board yes)')
        for k, v, hide in self.props:
            head.append(f'(property {q(k)} {q(v)} (at 0 0 0) {"(hide yes) " if hide else ""}{FONT})')
        body = f'(symbol {q(base + "_0_1")} ' + ' '.join(self.prims) + ')'
        pins = []
        for p in self.pins:
            pins.append(f'(pin {p["type"]} line (at {p["x"]:g} {p["y"]:g} {p["ang"]}) (length {p["len"]:g})'
                        f'{" (hide yes)" if p.get("hide") else ""} (name {q(p["name"])} {FONT}) (number {q(p["num"])} {FONT}))')
        return ' '.join(h for h in head if h) + ' ' + body + f' (symbol {q(base + "_1_1")} ' + ' '.join(pins) + '))'


# ------------------------------------------------------------------ drawing container (screen coords, y down)
class Draw:
    def __init__(self):
        self.items = []
        self.box = [math.inf, math.inf, -math.inf, -math.inf]

    def ext(self, x0, y0, x1, y1):
        b = self.box
        b[0], b[1] = min(b[0], x0, x1), min(b[1], y0, y1)
        b[2], b[3] = max(b[2], x0, x1), max(b[3], y0, y1)

    def wire(self, a, b):
        a, b = (snap(a[0]), snap(a[1])), (snap(b[0]), snap(b[1]))
        if a != b:
            self.items.append(('wire', a, b))
            self.ext(*a, *b)

    def path(self, pts, junctions=()):
        for a, b in zip(pts, pts[1:]):
            self.wire(a, b)
        for j in junctions:
            self.junc(j)

    def junc(self, p):
        self.items.append(('junc', (snap(p[0]), snap(p[1]))))

    def nc(self, p):
        self.items.append(('nc', (snap(p[0]), snap(p[1]))))

    def label(self, net, p, ang):
        p = (snap(p[0]), snap(p[1]))
        if net.startswith('unconnected-'):               # KiCad 只给单引脚网络起此名：画不连接标记而非孤立标签
            self.nc(p)
            return
        self.items.append(('label', net, p, ang))
        w = textw(net) + 2.54
        dx, dy = {0: (w, 0), 180: (-w, 0), 90: (0, -w), 270: (0, w)}[ang]
        if dx:
            self.ext(p[0], p[1] - 1.4, p[0] + dx, p[1] + 1.4)
        else:
            self.ext(p[0] - 1.4, p[1], p[0] + 1.4, p[1] + dy)

    def power(self, net, p):
        p = (snap(p[0]), snap(p[1]))
        self.items.append(('pwr', net, p))
        w = textw(net) / 2 + 0.5
        if net == 'GND':
            self.ext(p[0] - max(w, 1.4), p[1], p[0] + max(w, 1.4), p[1] + 4.6)
        else:
            self.ext(p[0] - w, p[1] - 4.3, p[0] + w, p[1])

    def sym(self, ref, origin, fields, box):
        self.items.append(('sym', ref, (snap(origin[0]), snap(origin[1])), fields))
        self.ext(*box)
        for name, dx, dy, just, s in fields:
            x, y = origin[0] + dx, origin[1] + dy
            w = textw(s)
            x0 = x if just == 'left' else (x - w if just == 'right' else x - w / 2)
            self.ext(x0, y - 0.8, x0 + w, y + 0.8)

    def text(self, s, p, size=1.27, bold=False):
        self.items.append(('text', s, p, size, bold))
        self.ext(p[0], p[1] - size, p[0] + textw(s, size), p[1] + size)

    def shifted(self, dx, dy):
        dx, dy = snap(dx, P), snap(dy, P)
        out = Draw()
        mv = lambda p: (round(p[0] + dx, 4), round(p[1] + dy, 4))
        for it in self.items:
            k = it[0]
            if k == 'wire':
                out.items.append((k, mv(it[1]), mv(it[2])))
            elif k in ('junc', 'nc'):
                out.items.append((k, mv(it[1])))
            elif k == 'label':
                out.items.append((k, it[1], mv(it[2]), it[3]))
            elif k == 'pwr':
                out.items.append((k, it[1], mv(it[2])))
            elif k == 'sym':
                out.items.append((k, it[1], mv(it[2]), it[3]))
            elif k == 'text':
                out.items.append((k, it[1], mv(it[2]), it[3], it[4]))
        b = self.box
        out.box = [b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy]
        return out

    def merge(self, other):
        self.items += other.items
        self.ext(*other.box)

    @property
    def w(self):
        return self.box[2] - self.box[0]

    @property
    def h(self):
        return self.box[3] - self.box[1]


# ------------------------------------------------------------------ the design
class Design:
    def __init__(self, inp, netp, pcbp):
        text = open(inp).read()
        self.text = text
        items = top_items(text)
        self.items = items
        lib = next(text[a:b] for h, a, b in items if h == 'lib_symbols')
        self.lib = {}
        i = 0
        while True:
            m = re.compile(r'\(symbol "(Panda7:[^"]+)"').search(lib, i)
            if not m:
                break
            body = lib[m.start():balanced(lib, m.start())]
            i = m.start() + len(body)
            pins = {}
            for p in re.finditer(r'\(pin (\w+) \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)\s*\(length [-\d.]+\)\s*'
                                 r'\(name "([^"]*)".*?\(number "([^"]*)"', body):
                pins[p.group(6)] = dict(type=p.group(1), name=p.group(5), x=float(p.group(2)), y=float(p.group(3)))
            props = re.findall(r'\(property "([^"]+)" "((?:[^"\\]|\\.)*)"', body)
            self.lib[m.group(1)] = dict(pins=pins, props=props)
        self.parts = {}
        for h, a, b in items:
            if h != 'symbol':
                continue
            s = text[a:b]
            lib_id = re.search(r'\(lib_id "([^"]+)"\)', s).group(1)
            ref = re.search(r'\(property "Reference" "([^"]+)"', s).group(1)
            at = re.search(r'\(lib_id "[^"]+"\)\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)', s)
            props = []
            for pm in re.finditer(r'\(property "([^"]+)" "((?:[^"\\]|\\.)*)"', s):
                props.append((pm.group(1), pm.group(2)))
            flags = {k: re.search(r'\(' + k + r' (\w+)\)', s).group(1) for k in ('in_bom', 'on_board', 'dnp')}
            self.parts[ref] = dict(ref=ref, lib=lib_id, x=float(at.group(1)), y=float(at.group(2)),
                                   uuid=re.search(r'\(uuid "([^"]+)"\)', s).group(1), props=props, flags=flags,
                                   value=dict(props).get('Value', ''))
        self.title = re.search(r'\(title_block.*', text)
        # pin -> net: labels on the input sheet's pin ends (cover power flags) + the board netlist
        at_label = {}
        for h, a, b in items:
            if h == 'global_label':
                m = re.match(r'\(global_label "([^"]+)".*?\(at ([-\d.]+) ([-\d.]+)', text[a:b])
                at_label[(round(float(m.group(2)), 3), round(float(m.group(3)), 3))] = m.group(1)
        root = ET.parse(netp).getroot()
        self.pin_net = {}
        self.pintype = {}
        for n in root.iter('net'):
            for x in n.iter('node'):
                self.pin_net[(x.get('ref'), x.get('pin'))] = n.get('name').lstrip('/')
        for ref, s in self.parts.items():
            for num, p in self.lib[s['lib']]['pins'].items():
                k = (round(s['x'] + p['x'], 3), round(s['y'] - p['y'], 3))
                if k in at_label:
                    assert self.pin_net.get((ref, num), at_label[k]) == at_label[k], (ref, num)
                    self.pin_net[(ref, num)] = at_label[k]
                assert (ref, num) in self.pin_net, ('pin without net', ref, num)
        self.net_pins = defaultdict(list)
        for k, n in self.pin_net.items():
            self.net_pins[n].append(k)
        self.pcb = parse_pcb(pcbp) if pcbp and Path(pcbp).exists() else {}

    def pins(self, ref):
        lib = self.lib[self.parts[ref]['lib']]['pins']
        return {num: dict(lib[num], num=num, net=self.pin_net[(ref, num)]) for num in lib}

    def is_nc(self, net):
        return net.startswith('unconnected-') and len(self.net_pins[net]) == 1

    def where(self, ref, pin=None):
        f = self.pcb.get(ref)
        if not f:
            m = re.match(r'[A-Z#]+(\d+)', ref)
            return (int(m.group(1)) if m else 0, 0.0)
        if pin and pin in f['pads']:
            return f['pads'][pin]
        return f['pos']


def parse_pcb(path):
    text = open(path).read()
    out = {}
    for m in re.finditer(r'\n\t\(footprint "', text):
        a = m.start() + 2
        b = balanced(text, a)
        s = text[a:b]
        at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', s)
        ref = re.search(r'\(property "Reference" "([^"]+)"', s)
        if not at or not ref:
            continue
        fx, fy, fa = float(at.group(1)), float(at.group(2)), math.radians(float(at.group(3) or 0))
        pads = {}
        for p in re.finditer(r'\(pad "([^"]*)" \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+)', s):
            x, y = float(p.group(2)), float(p.group(3))
            pads.setdefault(p.group(1), (fx + x * math.cos(fa) + y * math.sin(fa), fy - x * math.sin(fa) + y * math.cos(fa)))
        out[ref.group(1)] = dict(pos=(fx, fy), pads=pads)
    return out


# ------------------------------------------------------------------ symbol construction
def stock_name(D, ref):
    pre = re.match(r'[A-Z]+', ref).group(0)
    val = D.parts[ref]['value'].upper()
    if pre == 'D':
        return 'D_Zener' if ('SGM05' in val or 'TVS' in val or 'ESD' in val) else 'D_Schottky'
    return {'R': 'R', 'C': 'C', 'L': 'L', 'TH': 'Thermistor_NTC', 'SW': 'SW_Push', 'BT': 'Battery_Cell',
            'TP': 'TestPoint', 'TPG': 'TestPoint'}[pre]


def lib_props(D, ref):
    props = dict(D.lib[D.parts[ref]['lib']]['props'])
    return [('Reference', props.get('Reference', ref), False), ('Value', props.get('Value', ''), True),
            ('Footprint', props.get('Footprint', ''), True)]


def prim_box(prims, pins):
    xs, ys = [], []
    for pr in prims:
        for m in re.finditer(r'\((?:xy|start|end|mid|center) ([-\d.]+) ([-\d.]+)\)', pr):
            xs.append(float(m.group(1))); ys.append(float(m.group(2)))
        c = re.search(r'\(center ([-\d.]+) ([-\d.]+)\)\s*\(radius ([\d.]+)\)', pr)
        if c:
            r = float(c.group(3)); xs += [float(c.group(1)) - r, float(c.group(1)) + r]; ys += [float(c.group(2)) - r, float(c.group(2)) + r]
    for p in pins:
        xs.append(p['x']); ys.append(p['y'])
    return min(xs), min(ys), max(xs), max(ys)


class Baked:
    """A two-terminal (or one-terminal) part drawn from stock graphics, rotated so that pin `a` comes first
    along screen direction `d`."""

    def __init__(self, D, ref, a, d):
        name = stock_name(D, ref)
        prims, spins = STOCK[name]
        pins = D.pins(ref)
        sp = {n: (x, y, ang, ln) for n, x, y, ang, ln in spins}
        nums = sorted(pins, key=natural)
        b = next((n for n in nums if n != a), None)
        want = (d[0], -d[1])
        k = 0
        if b is not None:
            v = (sp[b][0] - sp[a][0], sp[b][1] - sp[a][1])
            L = math.hypot(*v)
            for k in range(4):
                r = rot(*v, k)
                if abs(r[0] - want[0] * L) < 1e-3 and abs(r[1] - want[1] * L) < 1e-3:
                    break
            else:
                raise AssertionError(ref)
        else:
            for k in range(4):        # one-pin parts: the body extends from the pin along d
                if rot(0, 1, k) == want:
                    break
        self.k = k
        self.prims = [rot_prim(p, k) for p in prims]
        self.pins = []
        for n in nums:
            x, y = rot(sp[n][0], sp[n][1], k)
            self.pins.append(dict(type=pins[n]['type'], name=pins[n]['name'], num=n, x=x, y=y,
                                  ang=(sp[n][2] + 90 * k) % 360, len=sp[n][3]))
        self.lib = LibSym(ref, lib_props(D, ref), self.prims, self.pins)
        self.pa = next(p for p in self.pins if p['num'] == a)
        self.pb = next((p for p in self.pins if p['num'] == b), None)
        self.length = math.hypot(self.pb['x'] - self.pa['x'], self.pb['y'] - self.pa['y']) if self.pb else 0.0
        x0, y0, x1, y1 = prim_box(self.prims, self.pins)
        self.box = (x0, -y1, x1, -y0)          # screen-relative to origin

    def origin_for(self, at):
        return (at[0] - self.pa['x'], at[1] + self.pa['y'])

    def other_end(self, at):
        o = self.origin_for(at)
        return (round(o[0] + self.pb['x'], 4), round(o[1] - self.pb['y'], 4))


def stock_anchor(D, ref):
    """Q, dual-diode and crystal anchors keep their stock drawing at rotation 0."""
    pins = D.pins(ref)
    pre = re.match(r'[A-Z]+', ref).group(0)
    if pre == 'Q':
        name = 'Q_NMOS'
        by_name = {p['name']: n for n, p in pins.items()}
        mapping = {by_name[s]: s for s in ('G', 'D', 'S')}
    elif pre == 'Y' and len(pins) == 4:
        name, mapping = 'Crystal_GND24', {n: n for n in pins}
    elif pre == 'D' and len(pins) == 3:
        name, mapping = 'D_Dual_Series_AKC', {n: n for n in pins}
    else:
        return None
    prims, spins = STOCK[name]
    sp = {n: (x, y, ang, ln) for n, x, y, ang, ln in spins}
    out = []
    for n in sorted(pins, key=natural):
        x, y, ang, ln = sp[mapping[n]]
        out.append(dict(type=pins[n]['type'], name=pins[n]['name'], num=n, x=x, y=y, ang=ang, len=ln))
    return LibSym(ref, lib_props(D, ref), prims, out)


SIDE_OF_ANGLE = {0: 'L', 180: 'R', 270: 'T', 90: 'B'}


class Anchor:
    def __init__(self, D, ref, shunts):
        self.D, self.ref = D, ref
        self.pins = D.pins(ref)
        self.shunts = shunts                       # pin -> [Shunt]
        stock = stock_anchor(D, ref)
        if stock:
            self.lib = stock
            self.groups = defaultdict(list)          # side -> [[pin,...]]
            pos = {}
            for p in stock.pins:
                key = (p['x'], p['y'])
                side = SIDE_OF_ANGLE[p['ang']]
                if key in pos:
                    pos[key].append(p['num'])
                else:
                    pos[key] = [p['num']]
                    self.groups[side].append(pos[key])
            self.end = {p['num']: (p['x'], -p['y']) for p in stock.pins}
            self.stacked = True
            x0, y0, x1, y1 = prim_box(stock.prims, stock.pins)
            self.body = (x0, -y1, x1, -y0)
            spec = spec_of(D.parts[ref]['value'])
            if not self.groups['R']:
                self.fields = [('Reference', x1 + 1.27, -(y0 + y1) / 2 - 1.27, 'left', ref),
                               ('Spec', x1 + 1.27, -(y0 + y1) / 2 + 1.27, 'left', spec)]
            else:
                self.fields = [('Reference', x0, -y1 - 3.81, 'left', ref), ('Spec', x0, -y1 - 1.524, 'left', spec)]
        else:
            self.stacked = False
            self.box_symbol()

    # pins whose attachments make a row taller
    def band(self, g):
        net = self.pins[g[0]]['net']
        D = self.D
        if D.is_nc(net):
            return 1.27, 1.27
        if net in SUPPLY:
            return 5.08, 1.27
        if net == 'GND':
            return 1.27, 5.08
        U = Dn = 1.27
        for s in self.shunts_of(g):
            if s.kind == 'down':
                Dn = max(Dn, s.baked.length + 4.9)
            elif s.kind == 'up':
                U = max(U, s.baked.length + 4.6)
            else:
                U = max(U, 5.08)
        return U, Dn

    def shunts_of(self, g):
        return [s for n in g for s in self.shunts.get(n, [])]

    def box_symbol(self):
        D, ref, pins = self.D, self.ref, self.pins
        order = sorted(pins, key=natural)
        conn = ref.startswith('J')
        top, bot, side = [], [], []
        for n in order:
            net = pins[n]['net']
            if not conn and net in SUPPLY:
                top.append(n)
            elif not conn and net == 'GND':
                bot.append(n)
            else:
                side.append(n)
        ncs = [n for n in side if D.is_nc(pins[n]['net'])]
        side = [n for n in side if n not in ncs] + ncs
        rank = {n: i for i, n in enumerate(POWER_NETS)}
        top.sort(key=lambda n: (rank[pins[n]['net']], natural(n)))
        def grouped(lst):
            out = []
            for n in lst:
                if out and pins[out[-1][-1]]['net'] == pins[n]['net'] and not D.is_nc(pins[n]['net']):
                    out[-1].append(n)
                else:
                    out.append([n])
            return out
        show_names = not all(p['name'] == n or p['name'].startswith(n + '_') for n, p in pins.items())
        name_w = lambda ns: max([textw(pins[n]['name']) for n in ns] or [0]) if show_names else 0.0
        top_res = snap_up(name_w(top) + 2.0) if top else P
        bot_res = snap_up(name_w(bot) + 2.0) if bot else P
        ends = {}

        def rows(groups, x, out):
            y, last, prev = None, None, None
            for g in groups:
                U, Dn = self.band(g)
                if y is None:
                    y = snap_up(max(top_res, U))
                else:
                    g0, d0 = prev
                    # GND symbols hang below the last pin of a group, everything else below the first
                    reach = d0 if pins[g0[0]]['net'] == 'GND' else d0 - (len(g0) - 1) * P
                    y = snap_up(last + max(P, max(1.27, reach) + U))
                for i, n in enumerate(g):
                    out[n] = (x, y + i * P)
                last = y + (len(g) - 1) * P
                prev = (g, Dn)
            return last if last is not None else top_res
        gside = grouped(side)
        if conn:
            gl, gr = [], gside
        else:                                # split the pin groups so both sides end at a similar height
            best = None
            for k in range(len(gside) + 1):
                h = max(rows(gside[:k], 0, {}), rows(gside[k:], 0, {}))
                score = (h, abs(sum(map(len, gside[:k])) - sum(map(len, gside[k:]))))
                if best is None or score < best[0]:
                    best = (score, k)
            gl, gr = gside[:best[1]], gside[best[1]:]
        L, R = [n for g in gl for n in g], [n for g in gr for n in g]
        gt, gb = grouped(top), grouped(bot)
        PL = 3.81 if conn else P
        spec = spec_of(D.parts[ref]['value'])
        ref_w = max(textw(ref), textw(spec))
        # widths
        w_side = name_w(L) + name_w(R) + 2 * 1.016 + (P if L and R else 1.27)
        x = snap_up(ref_w + P) if not conn else 0.0
        tops = []
        prev_w = None
        for g in gt:
            tw = textw(pins[g[0]]['net'])
            if prev_w is not None:
                x = snap_up(x + max(2 * P, (prev_w + tw) / 2 + 1.27))
            tops.append((g, x))
            x += (len(g) - 1) * P
            prev_w = tw
        w_top = x + P if gt else 0.0
        xb = P
        bots = []
        for g in gb:
            bots.append((g, xb))
            xb += len(g) * P + P
        w_bot = xb if gb else 0.0
        W = snap_up(max(w_side, w_top, w_bot, (5.08 if conn else 10.16)), P)
        if conn:
            W = snap_up(max(W, name_w(R) + 2.54), P)
        last_l = rows(gl, -PL, ends)
        last_r = rows(gr, W + PL, ends)
        H = snap_up(max(last_l, last_r) + bot_res, P)
        for g, x0 in tops:
            for i, n in enumerate(g):
                ends[n] = (x0 + i * P, -P)
        for g, x0 in bots:
            for i, n in enumerate(g):
                ends[n] = (x0 + i * P, H + P)
        self.groups = {'L': gl, 'R': gr, 'T': gt, 'B': gb}
        self.end = ends
        lpins = []
        for n in order:
            x, y = ends[n]
            side = 'L' if x < 0 else 'R' if x > W else ('T' if y < 0 else 'B')
            ang = {'L': 0, 'R': 180, 'T': 270, 'B': 90}[side]
            lpins.append(dict(type=pins[n]['type'], name=pins[n]['name'], num=n, x=x, y=-y, ang=ang,
                              len=PL if side in 'LR' else P))
        prim = (f'(rectangle (start 0 0) (end {W:g} {-H:g}) (stroke (width 0.254) (type default)) '
                f'(fill (type background)))')
        self.lib = LibSym(ref, lib_props(D, ref), [prim], lpins, show_names=show_names, show_numbers=True)
        self.body = (0.0, 0.0, W, H)
        self.fields = [('Reference', 0.0, -3.81, 'left', ref), ('Spec', 0.0, -1.524, 'left', spec)]
        if conn:
            self.fields = [('Reference', 0.0, -3.81, 'left', ref), ('Spec', 0.0, -1.524, 'left', spec)]


class Shunt:
    def __init__(self, ref, kind, pin_on_spine, net_other):
        self.ref, self.kind, self.a, self.other = ref, kind, pin_on_spine, net_other
        self.baked = None


# ------------------------------------------------------------------ planning
def plan(D):
    anchors, sats, flags = [], [], []
    for ref, p in D.parts.items():
        if ref.startswith('#'):
            flags.append(ref)
            continue
        pre = re.match(r'[A-Z]+', ref).group(0)
        if len(D.lib[p['lib']]['pins']) >= 3 or pre in ('J', 'U', 'Q', 'Y'):
            anchors.append(ref)
        else:
            sats.append(ref)
    block = {}
    for r in anchors + sats:
        m = re.match(r'[A-Z]+(\d+)$', r)
        if m and len(m.group(1)) >= 3 and m.group(1)[0] in SHEETS:
            block[r] = m.group(1)[0]
    for r in anchors:                              # anchors without a block follow their nets
        if r in block:
            continue
        votes = defaultdict(int)
        for (rr, pn), n in D.pin_net.items():
            if rr == r and n not in POWER_NETS:
                for r2, _ in D.net_pins[n]:
                    if r2 in block and r2 in anchors:
                        votes[block[r2]] += 1
        block[r] = max(votes, key=votes.get) if votes else '5'
    anchor_pins = defaultdict(list)
    for r in anchors:
        for n, p in D.pins(r).items():
            if p['net'] not in POWER_NETS and not D.is_nc(p['net']):
                anchor_pins[p['net']].append((r, n))
    power_pins = defaultdict(list)
    for r in anchors:
        for n, p in D.pins(r).items():
            if p['net'] in POWER_NETS:
                power_pins[p['net']].append((r, n))

    def nearest(ref, cands):
        if not cands:
            cands = [(a, None) for a in anchors]
        b = block.get(ref)
        same = [c for c in cands if block.get(c[0]) == b]
        cands = same or cands
        sp = D.where(ref)
        return min(cands, key=lambda c: (math.dist(D.where(c[0], c[1]), sp), c[0], c[1] or ''))

    shunts = defaultdict(lambda: defaultdict(list))      # anchor -> pin -> [Shunt]
    banks = defaultdict(lambda: defaultdict(list))       # anchor -> bank key -> [(ref, info)]
    # power flags missing on power nets without an output-power pin (ERC needs a driver for power symbols)
    flagged = {D.pin_net[(f, '1')] for f in flags}
    outputs = {n for n, ps in D.net_pins.items() if any(D.lib[D.parts[r]['lib']]['pins'][p]['type'] == 'power_out'
                                                         for r, p in ps if r in D.parts)}
    proto = D.parts[flags[0]]
    k = max(int(re.search(r'\d+', f).group(0)) for f in flags)
    for net in POWER_NETS:
        if net not in flagged and net not in outputs:
            k += 1
            ref = f'#FLG{k}'
            D.parts[ref] = dict(proto, ref=ref, uuid=uid('flag', net),
                                props=[(a, ref if a == 'Reference' else b) for a, b in proto['props']])
            D.pin_net[(ref, '1')] = net
            D.net_pins[net].append((ref, '1'))
            flags.append(ref)
    for ref in sats + flags:
        pins = D.pins(ref) if not ref.startswith('#') else {'1': dict(net=D.pin_net[(ref, '1')])}
        nets = [(n, pins[n]['net']) for n in sorted(pins, key=natural)]
        pw = [(n, net) for n, net in nets if net in POWER_NETS]
        sg = [(n, net) for n, net in nets if net not in POWER_NETS]
        if len(nets) == 1:
            n, net = nets[0]
            kind = 'flag' if ref.startswith('#') else 'tp'
            if net not in POWER_NETS and anchor_pins.get(net):
                a, ap = nearest(ref, anchor_pins[net])
                shunts[a][ap].append(Shunt(ref, kind, n, None))
            else:
                a, _ = nearest(ref, power_pins.get(net) if net in POWER_NETS else [])
                banks[a][('tp',)].append((ref, dict(pin=n, net=net, kind=kind)))
        elif len(pw) == 2:
            top = next(((n, net) for n, net in pw if net != 'GND'), pw[0])
            bot = next((n, net) for n, net in pw if n != top[0])
            a, _ = nearest(ref, power_pins.get(top[1]))
            banks[a][('decap', top[1], bot[1])].append((ref, dict(top=top[0], bot=bot[0])))
        elif len(pw) == 1:
            (pn, pnet), (sn, snet) = pw[0], sg[0]
            kind = 'down' if pnet == 'GND' else 'up'
            if anchor_pins.get(snet):
                a, ap = nearest(ref, anchor_pins[snet])
                shunts[a][ap].append(Shunt(ref, kind, sn, pnet))
            else:
                a, _ = nearest(ref, [])
                banks[a][('pull', pnet)].append((ref, dict(pin=pn, sig=sn)))
        else:
            cands = [c for _, net in sg for c in anchor_pins.get(net, [])]
            a, _ = nearest(ref, cands)
            banks[a][('series',)].append((ref, dict()))
    # at most four shunts per pin; the rest go to banks of the same anchor
    for a, per in shunts.items():
        for ap, lst in per.items():
            for s in lst[4:]:
                move_to_bank(D, banks[a], s)
            del lst[4:]
    return anchors, block, shunts, banks


def move_to_bank(D, banks, s):
    if s.kind in ('tp', 'flag'):
        net = D.pin_net[(s.ref, s.a)]
        banks[('tp',)].append((s.ref, dict(pin=s.a, net=net, kind=s.kind)))
    else:
        other = next(n for n in D.pins(s.ref) if n != s.a)
        banks[('pull', s.other)].append((s.ref, dict(pin=other, sig=s.a)))



# ------------------------------------------------------------------ drawing a cluster
def flag_lib():
    prims, _ = STOCK['PWR_FLAG']
    return LibSym('POWER_SOURCE', [('Reference', '#FLG', True), ('Value', 'POWER_SOURCE', False)], prims,
                  [dict(type='power_out', name='pwr', num='1', x=0, y=0, ang=90, len=0)], power=True)


def power_lib(net):
    prims, _ = STOCK['GND' if net == 'GND' else '+3V3']
    pin = dict(type='power_in', name=net, num='1', x=0, y=0, ang=270 if net == 'GND' else 90, len=0, hide=True)
    return LibSym('PWR_' + net, [('Reference', '#PWR', True), ('Value', net, False)], prims, [pin], power=True)


def half_w(b):
    return max(abs(b.box[0] - b.pa['x']), abs(b.box[2] - b.pa['x']), 1.016) + 0.635


def text_fields(ref, spec, at_x, y_mid, sgn, origin, off=1.905):
    tx = at_x + sgn * off
    just = 'left' if sgn > 0 else 'right'
    return [('Reference', tx - origin[0], y_mid - 1.27 - origin[1], just, ref),
            ('Spec', tx - origin[0], y_mid + 1.27 - origin[1], just, spec)]


def abs_box(o, box):
    return (o[0] + box[0], o[1] + box[1], o[0] + box[2], o[1] + box[3])


def place_shunt(d, D, s, at, sgn, reg):
    ref = s.ref
    spec = spec_of(D.parts[ref]['value'])
    if s.kind in ('down', 'up'):
        down = s.kind == 'down'
        b = Baked(D, ref, s.a, (0, 1) if down else (0, -1))
        s.baked = b
        reg[ref] = b.lib
        o, e = b.origin_for(at), b.other_end(at)
        d.power(s.other, e)
        mid = at[1] + (b.length / 2 if down else -b.length / 2)
        off = half_w(b)
        d.sym(ref, o, text_fields(ref, spec, at[0], mid, sgn, o, off), abs_box(o, b.box))
        return off + max(textw(ref), textw(spec))
    if s.kind == 'tp':
        b = Baked(D, ref, s.a, (0, -1))
        reg[ref] = b.lib
        o = b.origin_for(at)
        just = 'left' if sgn > 0 else 'right'
        d.sym(ref, o, [('Reference', at[0] + sgn * 1.905 - o[0], at[1] - 3.3 - o[1], just, ref)], abs_box(o, b.box))
        return 1.905 + textw(ref)
    reg['POWER_SOURCE'] = flag_lib()
    just = 'left' if sgn > 0 else 'right'
    d.sym(ref, at, [('Value', sgn * 1.905, -2.2, just, 'POWER_SOURCE')], (at[0] - 1.1, at[1] - 2.6, at[0] + 1.1, at[1]))
    return 1.905 + textw('POWER_SOURCE')


def pre_bake(D, shunts):
    # shunt lengths are needed for row bands before the anchor symbol exists
    for lst in shunts.values():
        for s in lst:
            if s.kind in ('down', 'up'):
                s.baked = Baked(D, s.ref, s.a, (0, 1) if s.kind == 'down' else (0, -1))


def side_group(d, D, A, g, sgn, reg):
    net = A.pins[g[0]]['net']
    pts = []
    for n in g:
        if A.end[n] not in pts:
            pts.append(A.end[n])
    if D.is_nc(net):
        for p in pts:
            d.nc(p)
        return
    for a, b in zip(pts, pts[1:]):
        d.wire(a, b)
    if net in POWER_NETS:
        p = pts[-1] if net == 'GND' else pts[0]
        stub = snap_up(max(P, textw(net) / 2 + 0.8))
        e = (p[0] + sgn * stub, p[1])
        d.wire(p, e)
        d.power(net, e)
        return
    p = pts[0]
    cur, atts, end = 5.08, [], P
    for s in A.shunts_of(g):
        ua = snap_up(cur)
        at = (round(p[0] + sgn * ua, 4), p[1])
        span = place_shunt(d, D, s, at, sgn, reg)
        atts.append(at)
        cur = ua + span + 2.54
        end = snap_up(ua + span + 1.27)
    e = (round(p[0] + sgn * end, 4), p[1])
    d.path([p] + atts + [e])
    d.label(net, e, 0 if sgn > 0 else 180)


def vert_group(d, D, A, g, side, extra):
    net = A.pins[g[0]]['net']
    pts = []
    for n in g:
        if A.end[n] not in pts:
            pts.append(A.end[n])
    sv = -1 if side == 'T' else 1
    for s in A.shunts_of(g):                    # vertical pins carry no inline parts
        extra.append(s)
    if D.is_nc(net):
        for p in pts:
            d.nc(p)
        return
    if net in POWER_NETS:
        wrong = (side == 'T') == (net == 'GND')
        if len(pts) == 1 and not wrong:
            d.power(net, pts[0])
            return
        yb = pts[0][1] + sv * P
        bar = [(p[0], yb) for p in pts]
        for p, b in zip(pts, bar):
            d.wire(p, b)
        d.path(bar)
        if wrong:
            e = (bar[-1][0] + 2 * P, yb)
            d.wire(bar[-1], e)
            d.power(net, e)
        else:
            d.power(net, bar[(len(bar) - 1) // 2])
        return
    for p in pts:
        e = (p[0], p[1] + sv * P)
        d.wire(p, e)
        d.label(net, e, 90 if side == 'T' else 270)


def bank_decap(D, items, top, bot, reg):
    d = Draw()
    x, tops, ends = 0.0, [], []
    for ref, info in items:
        b = Baked(D, ref, info['top'], (0, 1))
        reg[ref] = b.lib
        at = (x, 0.0)
        o, e = b.origin_for(at), b.other_end(at)
        spec = spec_of(D.parts[ref]['value'])
        off = half_w(b)
        d.sym(ref, o, text_fields(ref, spec, x, b.length / 2, 1, o, off), abs_box(o, b.box))
        tops.append(at)
        ends.append(e)
        x = snap_up(x + max(5.08, off + max(textw(ref), textw(spec)) + 2.54))
    yb = max(e[1] for e in ends)
    for e in ends:
        d.wire(e, (e[0], yb))
    d.path(tops)
    d.path([(e[0], yb) for e in ends])
    d.power(top, tops[0])
    if bot == 'GND':
        d.power(bot, (ends[0][0], yb))
    else:
        q2 = (ends[0][0] - 2 * P, yb)
        d.wire((ends[0][0], yb), q2)
        d.power(bot, q2)
    return d


def bank_pull(D, items, pnet, reg):
    d = Draw()
    x, rail, ends = 0.0, [], []
    for ref, info in items:
        sig_net = D.pin_net[(ref, info['sig'])]
        spec = spec_of(D.parts[ref]['value'])
        if pnet == 'GND':
            b = Baked(D, ref, info['sig'], (0, 1))
            at = (x, 0.0)
            o, e = b.origin_for(at), b.other_end(at)
            lab = (x, -P)
            d.wire(at, lab)
            d.label(sig_net, lab, 90)
            rail.append(e)
        else:
            b = Baked(D, ref, info['pin'], (0, 1))
            at = (x, 0.0)
            o, e = b.origin_for(at), b.other_end(at)
            lab = (e[0], e[1] + P)
            d.wire(e, lab)
            d.label(sig_net, lab, 270)
            rail.append(at)
        reg[ref] = b.lib
        off = half_w(b)
        d.sym(ref, o, text_fields(ref, spec, x, b.length / 2, 1, o, off), abs_box(o, b.box))
        x = snap_up(x + max(5.08, off + max(textw(ref), textw(spec)) + 2.54))
    yr = rail[0][1]
    d.path(rail)
    d.power(pnet, rail[0])
    return d


def bank_series(D, items, reg):
    d = Draw()
    y = 0.0
    for ref, _ in items:
        nums = sorted(D.pins(ref), key=natural)
        b = Baked(D, ref, nums[0], (1, 0))
        reg[ref] = b.lib
        at = (0.0, y)
        o, e = b.origin_for(at), b.other_end(at)
        for pt, num, sgn in ((at, nums[0], -1), (e, nums[1], 1)):
            net = D.pin_net[(ref, num)]
            if D.is_nc(net):
                d.nc(pt)
                continue
            lab = (pt[0] + sgn * P, pt[1])
            d.wire(pt, lab)
            d.label(net, lab, 0 if sgn > 0 else 180)
        spec = spec_of(D.parts[ref]['value'])
        cx = b.length / 2
        d.sym(ref, o, [('Reference', cx - o[0], y - 2.54 - o[1], 'center', ref),
                       ('Spec', cx - o[0], y + 2.54 - o[1], 'center', spec)], abs_box(o, b.box))
        y += 3 * P
    return d


def bank_tp(D, items, reg):
    d = Draw()
    y = 0.0
    for ref, info in items:
        net, pt = info['net'], (0.0, y)
        if info['kind'] == 'tp':
            b = Baked(D, ref, info['pin'], (0, -1))
            reg[ref] = b.lib
            o = b.origin_for(pt)
            d.sym(ref, o, [('Reference', 1.905 - o[0], y - 3.3 - o[1], 'left', ref)], abs_box(o, b.box))
        else:
            reg['POWER_SOURCE'] = flag_lib()
            d.sym(ref, pt, [('Value', 1.905, -2.2, 'left', 'POWER_SOURCE')], (-1.1, y - 2.6, 1.1, y))
        if net == 'GND':
            d.power(net, pt)
        elif net in SUPPLY:
            q2 = (-snap_up(textw(net) / 2 + 2.54), y)
            d.wire(pt, q2)
            d.power(net, q2)
        else:
            d.label(net, pt, 180)
        y += 4 * P
    return d


BANK_LIMIT = {'decap': 8, 'pull': 8, 'series': 12, 'tp': 8}


def build_cluster(D, ref, shunts, banks, reg):
    pre_bake(D, shunts)
    A = Anchor(D, ref, shunts)
    reg[ref] = A.lib
    d = Draw()
    x0, y0, x1, y1 = A.body
    for p in A.end.values():
        d.ext(p[0], p[1], p[0], p[1])
    d.sym(ref, (0.0, 0.0), A.fields, (x0, y0, x1, y1))
    extra = []
    for side, sgn in (('L', -1), ('R', 1)):
        for g in A.groups.get(side, []):
            side_group(d, D, A, g, sgn, reg)
    for side in ('T', 'B'):
        for g in A.groups.get(side, []):
            vert_group(d, D, A, g, side, extra)
    for s in extra:
        move_to_bank(D, banks, s)
    # banks stacked in columns to the right of the anchor
    base = list(d.box)
    colx, y, colw = base[2] + 7.62, base[1], 0.0
    maxh = max(base[3] - base[1], 60.0)
    for key in sorted(banks, key=lambda k: (['decap', 'pull', 'tp', 'series'].index(k[0]), k)):
        items = banks[key]
        lim = BANK_LIMIT[key[0]]
        for i in range(0, len(items), lim):
            chunk = items[i:i + lim]
            if key[0] == 'decap':
                bd = bank_decap(D, chunk, key[1], key[2], reg)
            elif key[0] == 'pull':
                bd = bank_pull(D, chunk, key[1], reg)
            elif key[0] == 'series':
                bd = bank_series(D, chunk, reg)
            else:
                bd = bank_tp(D, chunk, reg)
            if y > base[1] and y + bd.h > base[1] + maxh:
                colx, y, colw = colx + colw + 7.62, base[1], 0.0
            d.merge(bd.shifted(colx - bd.box[0], y - bd.box[1]))
            y += bd.h + 7.62
            colw = max(colw, bd.w)
    return d


# ------------------------------------------------------------------ pages
def pack(clusters, W, H):
    """Shelf packing inside the drawing frame, keeping clear of the title block; None if it does not fit."""
    x0, y0, x1, y1 = 20.0, 35.56, W - 20.0, H - 20.0
    tb = (W - 20.0 - 120.0, H - 20.0 - 40.0)          # title block corner
    out, x, y, row_h = [], x0, y0, 0.0
    for c in clusters:
        if c.w > x1 - x0:
            return None
        while True:
            if x > x0 and x + c.w > x1:
                x, y, row_h = x0, y + row_h + 12.7, 0.0
            if y + c.h > y1:
                return None
            if x + c.w > tb[0] and y + c.h > tb[1]:          # would cover the title block
                if x == x0:
                    return None
                x, y, row_h = x0, y + row_h + 12.7, 0.0
                continue
            break
        out.append((c, x - x0, y - y0))
        x += c.w + 15.24
        row_h = max(row_h, c.h)
    return out


def fit(clusters):
    orders = [clusters, sorted(clusters, key=lambda c: -c.h)]
    for name, W, H in PAPERS[:2]:                        # A4, then A3
        for o in orders:
            placed = pack(o, W, H)
            if placed:
                return (name, W, H, placed)
    return None


def paginate(clusters):
    one = fit(clusters)
    if one:
        return [one]
    pages, cur = [], []                                  # several A3 pages, in drawing order
    for c in clusters:
        if cur and not fit(cur + [c]):
            pages.append(cur)
            cur = []
        cur.append(c)
    pages.append(cur)
    out = []
    for p in pages:
        f = fit(p)
        if not f:                                        # a single oversize cluster
            name, W, H = PAPERS[-1]
            f = (name, W, H, pack(p, W, H) or [(p[0], 0.0, 0.0)])
        out.append(f)
    return out


# ------------------------------------------------------------------ emission
def fmt(v):
    return f'{v:.4f}'.rstrip('0').rstrip('.')


def effects(just=None, hide=False):
    j = f' (justify {just})' if just and just != 'center' else ''
    return f'{"(hide yes) " if hide else ""}(effects (font (size 1.27 1.27)){j})'


def part_instance(D, ref, origin, fields, path):
    p = D.parts[ref]
    vis = {f[0]: f for f in fields}
    x, y = origin
    out = [f'(symbol (lib_id {q(p["lib"])}) (at {fmt(x)} {fmt(y)} 0) (unit 1) (exclude_from_sim no) '
           f'(in_bom {p["flags"]["in_bom"]}) (on_board {p["flags"]["on_board"]}) (dnp {p["flags"]["dnp"]}) '
           f'(uuid {q(p["uuid"])})']
    for k, v in p['props']:
        if k in vis:
            _, dx, dy, just, _ = vis[k]
            out.append(f'(property {q(k)} {q(v)} (at {fmt(x + dx)} {fmt(y + dy)} 0) {effects(just)})')
        else:
            out.append(f'(property {q(k)} {q(v)} (at {fmt(x)} {fmt(y)} 0) {effects(hide=True)})')
    if 'Spec' in vis:
        _, dx, dy, just, s = vis['Spec']
        out.append(f'(property "Spec" {q(s)} (at {fmt(x + dx)} {fmt(y + dy)} 0) {effects(just)})')
    out.append(f'(instances (project {q(PROJECT)} (path {q(path)} (reference {q(ref)}) (unit 1)))))')
    return ' '.join(out)


def power_instance(net, p, ref, path, key):
    x, y = p
    vy = y + 3.81 if net == 'GND' else y - 3.556
    return (f'(symbol (lib_id {q("Panda7:PWR_" + net)}) (at {fmt(x)} {fmt(y)} 0) (unit 1) (exclude_from_sim no) '
            f'(in_bom no) (on_board no) (dnp no) (uuid {q(uid("pwr", key))}) '
            f'(property "Reference" {q(ref)} (at {fmt(x)} {fmt(y)} 0) {effects(hide=True)}) '
            f'(property "Value" {q(net)} (at {fmt(x)} {fmt(vy)} 0) {effects()}) '
            f'(property "Footprint" "" (at {fmt(x)} {fmt(y)} 0) {effects(hide=True)}) '
            f'(property "Datasheet" "" (at {fmt(x)} {fmt(y)} 0) {effects(hide=True)}) '
            f'(instances (project {q(PROJECT)} (path {q(path)} (reference {q(ref)}) (unit 1)))))')


# 版本信息由构建器设置（R49 构建器沿用默认值）
REVISION = {'version': 'v0.1.2', 'revision': 'R49', 'date': '2026-11-06'}
PRODUCT = 'Single'                 # product name in title blocks / index page
BOARD_DESC = '71 x 99 mm 4-layer'


def title_block(sub, rev):
    v = REVISION
    return (f'(title_block (title {q(sub)}) (date {q(v["date"])}) (rev {q(rev)}) '
            f'(company "Panda Intelligence") (comment 1 "Panda Standard 4.7 {PRODUCT} {v["version"]} / {v["revision"]}, {BOARD_DESC}") '
            f'(comment 2 "Netlist identical to the {v["revision"]} board; drawn by readable_schematic.py"))')


def emit_sheet(D, reg, draw, paper, sub, path, file_uuid, pwr_seq, rev):
    syms, body = [], []
    used = set()
    pin_pts = defaultdict(int)
    for it in draw.items:
        if it[0] == 'sym':
            ref, o, fields = it[1], it[2], it[3]
            base = D.parts[ref]['lib'].split(':', 1)[1]
            used.add(base)
            for pn in reg[base].pins:
                pin_pts[(round(o[0] + pn['x'], 3), round(o[1] - pn['y'], 3))] += 1
            syms.append(part_instance(D, ref, o, fields, path))
        elif it[0] == 'pwr':
            net, p = it[1], it[2]
            used.add('PWR_' + net)
            reg.setdefault('PWR_' + net, power_lib(net))
            pwr_seq[0] += 1
            ref = f'#PWR{pwr_seq[0]:04d}'
            pin_pts[(round(p[0], 3), round(p[1], 3))] += 1
            syms.append(power_instance(net, p, ref, path, (path, ref)))
    ends = defaultdict(int)
    for it in draw.items:
        if it[0] == 'wire':
            a, b = it[1], it[2]
            ends[(round(a[0], 3), round(a[1], 3))] += 1
            ends[(round(b[0], 3), round(b[1], 3))] += 1
            body.append(f'(wire (pts (xy {fmt(a[0])} {fmt(a[1])}) (xy {fmt(b[0])} {fmt(b[1])})) '
                        f'(stroke (width 0) (type default)) (uuid {q(uid("w", path, a, b))}))')
        elif it[0] == 'label':
            net, p, ang = it[1], it[2], it[3]
            just = 'left' if ang in (0, 90) else 'right'
            body.append(f'(global_label {q(net)} (shape passive) (at {fmt(p[0])} {fmt(p[1])} {ang}) '
                        f'(fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {just})) '
                        f'(uuid {q(uid("gl", path, net, p, ang))}) '
                        f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {fmt(p[0])} {fmt(p[1])} 0) '
                        f'(effects (font (size 1.27 1.27)) (hide yes))))')
        elif it[0] == 'nc':
            p = it[1]
            body.append(f'(no_connect (at {fmt(p[0])} {fmt(p[1])}) (uuid {q(uid("nc", path, p))}))')
        elif it[0] == 'text':
            s, p, size, bold = it[1], it[2], it[3], it[4]
            body.append(f'(text {q(s)} (exclude_from_sim no) (at {fmt(p[0])} {fmt(p[1])} 0) '
                        f'(effects (font (size {size} {size}){" (thickness 0.5) bold" if bold else ""}) (justify left)) '
                        f'(uuid {q(uid("t", path, s, p))}))')
    for p, n in ends.items():
        if n >= 3 or (n >= 2 and pin_pts.get(p)):
            body.append(f'(junction (at {fmt(p[0])} {fmt(p[1])}) (diameter 0) (color 0 0 0 0) (uuid {q(uid("j", path, p))}))')
    libs = ' '.join(reg[b].text('Panda7:' + b) for b in sorted(used))
    name, W, H = paper
    head = [f'(version 20250114)', '(generator "eeschema")', '(generator_version "9.0")', f'(uuid {q(file_uuid)})',
            f'(paper {q(name)})' if name in ('A4', 'A3', 'A2', 'A1') else f'(paper "User" {fmt(W)} {fmt(H)})',
            title_block(sub, rev), f'(lib_symbols {libs})']
    return '(kicad_sch\n' + '\n'.join(head + syms + body + ['(embedded_fonts no)']) + '\n)\n'


def footprint_specs(sch_dir, stem='Single'):
    """Spec text of every on-board part in the generated sheets, for syncing to the board footprints."""
    out = {}
    for f in sorted(Path(sch_dir).glob(stem + '-*.kicad_sch')):
        text = f.read_text()
        for h, a, b in top_items(text):
            if h != 'symbol':
                continue
            s = text[a:b]
            ref = re.search(r'\(property "Reference" "([^"]+)"', s).group(1)
            m = re.search(r'\(property "Spec" "((?:[^"\\]|\\.)*)"', s)
            if m and not ref.startswith('#') and '(on_board yes)' in s:
                out[ref] = m.group(1).replace('\\"', '"').replace('\\\\', '\\')
    return out


# ------------------------------------------------------------------ main
def main(inp, netp, outp, pcbp=None):
    outp = Path(outp)
    pcbp = pcbp or outp.with_suffix('.kicad_pcb')
    D = Design(inp, netp, pcbp)
    root_uuid = re.search(r'\(uuid "([^"]+)"\)', D.text).group(1)
    anchors, block, shunts, banks = plan(D)
    reg = {}
    sheet_clusters = defaultdict(list)
    rank = {'U': 0, 'J': 1, 'Q': 2, 'D': 3, 'Y': 4}
    order = sorted(anchors, key=lambda r: (block[r], rank.get(re.match(r'[A-Z]+', r).group(0), 9),
                                           -len(D.pins(r)), natural(re.sub(r'^[A-Z]+', '', r) or '0')))
    for ref in order:
        c = build_cluster(D, ref, shunts[ref], banks[ref], reg)
        sheet_clusters[block[ref]].append(c)
    reg['POWER_SOURCE'] = flag_lib()
    rev = f'{REVISION["version"]} / {REVISION["revision"]}'
    pages = []                                     # (key, file, sheetname, title, paper, draw)
    for key in sorted(sheet_clusters):
        suffix, sname, title = SHEETS[key]
        laid = paginate(sheet_clusters[key])
        for i, (pname, W, H, placed) in enumerate(laid):
            d = Draw()
            t = title if len(laid) == 1 else f'{title} ({i + 1}/{len(laid)})'
            d.text(t, (20.0, 22.0), 3.0, True)
            for c, x, y in placed:
                d.merge(c.shifted(20.0 + x - c.box[0], 35.56 + y - c.box[1]))
            sfx = suffix if len(laid) == 1 else f'{suffix}{i + 1}'
            nm = sname if len(laid) == 1 else f'{sname}_{i + 1}'
            pages.append((sfx, nm, t, (pname, W, H), d))
    out_dir = outp.parent
    sheets_txt = []
    pwr_seq = [0]
    for idx, (sfx, nm, t, paper, d) in enumerate(pages):
        su = uid('sheet', nm)
        fname = f'{outp.stem}-{sfx}.kicad_sch'
        path = f'/{root_uuid}/{su}'
        (out_dir / fname).write_text(emit_sheet(D, reg, d, paper, t, path, uid('file', nm), pwr_seq, rev))
        col, row = idx % 3, idx // 3
        x, y = 22.86 + col * 88.9, 53.34 + row * 25.4
        sheets_txt.append(
            f'(sheet (at {fmt(x)} {fmt(y)}) (size 76.2 12.7) (exclude_from_sim no) (in_bom yes) (on_board yes) '
            f'(dnp no) (fields_autoplaced yes) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) '
            f'(uuid {q(su)}) '
            f'(property "Sheetname" {q(nm)} (at {fmt(x)} {fmt(y - 0.7116)} 0) (effects (font (size 1.27 1.27)) (justify left bottom))) '
            f'(property "Sheetfile" {q(fname)} (at {fmt(x)} {fmt(y + 13.2916)} 0) (effects (font (size 1.27 1.27)) (justify left top))) '
            f'(instances (project {q(PROJECT)} (path {q("/" + root_uuid)} (page {q(str(idx + 2))})))))')
        sheets_txt.append(f'(text {q(t)} (exclude_from_sim no) (at {fmt(x + 2.54)} {fmt(y + 6.35)} 0) '
                          f'(effects (font (size 1.6 1.6)) (justify left)) (uuid {q(uid("st", nm))}))')
    head = ['(version 20250114)', '(generator "eeschema")', '(generator_version "9.0")', f'(uuid {q(root_uuid)})',
            '(paper "A4")', title_block('Index', rev), '(lib_symbols)',
            f'(text "Panda Standard 4.7 {PRODUCT} main board schematic ({REVISION["version"]} / {REVISION["revision"]})" (exclude_from_sim no) (at 25.4 30.48 0) '
            f'(effects (font (size 3.5 3.5) (thickness 0.6) bold) (justify left)) (uuid {q(uid("root-title"))}))',
            f'(text "Sheets connect through global labels and power symbols of the same name; the netlist matches the {REVISION["revision"]} PCB exactly." (exclude_from_sim no) (at 25.4 38.1 0) '
            f'(effects (font (size 1.8 1.8)) (justify left)) (uuid {q(uid("root-note"))}))']
    outp.write_text('(kicad_sch\n' + '\n'.join(head + sheets_txt +
                                                ['(sheet_instances (path "/" (page "1")))', '(embedded_fonts no)']) + '\n)\n')
    # library: every generated symbol, power symbols and the power flag
    for net in POWER_NETS:
        reg.setdefault('PWR_' + net, power_lib(net))
    lib = '(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n' + \
          '\n'.join(reg[b].text(b) for b in sorted(reg)) + '\n)\n'
    (out_dir / 'Panda7.kicad_sym').write_text(lib)
    n_wires = sum(1 for _, _, _, _, d in pages for it in d.items if it[0] == 'wire')
    n_labels = sum(1 for _, _, _, _, d in pages for it in d.items if it[0] == 'label')
    print(f'{len(D.parts)} symbols on {len(pages)} pages ({", ".join(p[3][0] for p in pages)}), '
          f'{n_wires} wires, {n_labels} labels, {pwr_seq[0]} power symbols')
    return [out_dir / f'{outp.stem}-{p[0]}.kicad_sch' for p in pages]


if __name__ == '__main__':
    main(*sys.argv[1:5])
