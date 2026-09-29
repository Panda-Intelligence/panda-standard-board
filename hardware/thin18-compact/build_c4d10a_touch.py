#!/usr/bin/env python3
"""Build the C4D-10A touch-interface candidate from the clean C4D-9 checkpoint.

This stage deliberately excludes the front-light driver. It adds only the exact
six-pin touch FPC connector, two mainland pull-ups, and allocates U601 P16/P17.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "c4d9-96x68-aip-buffers"
DST = ROOT / "c4d10a-96x68-touch"
REL = Path("eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16")
STEM = "PANDA-STD-CORE-EVT-quilter-j501-merged"
SCH = DST / REL / f"{STEM}.kicad_sch"
PCB = DST / REL / f"{STEM}.kicad_pcb"
PROJECT_LIB = DST / REL / "PandaDomestic.kicad_sym"
PROJECT_PRETTY = DST / REL / "PandaDomestic.pretty"
KICAD = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KICAD_PY = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"


def uid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "thin18-c4d10a-" + seed))


def balanced(text: str, start: int) -> int:
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        else:
            if char == '"':
                quoted = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return index + 1
    raise RuntimeError("unterminated s-expression")


def block_by_ref(text: str, kind: str, ref: str):
    marker = f'(property "Reference" "{ref}"'
    position = text.index(marker)
    start = text.rfind(f"({kind} ", 0, position)
    return start, balanced(text, start), text[start : balanced(text, start)]


def reuuid(block: str, seed: str) -> str:
    mapped = {}

    def replace(match):
        old = match.group(1)
        if old not in mapped:
            mapped[old] = uid(f"{seed}-{len(mapped)}")
        return f'uuid "{mapped[old]}"'

    return re.sub(r'uuid "([^"]+)"', replace, block)


def replace_property(block: str, name: str, value: str) -> str:
    pattern = rf'(\(property "{re.escape(name)}" ")[^"]*(")'
    if re.search(pattern, block):
        return re.sub(pattern, lambda m: m.group(1) + value + m.group(2), block, count=1)
    return block


def sch_property(name: str, value: str, x: float, y: float) -> str:
    return (
        f'(property "{name}" "{value}" (at {x:.2f} {y:.2f} 0) '
        '(hide yes) (show_name no) (do_not_autoplace no) '
        '(effects (font (size 1 1))))'
    )


def pcb_property(ref: str, name: str, value: str) -> str:
    return (
        f'(property "{name}" "{value}" (at 0 0 0) (layer "F.Fab") '
        f'(hide yes) (uuid "{uid(ref + "-" + name)}") '
        '(effects (font (size 1 1) (thickness 0.15))))'
    )


def global_label(name: str, x: float, y: float, key: str) -> str:
    return (
        f'(global_label "{name}" (shape passive) (at {x:.2f} {y:.2f} 0) '
        '(effects (font (size 1.0 1.0)) (justify left bottom)) '
        f'(uuid "{uid("label-" + key)}"))'
    )


FPC_CACHE_SYMBOL = '''(symbol "PandaDomestic:FH34SRJ-6S-0.5SH_50"
(pin_names (offset 1.016) (hide yes))
(exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes)
(property "Reference" "J" (at 0 8.89 0) (effects (font (size 1 1))))
(property "Value" "FH34SRJ-6S-0.5SH(50)" (at 0 -8.89 0) (effects (font (size 1 1))))
(property "Footprint" "PandaDomestic:FH34SRJ-6S-0.5SH_50" (at 0 0 0) (hide yes) (effects (font (size 1 1))))
(property "Datasheet" "https://www.hirose.com/product/p/CL0580-1236-1-50" (at 0 0 0) (hide yes) (effects (font (size 1 1))))
(property "Description" "Hirose FH34SRJ 6-position 0.5 mm dual-contact back-flip FPC connector" (at 0 0 0) (hide yes) (effects (font (size 1 1))))
(symbol "FH34SRJ-6S-0.5SH_50_0_1"
(rectangle (start -1.27 7.62) (end 1.27 -7.62) (stroke (width 0.254) (type default)) (fill (type background))))
(symbol "FH34SRJ-6S-0.5SH_50_1_1"
(pin passive line (at -5.08 6.35 0) (length 3.81) (name "GND" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
(pin passive line (at -5.08 3.81 0) (length 3.81) (name "VDD3V3" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))
(pin passive line (at -5.08 1.27 0) (length 3.81) (name "RST" (effects (font (size 1 1)))) (number "3" (effects (font (size 1 1)))))
(pin passive line (at -5.08 -1.27 0) (length 3.81) (name "INT" (effects (font (size 1 1)))) (number "4" (effects (font (size 1 1)))))
(pin passive line (at -5.08 -3.81 0) (length 3.81) (name "SDA" (effects (font (size 1 1)))) (number "5" (effects (font (size 1 1)))))
(pin passive line (at -5.08 -6.35 0) (length 3.81) (name "SCL" (effects (font (size 1 1)))) (number "6" (effects (font (size 1 1)))))))'''

FPC_PROJECT_SYMBOL = FPC_CACHE_SYMBOL.replace(
    'PandaDomestic:FH34SRJ-6S-0.5SH_50',
    'FH34SRJ-6S-0.5SH_50',
    1,
)

# Land pattern transcribed from a public KiCad C224194 footprint and retained with
# signal pads 1..6 plus non-electrical support pads S1/S2.
FPC_LIBRARY_FOOTPRINT = '''(footprint "FH34SRJ-6S-0.5SH_50"
(version 20240108) (generator pcbnew) (layer "F.Cu")
(descr "Hirose FH34SRJ-6S-0.5SH(50), LCSC/JLC C224194, 6P 0.5 mm dual-contact back-flip")
(tags "FH34SRJ FPC 6P 0.5mm C224194")
(property "Reference" "REF**" (at 0.65 0 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
(property "Value" "FH34SRJ-6S-0.5SH(50)" (at 0 -4.298 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
(attr smd)
(fp_line (start -2.45 -1.25) (end -1.631 -1.25) (stroke (width 0.254) (type solid)) (layer "F.SilkS"))
(fp_line (start -2.45 0.619) (end -2.45 -1.25) (stroke (width 0.254) (type solid)) (layer "F.SilkS"))
(fp_line (start -2.278 -2.228) (end 2.25 -2.228) (stroke (width 0.254) (type solid)) (layer "F.SilkS"))
(fp_line (start -2.278 -1.25) (end -2.278 -2.228) (stroke (width 0.254) (type solid)) (layer "F.SilkS"))
(fp_line (start -1.814 1.624) (end 1.761 1.624) (stroke (width 0.254) (type solid)) (layer "F.SilkS"))
(fp_line (start 1.631 -1.25) (end 2.45 -1.25) (stroke (width 0.254) (type solid)) (layer "F.SilkS"))
(fp_line (start 2.25 -2.228) (end 2.25 -1.25) (stroke (width 0.254) (type solid)) (layer "F.SilkS"))
(fp_line (start 2.45 0.619) (end 2.45 -1.25) (stroke (width 0.254) (type solid)) (layer "F.SilkS"))
(fp_rect (start -2.7 -2.48) (end 2.7 1.95) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
(fp_rect (start -2.45 -2.228) (end 2.45 1.624) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
(pad "1" smd rect (at 1.25 -1.25 90) (size 1 0.3) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "2" smd rect (at 0.75 -1.25 90) (size 1 0.3) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "3" smd rect (at 0.25 -1.25 90) (size 1 0.3) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "4" smd rect (at -0.25 -1.25 90) (size 1 0.3) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "5" smd rect (at -0.75 -1.25 90) (size 1 0.3) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "6" smd rect (at -1.25 -1.25 90) (size 1 0.3) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "S1" smd rect (at -2.25 1.25 90) (size 1 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "S2" smd rect (at 2.25 1.25 90) (size 1 0.6) (layers "F.Cu" "F.Paste" "F.Mask")))'''


def connector_instance(x: float, y: float) -> str:
    pins = " ".join(
        f'(pin "{number}" (uuid "{uid("j803-pin-" + str(number))}"))'
        for number in range(1, 7)
    )
    fields = " ".join(
        [
            sch_property("Manufacturer", "Hirose", x, y),
            sch_property("MPN", "FH34SRJ-6S-0.5SH(50)", x, y),
            sch_property("LCSC", "C224194", x, y),
            sch_property("ECO_ID", "THIN18-C4D10A-TOUCH", x, y),
            sch_property(
                "Qualification",
                "Exact C224194 land pattern imported; FPC orientation and physical insertion qualification open",
                x,
                y,
            ),
        ]
    )
    root_uuid = ROOT_SCHEMATIC_UUID
    return f'''(symbol (lib_id "PandaDomestic:FH34SRJ-6S-0.5SH_50") (at {x:.2f} {y:.2f} 0)
(unit 1) (body_style 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes) (dnp no)
(uuid "{uid("j803-symbol")}")
(property "Reference" "J803" (at {x:.2f} {y - 8.89:.2f} 0) (effects (font (size 1 1))))
(property "Value" "FH34SRJ-6S-0.5SH(50)" (at {x:.2f} {y + 8.89:.2f} 0) (effects (font (size 1 1))))
(property "Footprint" "PandaDomestic:FH34SRJ-6S-0.5SH_50" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1 1))))
(property "Datasheet" "https://www.hirose.com/product/p/CL0580-1236-1-50" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1 1))))
(property "Description" "Hirose FH34SRJ 6-position 0.5 mm dual-contact back-flip FPC connector" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1 1))))
{fields} {pins}
(instances (project "PANDA-STD-CORE-EVT" (path "/{root_uuid}" (reference "J803") (unit 1)))))'''


def resistor_instance(ref: str, x: float, y: float, signal: str) -> str:
    fields = " ".join(
        [
            sch_property("Manufacturer", "FH (Fenghua Advanced)", x, y),
            sch_property("MPN", "THC02H1002BT", x, y),
            sch_property("LCSC", "C2991528", x, y),
            sch_property("Tolerance", "0.1%", x, y),
            sch_property("Power_Rating", "62.5mW", x, y),
            sch_property("Voltage_Rating", "50V", x, y),
            sch_property("ECO_ID", "THIN18-C4D10A-TOUCH", x, y),
            sch_property(
                "Qualification",
                "Mainland 10k pull-up; touch timing/current and assembly qualification open",
                x,
                y,
            ),
        ]
    )
    return f'''(symbol (lib_id "Device:R") (at {x:.2f} {y:.2f} 0) (unit 1) (body_style 1)
(exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes) (dnp no)
(uuid "{uid(ref + "-symbol")}")
(property "Reference" "{ref}" (at {x + 2.54:.2f} {y - 1.27:.2f} 0) (effects (font (size 1 1))))
(property "Value" "10k / {signal}_PU" (at {x + 2.54:.2f} {y + 1.27:.2f} 0) (effects (font (size 1 1))))
(property "Footprint" "Resistor_SMD:R_0402_1005Metric" (at {x:.2f} {y:.2f} 90) (hide yes) (effects (font (size 1 1))))
(property "Datasheet" "https://jlcpcb.com/partdetail/3454095-THC02H1002BT/C2991528" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1 1))))
(property "Description" "Fenghua mainland 10k 0.1% 62.5mW 50V 0402 pull-up" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1 1))))
{fields}
(pin "1" (uuid "{uid(ref + "-pin-1")}")) (pin "2" (uuid "{uid(ref + "-pin-2")}"))
(instances (project "PANDA-STD-CORE-EVT" (path "/{ROOT_SCHEMATIC_UUID}" (reference "{ref}") (unit 1)))))'''


def clone_resistor_footprint(board_text: str, ref: str, x: float, y: float, signal: str) -> str:
    _, _, block = block_by_ref(board_text, "footprint", "R529")
    block = reuuid(block, ref)
    block = re.sub(r'(\(at\s+)[\d.-]+\s+[\d.-]+(?:\s+[\d.-]+)?', rf'\g<1>{x:.2f} {y:.2f}', block, count=1)
    block = replace_property(block, "Reference", ref)
    block = replace_property(block, "Value", f"10k / {signal}_PU")
    block = replace_property(block, "Datasheet", "https://jlcpcb.com/partdetail/3454095-THC02H1002BT/C2991528")
    block = replace_property(block, "Description", "Fenghua mainland 10k 0.1% 62.5mW 50V 0402 pull-up")
    block = re.sub(r'\(path "[^"]+"\)', "", block, count=1)
    fields = {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "THC02H1002BT",
        "LCSC": "C2991528",
        "Tolerance": "0.1%",
        "Power_Rating": "62.5mW",
        "Voltage_Rating": "50V",
        "ECO_ID": "THIN18-C4D10A-TOUCH",
        "Qualification": "Mainland 10k pull-up; touch timing/current and assembly qualification open",
    }
    for name, value in fields.items():
        block = replace_property(block, name, value)
    attr = block.index("(attr smd)")
    missing = " ".join(
        pcb_property(ref, name, value)
        for name, value in fields.items()
        if f'(property "{name}" ' not in block
    )
    if missing:
        block = block[:attr] + missing + " " + block[attr:]
    for pad, net in {"1": "3V3_TOUCH", "2": signal}.items():
        pattern = rf'(\(pad "{pad}" .*?\(net ")[^"]*("\))'
        block, count = re.subn(pattern, lambda m: m.group(1) + net + m.group(2), block, count=1, flags=re.S)
        if count != 1:
            raise SystemExit(f"{ref} pad {pad} net replacement failed")
    return block


def board_connector_footprint(x: float, y: float) -> str:
    pad_nets = {
        1: "GND",
        2: "3V3_TOUCH",
        3: "TOUCH_RST",
        4: "TOUCH_INT",
        5: "I2C_SDA",
        6: "I2C_SCL",
    }
    x_positions = [1.25, 0.75, 0.25, -0.25, -0.75, -1.25]
    pads = " ".join(
        f'(pad "{pin}" smd rect (at {px} -1.25 90) (size 1 0.3) '
        f'(layers "F.Cu" "F.Paste" "F.Mask") (net "{pad_nets[pin]}") (uuid "{uid("j803-pad-" + str(pin))}"))'
        for pin, px in enumerate(x_positions, 1)
    )
    anchors = (
        f'(pad "S1" smd rect (at -2.25 1.25 90) (size 1 0.6) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{uid("j803-s1")}")) '
        f'(pad "S2" smd rect (at 2.25 1.25 90) (size 1 0.6) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{uid("j803-s2")}"))'
    )
    fields = " ".join(
        [
            pcb_property("J803", "Manufacturer", "Hirose"),
            pcb_property("J803", "MPN", "FH34SRJ-6S-0.5SH(50)"),
            pcb_property("J803", "LCSC", "C224194"),
            pcb_property("J803", "ECO_ID", "THIN18-C4D10A-TOUCH"),
            pcb_property(
                "J803",
                "Qualification",
                "Exact C224194 land pattern imported; FPC orientation and physical insertion qualification open",
            ),
        ]
    )
    return f'''(footprint "PandaDomestic:FH34SRJ-6S-0.5SH_50" (locked yes) (layer "F.Cu")
(uuid "{uid("j803-footprint")}") (at {x:.2f} {y:.2f})
(descr "Hirose FH34SRJ-6S-0.5SH(50), C224194") (tags "FH34SRJ FPC 6P 0.5mm C224194")
(property "Reference" "J803" (at 0.65 0 0) (layer "F.SilkS") (hide yes) (uuid "{uid("j803-ref")}") (effects (font (size 1 1) (thickness 0.15))))
(property "Value" "FH34SRJ-6S-0.5SH(50)" (at 0 -4.298 0) (layer "F.Fab") (uuid "{uid("j803-value")}") (effects (font (size 1 1) (thickness 0.15))))
(property "Datasheet" "https://www.hirose.com/product/p/CL0580-1236-1-50" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uid("j803-datasheet")}") (effects (font (size 1 1))))
(property "Description" "Hirose FH34SRJ 6-position 0.5 mm dual-contact back-flip FPC connector" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uid("j803-description")}") (effects (font (size 1 1))))
{fields} (attr smd)
(fp_line (start -2.45 -1.25) (end -1.631 -1.25) (stroke (width 0.254) (type solid)) (layer "F.SilkS") (uuid "{uid("j803-line-1")}"))
(fp_line (start -2.45 0.619) (end -2.45 -1.25) (stroke (width 0.254) (type solid)) (layer "F.SilkS") (uuid "{uid("j803-line-2")}"))
(fp_line (start -2.278 -2.228) (end 2.25 -2.228) (stroke (width 0.254) (type solid)) (layer "F.SilkS") (uuid "{uid("j803-line-3")}"))
(fp_line (start -2.278 -1.25) (end -2.278 -2.228) (stroke (width 0.254) (type solid)) (layer "F.SilkS") (uuid "{uid("j803-line-4")}"))
(fp_line (start -1.814 1.624) (end 1.761 1.624) (stroke (width 0.254) (type solid)) (layer "F.SilkS") (uuid "{uid("j803-line-5")}"))
(fp_line (start 1.631 -1.25) (end 2.45 -1.25) (stroke (width 0.254) (type solid)) (layer "F.SilkS") (uuid "{uid("j803-line-6")}"))
(fp_line (start 2.25 -2.228) (end 2.25 -1.25) (stroke (width 0.254) (type solid)) (layer "F.SilkS") (uuid "{uid("j803-line-7")}"))
(fp_line (start 2.45 0.619) (end 2.45 -1.25) (stroke (width 0.254) (type solid)) (layer "F.SilkS") (uuid "{uid("j803-line-8")}"))
{pads} {anchors})'''


if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("verification", "__pycache__", "*.pyc"))
(DST / "verification").mkdir()
PROJECT_PRETTY.mkdir(exist_ok=True)
(PROJECT_PRETTY / "FH34SRJ-6S-0.5SH_50.kicad_mod").write_text(FPC_LIBRARY_FOOTPRINT + "\n")

# Keep project symbol library synchronized with the schematic cache.
project_library = PROJECT_LIB.read_text()
if '(symbol "FH34SRJ-6S-0.5SH_50"' not in project_library:
    end = project_library.rfind(")")
    project_library = project_library[:end] + " " + FPC_PROJECT_SYMBOL + " " + project_library[end:]
PROJECT_LIB.write_text(project_library)

schematic = SCH.read_text()
root_match = re.search(r'^\(kicad_sch .*?\(uuid "([^"]+)"\)', schematic)
if not root_match:
    raise SystemExit("root schematic UUID not found")
ROOT_SCHEMATIC_UUID = root_match.group(1)

# Add cached connector symbol.
lib_start = schematic.index("(lib_symbols ")
lib_end = balanced(schematic, lib_start)
if '(symbol "PandaDomestic:FH34SRJ-6S-0.5SH_50"' not in schematic[lib_start:lib_end]:
    schematic = schematic[: lib_end - 1] + " " + FPC_CACHE_SYMBOL + schematic[lib_end - 1 :]

# Allocate U601 P16/P17 to touch INT/RST. P15 remains spare for the gated front-light stage.
for coordinate, net, key in [
    ("78.74 86.36", "TOUCH_INT", "u601-p16"),
    ("78.74 88.9", "TOUCH_RST", "u601-p17"),
]:
    marker = f"(no_connect (at {coordinate})"
    position = schematic.find(marker)
    if position < 0:
        raise SystemExit(f"missing U601 spare no-connect at {coordinate}")
    end = balanced(schematic, position)
    x, y = map(float, coordinate.split())
    schematic = schematic[:position] + global_label(net, x, y, key) + schematic[end:]

# Add touch connector and pull-ups in a blank root-sheet region.
jx, jy = 25.40, 215.90
rx1, ry1 = 55.88, 215.90
rx2, ry2 = 73.66, 215.90
items = [
    connector_instance(jx, jy),
    resistor_instance("R910", rx1, ry1, "TOUCH_INT"),
    resistor_instance("R911", rx2, ry2, "TOUCH_RST"),
]
connector_nets = ["GND", "3V3_TOUCH", "TOUCH_RST", "TOUCH_INT", "I2C_SDA", "I2C_SCL"]
connector_relative_y = [6.35, 3.81, 1.27, -1.27, -3.81, -6.35]
labels = [
    global_label(net, jx - 5.08, jy - rel_y, f"j803-{pin}")
    for pin, (net, rel_y) in enumerate(zip(connector_nets, connector_relative_y), 1)
]
labels.extend(
    [
        global_label("3V3_TOUCH", rx1, ry1 - 3.81, "r910-1"),
        global_label("TOUCH_INT", rx1, ry1 + 3.81, "r910-2"),
        global_label("3V3_TOUCH", rx2, ry2 - 3.81, "r911-1"),
        global_label("TOUCH_RST", rx2, ry2 + 3.81, "r911-2"),
    ]
)
root_end = schematic.rfind(")")
SCH.write_text(schematic[:root_end] + " " + " ".join(items + labels) + schematic[root_end:])

# PCB U601 pin allocation plus exact J803 and pull-up footprints.
board = PCB.read_text()
start, end, u601 = block_by_ref(board, "footprint", "U601")
for pad, old_net, new_net in [
    ("19", "unconnected-(U601-P16-Pad19)", "TOUCH_INT"),
    ("20", "unconnected-(U601-P17-Pad20)", "TOUCH_RST"),
]:
    pattern = rf'(\(pad "{pad}" .*?\(net "){re.escape(old_net)}("\))'
    u601, count = re.subn(pattern, lambda m: m.group(1) + new_net + m.group(2), u601, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"U601 pad {pad} allocation failed")
board = board[:start] + u601 + board[end:]

new_footprints = [
    board_connector_footprint(6.35, 39.37),
    clone_resistor_footprint(board, "R910", 12.70, 38.50, "TOUCH_INT"),
    clone_resistor_footprint(board, "R911", 12.70, 41.00, "TOUCH_RST"),
]
board_end = board.rfind(")")
PCB.write_text(board[:board_end] + " " + " ".join(new_footprints) + board[board_end:])

# Save the exact scripted board footprint back through KiCad's native footprint
# writer. The board retains its correct PandaDomestic FPID while the library copy
# is canonicalized to the identical geometry/properties used by DRC.
library_saver = f"""import pcbnew
from pathlib import Path
board = pcbnew.LoadBoard(r'{PCB}')
footprint = board.FindFootprintByReference('J803')
if footprint is None:
    raise SystemExit('J803 board footprint missing')
