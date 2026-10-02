#!/usr/bin/env python3
"""Rebuild both native candidates, compare their CAD, and verify sourcing identities."""
from pathlib import Path
import argparse, hashlib, json, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
from _split_c1_common import ROOT, REPO, REL, STEM, BASELINE_COMMIT, kicad_python, sha
from _split_c1_sourcing import geometry_digest, patch_block
from _core_c1_pcb_patch import copper
sys.path.insert(0, str(ROOT / "tools"))
from prune_core_c1_stubs import blocks

def canonical(text, pcb):
    if not pcb:
        return re.sub(r"\s+", " ", re.sub(r'\(uuid "[^"]+"\)', "", text)).strip()
    items = list(blocks(text, "(segment")) + list(blocks(text, "(via"))
    rest = text
    for start, end, _ in sorted(items, reverse=True):
        rest = rest[:start] + rest[end:]
    normalized = re.sub(r"\s+", " ", rest).strip()
    ordered = "\n".join(re.sub(r"\s+", " ", block).strip() for _, block in sorted(copper(text).items()))
    return normalized + "\n" + ordered

def counts(folder):
    drc = json.loads((folder / "verification/drc.json").read_text())
    erc = json.loads((folder / "verification/erc.json").read_text())
    result = {"drc": len(drc["violations"]), "open": len(drc["unconnected_items"]),
              "parity": len(drc["schematic_parity"]),
              "erc": sum(len(sheet["violations"]) for sheet in erc["sheets"])}
    if any(result.values()):
        raise ValueError("Native CAD gates failed: " + str(result))
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "split-c1-validation.json")
    args = parser.parse_args()
    subprocess.run([kicad_python(), str(ROOT / "verify_split_c1.py")], check=True)
    record = {"schema": "panda-split-c1-validation-v2", "replay_baseline_commit": BASELINE_COMMIT,
              "files": {}, "manufacturing_release": False}
    with tempfile.TemporaryDirectory(prefix="panda-split-c1-validation-") as temporary:
        for board, candidate, builder, relative in [
            ("Core-C1", "core-c1-96x68-split", "build_core_c1_split.py", REL / (STEM + ".kicad_pcb")),
            ("Display-C1", "display-c1-45x36-production-bom", "build_display_c1_production.py", Path("PANDA-EPD0426-SPI-EVT.kicad_pcb"))]:
            current = ROOT / candidate
            rebuilt = Path(temporary) / candidate
            subprocess.run([sys.executable, str(ROOT / builder), "--output", str(rebuilt)], check=True)
            paths = [current / relative] + sorted((current / relative).parent.glob("*.kicad_sch"))
            for path in paths:
                replay = rebuilt / path.relative_to(current)
                if canonical(path.read_text(), path.suffix == ".kicad_pcb") != canonical(replay.read_text(), path.suffix == ".kicad_pcb"):
                    raise ValueError("Rebuilt CAD differs: " + str(path.relative_to(REPO)))
                record["files"][str(path.relative_to(REPO))] = {
                    "sha256": sha(path), "non_property_cad_digest": geometry_digest(path.read_text()),
                    "rebuild_geometry_and_properties_equal": True,
                    "rebuild_comparison_note": "Schematic object UUIDs ignored; PCB segment/via order canonicalized with UUIDs retained."}
            record["files"][board] = {"native_checks": {"current": counts(current), "fresh_rebuild": counts(rebuilt)}}
    source_paths = [ROOT / name for name in [
        "_split_c1_common.py", "_split_c1_sourcing.py", "_split_c1_prototype_eco.py", "_split_c1_domestic_eco.py", "_split_c1_usb_eco.py", "split-c1-domestic-eco.json", "_core_c1_pcb_patch.py",
        "build_core_c1_split.py", "build_display_c1_production.py", "validate_split_c1.py",
        "verify_split_c1.py", "audit_split_c1_mechanical.py", "audit_split_c1_domestic.py",
        "split-c1-domestic-policy.json", "SPLIT-C1-DOMESTICIZATION.md", "C4D8-RTC-DECISION.md", "export_production.py",
        "export_jlc.py", "freeze_split_c1_release.py", "release_split_c1.py",
        "split-c1-sourcing-evidence.json", "core-c1-routing-closure.json",
        "package_jlc_prototype.py", "JLC-PROTOTYPE-HANDOFF.md",
        "split-c1-mechanical-inputs.json", "tools/prune_core_c1_stubs.py",
        "qualification/c4d-evt/verify_qualification.py", "qualification/c4d-evt/qualification-plan.json"]]
    for candidate in ["core-c1-96x68-split", "display-c1-45x36-production-bom"]:
        source_paths.extend(p for p in (ROOT / candidate).rglob("*") if p.is_file()
                            and (p.suffix in {".kicad_mod", ".kicad_sym", ".kicad_pro", ".kicad_dru"}
                                 or p.name in {"fp-lib-table", "sym-lib-table"}))
    for path in sorted(source_paths):
        record["files"].setdefault(str(path.relative_to(REPO)), {"sha256": sha(path)})
    evidence = json.loads((ROOT / "split-c1-sourcing-evidence.json").read_text())
    verified = 0
    for board, candidate in [("Core-C1", "core-c1-96x68-split"), ("Display-C1", "display-c1-45x36-production-bom")]:
        tree = ET.parse(ROOT / candidate / "verification/netlist.xml")
        components = {c.get("ref"): {f.get("name"): f.text or "" for f in c.findall("fields/field")}
                      for c in tree.findall("components/comp")}
        for row in evidence["entries"]:
            if row["board"] != board:
                continue
            for ref in row["refs"]:
                fields = components[ref]
                for key in ["Manufacturer", "MPN", "LCSC"]:
                    expected = row[{"Manufacturer":"manufacturer", "MPN":"mpn", "LCSC":"library_id"}[key]]
                    if fields.get(key) != expected:
                        raise ValueError(f"Wrong purchasing identity: {board}/{ref}/{key}")
                verified += 1
    # A plug library ID must never be accepted for a socket.
    test = '(footprint "test" (property "Reference" "J601") (property "Manufacturer" "HCTL") (property "MPN" "HC-PBB40C-60DS-0.4V-1.5-02") (property "LCSC" "C19089235"))'
    socket = next(row for row in evidence["entries"] if row["board"] == "Core-C1" and "J601" in row["refs"])
    try:
        patch_block(test, "J601", socket, True)
    except ValueError:
        pass
    else:
        raise ValueError("Conflicting catalog ID was accepted")
    record.update(identity_verified_new_refs=verified, conflicting_part_id_rejection_checked=True,
                  native_all_60_pin_check_passed=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"rebuilds_match": True, "identity_verified_refs": verified, "manufacturing_release": False}, indent=2))

if __name__ == "__main__":
    main()
