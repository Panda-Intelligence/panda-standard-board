#!/usr/bin/env python3
"""2026-11-08 Claude：R50，整板 SMT 物料改为嘉立创现货，并按现货重做墨水屏 PMIC 与前光驱动。

用户 2026-11-08 要求：所有 SMT/BOM 都在嘉立创库存内，并尽量降低器件高度。
- `single_r50_jlc_stock_delta.json`：同封装、同焊盘、同网络的现货换料（含 L401/L402 改 1.2 mm 低高度电感）。
- `single_r50_pmic_frontlight_delta.json`：
  * U810 SY7636ARMC（无货）改 TI TPS651851RSLR，同一 6x6 QFN-48 焊盘：WAKEUP/DGND/VCOM_PWR/PBKG/
    VEE_IN/VDDH_IN/VPOS_IN 与裸焊盘(VN) 新接线，R804 下端改接 GND，R805 不贴，泵电容与参考电容按 TI 典型值；
  * U905 SGM37601（无货）改 AWINIC AW99703CSR（与 TI LM3697 引脚兼容），WLCSP-12 原位放置，C922 不贴。
铜改动以“网络 + 窗口”几何规则表达（回放铜的 UUID 每次重建都会变化），全部由 router2 / power_connect 生成后固化。
起点为 R49 网表式回放（readable=False），最后才转换为常规多页原理图。生成物只写入 .work 或外部目录，
manufacturing_release 保持 false。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
import uuid as uuidlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_pico47_single as B
import build_pico47_single_r49 as R49
from verify_mainland_bom_compliance import _balanced_end, patch_pcb_or_mod_text, patch_schematic_text

STOCK = HERE / 'r25_router' / 'single_r50_jlc_stock_delta.json'
ECO = HERE / 'r25_router' / 'single_r50_pmic_frontlight_delta.json'
NS = uuidlib.UUID('6f1b8a52-6c4e-4f53-9d1c-2f0b5a1e5050')


def uid(*parts):
    return str(uuidlib.uuid5(NS, '/'.join(map(str, parts))))


# ---------------------------------------------------------------- 物料字段

def part_fields(stock, eco):
    """ref -> {field: value}，换料与 PMIC/前光器件身份合并；同一位号不得重复。"""
    out = {}
    for group in stock['substitutions']:
        to = group['to']
        fields = {'Manufacturer': to['manufacturer'], 'MPN': to['mpn'], 'LCSC': to['lcsc'],
                  'Datasheet': group['datasheet'], 'PandaSupplyRoute': 'JLC_ASSEMBLY_STOCK',
                  'PandaSupplyStatus': 'JLC_STOCK_20261108'}
        if 'value' in to:
            fields['Value'] = to['value']
        if 'description' in group:
            fields['Description'] = group['description']
        for ref in group['refs']:
            B.require(ref not in out, 'Duplicate R50 part edit ' + ref)
            out[ref] = dict(fields)
    for ref, fields in eco['part_fields'].items():
        B.require(ref not in out, 'Duplicate R50 part edit ' + ref)
        out[ref] = dict(fields)
    return out


# ---------------------------------------------------------------- 网表式原理图

def _blocks(text, head):
    for m in re.finditer(re.escape(head), text):
        yield m.start(), _balanced_end(text, m.start())


def _lib_symbol(text, ref):
    start = text.index(f'(symbol "Panda7:{ref}"')
    return start, _balanced_end(text, start)


def _instance(text, ref):
    m = re.search(r'\(symbol\(lib_id "Panda7:%s"\)\(at ([-\d.]+) ([-\d.]+) (\d+)\)' % re.escape(ref), text)
    B.require(m and m.group(3) == '0', 'Unexpected symbol placement ' + ref)
    return float(m.group(1)), float(m.group(2)), m.start(), _balanced_end(text, m.start())


def _pins(text, ref):
    s, e = _lib_symbol(text, ref)
    pins = {}
    for m in re.finditer(r'\(pin (\w+) line \(at ([-\d.]+) ([-\d.]+) (\d+)\) \(length [\d.]+\) \(name "([^"]*)"'
                         r'.*?\(number "([^"]+)"', text[s:e]):
        pins[m.group(6)] = dict(type=m.group(1), x=float(m.group(2)), y=float(m.group(3)), ang=int(m.group(4)),
                                name=m.group(5), start=s + m.start(), end=s + m.start() + len(m.group(0)))
    return pins


def _marker_at(text, x, y):
    """Global label or no-connect whose anchor is the pin end (x, y)."""
    pat = re.compile(r'\((global_label "([^"]*)" \(shape passive\)\(at ([-\d.]+) ([-\d.]+) (\d+)\)|no_connect\(at ([-\d.]+) ([-\d.]+)\))')
    hits = []
    for m in pat.finditer(text):
        mx, my = (m.group(3), m.group(4)) if m.group(2) is not None else (m.group(6), m.group(7))
        if abs(float(mx) - x) < 1e-3 and abs(float(my) - y) < 1e-3:
            hits.append((m.start(), _balanced_end(text, m.start()), m.group(2)))
    B.require(len(hits) == 1, f'Expected one marker at {x:.4f},{y:.4f}, found {len(hits)}')
    return hits[0]


def _label(net, x, y, ang, key):
    return (f'(global_label "{net}" (shape passive)(at {x:.4f} {y:.4f} {ang}) '
            f'(effects (font (size 0.9 0.9))(justify left))(uuid "{uid("label", key)}"))')


def _no_connect(x, y, key):
    return f'(no_connect(at {x:.4f} {y:.4f})(uuid "{uid("nc", key)}"))'


def set_pin_net(text, ref, num, net):
    X, Y, _, _ = _instance(text, ref)
    pin = _pins(text, ref)[num]
    x, y = X + pin['x'], Y - pin['y']
    s, e, old = _marker_at(text, x, y)
    new = _label(net, x, y, 0 if pin['ang'] == 0 else 180, f'{ref}.{num}') if net else _no_connect(x, y, f'{ref}.{num}')
    return text[:s] + new + text[e:], old


def set_pin_type_and_name(text, ref, num, ptype=None, name=None):
    pin = _pins(text, ref)[num]
    seg = text[pin['start']:pin['end']]
    if ptype:
        seg = seg.replace(f'(pin {pin["type"]} line', f'(pin {ptype} line', 1)
    if name is not None:
        seg = seg.replace(f'(name "{pin["name"]}"', f'(name "{name}"', 1)
    return text[:pin['start']] + seg + text[pin['end']:]


def replace_u905_symbol(text, eco):
    """SGM37601 (21 pins) -> AW99703 (12 balls): new library symbol, same instance, new pin markers."""
    X, Y, _, _ = _instance(text, 'U905')
    for num, pin in _pins(text, 'U905').items():
        s, e, _ = _marker_at(text, X + pin['x'], Y - pin['y'])
        text = text[:s] + text[e:]
    pins = eco['u905']['pins']
    left = ['A1', 'A2', 'A3', 'B2', 'B3', 'D3']
    right = ['B1', 'C1', 'D1', 'D2', 'C2', 'C3']
    rows = [7.62, 5.08, 2.54, 0.0, -2.54, -5.08]
    body = ''.join(
        f'(pin passive line (at {sx} {y} {ang}) (length 2.54) (name "{pins[n][0]}" (effects (font (size 0.85 0.85))))'
        f'(number "{n}" (effects (font (size 0.85 0.85)))))'
        for side, sx, ang in ((left, -12.7, 0), (right, 12.7, 180)) for n, y in zip(side, rows))
    s, e = _lib_symbol(text, 'U905')
    old = text[s:e]
    head = old[:old.index('(symbol "U905_0_1"')]
    head = re.sub(r'\(property "Value" "[^"]*"', '(property "Value" "AW99703CSR"', head)
    new = (head + '(symbol "U905_0_1"(rectangle(start -10.16 10.16)(end 10.16 -7.62)(stroke(width .254)(type default))'
           '(fill(type background))))(symbol "U905_1_1"' + body + '))')
    text = text[:s] + new + text[e:]
    markers = []
    for side, sx, ang in ((left, -12.7, 0), (right, 12.7, 180)):
        for n, y in zip(side, rows):
            x, yy = X + sx, Y - y
            net = pins[n][1]
            markers.append(_label(net, x, yy, ang, f'U905.{n}') if net else _no_connect(x, yy, f'U905.{n}'))
    _, _, _, inst_end = _instance(text, 'U905')
    return text[:inst_end] + '\n' + '\n'.join(markers) + text[inst_end:]


def set_dnp(text, refs):
    for ref in refs:
        _, _, s, e = _instance(text, ref)
        block = text[s:e]
        B.require('(dnp no)' in block, 'Unexpected DNP state ' + ref)
        block = block.replace('(dnp no)', '(dnp yes)', 1)      # 与既有 DNP 件一致：留在 BOM 中、标记不贴
        text = text[:s] + block + text[e:]
    return text


def apply_schematic(sch: Path, fields, eco):
    text = sch.read_text()
    for key, net in eco['schematic_pin_nets'].items():
        ref, num = key.split('.')
        text, _ = set_pin_net(text, ref, num, net)
        text = set_pin_type_and_name(text, ref, num, ptype='passive')
    for num, name in eco['u810_pin_names'].items():
        text = set_pin_type_and_name(text, 'U810', num, name=name)
    text = replace_u905_symbol(text, eco)
    text = set_dnp(text, sorted(eco['dnp_refs']))
    text, updated = patch_schematic_text(text, fields)
    B.require(sorted(updated) == sorted(fields), 'R50 schematic part edits differ')
    sch.write_text(text)


# ---------------------------------------------------------------- 库与规则

def write_u905_footprint(path: Path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('u905fp', HERE / 'r50_u905_footprint.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    path.write_text(mod.footprint_text())


def apply_libraries(output: Path, fields, eco):
    write_u905_footprint(output / 'Panda47.pretty' / 'U905_Core.kicad_mod')
    updated = []
    for path in sorted((output / 'Panda47.pretty').glob('*.kicad_mod')):
        text, refs = patch_pcb_or_mod_text(path.read_text(), fields)
        if refs:
            path.write_text(text)
            updated.extend(refs)
    B.require(sorted(set(updated)) == sorted(fields), 'R50 library part edits differ: ' +
              str(sorted(set(fields) - set(updated))))
    with (output / 'Single.kicad_dru').open('a') as f:
        f.write('\n' + eco['dru_rules'].strip() + '\n')


# ---------------------------------------------------------------- PCB

def _seg_point(ax, ay, bx, by, px, py):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def _seg_rect(ax, ay, bx, by, r):
    x0, y0, x1, y1 = r
    if any(x0 <= x <= x1 and y0 <= y <= y1 for x, y in ((ax, ay), (bx, by))):
        return 0.0
    edges = [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]

    def o(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    for e in edges:
        p, q = (e[0], e[1]), (e[2], e[3])
        if o((ax, ay), (bx, by), p) * o((ax, ay), (bx, by), q) < 0 and o(p, q, (ax, ay)) * o(p, q, (bx, by)) < 0:
            return 0.0
    return min([_seg_point(ax, ay, bx, by, cx, cy) for cx, cy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))] +
               [_seg_point(*e, px, py) for e in edges for px, py in ((ax, ay), (bx, by))])


def footprint(board, ref):
    """FindFootprintByReference 在本流程中偶发返回未包装的 SwigPyObject，改为遍历。"""
    found = [f for f in board.GetFootprints() if f.GetReference() == ref]
    B.require(len(found) == 1, 'Expected one footprint ' + ref)
    return found[0]


def apply_copper(board, d, keep):
    """Geometric copper delta (see single_r50_pmic_frontlight_delta.json)."""
    import pcbnew as P
    mm, MM = P.FromMM, P.ToMM

    def net(name):
        n = board.FindNet(name)
        if n is None:
            n = P.NETINFO_ITEM(board, name)
            board.Add(n)
            n.thisown = 0       # 归板所有；否则 Python 回收后板上留下悬空网络
        return n
    for key, name in d.get('pad_nets', {}).items():
        ref, num = key.split('.')
        pads = [p for p in footprint(board, ref).Pads() if p.GetNumber() == num]
        B.require(pads, 'Missing pad ' + key)
        for p in pads:
            p.SetNet(net(name))
    remove = []
    for t in list(board.GetTracks()):
        n = t.GetNetname()
        if n in d.get('remove_all_copper_of_nets', []):
            remove.append(t)
            continue
        if t.GetClass() == 'PCB_VIA':
            x, y, r = MM(t.GetPosition().x), MM(t.GetPosition().y), MM(t.GetWidth(P.F_Cu)) / 2
            if any(v['net'] == n and abs(v['x'] - x) < 1e-3 and abs(v['y'] - y) < 1e-3 for v in d.get('remove_vias', [])) \
                    or any(_seg_rect(x, y, x, y, w) <= r for w in d.get('remove_in_windows', {}).get(n, [])):
                remove.append(t)
            continue
        ax, ay, bx, by = MM(t.GetStart().x), MM(t.GetStart().y), MM(t.GetEnd().x), MM(t.GetEnd().y)
        ly, hw = board.GetLayerName(t.GetLayer()), MM(t.GetWidth()) / 2
        hit = False
        for rule in d.get('remove_tracks', []):
            if rule['net'] != n or rule['layer'] != ly:
                continue
            if 'bbox' in rule:
                x0, y0, x1, y1 = rule['bbox']
                hit = all(x0 - 1e-6 <= x <= x1 + 1e-6 for x in (ax, bx)) and all(y0 - 1e-6 <= y <= y1 + 1e-6 for y in (ay, by))
            else:
                hit = abs(ay - rule['y']) < 1e-6 and abs(by - rule['y']) < 1e-6 and max(ax, bx) <= rule['x_max'] + 1e-6
            if hit:
                break
        if hit or any(_seg_rect(ax, ay, bx, by, w) <= hw for w in d.get('remove_in_windows', {}).get(n, [])):
            remove.append(t)
    for t in remove:
        board.Delete(t)   # Remove() 后 Python 回收包装会破坏板对象表
    for a in d.get('add_tracks', []):
        tr = P.PCB_TRACK(board)
        tr.SetStart(P.VECTOR2I(mm(a['x1']), mm(a['y1'])))
        tr.SetEnd(P.VECTOR2I(mm(a['x2']), mm(a['y2'])))
        tr.SetWidth(mm(a['w']))
        tr.SetLayer(board.GetLayerID(a['layer']))
        tr.SetNet(net(a['net']))
        board.Add(tr)
        tr.thisown = 0
        keep.append(tr)
    for a in d.get('add_vias', []):
        v = P.PCB_VIA(board)
        v.SetViaType(P.VIATYPE_THROUGH)
        v.SetLayerPair(P.F_Cu, P.B_Cu)
        v.SetWidth(mm(a['d']))
        v.SetDrill(mm(a['drill']))
        v.SetPosition(P.VECTOR2I(mm(a['x']), mm(a['y'])))
        v.SetNet(net(a['net']))
        board.Add(v)
        v.thisown = 0
        keep.append(v)
    return len(remove)


def swap_u905(board, output: Path, eco):
    import pcbnew as P
    mm, MM = P.FromMM, P.ToMM
    old = footprint(board, 'U905')
    fields = {f.GetName(): f.GetText() for f in old.GetFields()}
    new = P.FootprintLoad(str(output / 'Panda47.pretty'), 'U905_Core')
    B.require(new is not None, 'Cannot load the AW99703 footprint')
    new.SetReference('U905')
    for name, text in fields.items():
        if name not in ('Reference', 'Value', 'Footprint') and new.GetField(name) is None:
            new.SetField(name, text)
            new.GetField(name).SetVisible(False)
    new.SetValue(fields['Value'])
    cx, cy = eco['u905']['center_mm']
    new.SetPosition(P.VECTOR2I(mm(cx), mm(cy)))
    new.SetOrientationDegrees(eco['u905']['rotation_deg'])
    new.SetPath(old.GetPath())
    new.SetFPID(old.GetFPID())
    for pad in new.Pads():
        name = eco['u905']['pins'][pad.GetNumber()][1]
        if name:
            pad.SetNet(board.FindNet(name))
    board.Delete(old)
    board.Add(new)
    new.thisown = 0
    x0, y0, x1, y1 = eco['u905']['old_gnd_copper_box']
    gone = 0
    for t in list(board.GetTracks()):
        pts = [t.GetPosition()] if t.GetClass() == 'PCB_VIA' else [t.GetStart(), t.GetEnd()]
        if t.GetNetname() == 'GND' and all(x0 <= MM(p.x) <= x1 and y0 <= MM(p.y) <= y1 for p in pts):
            board.Delete(t)   # Remove() 后 Python 回收包装会破坏板对象表
            gone += 1
    return new, gone


def apply_board(board, output: Path, fields, eco, keep):
    import pcbnew as P
    for ref, values in fields.items():
        fp = footprint(board, ref)
        B.require(fp is not None, 'Missing R50 footprint ' + ref)
        for name, text in values.items():
            if name == 'Value':
                fp.SetValue(text)
            else:
                fp.SetField(name, text)
                fp.GetField(name).SetVisible(False)
    for ref in eco['dnp_refs']:
        fp = footprint(board, ref)
        fp.SetDNP(True)
    removed = apply_copper(board, eco['pmic_copper'], keep)
    _, gone = swap_u905(board, output, eco)
    removed += gone + apply_copper(board, eco['frontlight_copper'], keep)
    # 原理图中改为不连接的引脚（C922 不贴后 FL_VDC 只剩一端）
    for key, name in eco['schematic_pin_nets'].items():
        if name:
            continue
        ref, num = key.split('.')
        nname = f'unconnected-({ref}-Pad{num})'
        net = P.NETINFO_ITEM(board, nname)
        board.Add(net)
        net.thisown = 0
        for pad in footprint(board, ref).Pads():
            if pad.GetNumber() == num:
                pad.SetNet(net)
    # 未连接引脚的网名含引脚名，随 TPS651851 / AW99703 引脚名更新，与原理图一致
    names = {'U810': eco['u810_pin_names'], 'U905': {k: v[0] for k, v in eco['u905']['pins'].items()}}
    for ref, pin_names in names.items():
        for pad in footprint(board, ref).Pads():
            n = pad.GetNetname()
            if pad.GetNumber() in pin_names and (not n or n.startswith('unconnected-')):
                name = f'unconnected-({ref}-{pin_names[pad.GetNumber()]}-Pad{pad.GetNumber()})'
                net = board.FindNet(name)
                if net is None:
                    net = P.NETINFO_ITEM(board, name)
                    board.Add(net)
                    net.thisown = 0
                pad.SetNet(net)
    return removed


# ---------------------------------------------------------------- 检查合同

def r50_spec(spec, eco_sha, stock_sha, ground_pad_count, vip_inventory):
    """R50 inspection contract derived from the R48/R49 one; every change is explicit."""
    ov = json.loads(json.dumps(spec['layout_ecos']['R48'].get('inspection_overrides', {})))
    remap = {'1': 'A2', '2': 'B2', '11': 'B1', '12': 'C1', '14': 'D2', '16': 'D3', '17': 'D3', '18': 'B3', '19': 'A3', '20': 'A1'}

    def links(rows):
        return [[a, remap.get(b, b) if a == 'U905' else b, c, remap.get(d, d) if c == 'U905' else d] for a, b, c, d in rows]
    spec = {**spec, 'critical_links': links(spec['critical_links']),
            'layout_critical_links': links(spec.get('layout_critical_links', []))}
    if 'layout_critical_links' in ov:
        ov['layout_critical_links'] = links(ov['layout_critical_links'])
    # SY7636 专用合同：VREF 0.1 uF 限制、7.5k/36k 温度网络与 1 uF 泵基电容，不适用于 TPS651851
    ov.pop('reference_filters', None)
    ov.pop('temperature_sense', None)
    pump = ov.get('pmic_charge_pump_storage')
    if pump:
        # TI 典型值：VDDH_D / VEE_D 100 nF，飞电容 10 nF；输出电容 1 uF 不变
        for part in (pump, pump.get('positive_storage', {})):
            part['value'] = '100n/50V/0805'
            part['flying_cap_value'] = '10n/50V/0805'
    ov['required_ground_pad_count'] = ground_pad_count
    ov['pmic_pin_expectations'] = {'49': 'P47_VN', '6': 'GND', '21': 'P47_HV_EN', '8': 'GND', '32': 'GND',
                                   '41': 'GND', '48': 'GND', '5': 'P47_WAKEUP'}
    if vip_inventory is not None and 'complete_via_in_pad_inventory' in ov:
        ov['complete_via_in_pad_inventory'] = {**ov['complete_via_in_pad_inventory'], 'soldered_vias': vip_inventory}
    return {**spec, 'revision': 'R50', 'required_ground_pad_count': ground_pad_count,
            'layout_ecos': {**spec.get('layout_ecos', {}),
                            'R50': {**spec['layout_ecos']['R48'], 'inspection_overrides': ov,
                                    'source': str(ECO.relative_to(HERE)), 'sha256': eco_sha,
                                    'stock_source': str(STOCK.relative_to(HERE)), 'stock_sha256': stock_sha}}}


# ---------------------------------------------------------------- 主流程

def build(output: Path, source: Path | None = None, readable: bool = True, reuse_r49: Path | None = None):
    import pcbnew as P
    from verify_jlc_coupon_compliance import export_jlc_orderpack
    output = output.resolve()
    B.require(not output.exists(), 'Choose a new output directory')
    B.require(not output.is_relative_to(B.REPO) or output.is_relative_to(B.REPO / '.work'),
              'Generated candidates belong in .work or external delivery')
    if reuse_r49:
        # 仅供迭代：复用一次已通过全部 R49 检查的网表式回放（须由本脚本同一流程生成）
        r49 = reuse_r49.resolve()
        B.require(json.loads((r49 / 'SINGLE-CHECKPOINT.json').read_text())['revision'] == 'R49', 'Not an R49 replay')
    else:
        r49 = output.parent / (output.name + '-r49-netlist')
        B.require(not r49.exists(), 'Remove the stale R49 replay directory ' + str(r49))
        R49.build(r49, source, readable=False)
    shutil.copytree(r49, output, ignore=shutil.ignore_patterns('orderpack', 'Single-*.json', 'Single-*.log', 'Single-*.xml',
                                                               'SINGLE-CHECKPOINT.json'))
    stock, eco = json.loads(STOCK.read_text()), json.loads(ECO.read_text())
    fields = part_fields(stock, eco)
    pcb, sch = output / 'Single.kicad_pcb', output / 'Single.kicad_sch'
    apply_libraries(output, fields, eco)
    apply_schematic(sch, fields, eco)
    if readable:
        import readable_schematic
        readable_schematic.REVISION = {'version': 'v0.1.3', 'revision': 'R50', 'date': '2026-11-08'}
        net = output / 'Single-pre-readable-netlist.xml'
        B.run_cli(['sch', 'export', 'netlist', '--format', 'kicadxml', '--output', net, sch],
                  output / 'Single-pre-readable-netlist.log')
        flat = output / 'Single.netlist-style.kicad_sch'
        shutil.copy2(sch, flat)
        readable_schematic.main(str(flat), str(net), str(sch))
        flat.unlink()
        after = output / 'Single-readable-netlist.xml'
        B.run_cli(['sch', 'export', 'netlist', '--format', 'kicadxml', '--output', after, sch],
                  output / 'Single-readable-netlist.log')

        def nets(path):
            root = B.ET.parse(path).getroot()
            return {frozenset((x.get('ref'), x.get('pin')) for x in n.iter('node')): n.get('name') for n in root.iter('net')}
        B.require(nets(net) == nets(after), 'Readable schematic changed the netlist')
    board = P.LoadBoard(str(pcb))
    keep = []
    removed = apply_board(board, output, fields, eco, keep)
    if readable:
        import readable_schematic
        for ref, text in readable_schematic.footprint_specs(output).items():
            fp = footprint(board, ref)
            B.require(fp is not None, 'Schematic part missing on the board: ' + ref)
            fp.SetField('Spec', text)
            field = fp.GetField('Spec')
            field.SetVisible(False)
            field.SetLayer(P.B_Fab if fp.IsFlipped() else P.F_Fab)
            field.SetPosition(fp.GetPosition())
    P.SaveBoard(str(pcb), board)
    del keep
    B.run_cli(['pcb', 'drc', '--refill-zones', '--save-board', '--severity-all', '--all-track-errors',
               '--schematic-parity', '--exit-code-violations', '--format', 'json', '--output',
               output / 'Single-drc.json', pcb], output / 'Single-drc.log')
    B.run_cli(['sch', 'erc', '--severity-all', '--exit-code-violations', '--format', 'json', '--output',
               output / 'Single-erc.json', sch], output / 'Single-erc.log')
    counts = B.counts_from_reports(json.loads((output / 'Single-drc.json').read_text()),
                                   json.loads((output / 'Single-erc.json').read_text()))
    B.require(not any(counts.values()), 'R50 native checks are not all zero: ' + json.dumps(counts))
    spec = json.loads(B.SPEC.read_text())
    board = P.LoadBoard(str(pcb))
    ground_pads = sum(1 for f in board.GetFootprints() for p in f.Pads() if p.GetNumber() and p.GetNetname() == 'GND')
    from build_pico47_single import inspect_solder_joint_vias

    def signature(row):
        return [row['net'], round(row['x_mm'], 6), round(row['y_mm'], 6), round(row['diameter_mm'], 6),
                round(row['drill_mm'], 6), row['soldered_contacts']]
    vip = sorted(signature(r) for r in inspect_solder_joint_vias(board, spec['via_in_pad']['process'])['filled_and_capped_vias'])
    rspec = r50_spec(spec, B.sha(ECO), B.sha(STOCK), ground_pads, vip)
    board, groups, inspection = B.inspect_single(output, rspec)
    orderpack = output / 'orderpack'
    export_jlc_orderpack(output, orderpack, revision='R50')
    B.write_csv(orderpack / 'REQUIRED-VIA-IN-PAD.csv', inspection['via_in_pad'])
    if inspection['pending_supply']:
        B.write_csv(orderpack / 'PENDING-SUPPLY.csv', inspection['pending_supply'])
    else:                                    # R50：所有 SMT 均有嘉立创现货编号，只写表头
        (orderpack / 'PENDING-SUPPLY.csv').write_text('\ufeffref,manufacturer,mpn,value,footprint,lcsc,supply_status\n')
    B.write_csv(orderpack / 'REQUIRED-POST-SMT.csv', inspection['required_post_smt'])
    qualification = B.build_qualification_report(output, rspec, inspection, B.SPEC)
    (orderpack / 'QUALIFICATION-STATUS.json').write_text(json.dumps(qualification, indent=2, ensure_ascii=False) + '\n')
    shutil.copy2(r49 / 'orderpack' / 'MANUFACTURING-REQUIREMENTS.md', orderpack / 'MANUFACTURING-REQUIREMENTS.md')
    with (orderpack / 'MANUFACTURING-REQUIREMENTS.md').open('a') as f:
        f.write(f'\nR50（2026-11-08）：全部 SMT 物料改为嘉立创现货；U810 改 TI TPS651851RSLR（裸焊盘接 VN，非 GND），'
                f'U905 改 AWINIC AW99703CSR（WLCSP-12，B2 SCL 0.25/0.15 mm 盘中孔同样须树脂塞孔+电镀封顶），'
                f'R805、C922 不贴。焊接盘过孔 {len(inspection["via_in_pad"])} 颗、待供 {len(inspection["pending_supply"])} 项，以本目录 CSV 为准。\n')
    manifest = dict(schema='panda47-single-rebuild-v1', revision='R50', baseline_revision='R49',
                    eco={'path': str(ECO.relative_to(HERE)), 'sha256': B.sha(ECO)},
                    stock={'path': str(STOCK.relative_to(HERE)), 'sha256': B.sha(STOCK)},
                    counts=counts, copper_items_removed=removed, ground_pads=ground_pads,
                    via_in_pad=len(inspection['via_in_pad']), pending_supply=len(inspection['pending_supply']),
                    **qualification['status_flags'],
                    files_sha256={str(f.relative_to(output)): B.sha(f) for f in sorted(output.rglob('*')) if f.is_file()})
    (output / 'SINGLE-CHECKPOINT.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--netlist-style-schematic', action='store_true')
    parser.add_argument('--reuse-r49', type=Path, help='development only: an existing R49 netlist-style replay')
    args = parser.parse_args()
    m = build(args.output, args.source, readable=not args.netlist_style_schematic, reuse_r49=args.reuse_r49)
    print(json.dumps({k: m[k] for k in ('counts', 'via_in_pad', 'pending_supply', 'ground_pads', 'manufacturing_release')}, indent=2))