library = Path(r'{PROJECT_PRETTY}')
target = library / 'FH34SRJ-6S-0.5SH_50.kicad_mod'
if target.exists():
    target.unlink()
plugin = pcbnew.PCB_IO_KICAD_SEXPR()
plugin.FootprintSave(str(library), footprint)
"""
subprocess.run([KICAD_PY, "-c", library_saver], check=True)

# Fresh native checks.
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

erc = json.loads((DST / "verification/erc.json").read_text())
drc = json.loads((DST / "verification/drc.json").read_text())
counts = {
    "erc": sum(len(sheet.get("violations", [])) for sheet in erc.get("sheets", [])),
    "drc": len(drc.get("violations", [])),
    "parity": len(drc.get("schematic_parity", [])),
    "open": len(drc.get("unconnected_items", [])),
}
if counts["erc"] or counts["drc"] or counts["parity"]:
    print(json.dumps(counts))
    raise SystemExit("C4D10A native checks not clean")


def semantic_netlist(path: Path):
    root = ET.parse(path).getroot()
    refs = sorted(component.get("ref") for component in root.findall("components/comp"))
    tuples = []
    values = {}
    fields = {}
    for component in root.findall("components/comp"):
        ref = component.get("ref")
        values[ref] = component.findtext("value") or ""
        fields[ref] = {field.get("name"): field.text or "" for field in component.findall("fields/field")}
    for net in root.findall("nets/net"):
        for node in net.findall("node"):
            tuples.append((node.get("ref"), node.get("pin"), net.get("name", "")))
    return refs, sorted(tuples), values, fields


source_refs, source_tuples, _, _ = semantic_netlist(SRC / "verification/netlist.xml")
target_refs, target_tuples, target_values, target_fields = semantic_netlist(DST / "verification/netlist.xml")
new_refs = {"J803", "R910", "R911"}
if set(target_refs) - set(source_refs) != new_refs or set(source_refs) - set(target_refs):
    raise SystemExit("unexpected component-set delta")

allowed_existing_changes = {("U601", "19"), ("U601", "20")}
source_map = {(ref, pin): net for ref, pin, net in source_tuples}
target_map = {(ref, pin): net for ref, pin, net in target_tuples}
changed_existing = []
for key in sorted(set(source_map) | set(target_map)):
    if key[0] in new_refs:
        continue
    if source_map.get(key) != target_map.get(key):
        changed_existing.append((key, source_map.get(key), target_map.get(key)))
if {entry[0] for entry in changed_existing} != allowed_existing_changes:
    raise SystemExit(f"unexpected existing-net delta: {changed_existing}")
if target_map.get(("U601", "19")) != "TOUCH_INT" or target_map.get(("U601", "20")) != "TOUCH_RST":
    raise SystemExit("U601 touch allocation mismatch")

expected_new_pinmap = {
    ("J803", "1"): "GND",
    ("J803", "2"): "3V3_TOUCH",
    ("J803", "3"): "TOUCH_RST",
    ("J803", "4"): "TOUCH_INT",
    ("J803", "5"): "I2C_SDA",
    ("J803", "6"): "I2C_SCL",
    ("R910", "1"): "3V3_TOUCH",
    ("R910", "2"): "TOUCH_INT",
    ("R911", "1"): "3V3_TOUCH",
    ("R911", "2"): "TOUCH_RST",
}
wrong_new = {
    str(key): (target_map.get(key), expected)
    for key, expected in expected_new_pinmap.items()
    if target_map.get(key) != expected
}
if wrong_new:
    raise SystemExit(f"new touch pin map mismatch: {wrong_new}")
if target_values.get("J803") != "FH34SRJ-6S-0.5SH(50)":
    raise SystemExit("J803 value mismatch")
if target_fields.get("J803", {}).get("LCSC") != "C224194":
    raise SystemExit("J803 procurement fields missing")

report = {
    "date": "2026-09-30",
    "kind": "C4D-10A exact touch-FPC integration",
    "source": "c4d9-96x68-aip-buffers",
    "added": ["J803", "R910", "R911"],
    "connector": {
        "mpn": "FH34SRJ-6S-0.5SH(50)",
        "catalog": "C224194",
        "land_pattern": "public C224194 KiCad footprint geometry, anchors made non-electrical",
        "panel_pinmap": connector_nets,
    },
    "u601_allocation": {"P16/pad19": "TOUCH_INT", "P17/pad20": "TOUCH_RST"},
    "pullups": {
        "R910": "Fenghua THC02H1002BT / C2991528 / TOUCH_INT",
        "R911": "Fenghua THC02H1002BT / C2991528 / TOUCH_RST",
    },
    "native_checks": counts,
    "refs": len(target_refs),
    "pin_net_tuples": len(target_tuples),
    "existing_net_delta": changed_existing,
    "physical_qualification": [
        "FT01C flex contact-side/orientation overlay",
        "FPC insertion/retention/rework clearance",
        "FT6336U reset timing",
        "TOUCH_INT logic level and latency",
        "touch power-domain leakage and wake policy",
    ],
    "frontlight_integrated": False,
    "manufacturing_release": False,
    "physical_qualification_complete": False,
    "pcb_sha256": hashlib.sha256(PCB.read_bytes()).hexdigest(),
}
(DST / "c4d10a-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
(DST / "README.md").write_text(
    "# Thin18 Compact C4D-10A — exact touch FPC\n\n"
    "J803 uses the exact FH34SRJ-6S-0.5SH(50) / C224194 six-pin footprint. "
    "U601 P16/P17 are allocated to TOUCH_INT/TOUCH_RST and two mainland Fenghua pull-ups are added.\n\n"
    f"Fresh checks: ERC={counts['erc']}, DRC={counts['drc']}, parity={counts['parity']}, "
    f"open={counts['open']} (expected because final routing has not started).\n\n"
    "Front-light CAD remains gated and is not included in this stage. Physical qualification remains open.\n"
)
print(json.dumps(report, ensure_ascii=False, indent=2))
