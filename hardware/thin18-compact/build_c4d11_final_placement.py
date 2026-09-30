#!/usr/bin/env python3
"""Freeze C4D-10B as the final 96x68 placement checkpoint for routing.

This stage changes no reference, pose, net or footprint geometry. It locks every
footprint, re-runs native KiCad checks, exports the placement CSV and records the
mechanical invariants required before DSN routing.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "c4d10b-96x68-frontlight"
DST = ROOT / "c4d11-96x68-final-placement"
REL = Path("eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16")
STEM = "PANDA-STD-CORE-EVT-quilter-j501-merged"
PCB = DST / REL / f"{STEM}.kicad_pcb"
SCH = DST / REL / f"{STEM}.kicad_sch"
KICAD = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KICAD_PY = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"


def balanced(text: str, start: int) -> int:
    depth = 0
    quote = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                quote = False
        else:
            if char == '"':
                quote = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return index + 1
    raise RuntimeError("unterminated s-expression")


def semantic_netlist(path: Path):
    root = ET.parse(path).getroot()
    refs = sorted(component.get("ref") for component in root.findall("components/comp"))
    tuples = sorted(
        (node.get("ref"), node.get("pin"), net.get("name", ""))
        for net in root.findall("nets/net")
        for node in net.findall("node")
    )
    return refs, tuples


if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("verification", "__pycache__", "*.pyc", "*.kicad_prl", "*.lck"))
(DST / "verification").mkdir()

# Lock each top-level footprint by preserving the exact source text and inserting
# only the native KiCad footprint lock flag where absent.
text = PCB.read_text()
position = 0
footprint_count = 0
newly_locked = []
while True:
    start = text.find("(footprint ", position)
    if start < 0:
        break
    end = balanced(text, start)
    block = text[start:end]
    # Skip cached/non-board forms if any; board footprint blocks always have a layer.
    layer_position = block.find("(layer ")
    if layer_position < 0:
        position = end
        continue
    footprint_count += 1
    ref_match = re.search(r'\(property "Reference" "([^"]+)"', block)
    ref = ref_match.group(1) if ref_match else f"#{footprint_count}"
    header = block[:layer_position]
    if "(locked yes)" not in header:
        block = block[:layer_position] + "(locked yes) " + block[layer_position:]
        text = text[:start] + block + text[end:]
        end = start + len(block)
        newly_locked.append(ref)
    position = end
PCB.write_text(text)

# Native checks and machine-readable placement export.
subprocess.run(
    [KICAD, "sch", "erc", "--format", "json", "--severity-all", "--output", str(DST / "verification/erc.json"), str(SCH)],
    check=True,
)
subprocess.run(
    [KICAD, "sch", "export", "netlist", "--format", "kicadxml", "--output", str(DST / "verification/netlist.xml"), str(SCH)],
    check=True,
)
subprocess.run(
    [KICAD, "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--output", str(DST / "verification/drc.json"), str(PCB)],
    check=True,
)
subprocess.run(
    [KICAD, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "--output", str(DST / "verification/placement.csv"), str(PCB)],
    check=True,
)

# Public evidence must not expose the local checkout path.
netlist_path = DST / "verification/netlist.xml"
netlist_text = netlist_path.read_text()
netlist_text = re.sub(
    r"<source>.*?</source>",
    "<source>eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16/PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_sch</source>",
    netlist_text,
    count=1,
)
netlist_path.write_text(netlist_text)

drc = json.loads((DST / "verification/drc.json").read_text())
erc = json.loads((DST / "verification/erc.json").read_text())
counts = {
    "erc": sum(len(sheet.get("violations", [])) for sheet in erc.get("sheets", [])),
    "drc": len(drc.get("violations", [])),
    "parity": len(drc.get("schematic_parity", [])),
    "open": len(drc.get("unconnected_items", [])),
}
if counts != {"erc": 0, "drc": 0, "parity": 0, "open": 436}:
    raise SystemExit(f"unexpected native checks: {counts}")

source_refs, source_tuples = semantic_netlist(SRC / "verification/netlist.xml")
target_refs, target_tuples = semantic_netlist(netlist_path)
if source_refs != target_refs or source_tuples != target_tuples:
    raise SystemExit("placement freeze changed schematic topology")

# Inspect board geometry/poses with KiCad's native API in an isolated subprocess.
audit_script = f'''import json, pcbnew\nboard=pcbnew.LoadBoard(r"{PCB}")\nbox=board.GetBoardEdgesBoundingBox()\npositions={{}}\nfor ref in ["J201","J301","J501","J502","J802","J803","J804","U501","U905","SW201","SW202","H801","H802","H803","H804"]:\n    fp=board.FindFootprintByReference(ref)\n    if fp is not None:\n        p=fp.GetPosition()\n        positions[ref]={{"x_mm":round(pcbnew.ToMM(p.x),3),"y_mm":round(pcbnew.ToMM(p.y),3),"rotation_deg":round(fp.GetOrientationDegrees(),1),"side":board.GetLayerName(fp.GetLayer()),"locked":bool(fp.IsLocked())}}\nresult={{\n "board_bbox_mm":[round(pcbnew.ToMM(box.GetX()),3),round(pcbnew.ToMM(box.GetY()),3),round(pcbnew.ToMM(box.GetWidth()),3),round(pcbnew.ToMM(box.GetHeight()),3)],\n "copper_layers":board.GetCopperLayerCount(),\n "footprints":len(list(board.GetFootprints())),\n "locked_footprints":sum(1 for fp in board.GetFootprints() if fp.IsLocked()),\n "tracks":len(list(board.GetTracks())),\n "zones":len(list(board.Zones())),\n "positions":positions,\n}}\nprint(json.dumps(result))\n'''
completed = subprocess.run([KICAD_PY, "-c", audit_script], check=True, capture_output=True, text=True)
geometry = json.loads(completed.stdout.strip().splitlines()[-1])
if geometry["copper_layers"] != 4 or geometry["footprints"] != 189 or geometry["locked_footprints"] != 189:
    raise SystemExit(f"placement-lock invariant failed: {geometry}")
if geometry["tracks"] != 0 or geometry["zones"] != 0:
    raise SystemExit("C4D11 must remain an unrouted placement checkpoint")
# The 0.025-mm Edge.Cuts stroke expands the native 0..96 x 0..68 rectangle.
if geometry["board_bbox_mm"] != [-0.025, -0.025, 96.05, 68.065]:
    raise SystemExit(f"board boundary changed: {geometry['board_bbox_mm']}")

expected_positions = {
    "J201": (39.0, 68.0, 0.0),
    "J501": (88.8, 18.75, -90.0),
    "J802": (61.0, 52.5, 0.0),
    "J803": (6.35, 39.37, 0.0),
    "J804": (6.35, 45.5, 0.0),
    "U905": (4.0, 52.5, 0.0),
    "H801": (15.0, 2.0, 0.0),
    "H802": (81.0, 2.0, 0.0),
    "H803": (93.0, 34.0, 0.0),
    "H804": (3.0, 34.0, 0.0),
}
for ref, expected in expected_positions.items():
    actual = geometry["positions"].get(ref)
    if actual is None or (actual["x_mm"], actual["y_mm"], actual["rotation_deg"]) != expected:
        raise SystemExit(f"key placement changed for {ref}: {actual} != {expected}")

report = {
    "date": "2026-09-30",
    "kind": "C4D-11 final compact placement checkpoint",
    "source": "c4d10b-96x68-frontlight",
    "target_board_mm": [96.0, 68.0],
    "coupon_hard_max_mm": [100.0, 100.0],
    "battery_rear_envelope_mm": [64.0, 60.0],
    "battery_rect_xyxy_mm": [21.0, 4.0, 85.0, 64.0],
    "footprints": geometry["footprints"],
    "locked_footprints": geometry["locked_footprints"],
    "newly_locked_refs": newly_locked,
    "tracks": geometry["tracks"],
    "zones": geometry["zones"],
    "native_checks": counts,
    "refs": len(target_refs),
    "pin_net_tuples": len(target_tuples),
    "key_positions": geometry["positions"],
    "placement_csv": "verification/placement.csv",
    "placement_gates": {
        "board_under_100x100": True,
        "all_footprints_locked": True,
        "native_drc_zero": True,
        "schematic_parity_zero": True,
        "erc_zero": True,
        "battery_envelope_inherited_from_c1": True,
        "physical_fpc_fit": False,
        "battery_thickness_swelling_harness": False,
        "enclosure_z_stack": False,
    },
    "routing_authority": False,
    "manufacturing_release": False,
    "physical_qualification_complete": False,
    "pcb_sha256": hashlib.sha256(PCB.read_bytes()).hexdigest(),
}
(DST / "c4d11-placement-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
# Native KiCad checks may create per-user session files; never publish them.
for session_file in DST.rglob("*.kicad_prl"):
    session_file.unlink()
for lock_file in DST.rglob("*.lck"):
    lock_file.unlink()

(DST / "README.md").write_text(
    "# Thin18 Compact C4D-11 — final placement checkpoint\n\n"
    "All 189 footprints are locked on the 96 × 68 mm compact board. No reference, pose, net or footprint geometry changed from C4D-10B.\n\n"
    f"Fresh checks: ERC={counts['erc']}, DRC={counts['drc']}, parity={counts['parity']}, open={counts['open']}. "
    "The checkpoint is intentionally unrouted and is the input to controlled DSN/SES routing.\n\n"
    "Physical battery/FPC/enclosure qualification remains open. Not a manufacturing release.\n"
)
print(json.dumps(report, ensure_ascii=False, indent=2))
