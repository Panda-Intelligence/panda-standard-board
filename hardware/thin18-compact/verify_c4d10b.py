#!/usr/bin/env python3
"""Fail-closed verification for the C4D-10B touch/front-light candidate."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CAND = ROOT / "c4d10b-96x68-frontlight"
REPORT = CAND / "c4d10b-report.json"
FIRMWARE = CAND / "frontlight-firmware-contract.json"
PCB = CAND / "eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16/PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_pcb"
NETLIST = CAND / "verification/netlist.xml"
DRC = CAND / "verification/drc.json"
ERC = CAND / "verification/erc.json"
OUT = ROOT / "c4d10b-verification.json"


def require(value, message):
    if not value:
        raise ValueError(message)


def pin_map(root, ref):
    result = {}
    for net in root.findall("nets/net"):
        for node in net.findall("node"):
            if node.get("ref") == ref:
                result[node.get("pin")] = net.get("name", "")
    return result


def main(release=False):
    report = json.loads(REPORT.read_text())
    firmware = json.loads(FIRMWARE.read_text())
    drc = json.loads(DRC.read_text())
    erc = json.loads(ERC.read_text())
    root = ET.parse(NETLIST).getroot()

    counts = {
        "drc": len(drc.get("violations", [])),
        "parity": len(drc.get("schematic_parity", [])),
        "open": len(drc.get("unconnected_items", [])),
        "erc": sum(len(sheet.get("violations", [])) for sheet in erc.get("sheets", [])),
    }
    require(counts == {"drc": 0, "parity": 0, "open": 436, "erc": 0}, f"native checks changed: {counts}")
    require(report["native_checks"] == counts, "report/native-count mismatch")
    require(report["refs"] == 197 and report["pin_net_tuples"] == 622, "netlist cardinality changed")
    require(report["manufacturing_release"] is False, "premature manufacturing release")
    require(report["physical_qualification_complete"] is False, "premature physical qualification")
    require(report["panel_current_limit"]["programmed_nominal_ma"] == 14.5, "panel current limit changed")
    require(report["panel_current_limit"]["panel_max_ma_per_string"] == 15.0, "panel maximum changed")
    require(report["boost_configuration"] == {
        "ovp_v": 18,
        "register_0x02": "0xA1",
        "frequency_hz": 1000000,
        "register_0x03": "0x2B",
    }, "boost register contract changed")
    require(report["first_order_sizing"]["isat_margin_ratio"] >= 2.0, "inductor saturation margin below 2x")
    require(report["first_order_sizing"]["rated_margin_ratio"] >= 1.5, "inductor rated-current margin below 1.5x")
    require(hashlib.sha256(PCB.read_bytes()).hexdigest() == report["pcb_sha256"], "PCB changed after verification")

    expected_u905 = {
        "1": "I2C_SDA", "2": "I2C_SCL", "3": "FL_VDC", "5": "GND", "9": "GND",
        "11": "FL_C_N", "12": "FL_W_N", "14": "FL_VOUT", "15": "GND",
        "16": "FL_SW", "17": "FL_SW", "18": "FL_VIN", "19": "FL_HWEN",
        "20": "FL_PWM", "21": "GND",
    }
    expected_j804 = {"1": "FL_W_N", "2": "FL_VOUT", "5": "FL_C_N", "6": "FL_VOUT"}
    expected_u601 = {"18": "FL_HWEN", "19": "FL_PWM", "20": "TOUCH_RST"}
    actual_u905 = pin_map(root, "U905")
    actual_j804 = pin_map(root, "J804")
    actual_u601 = pin_map(root, "U601")
    for pin, net in expected_u905.items():
        require(actual_u905.get(pin) == net, f"U905 pin {pin}: {actual_u905.get(pin)} != {net}")
    for pin, net in expected_j804.items():
        require(actual_j804.get(pin) == net, f"J804 pin {pin}: {actual_j804.get(pin)} != {net}")
    for pin, net in expected_u601.items():
        require(actual_u601.get(pin) == net, f"U601 pin {pin}: {actual_u601.get(pin)} != {net}")

    sequence = firmware["startup_sequence"]
    require(sequence[0] == "drive FL_HWEN=0 and FL_PWM=0", "unsafe startup first step")
    require(sequence[-1] == "drive FL_PWM=1", "PWM enabled before final programming step")
    require(any("REG0x01=0x56" in step for step in sequence), "14.5mA register write missing")
    require(any("REG0x02=0xA1" in step for step in sequence), "18V OVP register write missing")
    require(any("REG0x03=0x2B" in step for step in sequence), "1MHz/PFM register write missing")
    require("20mA" in firmware["default_register_hazard"] and "36V" in firmware["default_register_hazard"], "reset-default hazard missing")
    require(firmware["shutdown_sequence"] == ["drive FL_PWM=0", "drive FL_HWEN=0"], "shutdown sequence changed")

    result = {
        "date": "2026-09-30",
        "result": "PASS_C4D10B_DOCUMENTARY_AND_NATIVE_CHECKS",
        "candidate": "c4d10b-96x68-frontlight",
        "native_checks": counts,
        "refs": report["refs"],
        "pin_net_tuples": report["pin_net_tuples"],
        "driver": report["driver"],
        "firmware_safe_startup": True,
        "panel_current_limit_ma": 14.5,
        "ovp_v": 18,
        "first_order_sizing": report["first_order_sizing"],
        "physical_tests_completed": 0,
        "physical_qualification_complete": False,
        "manufacturing_release": False,
        "release_blockers": report["physical_qualification"] + [
            "final compact routing remains open (436 unconnected items)",
            "production RFQ/stock confirmation for SGM37601 remains open",
        ],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if release:
        print("manufacturing release blocked by open physical/routing gates", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()
    try:
        sys.exit(main(args.release))
    except (ValueError, KeyError, FileNotFoundError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(2)
