"""对 R25 几何试验执行受约束的器件区域重排。

该工具只处理实验几何 JSON，不直接写入 KiCad PCB。它保留焊盘 UUID、网络和
板框，移除旧焊盘附近的局部信号铜，并把 U710/U711/J503 等获批准的器件移动到
新姿态。In1.Cu 只允许 GND；跨器件焊盘、板边和铜间距在输出前检查。

用法：
  relayout_components.py source.json moves.json output.json

moves.json 示例：
  {"components": {
     "U710": {"x": 49.0, "y": 74.0, "old_rot": -90, "rot": -90},
     "U711": {"x": 68.0, "y": 80.0, "old_rot": 0, "rot": 0},
     "J503": {"x": 43.2822, "y": 80.0, "old_rot": 180, "rot": 180}},
   "outline": [[[73, 131], [42.12, 131], [42.12, 125.45],
                [32.88, 125.45], [32.88, 131], [2, 131], [2, 121],
                [40, 121], [40, 60], [55, 60], [55, 2], [73, 2]]]}
"""

from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union


CLR = 0.15
EDGE = 0.20
LOCAL_RIPUP = 0.60
SIGNAL_LAYERS = {"F.Cu", "In2.Cu", "B.Cu"}


def _shape(item):
    if "x1" in item:
        a = (item["x1"], item["y1"])
        b = (item["x2"], item["y2"])
        return (LineString([a, b]) if a != b else Point(a)).buffer(item["w"] / 2.0, 8)
    return Point(item["x"], item["y"]).buffer(item["d"] / 2.0, 16)


def _transform(x, y, ox, oy, cx, cy, delta_deg):
    angle = math.radians(delta_deg)
    dx, dy = x - ox, y - oy
    return (
        cx + math.cos(angle) * dx - math.sin(angle) * dy,
        cy + math.sin(angle) * dx + math.cos(angle) * dy,
    )


def _transform_rings(rings, ox, oy, cx, cy, delta_deg):
    return [
        [list(_transform(float(x), float(y), ox, oy, cx, cy, delta_deg)) for x, y in ring]
        for ring in rings
    ]


def _footprint_pad_union(pads):
    shapes = [
        Polygon(ring)
        for pad in pads
        for rings in pad.get("polys", {}).values()
        for ring in rings
        if len(ring) > 2
    ]
    if not shapes:
        raise ValueError("移动器件没有可用焊盘几何")
    return unary_union(shapes)


def _board_polygon(geometry):
    outlines = geometry.get("outline", [])
    if not outlines:
        raise ValueError("几何没有板框")
    return Polygon(outlines[0])


def _check_signal_layers(geometry):
    bad = [t for t in geometry.get("tracks", []) if t.get("layer") == "In1.Cu" and t.get("net") != "GND"]
    if bad:
        raise ValueError(f"In1.Cu 出现 {len(bad)} 条非 GND 走线")


def _check_moved_pads(geometry, moved_refs):
    board = _board_polygon(geometry).buffer(-EDGE)
    moved = [p for p in geometry["pads"] if p["ref"] in moved_refs]
    if not moved:
        raise ValueError("没有找到要移动的焊盘")
    for pad in moved:
        for rings in pad.get("polys", {}).values():
            for ring in rings:
                if len(ring) > 2 and not Polygon(ring).within(board):
                    raise ValueError(f"{pad['ref']}.{pad['num']} 超出板框安全边界")

    # 同一器件内部允许按封装定义保持近距离；不同器件必须满足实际铜间距。
    shapes = []
    for pad in geometry["pads"]:
        for layer, rings in pad.get("polys", {}).items():
            for ring in rings:
                if len(ring) > 2:
                    shapes.append((pad, layer, Polygon(ring), pad["ref"] in moved_refs))
    for i, (a, layer, shape, moved) in enumerate(shapes):
        for b, other_layer, other, other_moved in shapes[i + 1 :]:
            if not (moved or other_moved) or a["ref"] == b["ref"] or layer != other_layer:
                continue
            if a["net"] and b["net"] and a["net"] != b["net"] and shape.buffer(CLR).intersects(other):
                raise ValueError(f"移动器件焊盘间距不足：{a['ref']}.{a['num']} / {b['ref']}.{b['num']}")


