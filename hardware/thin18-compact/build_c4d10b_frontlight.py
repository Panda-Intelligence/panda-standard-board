#!/usr/bin/env python3
"""Build C4D-10B: exact dual-string front-light interface and mainland driver.

Source checkpoint: C4D-10A exact touch interface.
This stage adds SGM37601, J804 and the qualified support network, allocates
U601 P15/P16 to EN/PWM, and deliberately leaves the compact PCB unrouted.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "c4d10a-96x68-touch"
DST = ROOT / "c4d10b-96x68-frontlight"
REL = Path("eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16")
STEM = "PANDA-STD-CORE-EVT-quilter-j501-merged"
ROOT_SCH = DST / REL / f"{STEM}.kicad_sch"
DISPLAY_SCH = DST / REL / "display-integrated.kicad_sch"
PCB = DST / REL / f"{STEM}.kicad_pcb"
PROJECT_LIB = DST / REL / "PandaDomestic.kicad_sym"
PROJECT_PRETTY = DST / REL / "PandaDomestic.pretty"
KICAD = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KICAD_PY = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"
KICAD_FP_ROOT = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")


def uid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "thin18-c4d10b-" + seed))


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
    end = balanced(text, start)
    return start, end, text[start:end]


def cached_symbol(text: str, name: str) -> str:
    marker = f'(symbol "{name}"'
    start = text.index(marker)
    return text[start : balanced(text, start)]


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
        return re.sub(pattern, lambda match: match.group(1) + value + match.group(2), block, count=1)
    return block


def hidden_sch_property(name: str, value: str, x: float, y: float) -> str:
    return (
        f'(property "{name}" "{value}" (at {x:.2f} {y:.2f} 0) '
        '(hide yes) (show_name no) (do_not_autoplace no) '
        '(effects (font (size 1 1))))'
    )


def update_symbol_properties(text: str, ref: str, updates: dict) -> str:
    start, end, block = block_by_ref(text, "symbol", ref)
    x, y = map(float, re.search(r'\(at ([\d.-]+) ([\d.-]+)', block).groups())
    for name, value in updates.items():
        if f'(property "{name}" ' in block:
            block = replace_property(block, name, value)
        else:
            pin_position = block.index('(pin "1"')
            block = block[:pin_position] + hidden_sch_property(name, value, x, y) + " " + block[pin_position:]
    return text[:start] + block + text[end:]


def update_footprint_properties(text: str, ref: str, updates: dict) -> str:
    start, end, block = block_by_ref(text, "footprint", ref)
    for name, value in updates.items():
        if f'(property "{name}" ' in block:
            block = replace_property(block, name, value)
        else:
            attr = block.index("(attr smd)")
            prop = (
                f'(property "{name}" "{value}" (at 0 0 0) (layer "F.Fab") '
                f'(hide yes) (uuid "{uid(ref + "-" + name)}") '
                '(effects (font (size 1 1) (thickness 0.15))))'
            )
            block = block[:attr] + prop + " " + block[attr:]
    return text[:start] + block + text[end:]


def global_label(name: str, x: float, y: float, key: str, angle: int = 0) -> str:
    return (
        f'(global_label "{name}" (shape passive) (at {x:.2f} {y:.2f} {angle}) '
        '(effects (font (size 1.0 1.0)) (justify left bottom)) '
        f'(uuid "{uid("label-" + key)}"))'
    )


def no_connect(x: float, y: float, key: str) -> str:
    return f'(no_connect (at {x:.2f} {y:.2f}) (uuid "{uid("nc-" + key)}"))'


def simple_property(name: str, value: str, x: float, y: float) -> str:
    return (
        f'(property "{name}" "{value}" (at {x:.2f} {y:.2f} 0) '
        '(effects (font (size 1 1)) (hide yes)))'
    )


def passive_instance(
    lib_id: str,
    ref: str,
    value: str,
    footprint: str,
    datasheet: str,
    description: str,
    x: float,
    y: float,
    project: str,
    path: str,
    fields: dict,
) -> str:
    custom = " ".join(simple_property(name, val, x, y) for name, val in fields.items())
    return f'''(symbol (lib_id "{lib_id}") (at {x:.2f} {y:.2f} 0) (unit 1)
(in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref + "-symbol")}")
(property "Reference" "{ref}" (at {x:.2f} {y - 5.08:.2f} 0) (effects (font (size 1 1))))
(property "Value" "{value}" (at {x:.2f} {y - 2.54:.2f} 0) (effects (font (size 1 1))))
(property "Footprint" "{footprint}" (at {x:.2f} {y:.2f} 0) (effects (font (size 1 1)) (hide yes)))
(property "Datasheet" "{datasheet}" (at {x:.2f} {y:.2f} 0) (effects (font (size 1 1)) (hide yes)))
(property "Description" "{description}" (at {x:.2f} {y:.2f} 0) (effects (font (size 1 1)) (hide yes)))
{custom}
(pin "1" (uuid "{uid(ref + "-pin-1")}")) (pin "2" (uuid "{uid(ref + "-pin-2")}"))
(instances (project "{project}" (path "{path}" (reference "{ref}") (unit 1)))))'''


DRIVER_CACHE_SYMBOL = '''(symbol "PandaDomestic:SGM37601YTRL20G_TR"
(pin_names (offset 1.016) (hide yes))
(exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes)
(property "Reference" "U" (at 0 16.51 0) (effects (font (size 1 1))))
(property "Value" "SGM37601YTRL20G/TR" (at 0 -16.51 0) (effects (font (size 1 1))))
(property "Footprint" "PandaDomestic:SGM37601_TQFN20_3P5x3P5_EP2P05" (at 0 0 0) (hide yes) (effects (font (size 1 1))))
(property "Datasheet" "https://www.sg-micro.com/product/SGM37601" (at 0 0 0) (hide yes) (effects (font (size 1 1))))
(property "Description" "SGMICRO 40V boost converter with I2C-controlled six-channel LED sinks" (at 0 0 0) (hide yes) (effects (font (size 1 1))))
(symbol "SGM37601YTRL20G_TR_0_1"
(rectangle (start -5.08 13.97) (end 5.08 -13.97) (stroke (width 0.254) (type default)) (fill (type background))))
(symbol "SGM37601YTRL20G_TR_1_1"
(pin passive line (at -10.16 11.43 0) (length 5.08) (name "SDA" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
(pin passive line (at -10.16 8.89 0) (length 5.08) (name "SCL" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))
(pin passive line (at -10.16 6.35 0) (length 5.08) (name "VDC" (effects (font (size 1 1)))) (number "3" (effects (font (size 1 1)))))
(pin passive line (at -10.16 3.81 0) (length 5.08) (name "COMP" (effects (font (size 1 1)))) (number "4" (effects (font (size 1 1)))))
(pin passive line (at -10.16 1.27 0) (length 5.08) (name "A0" (effects (font (size 1 1)))) (number "5" (effects (font (size 1 1)))))
(pin passive line (at -10.16 -1.27 0) (length 5.08) (name "LED6" (effects (font (size 1 1)))) (number "6" (effects (font (size 1 1)))))
(pin passive line (at -10.16 -3.81 0) (length 5.08) (name "LED5" (effects (font (size 1 1)))) (number "7" (effects (font (size 1 1)))))
(pin passive line (at -10.16 -6.35 0) (length 5.08) (name "LED4" (effects (font (size 1 1)))) (number "8" (effects (font (size 1 1)))))
(pin passive line (at -10.16 -8.89 0) (length 5.08) (name "AGND" (effects (font (size 1 1)))) (number "9" (effects (font (size 1 1)))))
(pin passive line (at -10.16 -11.43 0) (length 5.08) (name "LED3" (effects (font (size 1 1)))) (number "10" (effects (font (size 1 1)))))
(pin passive line (at 10.16 -11.43 180) (length 5.08) (name "LED2" (effects (font (size 1 1)))) (number "11" (effects (font (size 1 1)))))
(pin passive line (at 10.16 -8.89 180) (length 5.08) (name "LED1" (effects (font (size 1 1)))) (number "12" (effects (font (size 1 1)))))
(pin passive line (at 10.16 -6.35 180) (length 5.08) (name "NC" (effects (font (size 1 1)))) (number "13" (effects (font (size 1 1)))))
(pin passive line (at 10.16 -3.81 180) (length 5.08) (name "VOUT" (effects (font (size 1 1)))) (number "14" (effects (font (size 1 1)))))
(pin passive line (at 10.16 -1.27 180) (length 5.08) (name "PGND" (effects (font (size 1 1)))) (number "15" (effects (font (size 1 1)))))
(pin passive line (at 10.16 1.27 180) (length 5.08) (name "SW" (effects (font (size 1 1)))) (number "16" (effects (font (size 1 1)))))
(pin passive line (at 10.16 3.81 180) (length 5.08) (name "SW" (effects (font (size 1 1)))) (number "17" (effects (font (size 1 1)))))
(pin passive line (at 10.16 6.35 180) (length 5.08) (name "VIN" (effects (font (size 1 1)))) (number "18" (effects (font (size 1 1)))))
(pin passive line (at 10.16 8.89 180) (length 5.08) (name "EN" (effects (font (size 1 1)))) (number "19" (effects (font (size 1 1)))))
(pin passive line (at 10.16 11.43 180) (length 5.08) (name "PWM" (effects (font (size 1 1)))) (number "20" (effects (font (size 1 1)))))
(pin passive line (at 0 -19.05 90) (length 5.08) (name "AGND_EP" (effects (font (size 1 1)))) (number "21" (effects (font (size 1 1)))))))'''
DRIVER_PROJECT_SYMBOL = DRIVER_CACHE_SYMBOL.replace(
    'PandaDomestic:SGM37601YTRL20G_TR', 'SGM37601YTRL20G_TR', 1
)

DRIVER_FOOTPRINT = '''(footprint "SGM37601_TQFN20_3P5x3P5_EP2P05"
(version 20240108) (generator pcbnew) (layer "F.Cu")
(descr "SGMICRO SGM37601 TQFN-3.5x3.5-20L EP2.05, recommended land pattern")
(tags "SGM37601 TQFN20 3.5x3.5")
(property "Reference" "REF**" (at 0 -3.1 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
(property "Value" "SGM37601YTRL20G/TR" (at 0 3.1 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
(attr smd)
(fp_rect (start -1.75 -1.75) (end 1.75 1.75) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
(fp_rect (start -2.4 -2.4) (end 2.4 2.4) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
(fp_line (start -2.2 -2.2) (end -1.8 -2.2) (stroke (width 0.2) (type solid)) (layer "F.SilkS"))
(fp_line (start -2.2 -2.2) (end -2.2 -1.8) (stroke (width 0.2) (type solid)) (layer "F.SilkS"))
(fp_circle (center -1.2 -1.2) (end -1.0 -1.2) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
(pad "1" smd rect (at -1.725 -1.0) (size 0.85 0.28) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "2" smd rect (at -1.725 -0.5) (size 0.85 0.28) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "3" smd rect (at -1.725 0.0) (size 0.85 0.28) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "4" smd rect (at -1.725 0.5) (size 0.85 0.28) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "5" smd rect (at -1.725 1.0) (size 0.85 0.28) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "6" smd rect (at -1.0 1.725) (size 0.28 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "7" smd rect (at -0.5 1.725) (size 0.28 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "8" smd rect (at 0.0 1.725) (size 0.28 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "9" smd rect (at 0.5 1.725) (size 0.28 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "10" smd rect (at 1.0 1.725) (size 0.28 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "11" smd rect (at 1.725 1.0) (size 0.85 0.28) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "12" smd rect (at 1.725 0.5) (size 0.85 0.28) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "13" smd rect (at 1.725 0.0) (size 0.85 0.28) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "14" smd rect (at 1.725 -0.5) (size 0.85 0.28) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "15" smd rect (at 1.725 -1.0) (size 0.85 0.28) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "16" smd rect (at 1.0 -1.725) (size 0.28 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "17" smd rect (at 0.5 -1.725) (size 0.28 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "18" smd rect (at 0.0 -1.725) (size 0.28 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "19" smd rect (at -0.5 -1.725) (size 0.28 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "20" smd rect (at -1.0 -1.725) (size 0.28 0.85) (layers "F.Cu" "F.Paste" "F.Mask"))
(pad "21" smd rect (at 0 0) (size 2.05 2.05) (layers "F.Cu" "F.Mask"))
(pad "" smd rect (at -0.55 -0.55) (size 0.8 0.8) (layers "F.Paste"))
(pad "" smd rect (at 0.55 -0.55) (size 0.8 0.8) (layers "F.Paste"))
(pad "" smd rect (at -0.55 0.55) (size 0.8 0.8) (layers "F.Paste"))
(pad "" smd rect (at 0.55 0.55) (size 0.8 0.8) (layers "F.Paste")))'''


def driver_instance(x: float, y: float, project: str, path: str) -> str:
    fields = " ".join(
        [
            simple_property("Manufacturer", "SGMICRO", x, y),
            simple_property("MPN", "SGM37601YTRL20G/TR", x, y),
            simple_property("ECO_ID", "THIN18-C4D10B-FRONTLIGHT", x, y),
            simple_property("Procurement_Status", "RFQ_REQUIRED", x, y),
            simple_property(
                "Qualification",
                "Official TQFN20 land pattern; 14.5mA/18V firmware limits and physical front-light qualification open",
                x,
                y,
            ),
        ]
    )
    pins = " ".join(
        f'(pin "{number}" (uuid "{uid("u905-pin-" + str(number))}"))'
        for number in range(1, 22)
    )
    return f'''(symbol (lib_id "PandaDomestic:SGM37601YTRL20G_TR") (at {x:.2f} {y:.2f} 0)
(unit 1) (body_style 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes) (dnp no)
(uuid "{uid("u905-symbol")}")
(property "Reference" "U905" (at {x:.2f} {y - 16.51:.2f} 0) (effects (font (size 1 1))))
(property "Value" "SGM37601YTRL20G/TR" (at {x:.2f} {y + 16.51:.2f} 0) (effects (font (size 1 1))))
(property "Footprint" "PandaDomestic:SGM37601_TQFN20_3P5x3P5_EP2P05" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1 1))))
(property "Datasheet" "https://www.sg-micro.com/product/SGM37601" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1 1))))
(property "Description" "SGMICRO 40V boost converter with I2C-controlled six-channel LED sinks" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1 1))))
{fields} {pins}
(instances (project "{project}" (path "{path}" (reference "U905") (unit 1)))))'''


def fpc_instance(x: float, y: float, project: str, path: str) -> str:
    fields = " ".join(
        [
            simple_property("Manufacturer", "Hirose", x, y),
            simple_property("MPN", "FH34SRJ-6S-0.5SH(50)", x, y),
            simple_property("LCSC", "C224194", x, y),
            simple_property("ECO_ID", "THIN18-C4D10B-FRONTLIGHT", x, y),
            simple_property(
                "Qualification",
                "Exact C224194 land pattern; FT01C FPC orientation and insertion qualification open",
                x,
                y,
            ),
        ]
    )
    pins = " ".join(
        f'(pin "{number}" (uuid "{uid("j804-pin-" + str(number))}"))'
        for number in range(1, 7)
    )
    return f'''(symbol (lib_id "PandaDomestic:FH34SRJ-6S-0.5SH_50") (at {x:.2f} {y:.2f} 0)
(unit 1) (body_style 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes) (dnp no)
(uuid "{uid("j804-symbol")}")
(property "Reference" "J804" (at {x:.2f} {y - 8.89:.2f} 0) (effects (font (size 1 1))))
(property "Value" "FH34SRJ-6S-0.5SH(50)" (at {x:.2f} {y + 8.89:.2f} 0) (effects (font (size 1 1))))
(property "Footprint" "PandaDomestic:FH34SRJ-6S-0.5SH_50" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1 1))))
(property "Datasheet" "https://www.hirose.com/product/p/CL0580-1236-1-50" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1 1))))
(property "Description" "FT01C six-pin warm/cool front-light FPC connector" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1 1))))
{fields} {pins}
(instances (project "{project}" (path "{path}" (reference "J804") (unit 1)))))'''


if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("verification", "__pycache__", "*.pyc"))
(DST / "verification").mkdir()
PROJECT_PRETTY.mkdir(exist_ok=True)
(PROJECT_PRETTY / "SGM37601_TQFN20_3P5x3P5_EP2P05.kicad_mod").write_text(DRIVER_FOOTPRINT + "\n")

# Add project symbol definition.
project_library = PROJECT_LIB.read_text()
if '(symbol "SGM37601YTRL20G_TR"' not in project_library:
    end = project_library.rfind(")")
    project_library = project_library[:end] + " " + DRIVER_PROJECT_SYMBOL + " " + project_library[end:]
PROJECT_LIB.write_text(project_library)

# Root sheet: allocate U601 P15/P16 and retain a mainland pull-down on FL_HWEN.
root = ROOT_SCH.read_text().replace("EXP_P15_SPARE", "FL_HWEN")
label_pattern = r'\(global_label "TOUCH_INT".*?\(at 78\.74 86\.36 0\)'
match = re.search(label_pattern, root)
if not match:
    raise SystemExit("U601 TOUCH_INT label at P16 not found")
label_start = match.start()
label_end = balanced(root, label_start)
root = root[:label_start] + root[label_start:label_end].replace('"TOUCH_INT"', '"FL_PWM"', 1) + root[label_end:]
root = update_symbol_properties(
    root,
    "R601",
    {
        "Value": "100k / FL_HWEN_PD",
        "Datasheet": "https://jlcpcb.com/partdetail/151545-RC02K1003FT/C140219",
        "Description": "Fenghua mainland 100k pull-down ensuring front-light hardware enable is low at boot",
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "RC-02K1003FT",
        "LCSC": "C140219",
        "Tolerance": "1%",
        "Power_Rating": "62.5mW",
        "Voltage_Rating": "50V",
        "ECO_ID": "THIN18-C4D10B-FRONTLIGHT",
        "Qualification": "Boot-safe FL_HWEN pull-down; assembly and shutdown-leakage qualification open",
    },
)
ROOT_SCH.write_text(root)

# Display sheet: add cached symbols and the complete labeled front-light circuit.
display = DISPLAY_SCH.read_text()
source_root = (SRC / REL / f"{STEM}.kicad_sch").read_text()
fpc_cache = cached_symbol(source_root, "PandaDomestic:FH34SRJ-6S-0.5SH_50")
lib_start = display.index("(lib_symbols ")
lib_end = balanced(display, lib_start)
insertions = []
if '(symbol "PandaDomestic:FH34SRJ-6S-0.5SH_50"' not in display[lib_start:lib_end]:
    insertions.append(fpc_cache)
if '(symbol "PandaDomestic:SGM37601YTRL20G_TR"' not in display[lib_start:lib_end]:
    insertions.append(DRIVER_CACHE_SYMBOL)
if insertions:
    display = display[: lib_end - 1] + " " + " ".join(insertions) + display[lib_end - 1 :]

_, _, source_cap = block_by_ref(display, "symbol", "C804")
instance_match = re.search(r'\(instances \(project "([^"]+)" \(path "([^"]+)"', source_cap)
if not instance_match:
    raise SystemExit("display project/path context not found")
project_name, instance_path = instance_match.groups()

# Symbol coordinates in unused lower section of the A2 sheet.
positions = {
    # All centers are on the 50-mil/1.27-mm schematic grid.
    "J804": (76.20, 381.00),
    "L905": (127.00, 355.60),
    "D905": (165.10, 355.60),
    "C920": (101.60, 355.60),
    "R920": (127.00, 386.08),
    "C921": (144.78, 386.08),
    "C922": (162.56, 386.08),
    "C923": (180.34, 386.08),
    "R922": (205.74, 386.08),
    "U905": (254.00, 381.00),
}

parts = [
    fpc_instance(*positions["J804"], project_name, instance_path),
    passive_instance(
        "Device:L", "L905", "10uH / FL_BOOST", "Inductor_SMD:L_Sunlord_SWPA252012S",
        "https://jlcpcb.com/partdetail/SWPA252012S100MT/C37428",
        "Sunlord 10uH 620mA rated / 880mA saturation front-light boost inductor",
        *positions["L905"], project_name, instance_path,
        {"Manufacturer":"Sunlord","MPN":"SWPA252012S100MT","LCSC":"C37428","Tolerance":"20%","ECO_ID":"THIN18-C4D10B-FRONTLIGHT","Qualification":"First-order peak current about 0.31A; EMI/thermal/saturation qualification open"},
    ),
    passive_instance(
        "Device:D_Schottky", "D905", "B5819W SL / FL_RECT", "Diode_SMD:D_SOD-123",
        "https://item.szlcsc.com/9093.html",
        "CJ mainland 40V 1A Schottky rectifier for 18V front-light boost",
        *positions["D905"], project_name, instance_path,
        {"Manufacturer":"CJ","MPN":"B5819W SL","LCSC":"C8598","Voltage_Rating":"40V","Current_Rating":"1A","ECO_ID":"THIN18-C4D10B-FRONTLIGHT","Qualification":"18V OVP baseline; reverse leakage/thermal/EMI qualification open"},
    ),
    passive_instance(
        "Device:C", "C920", "4.7uF 16V X7R / FL_CIN", "Capacitor_SMD:C_0805_2012Metric",
        "https://jlcpcb.com/partdetail/942886-0805B475K160NT/C880382",
        "Fenghua mainland front-light boost input capacitor",
        *positions["C920"], project_name, instance_path,
        {"Manufacturer":"FH (Fenghua Advanced)","MPN":"0805B475K160NT","LCSC":"C880382","Tolerance":"10%","Voltage_Rating":"16V","Dielectric":"X7R","ECO_ID":"THIN18-C4D10B-FRONTLIGHT","Qualification":"Effective capacitance/ripple/temperature qualification open"},
    ),
    passive_instance(
        "Device:R", "R920", "10R 1% / FL_VIN_RC", "Resistor_SMD:R_0603_1608Metric",
        "https://jlcpcb.com/partdetail/147912-RS03K10R0FT/C136596",
        "Fenghua mainland 10 ohm VIN noise-filter resistor",
        *positions["R920"], project_name, instance_path,
        {"Manufacturer":"FH (Fenghua Advanced)","MPN":"RS-03K10R0FT","LCSC":"C136596","Tolerance":"1%","Power_Rating":"100mW","Voltage_Rating":"50V","ECO_ID":"THIN18-C4D10B-FRONTLIGHT","Qualification":"Feeds driver VIN only; startup/UVLO/noise qualification open"},
    ),
    passive_instance(
        "Device:C", "C921", "1uF 10V X7R / FL_VIN", "Capacitor_SMD:C_0402_1005Metric",
        "https://jlcpcb.com/partdetail/1878-0402B105K100NT/C1526",
        "Fenghua mainland SGM37601 VIN local capacitor",
        *positions["C921"], project_name, instance_path,
        {"Manufacturer":"FH (Fenghua Advanced)","MPN":"0402B105K100NT","LCSC":"C1526","Tolerance":"10%","Voltage_Rating":"10V","Dielectric":"X7R","ECO_ID":"THIN18-C4D10B-FRONTLIGHT","Qualification":"Effective capacitance/UVLO qualification open"},
    ),
    passive_instance(
        "Device:C", "C922", "1uF 10V X7R / FL_VDC", "Capacitor_SMD:C_0402_1005Metric",
        "https://jlcpcb.com/partdetail/1878-0402B105K100NT/C1526",
        "Fenghua mainland SGM37601 VDC capacitor",
        *positions["C922"], project_name, instance_path,
        {"Manufacturer":"FH (Fenghua Advanced)","MPN":"0402B105K100NT","LCSC":"C1526","Tolerance":"10%","Voltage_Rating":"10V","Dielectric":"X7R","ECO_ID":"THIN18-C4D10B-FRONTLIGHT","Qualification":"VDC stability/effective-capacitance qualification open"},
    ),
    passive_instance(
        "Device:C", "C923", "4.7uF 50V X7R / FL_COUT", "Capacitor_SMD:C_1206_3216Metric",
        "https://jlcpcb.com/partdetail/30577-1206B475K500NT/C29823",
        "Fenghua mainland 50V front-light output capacitor",
        *positions["C923"], project_name, instance_path,
        {"Manufacturer":"FH (Fenghua Advanced)","MPN":"1206B475K500NT","LCSC":"C29823","Tolerance":"10%","Voltage_Rating":"50V","Dielectric":"X7R","ECO_ID":"THIN18-C4D10B-FRONTLIGHT","Qualification":"Effective capacitance at 18V/ripple/temperature qualification open"},
    ),
    passive_instance(
        "Device:R", "R922", "100k / FL_PWM_PD", "Resistor_SMD:R_0402_1005Metric",
        "https://jlcpcb.com/partdetail/151545-RC02K1003FT/C140219",
        "Fenghua mainland front-light PWM boot pull-down",
        *positions["R922"], project_name, instance_path,
        {"Manufacturer":"FH (Fenghua Advanced)","MPN":"RC-02K1003FT","LCSC":"C140219","Tolerance":"1%","Power_Rating":"62.5mW","Voltage_Rating":"50V","ECO_ID":"THIN18-C4D10B-FRONTLIGHT","Qualification":"Boot-safe FL_PWM pull-down; physical shutdown qualification open"},
    ),
    driver_instance(*positions["U905"], project_name, instance_path),
]

labels = []
# Vertical two-pin passives: pin1 is upper, pin2 is lower.
for ref, top, bottom in [
    ("L905", "VSYS_FL_IN", "FL_SW"),
    ("C920", "VSYS_FL_IN", "GND"),
    ("R920", "VSYS_FL_IN", "FL_VIN"),
    ("C921", "FL_VIN", "GND"),
    ("C922", "FL_VDC", "GND"),
    ("C923", "FL_VOUT", "GND"),
    ("R922", "FL_PWM", "GND"),
]:
    x, y = positions[ref]
    labels.extend([
        global_label(top, x, y - 3.81, ref + "-1"),
        global_label(bottom, x, y + 3.81, ref + "-2"),
    ])
# Schottky: pin1 is cathode (left), pin2 is anode (right).
dx, dy = positions["D905"]
labels.extend([
    global_label("FL_VOUT", dx - 3.81, dy, "d905-k"),
    global_label("FL_SW", dx + 3.81, dy, "d905-a"),
])
# J804 panel pin map.
jx, jy = positions["J804"]
for pin, (net, relative_y) in enumerate(
    [("FL_W_N", 6.35), ("FL_VOUT", 3.81), (None, 1.27), (None, -1.27), ("FL_C_N", -3.81), ("FL_VOUT", -6.35)], 1
):
    px, py = jx - 5.08, jy - relative_y
    labels.append(global_label(net, px, py, f"j804-{pin}") if net else no_connect(px, py, f"j804-{pin}"))
# U905 exact pin contract.
ux, uy = positions["U905"]
left_y = {pin: 11.43 - (pin - 1) * 2.54 for pin in range(1, 11)}
right_y = {pin: 11.43 - (20 - pin) * 2.54 for pin in range(11, 21)}
user_nets = {
    1:"I2C_SDA", 2:"I2C_SCL", 3:"FL_VDC", 5:"GND", 9:"GND",
    11:"FL_C_N", 12:"FL_W_N", 14:"FL_VOUT", 15:"GND",
    16:"FL_SW", 17:"FL_SW", 18:"FL_VIN", 19:"FL_HWEN", 20:"FL_PWM", 21:"GND",
}
for pin in range(1, 11):
    px, py = ux - 10.16, uy - left_y[pin]
    labels.append(global_label(user_nets[pin], px, py, f"u905-{pin}") if pin in user_nets else no_connect(px, py, f"u905-{pin}"))
for pin in range(11, 21):
    px, py = ux + 10.16, uy - right_y[pin]
    labels.append(global_label(user_nets[pin], px, py, f"u905-{pin}") if pin in user_nets else no_connect(px, py, f"u905-{pin}"))
labels.append(global_label("GND", ux, uy + 19.05, "u905-21", 90))

display_end = display.rfind(")")
DISPLAY_SCH.write_text(display[:display_end] + " " + " ".join(parts + labels) + display[display_end:])

# PCB text-level changes for the pre-existing front-light EN pull-down.
board_text = PCB.read_text().replace("EXP_P15_SPARE", "FL_HWEN")
board_text = update_footprint_properties(
    board_text,
    "R601",
    {
        "Value": "100k / FL_HWEN_PD",
        "Datasheet": "https://jlcpcb.com/partdetail/151545-RC02K1003FT/C140219",
        "Description": "Fenghua mainland 100k pull-down ensuring front-light hardware enable is low at boot",
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "RC-02K1003FT",
        "LCSC": "C140219",
        "Tolerance": "1%",
        "Power_Rating": "62.5mW",
        "Voltage_Rating": "50V",
        "ECO_ID": "THIN18-C4D10B-FRONTLIGHT",
        "Qualification": "Boot-safe FL_HWEN pull-down; assembly and shutdown-leakage qualification open",
    },
)

# Reallocate only U601 P16 from TOUCH_INT to FL_PWM. P15 was renamed globally.
u_start, u_end, u601_board = block_by_ref(board_text, "footprint", "U601")
u_pattern = r'(\(pad "19" .*?\(net ")TOUCH_INT("\))'
u601_board, changed = re.subn(
    u_pattern, lambda match: match.group(1) + "FL_PWM" + match.group(2),
    u601_board, count=1, flags=re.S,
)
if changed != 1:
    raise SystemExit("U601 pad 19 front-light allocation failed")
board_text = board_text[:u_start] + u601_board + board_text[u_end:]


def set_block_at(block: str, x: float, y: float) -> str:
    return re.sub(
        r'(\(at\s+)[\d.-]+\s+[\d.-]+(?:\s+[\d.-]+)?',
        lambda match: match.group(1) + f"{x:.2f} {y:.2f}",
        block, count=1,
    )


def set_pad_net(block: str, number: str, net: str) -> str:
    marker = f'(pad "{number}"'
    start = block.find(marker)
    if start < 0:
        raise SystemExit(f"pad {number} missing")
    end = balanced(block, start)
    pad = block[start:end]
    pad = re.sub(r'\s*\(net "[^"]*"\)', "", pad, count=1)
    insertion = pad.rfind(")")
    pad = pad[:insertion] + f' (net "{net}")' + pad[insertion:]
    return block[:start] + pad + block[end:]


def clone_board_footprint(
    source_text: str,
    source_ref: str,
    ref: str,
    value: str,
    x: float,
    y: float,
    fields: dict,
    pad_nets: dict,
) -> str:
    _, _, block = block_by_ref(source_text, "footprint", source_ref)
    block = reuuid(block, ref)
    block = set_block_at(block, x, y)
    block = replace_property(block, "Reference", ref)
    block = replace_property(block, "Value", value)
    block = re.sub(r'\s*\(path "[^"]+"\)', "", block, count=1)
    for name, field_value in fields.items():
        if f'(property "{name}" ' in block:
            block = replace_property(block, name, field_value)
        else:
            attr = block.index("(attr smd)")
            prop = (
                f'(property "{name}" "{field_value}" (at 0 0 0) (layer "F.Fab") '
                f'(hide yes) (uuid "{uid(ref + "-" + name)}") '
                '(effects (font (size 1 1) (thickness 0.15))))'
            )
            block = block[:attr] + prop + " " + block[attr:]
    for number, net in pad_nets.items():
        block = set_pad_net(block, number, net)
    return block


def serialized_library_footprint(
    libdir: Path,
    library: str,
    name: str,
    ref: str,
    value: str,
    x: float,
    y: float,
    fields: dict,
    pad_nets: dict,
) -> str:
    """Serialize one isolated footprint and splice it into the clean PCB text."""
    temp_board = DST / "verification" / f"_{ref}.kicad_pcb"
    helper_lines = [
        "import pcbnew",
        "board = pcbnew.BOARD()",
        f"fp = pcbnew.FootprintLoad(r'{libdir}', '{name}')",
        "assert fp is not None",
        f"fp.SetFPID(pcbnew.LIB_ID('{library}', '{name}'))",
        f"fp.SetReference({ref!r})",
        f"fp.SetValue({value!r})",
        "fp.Reference().SetVisible(False)",
        "fp.Value().SetVisible(False)",
        f"fp.SetFields({fields!r})",
        "board.Add(fp)",
        f"pcbnew.SaveBoard(r'{temp_board}', board)",
    ]
    subprocess.run([KICAD_PY, "-c", "\n".join(helper_lines)], check=True)
    isolated = temp_board.read_text()
    marker = f'(property "Reference" "{ref}"'
    pos = isolated.index(marker)
    fp_start = isolated.rfind('(footprint ', 0, pos)
    block = isolated[fp_start:balanced(isolated, fp_start)]
    temp_board.unlink()
    for sidecar_suffix in (".kicad_prl", ".kicad_pro"):
        temp_board.with_suffix(sidecar_suffix).unlink(missing_ok=True)
    block = reuuid(block, ref)
    block = set_block_at(block, x, y)
    # pcbnew defaults custom fields (including long procurement/qualification
    # strings) to F.SilkS. Hidden text on that layer still participates in DRC,
    # so keep only Reference on silk and move every other hidden property to Fab.
    position = 0
    while True:
        prop_start = block.find('(property "', position)
        if prop_start < 0:
            break
        prop_end = balanced(block, prop_start)
        prop = block[prop_start:prop_end]
        match = re.match(r'\(property "([^"]+)"', prop)
        name = match.group(1) if match else ""
        if name != "Reference" and '(layer "F.SilkS")' in prop:
            prop = prop.replace('(layer "F.SilkS")', '(layer "F.Fab")', 1)
            block = block[:prop_start] + prop + block[prop_end:]
            prop_end = prop_start + len(prop)
        position = prop_end
    for number, net in pad_nets.items():
        block = set_pad_net(block, number, net)
    return block


# Exact board-side metadata; strings intentionally match schematic fields.
j804_fields = {
    "Datasheet": "https://www.hirose.com/product/p/CL0580-1236-1-50",
    "Description": "FT01C six-pin warm/cool front-light FPC connector",
    "Manufacturer": "Hirose",
    "MPN": "FH34SRJ-6S-0.5SH(50)",
    "LCSC": "C224194",
    "ECO_ID": "THIN18-C4D10B-FRONTLIGHT",
    "Qualification": "Exact C224194 land pattern; FT01C FPC orientation and insertion qualification open",
}
u905_fields = {
    "Datasheet": "https://www.sg-micro.com/product/SGM37601",
    "Description": "SGMICRO 40V boost converter with I2C-controlled six-channel LED sinks",
    "Manufacturer": "SGMICRO",
    "MPN": "SGM37601YTRL20G/TR",
    "ECO_ID": "THIN18-C4D10B-FRONTLIGHT",
    "Procurement_Status": "RFQ_REQUIRED",
    "Qualification": "Official TQFN20 land pattern; 14.5mA/18V firmware limits and physical front-light qualification open",
}
l905_fields = {
    "Datasheet": "https://jlcpcb.com/partdetail/SWPA252012S100MT/C37428",
    "Description": "Sunlord 10uH 620mA rated / 880mA saturation front-light boost inductor",
    "Manufacturer": "Sunlord", "MPN": "SWPA252012S100MT", "LCSC": "C37428",
    "Tolerance": "20%", "ECO_ID": "THIN18-C4D10B-FRONTLIGHT",
    "Qualification": "First-order peak current about 0.31A; EMI/thermal/saturation qualification open",
}
d905_fields = {
    "Datasheet": "https://item.szlcsc.com/9093.html",
    "Description": "CJ mainland 40V 1A Schottky rectifier for 18V front-light boost",
    "Manufacturer": "CJ", "MPN": "B5819W SL", "LCSC": "C8598",
    "Voltage_Rating": "40V", "Current_Rating": "1A", "ECO_ID": "THIN18-C4D10B-FRONTLIGHT",
    "Qualification": "18V OVP baseline; reverse leakage/thermal/EMI qualification open",
}
c920_fields = {
    "Datasheet": "https://jlcpcb.com/partdetail/942886-0805B475K160NT/C880382",
    "Description": "Fenghua mainland front-light boost input capacitor",
    "Manufacturer": "FH (Fenghua Advanced)", "MPN": "0805B475K160NT", "LCSC": "C880382",
    "Tolerance": "10%", "Voltage_Rating": "16V", "Dielectric": "X7R",
    "ECO_ID": "THIN18-C4D10B-FRONTLIGHT",
    "Qualification": "Effective capacitance/ripple/temperature qualification open",
}
r920_fields = {
    "Datasheet": "https://jlcpcb.com/partdetail/147912-RS03K10R0FT/C136596",
    "Description": "Fenghua mainland 10 ohm VIN noise-filter resistor",
    "Manufacturer": "FH (Fenghua Advanced)", "MPN": "RS-03K10R0FT", "LCSC": "C136596",
    "Tolerance": "1%", "Power_Rating": "100mW", "Voltage_Rating": "50V",
    "ECO_ID": "THIN18-C4D10B-FRONTLIGHT",
    "Qualification": "Feeds driver VIN only; startup/UVLO/noise qualification open",
}
c921_fields = {
    "Datasheet": "https://jlcpcb.com/partdetail/1878-0402B105K100NT/C1526",
    "Description": "Fenghua mainland SGM37601 VIN local capacitor",
    "Manufacturer": "FH (Fenghua Advanced)", "MPN": "0402B105K100NT", "LCSC": "C1526",
    "Tolerance": "10%", "Voltage_Rating": "10V", "Dielectric": "X7R",
    "ECO_ID": "THIN18-C4D10B-FRONTLIGHT",
    "Qualification": "Effective capacitance/UVLO qualification open",
}
c922_fields = dict(c921_fields)
c922_fields["Description"] = "Fenghua mainland SGM37601 VDC capacitor"
c922_fields["Qualification"] = "VDC stability/effective-capacitance qualification open"
c923_fields = {
    "Datasheet": "https://jlcpcb.com/partdetail/30577-1206B475K500NT/C29823",
    "Description": "Fenghua mainland 50V front-light output capacitor",
    "Manufacturer": "FH (Fenghua Advanced)", "MPN": "1206B475K500NT", "LCSC": "C29823",
    "Tolerance": "10%", "Voltage_Rating": "50V", "Dielectric": "X7R",
    "ECO_ID": "THIN18-C4D10B-FRONTLIGHT",
    "Qualification": "Effective capacitance at 18V/ripple/temperature qualification open",
}
r922_fields = {
    "Datasheet": "https://jlcpcb.com/partdetail/151545-RC02K1003FT/C140219",
    "Description": "Fenghua mainland front-light PWM boot pull-down",
    "Manufacturer": "FH (Fenghua Advanced)", "MPN": "RC-02K1003FT", "LCSC": "C140219",
    "Tolerance": "1%", "Power_Rating": "62.5mW", "Voltage_Rating": "50V",
    "ECO_ID": "THIN18-C4D10B-FRONTLIGHT",
    "Qualification": "Boot-safe FL_PWM pull-down; physical shutdown qualification open",
}

new_footprints = [
    clone_board_footprint(board_text, "J803", "J804", "FH34SRJ-6S-0.5SH(50)", 6.35, 45.50,
        j804_fields, {"1":"FL_W_N","2":"FL_VOUT","3":"unconnected-(J804-RST-Pad3)","4":"unconnected-(J804-INT-Pad4)","5":"FL_C_N","6":"FL_VOUT"}),
    serialized_library_footprint(PROJECT_PRETTY, "PandaDomestic", "SGM37601_TQFN20_3P5x3P5_EP2P05",
        "U905", "SGM37601YTRL20G/TR", 4.00, 52.50, u905_fields,
        {"1":"I2C_SDA","2":"I2C_SCL","3":"FL_VDC","4":"unconnected-(U905-COMP-Pad4)","5":"GND",
         "6":"unconnected-(U905-LED6-Pad6)","7":"unconnected-(U905-LED5-Pad7)","8":"unconnected-(U905-LED4-Pad8)","9":"GND",
         "10":"unconnected-(U905-LED3-Pad10)","11":"FL_C_N","12":"FL_W_N","13":"unconnected-(U905-NC-Pad13)",
         "14":"FL_VOUT","15":"GND","16":"FL_SW","17":"FL_SW","18":"FL_VIN","19":"FL_HWEN","20":"FL_PWM","21":"GND"}),
    serialized_library_footprint(KICAD_FP_ROOT / "Inductor_SMD.pretty", "Inductor_SMD", "L_Sunlord_SWPA252012S",
        "L905", "10uH / FL_BOOST", 8.75, 51.00, l905_fields, {"1":"VSYS_FL_IN","2":"FL_SW"}),
    serialized_library_footprint(KICAD_FP_ROOT / "Diode_SMD.pretty", "Diode_SMD", "D_SOD-123",
        "D905", "B5819W SL / FL_RECT", 12.75, 51.00, d905_fields, {"1":"FL_VOUT","2":"FL_SW"}),
    serialized_library_footprint(KICAD_FP_ROOT / "Capacitor_SMD.pretty", "Capacitor_SMD", "C_0805_2012Metric",
        "C920", "4.7uF 16V X7R / FL_CIN", 2.50, 57.00, c920_fields, {"1":"VSYS_FL_IN","2":"GND"}),
    serialized_library_footprint(KICAD_FP_ROOT / "Resistor_SMD.pretty", "Resistor_SMD", "R_0603_1608Metric",
        "R920", "10R 1% / FL_VIN_RC", 5.75, 57.00, r920_fields, {"1":"VSYS_FL_IN","2":"FL_VIN"}),
    serialized_library_footprint(KICAD_FP_ROOT / "Capacitor_SMD.pretty", "Capacitor_SMD", "C_0402_1005Metric",
        "C921", "1uF 10V X7R / FL_VIN", 8.50, 57.00, c921_fields, {"1":"FL_VIN","2":"GND"}),
    serialized_library_footprint(KICAD_FP_ROOT / "Capacitor_SMD.pretty", "Capacitor_SMD", "C_0402_1005Metric",
        "C922", "1uF 10V X7R / FL_VDC", 11.00, 57.00, c922_fields, {"1":"FL_VDC","2":"GND"}),
    serialized_library_footprint(KICAD_FP_ROOT / "Capacitor_SMD.pretty", "Capacitor_SMD", "C_1206_3216Metric",
        "C923", "4.7uF 50V X7R / FL_COUT", 17.60, 51.00, c923_fields, {"1":"FL_VOUT","2":"GND"}),
    serialized_library_footprint(KICAD_FP_ROOT / "Resistor_SMD.pretty", "Resistor_SMD", "R_0402_1005Metric",
        "R922", "100k / FL_PWM_PD", 13.50, 57.00, r922_fields, {"1":"FL_PWM","2":"GND"}),
]
board_end = board_text.rfind(")")
PCB.write_text(board_text[:board_end] + " " + " ".join(new_footprints) + board_text[board_end:])

# Native checks.
subprocess.run([KICAD, "sch", "erc", "--format", "json", "--severity-all", "--output", str(DST / "verification/erc.json"), str(ROOT_SCH)], check=True)
subprocess.run([KICAD, "sch", "export", "netlist", "--format", "kicadxml", "--output", str(DST / "verification/netlist.xml"), str(ROOT_SCH)], check=True)
subprocess.run([KICAD, "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--output", str(DST / "verification/drc.json"), str(PCB)], check=True)

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
    raise SystemExit("C4D10B native checks not clean")


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
new_refs = {"U905","J804","L905","D905","C920","R920","C921","C922","C923","R922"}
if set(target_refs) - set(source_refs) != new_refs or set(source_refs) - set(target_refs):
    raise SystemExit("unexpected component-set delta")
source_map = {(ref, pin): net for ref, pin, net in source_tuples}
target_map = {(ref, pin): net for ref, pin, net in target_tuples}
changed_existing = []
for key in sorted(set(source_map) | set(target_map)):
    if key[0] in new_refs:
        continue
    if source_map.get(key) != target_map.get(key):
        changed_existing.append((key, source_map.get(key), target_map.get(key)))
expected_existing = {
    ("U601","18"): ("EXP_P15_SPARE","FL_HWEN"),
    ("R601","1"): ("EXP_P15_SPARE","FL_HWEN"),
    ("U601","19"): ("TOUCH_INT","FL_PWM"),
}
if {entry[0]:(entry[1],entry[2]) for entry in changed_existing} != expected_existing:
    raise SystemExit(f"unexpected existing-net delta: {changed_existing}")

expected_new = {
    ("J804","1"):"FL_W_N", ("J804","2"):"FL_VOUT", ("J804","5"):"FL_C_N", ("J804","6"):"FL_VOUT",
    ("L905","1"):"VSYS_FL_IN", ("L905","2"):"FL_SW",
    ("D905","1"):"FL_VOUT", ("D905","2"):"FL_SW",
    ("C920","1"):"VSYS_FL_IN", ("C920","2"):"GND",
    ("R920","1"):"VSYS_FL_IN", ("R920","2"):"FL_VIN",
    ("C921","1"):"FL_VIN", ("C921","2"):"GND",
    ("C922","1"):"FL_VDC", ("C922","2"):"GND",
    ("C923","1"):"FL_VOUT", ("C923","2"):"GND",
    ("R922","1"):"FL_PWM", ("R922","2"):"GND",
    ("U905","1"):"I2C_SDA", ("U905","2"):"I2C_SCL", ("U905","3"):"FL_VDC", ("U905","5"):"GND",
    ("U905","9"):"GND", ("U905","11"):"FL_C_N", ("U905","12"):"FL_W_N", ("U905","14"):"FL_VOUT",
    ("U905","15"):"GND", ("U905","16"):"FL_SW", ("U905","17"):"FL_SW", ("U905","18"):"FL_VIN",
    ("U905","19"):"FL_HWEN", ("U905","20"):"FL_PWM", ("U905","21"):"GND",
}
wrong_new = {str(key):(target_map.get(key), expected) for key, expected in expected_new.items() if target_map.get(key) != expected}
if wrong_new:
    raise SystemExit(f"front-light pin map mismatch: {wrong_new}")
if target_values.get("U905") != "SGM37601YTRL20G/TR":
    raise SystemExit("U905 value mismatch")
if target_fields.get("J804", {}).get("LCSC") != "C224194":
    raise SystemExit("J804 procurement fields missing")

# First-order boost-current sizing at the low-input/high-output corner.
vin = 3.0
vout = 15.0
current_total = 0.029  # two strings at 14.5 mA nominal
eta = 0.80
frequency = 1_000_000.0
inductance = 10e-6
duty = 1.0 - vin / vout
input_average = vout * current_total / (vin * eta)
ripple_pp = vin * duty / (inductance * frequency)
peak_current = input_average + ripple_pp / 2.0

firmware_contract = {
    "i2c_address": "0x36 (A0=GND)",
    "safe_gpio_reset_state": {"FL_HWEN":"low","FL_PWM":"low"},
    "startup_sequence": [
        "drive FL_HWEN=0 and FL_PWM=0",
        "drive FL_HWEN=1 while FL_PWM remains 0",
        "wait for I2C ACK",
        "write REG0x00=0x01 (DC dimming)",
        "write REG0x01=0x56 (14.5mA nominal, below panel 15mA maximum)",
        "write REG0x02=0xA1 (internal compensation, 18V OVP, 2.7V UVLO)",
        "write REG0x03=0x2B (PFM enabled, 1MHz switching)",
        "drive FL_PWM=1",
    ],
    "shutdown_sequence": ["drive FL_PWM=0", "drive FL_HWEN=0"],
    "default_register_hazard": "REG0x01 resets to 20mA and REG0x02 resets to 36V; PWM must stay low until reprogrammed",
}
(DST / "frontlight-firmware-contract.json").write_text(json.dumps(firmware_contract, ensure_ascii=False, indent=2) + "\n")

report = {
    "date": "2026-09-30",
    "kind": "C4D-10B mainland dual-string front-light integration",
    "source": "c4d10a-96x68-touch",
    "added": sorted(new_refs),
    "driver": {
        "manufacturer":"SGMICRO", "mpn":"SGM37601YTRL20G/TR", "package":"TQFN-3.5x3.5-20L",
        "catalog_status":"RFQ_REQUIRED", "i2c_address":"0x36", "strings_used":["LED1 warm","LED2 cool"],
    },
    "panel_current_limit": {"panel_max_ma_per_string":15.0, "programmed_nominal_ma":14.5, "register_0x01":"0x56"},
    "boost_configuration": {"ovp_v":18,"register_0x02":"0xA1","frequency_hz":1000000,"register_0x03":"0x2B"},
    "first_order_sizing": {
        "vin_v":vin,"vout_v":vout,"total_led_current_a":current_total,"efficiency_assumption":eta,
        "inductor_h":inductance,"estimated_input_average_a":round(input_average,4),
        "estimated_ripple_pp_a":round(ripple_pp,4),"estimated_peak_a":round(peak_current,4),
        "selected_inductor_isat_a":0.88,"selected_inductor_rated_a":0.62,
        "isat_margin_ratio":round(0.88/peak_current,2),"rated_margin_ratio":round(0.62/peak_current,2),
    },
    "u601_allocation": {"P15/pad18":"FL_HWEN","P16/pad19":"FL_PWM","P17/pad20":"TOUCH_RST"},
    "touch_policy":"TOUCH_INT remains on J803 with pull-up and is polled over I2C; it is no longer consumed by U601",
    "native_checks": counts,
    "refs": len(target_refs),
    "pin_net_tuples": len(target_tuples),
    "existing_net_delta": changed_existing,
    "firmware_contract":"frontlight-firmware-contract.json",
    "physical_qualification": [
        "front-light FPC contact-side/orientation and insertion",
        "14.5mA current accuracy on warm/cool strings",
        "18V OVP and open-string behavior",
        "COUT effective capacitance at operating bias",
        "Schottky reverse leakage and temperature",
        "inductor saturation/temperature and acoustic/EMI behavior",
        "shutdown leakage, fade behavior and enclosure thermal rise",
    ],
    "manufacturing_release": False,
    "physical_qualification_complete": False,
    "pcb_sha256": hashlib.sha256(PCB.read_bytes()).hexdigest(),
}
(DST / "c4d10b-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
(DST / "README.md").write_text(
    "# Thin18 Compact C4D-10B — mainland dual-string front light\n\n"
    "SGM37601YTRL20G/TR drives the FT01C warm/cool strings through exact J804 FPC mapping. "
    "The design uses boot-low EN/PWM, 14.5mA nominal current, 18V OVP and 1MHz switching.\n\n"
    f"Fresh checks: ERC={counts['erc']}, DRC={counts['drc']}, parity={counts['parity']}, "
    f"open={counts['open']} (expected because final routing has not started).\n\n"
    "Physical current, thermal, EMI, acoustic and mechanical qualification remain open. Not a manufacturing release.\n"
)
print(json.dumps(report, ensure_ascii=False, indent=2))
