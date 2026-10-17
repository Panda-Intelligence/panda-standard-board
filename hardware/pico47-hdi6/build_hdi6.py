#!/usr/bin/env python3
"""Build two independent native six-layer Panda47 engineering study boards.

Inputs: exact, hash-bound E0.2 r12 four-layer native checkpoint and matching
unchanged source design/layout. Outputs: six-layer KiCad boards, DRC/ERC/native
ground and pad-group evidence. No source PCB is modified and no release enabled.

Initial migration preserves every existing copper route, component, net, drill,
outline, pad mode and project rule. Adds In3 signal capacity and a new In4 GND
reference pour, retaining existing In1 GND. Future POFV/routing requires a
separately accepted source-bound ECO; it is not quietly inserted here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import uuid
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hardware" / "pico47"))
sys.path.insert(0, str(ROOT / "hardware" / "thin18-compact"))

from hdi6_contract import (BOARDS, LAYERS, SIGNAL_LAYERS, REFERENCE_LAYERS,
                           load_variant, verified_baseline, sha256,
                           require, require_native_counts)
from seven_mm_routing import sexpr_blocks
from prune_pico47_stubs import snapshot, preserves_groups
from pico47_ground_returns import inspect_ground_returns
from pico47_complete_ground_gate import require_complete_ground_returns
from pico47_panel_control_report import inspect_panel_control_links

KI_PYTHON_DEFAULT = (
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/"
    "Python.framework/Versions/Current/bin/python3"
)
KI_CLI_DEFAULT = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def read_counts(path: Path, erc_path: Path) -> dict:
    report = json.loads(path.read_text())
    erc = json.loads(erc_path.read_text())
    erc_violations = erc.get("violations", [])
    return {
        "open": len(report.get("unconnected_items", [])),
        "drc_errors": sum(v.get("severity") == "error" for v in report["violations"]),
        "drc_warnings": sum(v.get("severity") == "warning" for v in report["violations"]),
        "parity": len(report.get("schematic_parity", [])),
        "erc": len(erc_violations),
    }


def run(command: list[str], log: Path) -> None:
    with log.open("w") as out:
        subprocess.run(command, cwd=log.parent, stdout=out,
                       stderr=subprocess.STDOUT, check=True, timeout=180)


def native_fingerprint(board: object, p: object) -> dict:
    """Immutable component IDs and original track geometry, excluding zones."""
    def position(q):
        return (int(q.x), int(q.y))
    footprints = {}
    for f in board.GetFootprints():
        ref = f.GetReference()
        require(ref not in footprints, "duplicate footprint " + ref)
        pads = []
        for pad in f.Pads():
            pads.append((pad.m_Uuid.AsString(), str(pad.GetNumber()),
                         str(pad.GetNetname()), position(pad.GetPosition()),
                         position(pad.GetSize()), position(pad.GetDrillSize()),
                         int(pad.GetShape()), int(pad.GetAttribute())))
        footprints[ref] = {
            "reference": ref,
            "value": f.GetValue(),
            "footprint_library": str(f.GetFPID().GetLibNickname()),
            "footprint_name": str(f.GetFPID().GetLibItemName()),
            "position": position(f.GetPosition()),
            "angle": round(f.GetOrientationDegrees(), 6),
            "layer": board.GetLayerName(f.GetLayer()),
            "pads": sorted(pads),
        }
    copper = {}
    for track in board.GetTracks():
        uid = track.m_Uuid.AsString()
        net = str(track.GetNetname())
        if isinstance(track, p.PCB_VIA):
            row = ("via", net, position(track.GetPosition()),
                   int(track.GetWidth(p.F_Cu)), int(track.GetDrill()),
                   int(track.TopLayer()), int(track.BottomLayer()))
        elif isinstance(track, p.PCB_ARC):
            row = ("arc", net, board.GetLayerName(track.GetLayer()),
                   position(track.GetStart()), position(track.GetMid()),
                   position(track.GetEnd()), int(track.GetWidth()))
        else:
            row = ("track", net, board.GetLayerName(track.GetLayer()),
                   position(track.GetStart()), position(track.GetEnd()),
                   int(track.GetWidth()))
        require(uid not in copper, "duplicate copper UUID")
        copper[uid] = row
    return {"footprints": footprints, "original_copper": copper}


def add_reference_layer(board_path: Path, board_name: str, source_sha: str) -> None:
    """Clone exactly one existing In1 GND reference polygon onto In4."""
    text = board_path.read_text()
    zones = [
        z for z in sexpr_blocks(text, "(zone")
        if ('(net_name "GND")' in z or '(net "GND")' in z)
        and '(layer "In1.Cu")' in z and "(keepout" not in z
    ]
    require(len(zones) == 1,
            board_name + " must contain exactly one reviewed In1 GND zone")
    original_zone = zones[0]
    new = original_zone.replace('(layer "In1.Cu")',
                                '(layer "In4.Cu")', 1)
    require(new != original_zone, "new ground-layer replacement failed")
    # A stable distinct zone identity is required for reproducible source replay.
    new_id = str(uuid.uuid5(uuid.NAMESPACE_URL,
                 "pico47-hdi6-v1/" + board_name + "/In4-GND/" + source_sha))
    new, count = re.subn(r'\(uuid "[^"]+"\)',
                         '(uuid "' + new_id + '")', new, count=1)
    require(count == 1, "GND zone identity replacement failed")
    final = text.rfind(")")
    require(final > 0, "malformed KiCad board document")
    board_path.write_text(text[:final] + new + "\n" + text[final:])


def migrate_board(
    board_name: str, original_dir: Path, output_dir: Path,
    native_python: str, source_hash: str,
) -> None:
    script = """import wx