def relayout(source, moves, outline=None):
    geometry = copy.deepcopy(source)
    if outline is not None:
        if not outline or len(outline) != 1:
            raise ValueError("outline 必须是一个闭合板框环")
        candidate = Polygon(outline[0])
        if not candidate.is_valid or candidate.area <= 0:
            raise ValueError("outline 不是有效板框")
        geometry["outline"] = copy.deepcopy(outline)
    _check_signal_layers(geometry)
    pads_by_ref = {}
    for pad in geometry["pads"]:
        pads_by_ref.setdefault(pad["ref"], []).append(pad)

    removed = set()
    moved_refs = set()
    for ref, pose in moves.items():
        if ref not in pads_by_ref:
            raise ValueError(f"找不到器件 {ref}")
        old_pads = pads_by_ref[ref]
        old_union = _footprint_pad_union(old_pads)
        ox, oy = old_union.centroid.x, old_union.centroid.y
        cx, cy = float(pose["x"]), float(pose["y"])
        if "old_rot" not in pose:
            raise ValueError(f"{ref} 必须显式提供 old_rot，避免导出几何被重复旋转")
        old_rot = float(pose["old_rot"])
        new_rot = float(pose.get("rot", old_rot))
        delta = new_rot - old_rot
        local = old_union.buffer(LOCAL_RIPUP)

        for track in geometry.get("tracks", []):
            if track.get("layer") not in SIGNAL_LAYERS or track.get("net") == "GND":
                continue
            if _shape(track).intersects(local):
                removed.add(track["uuid"])
        for via in geometry.get("vias", []):
            if via.get("net") == "GND":
                continue
            if _shape(via).intersects(local):
                removed.add(via["uuid"])

        # 同步移动与器件相邻的 rule area，避免机械 keepout 留在旧坐标。
        for zone in geometry.get("zones", []):
            if not zone.get("rule") or not zone.get("outline"):
                continue
            if Polygon(zone["outline"][0]).intersects(old_union):
                zone["outline"] = _transform_rings(zone["outline"], ox, oy, cx, cy, delta)

        geometry["pads"] = [pad for pad in geometry["pads"] if pad["ref"] != ref]
        for pad in old_pads:
            moved = copy.deepcopy(pad)
            moved["x"], moved["y"] = _transform(pad["x"], pad["y"], ox, oy, cx, cy, delta)
            for layer, rings in moved.get("polys", {}).items():
                moved["polys"][layer] = _transform_rings(rings, ox, oy, cx, cy, delta)
            geometry["pads"].append(moved)
        moved_refs.add(ref)

    geometry["tracks"] = [track for track in geometry.get("tracks", []) if track["uuid"] not in removed]
    geometry["vias"] = [via for via in geometry.get("vias", []) if via["uuid"] not in removed]
    _check_signal_layers(geometry)
    _check_moved_pads(geometry, moved_refs)
    return geometry, sorted(removed)


def main(argv):
    if len(argv) != 4:
        raise SystemExit("usage: relayout_components.py source.json moves.json output.json")
    source_path, moves_path, output_path = map(Path, argv[1:])
    source = json.loads(source_path.read_text())
    document = json.loads(moves_path.read_text())
    moves = document.get("components", document)
    outline = document.get("outline") if isinstance(document, dict) else None
    result, removed = relayout(source, moves, outline=outline)
    Path(output_path).write_text(json.dumps(result, separators=(",", ":")))
    print(json.dumps({"moved": sorted(moves), "removed_copper": len(removed)}))


if __name__ == "__main__":
    main(sys.argv)
