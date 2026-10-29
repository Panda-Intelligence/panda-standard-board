#!/usr/bin/env python3
"""Verify 100% Chinese Mainland (PRC) component provenance across Pico47 boards.

Audits native KiCad PCB footprints (`.kicad_pcb`), schematic symbol instances
(`.kicad_sch`), and local footprint libraries (`Panda47.pretty/*.kicad_mod`) for
`Single`, `Core`, and `Display` candidates to ensure:
1. 100% of populated BOM components have a verified Chinese Mainland manufacturer
   identity (`Manufacturer`) and a non-empty part number (`MPN`).
2. 100% of DNP passives specify a verified Chinese Mainland manufacturer.
3. 100% of non-BOM bare PCB test points / debug landings are explicitly marked
   `Manufacturer = "PCB fabricated terminal"` and `MPN = "NOT_A_PURCHASED_PART"`.
4. Zero foreign/non-mainland component manufacturers appear anywhere in the BOM.
5. 100% metadata parity (`Manufacturer`, `MPN`, `LCSC`) holds between `.kicad_pcb`
   and `.kicad_sch` for every placed component.

Note: Per repository policy (`AGENTS.md`), mainland manufacturer identity does
not by itself certify internal die provenance, supplier stock receipt, or physical
EVT qualification. Unverified LCSC catalog codes are never fabricated.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


# Canonical registry of verified Chinese Mainland (PRC) electronic manufacturers
MAINLAND_MANUFACTURERS: dict[str, dict[str, str]] = {
    "Espressif": {
        "chinese_name": "乐鑫信息科技(上海)股份有限公司",
        "hq_location": "Shanghai, China (中国上海)",
        "category": "Wireless SoC / MCU",
    },
    "GigaDevice": {
        "chinese_name": "兆易创新科技集团股份有限公司",
        "hq_location": "Beijing, China (中国北京)",
        "category": "SPI NOR Flash Memory",
    },
    "SGMICRO": {
        "chinese_name": "圣邦微电子(北京)股份有限公司",
        "hq_location": "Beijing, China (中国北京)",
        "category": "Analog & Power Management ICs (Charger, Buck-Boost, Load Switch, Mux, LED Boost, Reset, TVS)",
    },
    "Silergy": {
        "chinese_name": "矽力杰半导体技术(杭州)有限公司",
        "hq_location": "Hangzhou, Zhejiang, China (中国浙江杭州)",
        "category": "E-Paper Display PMIC",
    },
    "Cellwise": {
        "chinese_name": "广东赛微微电子股份有限公司",
        "hq_location": "Dongguan, Guangdong, China (中国广东东莞)",
        "category": "Battery Fuel Gauge IC",
    },
    "QST (Shanghai QST)": {
        "chinese_name": "上海矽睿科技股份有限公司",
        "hq_location": "Shanghai, China (中国上海)",
        "category": "6-Axis MEMS IMU Sensor",
    },
    "Shenzhen Nsiway Tech": {
        "chinese_name": "深圳市纳芯威科技有限公司",
        "hq_location": "Shenzhen, Guangdong, China (中国广东深圳)",
        "category": "Digital Input Class-D Audio Amplifier IC",
    },
    "WAVE": {
        "chinese_name": "深圳市兴威帆电子技术有限公司",
        "hq_location": "Shenzhen, Guangdong, China (中国广东深圳)",
        "category": "High-Precision Real-Time Clock (RTC) IC",
    },
    "XINLUDA": {
        "chinese_name": "厦门芯路达电子科技有限公司",
        "hq_location": "Xiamen, Fujian / Shenzhen, China (中国福建厦门/深圳)",
        "category": "I2C/SMBus 16-Bit GPIO Expander IC",
    },
    "XySemi (Suzhou Saixin)": {
        "chinese_name": "苏州赛芯电子科技股份有限公司",
        "hq_location": "Suzhou, Jiangsu, China (中国江苏苏州)",
        "category": "Lithium-Ion Battery Protection IC",
    },
    "FH (Fenghua Advanced)": {
        "chinese_name": "广东风华高新科技股份有限公司",
        "hq_location": "Zhaoqing, Guangdong, China (中国广东肇庆)",
        "category": "MLCC Capacitors, Thick/Thin-Film Chip Resistors, NTC Thermistors",
    },
    "FH (Guangdong Fenghua Advanced Tech)": {
        "chinese_name": "广东风华高新科技股份有限公司",
        "hq_location": "Zhaoqing, Guangdong, China (中国广东肇庆)",
        "category": "Thick-Film Chip Resistors",
    },
    "CCTC": {
        "chinese_name": "潮州三环(集团)股份有限公司",
        "hq_location": "Chaozhou, Guangdong, China (中国广东潮州)",
        "category": "MLCC Capacitors",
    },
    "HRE": {
        "chinese_name": "芯声微电子科技有限公司",
        "hq_location": "Huaian, Jiangsu, China (中国江苏淮安)",
        "category": "MLCC Capacitors",
    },
    "FOJAN": {
        "chinese_name": "富捷电子科技有限公司",
        "hq_location": "Ma'anshan, Anhui / Shenzhen, China (中国安徽马鞍山/深圳)",
        "category": "Current-Sense & Precision Chip Resistors",
    },
    "Sunlord": {
        "chinese_name": "深圳顺络电子股份有限公司",
        "hq_location": "Shenzhen, Guangdong, China (中国广东深圳)",
        "category": "Power Inductors & High-Frequency RF Inductors",
    },
    "CJ": {
        "chinese_name": "江苏长电/长晶科技股份有限公司",
        "hq_location": "Nanjing / Wuxi, Jiangsu, China (中国江苏南京/无锡)",
        "category": "Discrete Schottky Diodes",
    },
    "JSCJ": {
        "chinese_name": "江苏长晶科技股份有限公司",
        "hq_location": "Nanjing, Jiangsu, China (中国江苏南京)",
        "category": "Discrete Schottky & Switching Diodes",
    },
    "JSMSEMI": {
        "chinese_name": "深圳市杰盛微半导体有限公司",
        "hq_location": "Shenzhen, Guangdong, China (中国广东深圳)",
        "category": "Discrete MOSFETs",
    },
    "LRC": {
        "chinese_name": "乐山无线电股份有限公司",
        "hq_location": "Leshan, Sichuan, China (中国四川乐山)",
        "category": "TVS / ESD Protection Diodes",
    },
    "Shandong Jingdao Microelectronics": {
        "chinese_name": "山东晶导微电子股份有限公司",
        "hq_location": "Qufu, Shandong, China (中国山东曲阜)",
        "category": "Schottky Barrier Diodes",
    },
    "YXC (Yangxing)": {
        "chinese_name": "深圳扬兴科技有限公司",
        "hq_location": "Shenzhen, Guangdong, China (中国广东深圳)",
        "category": "Quartz Crystal Resonators",
    },
    "XKB Connection": {
        "chinese_name": "广东星坤科技股份有限公司",
        "hq_location": "Dongguan, Guangdong, China (中国广东东莞)",
        "category": "FPC/FFC Connectors & Tactile Switches",
    },
    "XUNPU": {
        "chinese_name": "深圳市讯普电子有限公司",
        "hq_location": "Shenzhen, Guangdong, China (中国广东深圳)",
        "category": "microSD Push-Push Card Connectors",
    },
    "MUP": {
        "chinese_name": "深圳市满坤/慕普电子有限公司",
        "hq_location": "Shenzhen, Guangdong, China (中国广东深圳)",
        "category": "Mid-Mount USB Type-C Connectors",
    },
    "Yichang Power Glory Technology Co., Ltd.": {
        "chinese_name": "宜昌力佳科技有限公司",
        "hq_location": "Yichang, Hubei, China (中国湖北宜昌)",
        "category": "Primary Lithium Coin Cells (CR1216)",
    },
}

NON_PURCHASED_PCB_FEATURE_MANUFACTURER = "PCB fabricated terminal"
NON_PURCHASED_PCB_FEATURE_MPN = "NOT_A_PURCHASED_PART"

FORBIDDEN_FOREIGN_MANUFACTURERS = {
    "texas instruments",
    "ti",
    "stmicroelectronics",
    "st",
    "murata",
    "tdk",
    "yageo",
    "samsung",
    "walsin",
    "taiyo yuden",
    "kyocera",
    "avx",
    "vishay",
    "bourns",
    "bosch",
    "nxp",
    "microchip",
    "winbond",
    "analog devices",
    "adi",
    "maxim",
    "infineon",
    "rohm",
    "toshiba",
    "renesas",
    "panasonic",
    "omron",
    "hirose",
    "jst",
    "molex",
    "te connectivity",
    "amphenol",
    "micro crystal",
    "abracon",
    "ndk",
    "epson",
}

# Exact Chinese Mainland metadata completion ECO for C501, DNP passives,
# Display passives, and bare PCB test terminals.
MAINLAND_METADATA_ECO: dict[str, dict[str, str]] = {
    # Downsized 0603 22uF ESP32 bypass capacitor (matches C401/C402/C403 Fenghua 0603 22uF)
    "C501": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "0603X226M100NT",
        "LCSC": "C60077",
        "Description": "FH 22uF 10V X5R +/-20% 0603 local bypass for ESP32-S3 3V3_AON; DC-bias capacitance remains physical qualification.",
    },
    # DNP passives (explicitly bound to Fenghua Advanced domestic parts)
    "C514": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "0402CG0R8C500NT",
        "LCSC": "C40459",
    },
    "C515": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "0402CG0R8C500NT",
        "LCSC": "C40459",
    },
    "R301": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "RC-02K1004FT",
        "LCSC": "",
    },
    "R302": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "RC-02K1004FT",
        "LCSC": "",
    },
    "R305": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "RC-02K1003FT",
        "LCSC": "C140219",
    },
    # Display passives (Fenghua Advanced domestic MPNs; C801/C803/C816 match C206 10u/10V/0805)
    "C801": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "0805B106K100NT",
        "LCSC": "C90544",
    },
    "C803": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "0805B106K100NT",
        "LCSC": "C90544",
    },
    "C816": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "0805B106K100NT",
        "LCSC": "C90544",
    },
    "C807": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "0805B105K500NT",
        "LCSC": "",
    },
    "C809": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "0805B105K500NT",
        "LCSC": "",
    },
    "C810": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "0805B105K500NT",
        "LCSC": "",
    },
    "C812": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "0805B105K500NT",
        "LCSC": "",
    },
    "C808": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "0805B473K500NT",
        "LCSC": "",
    },
    "C811": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "0805B473K500NT",
        "LCSC": "",
    },
    "R801": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "THC02H4423BT",
        "LCSC": "",
    },
    "R802": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "THC02H2102BT",
        "LCSC": "",
    },
    "R803": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "THC02H7503BT",
        "LCSC": "",
    },
    "R804": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "THC02H5902BT",
        "LCSC": "",
    },
    "R805": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "RC-02K7501FT",
        "LCSC": "",
    },
    "R806": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "RC-02K3602FT",
        "LCSC": "",
    },
    "TH801": {
        "Manufacturer": "FH (Fenghua Advanced)",
        "MPN": "CMFA103F3950HANT",
        "LCSC": "",
    },
    # Non-BOM bare PCB debug landing and test pads (matching TP712 / TP801..TP806)
    **{
        ref: {
            "Manufacturer": NON_PURCHASED_PCB_FEATURE_MANUFACTURER,
            "MPN": NON_PURCHASED_PCB_FEATURE_MPN,
            "LCSC": "",
        }
        for ref in [
            "J503",
            "TP1", "TP2", "TP3", "TP4", "TP5", "TP6", "TP7", "TP8",
            "TP11", "TP12", "TP13", "TP14", "TP16", "TP18", "TP19",
            "TPG1", "TPG2", "TPG3", "TPG4", "TPG5", "TPG6",
        ]
    },
}


def _balanced_end(text: str, start: int) -> int:
    depth = 0
    in_quotes = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_quotes = not in_quotes
            continue
        if in_quotes:
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return idx + 1
    raise ValueError(f"Unbalanced S-expression starting at {start}")


def _extract_properties(block: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for m in re.finditer(r'\(property\s+"((?:\\.|[^"\\])*)"\s+"((?:\\.|[^"\\])*)"', block):
        key = json.loads(f'"{m.group(1)}"')
        val = json.loads(f'"{m.group(2)}"')
        props[key] = val
    return props


def _upsert_property_in_block(block: str, key: str, value: str, is_pcb: bool) -> str:
    qkey = json.dumps(key, ensure_ascii=False)
    qval = json.dumps(value, ensure_ascii=False)
    pattern = re.compile(rf'(\(property\s+{re.escape(qkey)}\s+)"(?:\\.|[^"\\])*"')
    m_existing = pattern.search(block)
    if m_existing:
        prop_start = m_existing.start()
        prop_end = _balanced_end(block, prop_start)
        prop_sub = block[prop_start:prop_end]
        prop_sub = pattern.sub(rf"\1{qval}", prop_sub, count=1)
        if is_pcb and key not in ("Reference", "Value") and "(hide yes)" not in prop_sub:
            prop_sub = re.sub(r'(\(layer\s+"[^"]+"\))', r'\1\n\t\t\t(hide yes)', prop_sub, count=1)
        return block[:prop_start] + prop_sub + block[prop_end:]

    # Insert new hidden property right after the last existing (property ...) in the block
    last_prop_end = None
    for m in re.finditer(r'\(property\s+"(?:\\.|[^"\\])*"\s+"(?:\\.|[^"\\])*"', block):
        last_prop_end = _balanced_end(block, m.start())
    if last_prop_end is None:
        raise ValueError("Cannot find any existing property to anchor new property")

    if is_pcb:
        new_prop = (
            f'\n\t\t(property {qkey} {qval}\n'
            f'\t\t\t(at 0 0 0)\n'
            f'\t\t\t(layer "F.Fab")\n'
            f'\t\t\t(hide yes)\n'
            f'\t\t\t(effects\n'
            f'\t\t\t\t(font\n'
            f'\t\t\t\t\t(size 1 1)\n'
            f'\t\t\t\t\t(thickness 0.15)\n'
            f'\t\t\t\t)\n'
            f'\t\t\t)\n'
            f'\t\t)'
        )
    else:
        at_match = re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)', block)
        ax, ay = (at_match.group(1), at_match.group(2)) if at_match else ("0", "0")
        new_prop = (
            f'(property {qkey} {qval} (at {ax} {ay} 0) (hide yes)'
            f'(effects (font (size 0.85 0.85))))'
        )
    return block[:last_prop_end] + new_prop + block[last_prop_end:]


def patch_pcb_or_mod_text(text: str, eco_map: dict[str, dict[str, str]]) -> tuple[str, list[str]]:
    """Apply metadata updates to footprints in `.kicad_pcb` or `.kicad_mod` text."""
    updated_refs: list[str] = []
    out: list[str] = []
    pos = 0
    for m in re.finditer(r'\(footprint\s+"', text):
        if m.start() < pos:
            continue
        start = m.start()
        end = _balanced_end(text, start)
        block = text[start:end]
        props = _extract_properties(block)
        ref = props.get("Reference", "")
        if ref in eco_map:
            for k, v in eco_map[ref].items():
                block = _upsert_property_in_block(block, k, v, is_pcb=True)
            updated_refs.append(ref)
        out.append(text[pos:start])
        out.append(block)
        pos = end
    out.append(text[pos:])
    return "".join(out), updated_refs


def patch_schematic_text(text: str, eco_map: dict[str, dict[str, str]]) -> tuple[str, list[str]]:
    """Apply metadata updates to placed symbol instances in `.kicad_sch` text."""
    lib_start = text.index("(lib_symbols")
    lib_end = _balanced_end(text, lib_start)
    updated_refs: list[str] = []
    out: list[str] = [text[:lib_end]]
    pos = lib_end
    for m in re.finditer(r'\(symbol\s*\(lib_id\s+"', text[lib_end:]):
        start = lib_end + m.start()
        if start < pos:
            continue
        end = _balanced_end(text, start)
        block = text[start:end]
        props = _extract_properties(block)
        ref = props.get("Reference", "")
        if ref in eco_map:
            for k, v in eco_map[ref].items():
                block = _upsert_property_in_block(block, k, v, is_pcb=False)
            updated_refs.append(ref)
        out.append(text[pos:start])
        out.append(block)
        pos = end
    out.append(text[pos:])
    return "".join(out), updated_refs


def apply_mainland_metadata_eco(candidate_dir: Path, boards: tuple[str, ...] = ("Single", "Core", "Display")) -> dict[str, Any]:
    """Apply the mainland component metadata completion ECO to `.kicad_pcb`, `.kicad_sch`, and `Panda47.pretty`."""
    candidate_dir = Path(candidate_dir).resolve()
    patched_boards: dict[str, Any] = {}
    for board in boards:
        pcb_path = candidate_dir / f"{board}.kicad_pcb"
        sch_path = candidate_dir / f"{board}.kicad_sch"
        if not pcb_path.exists() or not sch_path.exists():
            continue
        pcb_text, pcb_refs = patch_pcb_or_mod_text(pcb_path.read_text(), MAINLAND_METADATA_ECO)
        sch_text, sch_refs = patch_schematic_text(sch_path.read_text(), MAINLAND_METADATA_ECO)
        pcb_path.write_text(pcb_text)
        sch_path.write_text(sch_text)
        patched_boards[board] = {
            "pcb_updated_refs": sorted(pcb_refs),
            "sch_updated_refs": sorted(sch_refs),
        }

    pretty_dir = candidate_dir / "Panda47.pretty"
    patched_mods: list[str] = []
    if pretty_dir.is_dir():
        for mod_path in sorted(pretty_dir.glob("*.kicad_mod")):
            mod_text, mod_refs = patch_pcb_or_mod_text(mod_path.read_text(), MAINLAND_METADATA_ECO)
            if mod_refs:
                mod_path.write_text(mod_text)
                patched_mods.append(mod_path.name)

    return {
        "candidate_dir": str(candidate_dir),
        "patched_boards": patched_boards,
        "patched_footprint_mods": patched_mods,
    }


def parse_pcb_footprints(pcb_path: Path) -> list[dict[str, Any]]:
    """Parse all footprint blocks and metadata from a `.kicad_pcb` file without requiring pcbnew."""
    text = Path(pcb_path).read_text()
    items: list[dict[str, Any]] = []
    pos = 0
    for m in re.finditer(r'\(footprint\s+"([^"]+)"', text):
        if m.start() < pos:
            continue
        start = m.start()
        end = _balanced_end(text, start)
        block = text[start:end]
        pos = end
        fpid = m.group(1)
        props = _extract_properties(block)
        ref = props.get("Reference", "")
        val = props.get("Value", "")
        attr_match = re.search(r"\(attr\s+([^)]+)\)", block)
        attr_tokens = set(attr_match.group(1).split()) if attr_match else set()
        dnp = "dnp" in attr_tokens or "(dnp yes)" in block
        exclude_from_bom = "exclude_from_bom" in attr_tokens
        items.append({
            "ref": ref,
            "value": val,
            "fpid": fpid,
            "manufacturer": props.get("Manufacturer", "").strip(),
            "mpn": props.get("MPN", "").strip(),
            "lcsc": props.get("LCSC", "").strip(),
            "description": props.get("Description", "").strip(),
            "dnp": dnp,
            "in_bom": not exclude_from_bom,
        })
    return sorted(items, key=lambda x: x["ref"])


def parse_sch_symbols(sch_path: Path) -> dict[str, dict[str, Any]]:
    """Parse all placed symbol instances from a `.kicad_sch` file."""
    text = Path(sch_path).read_text()
    lib_start = text.index("(lib_symbols")
    lib_end = _balanced_end(text, lib_start)
    symbols: dict[str, dict[str, Any]] = {}
    pos = lib_end
    for m in re.finditer(r'\(symbol\s*\(lib_id\s+"([^"]+)"\)', text[lib_end:]):
        start = lib_end + m.start()
        if start < pos:
            continue
        end = _balanced_end(text, start)
        block = text[start:end]
        pos = end
        props = _extract_properties(block)
        ref = props.get("Reference", "")
        if not ref or ref.startswith("#"):
            continue
        symbols[ref] = {
            "ref": ref,
            "value": props.get("Value", ""),
            "manufacturer": props.get("Manufacturer", "").strip(),
            "mpn": props.get("MPN", "").strip(),
            "lcsc": props.get("LCSC", "").strip(),
            "dnp": "(dnp yes)" in block,
            "in_bom": "(in_bom yes)" in block,
        }
    return symbols


def verify_board_mainland_compliance(candidate_dir: Path, board: str) -> dict[str, Any]:
    """Audit a single board (`Single`, `Core`, or `Display`) for 100% Chinese Mainland provenance."""
    candidate_dir = Path(candidate_dir).resolve()
    pcb_path = candidate_dir / f"{board}.kicad_pcb"
    sch_path = candidate_dir / f"{board}.kicad_sch"
    if not pcb_path.is_file():
        raise FileNotFoundError(f"Missing PCB file: {pcb_path}")
    if not sch_path.is_file():
        raise FileNotFoundError(f"Missing schematic file: {sch_path}")

    footprints = parse_pcb_footprints(pcb_path)
    sch_symbols = parse_sch_symbols(sch_path)

    populated_bom: list[dict[str, Any]] = []
    dnp_parts: list[dict[str, Any]] = []
    non_bom_features: list[dict[str, Any]] = []

    missing_manufacturer_refs: list[str] = []
    missing_mpn_refs: list[str] = []
    unrecognized_manufacturer_refs: list[dict[str, str]] = []
    foreign_manufacturer_refs: list[dict[str, str]] = []
    sch_parity_mismatches: list[dict[str, Any]] = []
    manufacturer_breakdown: dict[str, dict[str, Any]] = {}

    for fp in footprints:
        ref = fp["ref"]
        mfg = fp["manufacturer"]
        mpn = fp["mpn"]
        lcsc = fp["lcsc"]

        if not mfg:
            missing_manufacturer_refs.append(ref)
        if not mpn:
            missing_mpn_refs.append(ref)

        if mfg.lower() in FORBIDDEN_FOREIGN_MANUFACTURERS:
            foreign_manufacturer_refs.append({"ref": ref, "manufacturer": mfg, "mpn": mpn})

        # Check schematic parity for Manufacturer, MPN, LCSC
        sch = sch_symbols.get(ref)
        if sch is None:
            sch_parity_mismatches.append({"ref": ref, "error": "missing_in_schematic"})
        else:
            for field in ("manufacturer", "mpn", "lcsc"):
                if fp[field] != sch[field]:
                    sch_parity_mismatches.append({
                        "ref": ref,
                        "field": field,
                        "pcb": fp[field],
                        "sch": sch[field],
                    })

        if not fp["in_bom"]:
            non_bom_features.append(fp)
            if mfg != NON_PURCHASED_PCB_FEATURE_MANUFACTURER:
                unrecognized_manufacturer_refs.append({"ref": ref, "manufacturer": mfg, "role": "non_bom_feature"})
        elif fp["dnp"]:
            dnp_parts.append(fp)
            if mfg not in MAINLAND_MANUFACTURERS:
                unrecognized_manufacturer_refs.append({"ref": ref, "manufacturer": mfg, "role": "dnp"})
        else:
            populated_bom.append(fp)
            if mfg not in MAINLAND_MANUFACTURERS:
                unrecognized_manufacturer_refs.append({"ref": ref, "manufacturer": mfg, "role": "populated_bom"})
            else:
                info = MAINLAND_MANUFACTURERS[mfg]
                entry = manufacturer_breakdown.setdefault(mfg, {
                    "manufacturer": mfg,
                    "chinese_name": info["chinese_name"],
                    "hq_location": info["hq_location"],
                    "category": info["category"],
                    "populated_count": 0,
                    "refs": [],
                    "mpns": set(),
                })
                entry["populated_count"] += 1
                entry["refs"].append(ref)
                if mpn:
                    entry["mpns"].add(mpn)

    # Convert sets to sorted lists for JSON serialization
    breakdown_list = []
    for mfg_key in sorted(manufacturer_breakdown):
        item = manufacturer_breakdown[mfg_key]
        item["mpns"] = sorted(item["mpns"])
        breakdown_list.append(item)

    all_passed = (
        len(footprints) > 0
        and len(missing_manufacturer_refs) == 0
        and len(missing_mpn_refs) == 0
        and len(unrecognized_manufacturer_refs) == 0
        and len(foreign_manufacturer_refs) == 0
        and len(sch_parity_mismatches) == 0
    )

    return {
        "board": board,
        "total_footprints": len(footprints),
        "populated_bom_count": len(populated_bom),
        "dnp_count": len(dnp_parts),
        "non_bom_pcb_feature_count": len(non_bom_features),
        "distinct_mainland_manufacturers": len(breakdown_list),
        "mainland_populated_rate_pct": round(
            100.0 * (len(populated_bom) - sum(1 for x in unrecognized_manufacturer_refs if x["role"] == "populated_bom")) / max(len(populated_bom), 1),
            2,
        ),
        "missing_manufacturer_refs": missing_manufacturer_refs,
        "missing_mpn_refs": missing_mpn_refs,
        "unrecognized_manufacturer_refs": unrecognized_manufacturer_refs,
        "foreign_manufacturer_refs": foreign_manufacturer_refs,
        "sch_parity_mismatches": sch_parity_mismatches,
        "manufacturer_breakdown": breakdown_list,
        "all_passed": all_passed,
    }


def verify_all_boards(candidate_dir: Path, boards: tuple[str, ...] = ("Single", "Core", "Display")) -> dict[str, Any]:
    candidate_dir = Path(candidate_dir).resolve()
    board_reports: dict[str, Any] = {}
    for board in boards:
        if (candidate_dir / f"{board}.kicad_pcb").is_file():
            board_reports[board] = verify_board_mainland_compliance(candidate_dir, board)

    all_passed = bool(board_reports) and all(r["all_passed"] for r in board_reports.values())
    return {
        "schema": "panda-pico47-mainland-bom-compliance-v1",
        "candidate_dir": str(candidate_dir),
        "boards": board_reports,
        "approved_mainland_manufacturers_count": len(MAINLAND_MANUFACTURERS),
        "mainland_identity_does_not_certify_internal_die_provenance_or_evt": True,
        "manufacturing_release": False,
        "all_passed": all_passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True, help="Path to engineering-candidate directory")
    parser.add_argument("--apply-eco", action="store_true", help="Apply mainland metadata completion ECO before auditing")
    parser.add_argument("--output-json", type=Path, help="Optional JSON report output path")
    args = parser.parse_args()

    if args.apply_eco:
        eco_res = apply_mainland_metadata_eco(args.candidate)
        print("Applied mainland metadata ECO:", json.dumps(eco_res, indent=2, ensure_ascii=False))

    report = verify_all_boards(args.candidate)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(json.dumps({
        "all_passed": report["all_passed"],
        "boards": {
            b: {
                "total_footprints": r["total_footprints"],
                "populated_bom_count": r["populated_bom_count"],
                "dnp_count": r["dnp_count"],
                "non_bom_pcb_feature_count": r["non_bom_pcb_feature_count"],
                "distinct_mainland_manufacturers": r["distinct_mainland_manufacturers"],
                "mainland_populated_rate_pct": r["mainland_populated_rate_pct"],
                "all_passed": r["all_passed"],
            }
            for b, r in report["boards"].items()
        },
    }, indent=2, ensure_ascii=False))

    if not report["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