app=wx.App(False)
import pcbnew as P
import sys
src=sys.argv[1]
board=P.LoadBoard(src)
assert board.GetCopperLayerCount()==4
assert abs(P.ToMM(board.GetDesignSettings().GetBoardThickness())-0.8)<0.001
board.SetCopperLayerCount(6)
board.GetDesignSettings().SetBoardThickness(P.FromMM(0.8))
board.GetDesignSettings().m_HasStackup=False
board.SetLayerType(P.In1_Cu,P.LT_POWER)
board.SetLayerType(P.In4_Cu,P.LT_POWER)
assert board.GetCopperLayerCount()==6
P.SaveBoard(src,board)
"""
    run([native_python, "-c", script, str(output_dir / (board_name + ".kicad_pcb"))],
        output_dir / (board_name + "-six-layer-conversion.log"))
    add_reference_layer(output_dir / (board_name + ".kicad_pcb"),
                        board_name, source_hash)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", type=Path, required=True,
                    help="Exact immutable published r12 engineering-candidate directory")
    ap.add_argument("--output", type=Path, required=True,
                    help="Fresh separate HDI6 engineering-study directory")
    ap.add_argument("--donor", type=Path, required=True,
                    help="Previously reviewed donor tooling/libs for independent inspector")
    ap.add_argument("--python", default=KI_PYTHON_DEFAULT)
    ap.add_argument("--kicad-cli", default=KI_CLI_DEFAULT)
    args = ap.parse_args()
    source = args.baseline.resolve()
    destination = args.output.resolve()
    donor = args.donor.resolve()
    variant = load_variant(HERE / "variant.json")
    baseline_sha = verified_baseline(variant, source, ROOT / "hardware" / "pico47")
    require(donor.is_dir(), "donor tooling directory unavailable")
    require(not destination.exists(), "output path already exists; use a new name")
    require(not destination.is_relative_to(source) and
            not source.is_relative_to(destination),
            "output cannot overwrite the four-layer checkpoint")
    require(not destination.is_relative_to(ROOT / "hardware"),
            "generated native CAD must stay outside tracked hardware source")

    destination.mkdir(parents=True)
    failure_note = destination / "HDI6-INCOMPLETE.txt"
    failure_note.write_text(
        "Six-layer engineering-study build in progress; NOT manufacturing release.\n")
    try:
        for board_name in BOARDS:
            for ext in (".kicad_pcb", ".kicad_pro", ".kicad_dru", ".kicad_sch"):
                f = source / (board_name + ext)
                require(f.is_file(), "missing " + f.name)
                shutil.copy2(f, destination / f.name)
        for name in ("Panda7.kicad_sym", "fp-lib-table", "sym-lib-table"):
            shutil.copy2(source / name, destination / name)
        shutil.copytree(source / "Panda47.pretty", destination / "Panda47.pretty")

        import wx
        app = wx.GetApp() or wx.App(False)
        import pcbnew as P
        before = {}
        for board_name in BOARDS:
            path = source / (board_name + ".kicad_pcb")
            native = P.LoadBoard(str(path))
            require(native.GetCopperLayerCount() == 4,
                    "source unexpectedly not four-layer: " + board_name)
            before[board_name] = native_fingerprint(native, P)
            migrate_board(board_name, source, destination,
                          args.python, baseline_sha[board_name + ".kicad_pcb"])

        results = {}
        grounds = {}
        for board_name in BOARDS:
            pcb = destination / (board_name + ".kicad_pcb")
            sch = destination / (board_name + ".kicad_sch")
            report_file = destination / (board_name + "-drc.json")
            erc_file = destination / (board_name + "-erc.json")
            run([args.kicad_cli, "pcb", "drc", "--refill-zones", "--save-board",
                 "--severity-all", "--all-track-errors", "--schematic-parity",
                 "--format", "json", "--output", str(report_file), str(pcb)],
                destination / (board_name + "-drc.log"))
            run([args.kicad_cli, "sch", "erc", "--severity-all", "--format",
                 "json", "--output", str(erc_file), str(sch)],
                destination / (board_name + "-erc.log"))

            new = P.LoadBoard(str(pcb))
            require(new.GetCopperLayerCount() == 6,
                    board_name + " is not six-layer")
            require(native_fingerprint(new, P) == before[board_name],
                    board_name + " original components or copper changed")
            require(all(
                new.GetLayerName(t.GetLayer()) not in REFERENCE_LAYERS
                for t in new.GetTracks() if not isinstance(t, P.PCB_VIA)
                and t.GetNetname() != "GND"
            ), board_name + " has signal tracks on reference planes")
            zones = {(new.GetLayerName(z.GetLayer()), z.GetNetname())
                     for z in new.Zones()}
            require(all((layer, "GND") in zones for layer in REFERENCE_LAYERS),
                    board_name + " new GND reference zone missing")
            old_groups = snapshot(source / (board_name + ".kicad_pcb"),
                                  destination / (board_name + "-old-pad-groups.json"))
            new_groups = snapshot(pcb, destination / (board_name + "-new-pad-groups.json"))
            require(preserves_groups(old_groups, new_groups),
                    board_name + " broke original connected pad groups")

            if board_name == "Core":
                ground = inspect_ground_returns(new, "U501", "57",
                                                [("J601", "36"), ("J601", "38")])
                control_links = inspect_panel_control_links(new)
                require(all(v["connected"] for v in control_links.values()),
                        "Core control connection was lost")
                (destination / "CORE-CONTROL-LINKS.json").write_text(
                    json.dumps(control_links, indent=2) + "\n")
            else:
                ground = inspect_ground_returns(new, "C804", "2", [
                    ("J820", "9"), ("J820", "22"), ("R809", "2"),
                    ("R810", "2"), ("U810", "32"), ("U810", "41"),
                ])
                ep = next(x for f in new.GetFootprints() if f.GetReference() == "U810"
                          for x in f.Pads() if x.GetNumber() == "49")
                require(ep.GetNetname() != "GND",
                        "negative PMIC exposed pad must never be grounded")
            grounds[board_name] = ground
            results[board_name] = read_counts(report_file, erc_file)
            for ext in (".kicad_pro", ".kicad_dru", ".kicad_sch"):
                original = source / (board_name + ext)
                converted = destination / (board_name + ext)
                if ext != ".kicad_pro" or sha256(original) == sha256(converted):
                    require(sha256(original) == sha256(converted),
                            board_name + ext + " unexpectedly changed")
                    continue
                # KiCad normalizes an inherited donor project's display name
                # during the first native DRC. Allow only exact file/sheet
                # metadata normalization; all design rules must match verbatim.
                prior = json.loads(original.read_text())
                after = json.loads(converted.read_text())
                require(prior["board"] == after["board"],
                        board_name + " KiCad project board rules changed")
                require(board_name == "Display",
                        "unexpected project normalization for " + board_name)
                prior["meta"]["filename"] = board_name + ".kicad_pro"
                top = prior["schematic"]["top_level_sheets"]
                require(len(top) == 1, "ambiguous schematic sheet normalization")
                top[0]["filename"] = board_name + ".kicad_sch"
                top[0]["name"] = board_name
                require(prior == after,
                        "KiCad changed more than project filename metadata")
        require_complete_ground_returns(grounds)
        require_native_counts(variant, results)
        status = {
            "variant": variant["variant_id"],
            "revision": variant["revision"],
            "baseline": str(source),
            "native_counts": results,
            "layer_count": 6,
            "reference_ground_layers": list(REFERENCE_LAYERS),
            "all_original_components_and_copper_identical": True,
            "all_previous_pad_connections_preserved": True,
            "complete_ground_gate": True,
            "new_signal_routes_added": 0,
            "full_routing_complete": all(v["open"] == 0 for v in results.values()),
            "six_layer_factory_stackup_confirmed": False,
            "hdi_microvia_pofv_process_confirmed": False,
            "mechanical_fit_verified": False,
            "manufacturing_release": False,
            "physical_qualification_complete": False,
        }
        (destination / "CURRENT-STATUS.json").write_text(
            json.dumps(status, indent=2) + "\n")
        bound = {
            "schema": "pico47-hdi6-source-checkpoint-v1",
            "variant": variant["variant_id"],
            "baseline_sources_sha256": baseline_sha,
            "variant_sha256": sha256(HERE / "variant.json"),
            "files_sha256": {
                f.name: sha256(f) for f in destination.iterdir()
                if f.is_file() and f.name.endswith(
                    (".kicad_pcb", ".kicad_sch", ".kicad_dru", ".kicad_pro"))
            },
            "native_counts": results,
            "manufacturing_release": False,
        }
        (destination / "SOURCE-CHECKPOINT.json").write_text(
            json.dumps(bound, indent=2) + "\n")
        failure_note.unlink()
        print(json.dumps(status, indent=2))
    except Exception as error:
        failure_note.write_text(
            "INCOMPLETE: " + type(error).__name__ + ": " + str(error)
            + "\nNever use this candidate for fabrication.\n")
        raise


if __name__ == "__main__":
    main()
