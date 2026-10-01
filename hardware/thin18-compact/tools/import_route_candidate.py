#!/usr/bin/env python3
"""Import a FreeRouting SES into a complete Thin18 candidate and evaluate it natively.

Run with KiCad's bundled Python so `pcbnew` is available. The tool copies the
complete source project, imports the SES, raises imported copper below the native
minimum width, verifies that no footprint moved, and runs KiCad DRC/ERC/parity.
It is an evaluator: non-zero open/violations are recorded rather than approved.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import wx

APP = wx.App(False)
import pcbnew  # noqa: E402

KICAD = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
REL = Path("eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16")
STEM = "PANDA-STD-CORE-EVT-quilter-j501-merged"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pose_map(board: pcbnew.BOARD) -> dict[str, tuple[int, int, int, int]]:
    result = {}
    for footprint in board.GetFootprints():
        position = footprint.GetPosition()
        result[footprint.GetReference()] = (
            position.x,
            position.y,
            int(footprint.GetOrientation().AsTenthsOfADegree()),
            int(footprint.GetLayer()),
        )
    return result


def sanitize_netlist(path: Path) -> None:
    text = path.read_text()
    text = re.sub(
        r"<source>.*?</source>",
        "<source>eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16/PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_sch</source>",
        text,
        count=1,
    )
    path.write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="complete source candidate root")
    parser.add_argument("--ses", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-width-mm", type=float, default=0.15)
    args = parser.parse_args()

    source = args.source.resolve()
    ses = args.ses.resolve()
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(
        source,
        output,
        ignore=shutil.ignore_patterns("verification", "__pycache__", "*.pyc", "*.kicad_prl", "*.lck"),
    )
    verification = output / "verification"
    verification.mkdir()

    pcb_path = output / REL / f"{STEM}.kicad_pcb"
    sch_path = output / REL / f"{STEM}.kicad_sch"
    source_board = pcbnew.LoadBoard(str(source / REL / f"{STEM}.kicad_pcb"))
    source_poses = pose_map(source_board)
    board = pcbnew.LoadBoard(str(pcb_path))
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise SystemExit("SES import failed")

    minimum_width = pcbnew.FromMM(args.minimum_width_mm)
    normalized = []
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA):
            continue
        if item.GetWidth() < minimum_width:
            normalized.append({
                "net": item.GetNetname(),
                "old_width_mm": pcbnew.ToMM(item.GetWidth()),
                "new_width_mm": args.minimum_width_mm,
            })
            item.SetWidth(minimum_width)

    target_poses = pose_map(board)
    if target_poses != source_poses:
        moved = sorted(ref for ref in set(target_poses) | set(source_poses) if target_poses.get(ref) != source_poses.get(ref))
        raise SystemExit(f"SES changed footprint poses: {moved}")

    # Specctra SES round-tripping rewrites footprint fields/graphics and can create
    # false parity/clearance failures. Save imported copper first; then restore
    # native source footprint blocks textually so only tracks/vias come from SES.
    pcbnew.SaveBoard(str(pcb_path), board)
    imported_text = pcb_path.read_text()
    source_text = (source / REL / f"{STEM}.kicad_pcb").read_text()

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

    def footprint_blocks(text: str) -> dict[str, str]:
        result = {}
        pos = 0
        while True:
            start = text.find("(footprint ", pos)
            if start < 0:
                break
            end = balanced(text, start)
            block = text[start:end]
            match = re.search(r'\(property "Reference" "([^"]+)"', block)
            if match:
                result[match.group(1)] = block
            pos = end
        return result

    native_blocks = footprint_blocks(source_text)
    pos = 0
    chunks = []
    while True:
        start = imported_text.find("(footprint ", pos)
        if start < 0:
            chunks.append(imported_text[pos:])
            break
        end = balanced(imported_text, start)
        block = imported_text[start:end]
        match = re.search(r'\(property "Reference" "([^"]+)"', block)
        chunks.append(imported_text[pos:start])
        if not match or match.group(1) not in native_blocks:
            raise SystemExit("unable to restore imported footprint")
        chunks.append(native_blocks[match.group(1)])
        pos = end
    pcb_path.write_text("".join(chunks))
    restored_board = pcbnew.LoadBoard(str(pcb_path))
    if pose_map(restored_board) != source_poses:
        raise SystemExit("native footprint restoration changed placement")

    subprocess.run(
        [KICAD, "sch", "erc", "--format", "json", "--severity-all", "--output", str(verification / "erc.json"), str(sch_path)],
        check=True,
    )
    subprocess.run(
        [KICAD, "sch", "export", "netlist", "--format", "kicadxml", "--output", str(verification / "netlist.xml"), str(sch_path)],
        check=True,
    )
    subprocess.run(
        [KICAD, "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--output", str(verification / "drc.json"), str(pcb_path)],
        check=True,
    )
    sanitize_netlist(verification / "netlist.xml")

    drc = json.loads((verification / "drc.json").read_text())
    erc = json.loads((verification / "erc.json").read_text())
    counts = {
        "drc": len(drc.get("violations", [])),
        "open": len(drc.get("unconnected_items", [])),
        "parity": len(drc.get("schematic_parity", [])),
        "erc": sum(len(sheet.get("violations", [])) for sheet in erc.get("sheets", [])),
    }
    types = dict(collections.Counter(item.get("type", "unknown") for item in drc.get("violations", [])))
    reloaded = pcbnew.LoadBoard(str(pcb_path))
    tracks = list(reloaded.GetTracks())
    report = {
        "date": "2026-09-30",
        "source": source.name,
        "ses_sha256": sha256(ses),
        "minimum_width_mm": args.minimum_width_mm,
        "normalized_track_segments": len(normalized),
        "normalized_by_net": dict(collections.Counter(item["net"] for item in normalized)),
        "native_checks": counts,
        "violation_types": types,
        "tracks_and_vias": len(tracks),
        "vias": sum(isinstance(item, pcbnew.PCB_VIA) for item in tracks),
        "footprint_poses_identical": True,
        "routing_complete": counts == {"drc": 0, "open": 0, "parity": 0, "erc": 0},
        "manufacturing_release": False,
        "pcb_sha256": sha256(pcb_path),
    }
    (output / "route-import-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (output / "README.md").write_text(
        f"# {output.name}\n\n"
        f"Imported from `{source.name}` using SES SHA-256 `{report['ses_sha256']}`.\n\n"
        f"Native result: ERC={counts['erc']}, DRC={counts['drc']}, parity={counts['parity']}, open={counts['open']}.\n\n"
        "This is not manufacturing release unless a later controlled checkpoint explicitly says so.\n"
    )
    for transient in output.rglob("*.kicad_prl"):
        transient.unlink()
    for transient in output.rglob("*.lck"):
        transient.unlink()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
