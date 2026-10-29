#!/usr/bin/env python3
"""应用 R25 CHIP_PU 分裂复位 ECO。

输入是一个实验性 Core 原理图/PCB，输出必须是新的 ``.work`` 或外部目录。
工具只改 CHIP_PU 相关端点、删除旧 CHIP_PU 铜、增加 R533 串联电阻，并可按
显式 JSON 姿态移动复位密集簇。它不修改正式 R24 candidate，也不改变规则。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import uuid
from pathlib import Path


MAPPING = {
    "U501.4": "CHIP_PU_MCU",
    "R510.2": "CHIP_PU_MCU",
    "C510.1": "CHIP_PU_MCU",
    "TP18.1": "CHIP_PU_MCU",
    "J503.1": "CHIP_PU_DEBUG",
}
R533_VALUE = "1k / CHIP_PU_DEBUG_SERIES"
R533_MPN = "RC-02K1001FT"
R533_LCSC = "C140197"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def balanced(text: str, start: int) -> int:
    """返回 start 所在 S-expression 的结束位置。"""
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("未闭合的 KiCad S-expression")


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _property(text: str, name: str, value: str) -> str:
    pattern = rf'(\(property\s+"{re.escape(name)}"\s+)"[^"]*"'
    replaced, count = re.subn(pattern, rf'\1{_quoted(value)}', text, count=1)
    if count != 1:
        raise ValueError(f"找不到 schematic property: {name}")
    return replaced


def _maybe_property(text: str, name: str, value: str) -> str:
    """对简化测试 symbol 允许缺少非电气 metadata。"""
    return _property(text, name, value) if f'(property "{name}"' in text else text


def _library_pin_map(schematic: str) -> dict[str, dict[str, tuple[float, float]]]:
    lib_start = schematic.index("(lib_symbols")
    lib_end = balanced(schematic, lib_start)
    library = schematic[lib_start:lib_end]
    result: dict[str, dict[str, tuple[float, float]]] = {}
    for match in re.finditer(r'\(symbol "([^"]+)"', library):
        name = match.group(1)
        if name.count("_") >= 2 and re.search(r"_\d+_\d+$", name):
            continue
        block = library[match.start():balanced(library, match.start())]
        pins: dict[str, tuple[float, float]] = {}
        for pin in re.finditer(
            r'\(pin\s+\w+\s+\w+\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+[-\d.]+\)'
            r'\s+\(length\s+[-\d.]+\).*?\(number\s+"([^"]+)"',
            block,
            re.S,
        ):
            pins[pin.group(3)] = (float(pin.group(1)), float(pin.group(2)))
        result[name] = pins
    return result


def _pin_locations(schematic: str, refs: set[str]) -> dict[str, tuple[float, float]]:
    """计算实例 pin 坐标，沿用项目既有 sch_pin_labels 的坐标约定。"""
    pins = _library_pin_map(schematic)
    lib_start = schematic.index("(lib_symbols")
    lib_end = balanced(schematic, lib_start)
    locations: dict[str, tuple[float, float]] = {}
    for match in re.finditer(
        r'\(symbol\s*\(lib_id\s+"([^"]+)"\)\s*'
        r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)',
        schematic[lib_end:],
    ):
        block_start = lib_end + match.start()
        block = schematic[block_start:balanced(schematic, block_start)]
        reference = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if not reference or reference.group(1) not in refs:
            continue
        ref = reference.group(1)
        library_pins = pins.get(match.group(1), {})
        x, y, angle = map(float, match.groups()[1:])
        radians = math.radians(angle)
        for number, (px, py) in library_pins.items():
            rx = px * math.cos(radians) - py * math.sin(radians)
            ry = px * math.sin(radians) + py * math.cos(radians)
            locations[f"{ref}.{number}"] = (round(x + rx, 4), round(y - ry, 4))
    return locations


def _rename_pin_labels(schematic: str) -> tuple[str, int]:
    locations = _pin_locations(schematic, {key.split(".", 1)[0] for key in MAPPING})
    labels = []
    for match in re.finditer(
        r'\(global_label\s+"([^"]*)"\s+\(shape\s+\w+\)\s*'
        r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+[-\d.]+\)',
        schematic,
    ):
        labels.append((float(match.group(2)), float(match.group(3)), match.start(1), match.end(1), match.group(1)))
    edits = []
    for key, new_net in MAPPING.items():
        if key not in locations:
            raise ValueError(f"找不到 schematic pin: {key}")
        x, y = locations[key]
        hits = [item for item in labels if abs(item[0] - x) < 1e-3 and abs(item[1] - y) < 1e-3]
        if len(hits) != 1:
            raise ValueError(f"{key} 的 global label 数量不是1: {len(hits)}")
        hit = hits[0]
        if hit[4] != "CHIP_PU":
            raise ValueError(f"{key} 原 net 不是 CHIP_PU: {hit[4]}")
        edits.append((hit[2], hit[3], new_net))
    output = schematic
    for start, end, value in sorted(edits, reverse=True):
        output = output[:start] + value + output[end:]
    return output, len(edits)


def _r533_definition(schematic: str) -> str:
    lib_start = schematic.index("(lib_symbols")
    lib_end = balanced(schematic, lib_start)
    library = schematic[lib_start:lib_end]
    marker = '(symbol "Panda7:R510"'
    start = library.find(marker)
    if start < 0:
        raise ValueError("lib_symbols 中没有 Panda7:R510")
    block = library[start:balanced(library, start)]
    block = block.replace('"Panda7:R510"', '"Panda7:R533"', 1)
    block = block.replace('"R510_0_1"', '"R533_0_1"', 1)
    block = block.replace('"R510_1_1"', '"R533_1_1"', 1)
    block = _maybe_property(block, "Reference", "R533")
    block = _maybe_property(block, "Value", R533_VALUE)
    # 保留原 R510 定义，把 R533 定义追加到 lib_symbols 的闭合括号前。
    return library[:-1] + block + library[-1:]


def _r533_instance(schematic: str, x: float, y: float) -> str:
    lib_start = schematic.index("(lib_symbols")
    lib_end = balanced(schematic, lib_start)
    marker = '(symbol(lib_id "Panda7:R510")'
    start = schematic.find(marker, lib_end)
    if start < 0:
        raise ValueError("schematic 中没有 R510 instance")
    block = schematic[start:balanced(schematic, start)]
    block = block.replace('"Panda7:R510"', '"Panda7:R533"', 1)
    block = re.sub(r'\(reference\s+"R510"\)', '(reference "R533")', block, count=1)
    block = re.sub(
        r'\(uuid\s+"[^"]+"\)',
        f'(uuid "{uuid.uuid5(uuid.NAMESPACE_URL, "panda47/r25/chip-pu/R533-instance")}")',
        block,
        count=1,
    )
    block = _property(block, "Reference", "R533")
    block = _property(block, "Value", R533_VALUE)
    block = _property(block, "Footprint", "Panda47:R533_Core")
    block = _maybe_property(block, "Manufacturer", "FH (Fenghua Advanced)")
    block = _maybe_property(block, "MPN", R533_MPN)
    block = _maybe_property(block, "LCSC", R533_LCSC)
    block = _maybe_property(block, "Description", "R25 CHIP_PU debug active-low series isolation; exact reset timing qualification remains open.")
    block = re.sub(r'\(at\s+[-\d.]+\s+[-\d.]+\s+[-\d.]+\)', f"(at {x:.4f} {y:.4f} 0)", block, count=1)
    return block


def apply_schematic(input_path: Path, output_path: Path, r533_position=(571.5, 701.04)) -> dict:
    source = input_path.read_text()
    renamed, changed = _rename_pin_labels(source)
    lib_start = renamed.index("(lib_symbols")
    lib_end = balanced(renamed, lib_start)
    library = renamed[lib_start:lib_end]
    if '"Panda7:R533"' in library:
        raise ValueError("schematic 已经包含 R533，拒绝重复 ECO")
    new_library = _r533_definition(renamed)
    renamed = renamed[:lib_start] + new_library + renamed[lib_end:]
    lib_end = lib_start + len(new_library)
    instance = _r533_instance(renamed, *r533_position)
    root_end = renamed.rfind(")")
    labels = []
    x, y = r533_position
    for net, px, suffix in [("CHIP_PU_MCU", x - 12.7, "mcu"), ("CHIP_PU_DEBUG", x + 12.7, "debug")]:
        uid = uuid.uuid5(uuid.NAMESPACE_URL, f"panda47/r25/chip-pu/{suffix}")
        labels.append(
            f'(global_label "{net}" (shape passive) (at {px:.4f} {y:.4f} 0) '
            f'(effects (font (size 0.9 0.9))(justify left))(uuid "{uid}"))'
        )
    output = renamed[:root_end] + instance + "".join(labels) + renamed[root_end:]
    output_path.write_text(output)
    return {"renamed_pin_labels": changed, "added_ref": "R533", "r533_position": list(r533_position)}


def _set_field(footprint, name: str, value: str) -> None:
    field = next((item for item in footprint.GetFields() if item.GetName() == name), None)
    if field is None:
        import pcbnew as P
        field = P.PCB_FIELD(footprint, P.FIELD_T_USER, name)
        footprint.Add(field)
    field.SetText(value)
    field.SetVisible(False)


def apply_pcb(input_path: Path, output_path: Path, cluster=None) -> dict:
    import wx
    _app = wx.GetApp() or wx.App(False)
    import pcbnew as P

    board = P.LoadBoard(str(input_path))
    if board.GetCopperLayerCount() != 4:
        raise ValueError("CHIP_PU ECO 只允许四层板")
    for item in board.GetTracks():
        if not isinstance(item, P.PCB_VIA) and item.GetLayer() == P.In1_Cu and str(item.GetNetname()) != "GND":
            raise ValueError("输入 PCB 已有 In1.Cu 非 GND signal")
    old = board.FindNet("CHIP_PU")
    if old is None:
        raise ValueError("PCB 没有原 CHIP_PU net")
    if board.FindNet("CHIP_PU_MCU") is not None or board.FindNet("CHIP_PU_DEBUG") is not None:
        raise ValueError("输入 PCB 已包含 R25 CHIP_PU 分裂 net")
    # 不调用 NETINFO_ITEM.SetNetname：KiCad 10 的 Python binding 在重命名
    # 已挂接 net 后会使 FindFootprintByReference 返回失效的裸指针。
    mcu = P.NETINFO_ITEM(board, "CHIP_PU_MCU")
    debug = P.NETINFO_ITEM(board, "CHIP_PU_DEBUG")
    board.Add(mcu)
    board.Add(debug)
    old_code = old.GetNetCode()
    for ref, pin, net_name in [
        ("U501", "4", "CHIP_PU_MCU"),
        ("R510", "2", "CHIP_PU_MCU"),
        ("C510", "1", "CHIP_PU_MCU"),
        ("TP18", "1", "CHIP_PU_MCU"),
        ("J503", "1", "CHIP_PU_DEBUG"),
    ]:
        footprint = board.FindFootprintByReference(ref)
        if footprint is None:
            raise ValueError("缺少 PCB footprint " + ref)
        pads = [pad for pad in footprint.Pads() if pad.GetNumber() == pin]
        if len(pads) != 1:
            raise ValueError(f"缺少唯一 pad {ref}.{pin}")
        pads[0].SetNet(mcu if net_name == "CHIP_PU_MCU" else debug)
    if board.FindFootprintByReference("R533") is not None:
        raise ValueError("PCB 已经包含 R533，拒绝重复 ECO")
    source = board.FindFootprintByReference("R510")
    clone = P.Cast_to_FOOTPRINT(source.Duplicate(False))
    clone.SetReference("R533")
    clone.SetValue(R533_VALUE)
    clone.SetFPIDAsString("Panda47:R533_Core")
    clone.SetPosition(P.VECTOR2I(P.FromMM(57.5), P.FromMM(98.0)))
    clone.SetOrientationDegrees(0)
    _set_field(clone, "Manufacturer", "FH (Fenghua Advanced)")
    _set_field(clone, "MPN", R533_MPN)
    _set_field(clone, "LCSC", R533_LCSC)
    _set_field(clone, "Description", "R25 CHIP_PU debug active-low series isolation; exact reset timing qualification remains open.")
    _set_field(clone, "PandaRevision", "E0-R25")
    _set_field(clone, "PandaQualification", "UNQUALIFIED_ELECTRICAL_CANDIDATE")
    _set_field(clone, "PandaSupplyStatus", "CATALOG_IDENTITY_ONLY")
    board.Add(clone)
    pads = {pad.GetNumber(): pad for pad in clone.Pads()}
    if set(pads) != {"1", "2"}:
        raise ValueError("R533 必须是两焊盘串联电阻")
    pads["1"].SetNet(mcu)
    pads["2"].SetNet(debug)
    moved = []
    moved_boxes = []
    if cluster:
        for ref, pose in cluster.items():
            footprint = board.FindFootprintByReference(ref)
            if footprint is None:
                raise ValueError("缺少 cluster footprint " + ref)
            if ref not in {"U501", "R510", "C510", "TP18", "R533", "J503"}:
                raise ValueError("cluster 含未批准器件 " + ref)
            box = footprint.GetBoundingBox(False, False)
            moved_boxes.append((
                P.ToMM(box.GetX()) - 0.6,
                P.ToMM(box.GetY()) - 0.6,
                P.ToMM(box.GetRight()) + 0.6,
                P.ToMM(box.GetBottom()) + 0.6,
            ))
            footprint.SetPosition(P.VECTOR2I(P.FromMM(float(pose[0])), P.FromMM(float(pose[1]))))
            footprint.SetOrientationDegrees(float(pose[2]))
            moved.append(ref)
    # 端点和新器件已经绑定到新 net 后再删除旧 CHIP_PU 铜；KiCad
    # Python binding 在 board.Remove(track) 后会使旧 footprint 迭代器失效。
    removed = 0
    def overlaps(a, b):
        return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

    moved_removed = 0
    for item in list(board.GetTracks()):
        is_old_reset = item.GetNetCode() == old_code
        is_moved_local = False
        if str(item.GetNetname()) != "GND" and moved_boxes:
            box = item.GetBoundingBox()
            ibox = (P.ToMM(box.GetX()), P.ToMM(box.GetY()), P.ToMM(box.GetRight()), P.ToMM(box.GetBottom()))
            is_moved_local = any(overlaps(ibox, target) for target in moved_boxes)
        if is_old_reset or is_moved_local:
            board.Remove(item)
            if is_old_reset:
                removed += 1
            elif is_moved_local:
                moved_removed += 1
    board.BuildConnectivity()
    P.SaveBoard(str(output_path), board)
    return {"removed_old_chip_pu_copper": removed, "removed_moved_cluster_copper": moved_removed,
            "added_ref": "R533", "moved_refs": moved,
            "four_layers": board.GetCopperLayerCount(), "in1_signal_tracks": 0}


def require_output(path: Path, source: Path) -> None:
    if path.exists():
        raise ValueError("输出必须是全新路径: " + str(path))
    if path.resolve() == source.resolve() or source.resolve().is_relative_to(path.resolve()):
        raise ValueError("拒绝覆盖输入")
    parts = path.resolve().parts
    if ".work" not in parts and "panda-board-deliverables" not in str(path.resolve()):
        raise ValueError("生成 CAD 只能写入 .work 或外部交付目录")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcb", type=Path, required=True)
    parser.add_argument("--sch", type=Path, required=True)
    parser.add_argument("--output-pcb", type=Path, required=True)
    parser.add_argument("--output-sch", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--cluster-json", type=Path)
    args = parser.parse_args(argv)
    require_output(args.output_pcb, args.pcb)
    require_output(args.output_sch, args.sch)
    cluster = json.loads(args.cluster_json.read_text()) if args.cluster_json else None
    before = {"pcb": sha(args.pcb), "sch": sha(args.sch)}
    sch_report = apply_schematic(args.sch, args.output_sch)
    pcb_report = apply_pcb(args.pcb, args.output_pcb, cluster=cluster)
    report = {"input": {**before}, "output": {"pcb": sha(args.output_pcb), "sch": sha(args.output_sch)},
              "schematic": sch_report, "pcb": pcb_report, "status": "EXPERIMENTAL_NOT_CHECKPOINT",
              "manufacturing_release": False, "core14": False}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
