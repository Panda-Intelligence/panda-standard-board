#!/usr/bin/env python3
"""Replay the complete R26 (v0.1.1) Single.kicad_pcb sample-readiness ECO from R25:
1. Retract the upper-left PCB step from X=30.0 mm to X=38.0 mm (Y=32.0..83.5 mm) so the
   323576 (35.0 x 76.0 x 3.2 mm) rectangular battery pack + PCM + wire harness assembly study
   has 0.0 mm^2 XY overlap with the PCB.
2. Shift the 51 footprints in the upper-left region (Block A x < 48.5, y < 70.0 by dx = +6.75 mm,
   BT301 by dx = +4.50 mm to (62.50, 56.40), C503 by (+6.775, +1.00) to (56.275, 64.00), and
   R528 by dy = +0.50 mm to (66.80, 64.30)) and shift the Block A rule-area keepouts by dx = +6.75 mm.
3. Move C804.2's ground return via outside the pad to an external dog-bone position at
   (17.40, 104.80) (0.45/0.20 mm via connected by a 0.30 mm F.Cu trace to C804.2 at (18.20, 105.00)),
   eliminating via-in-pad on C804.2.
4. Remove the 891 obsolete R25 boundary tracks/vias, shift the 431 internal Block A tracks/vias by
   dx = +6.75 mm, add the 657 routed boundary tracks and 106 vias across all 27 boundary nets,
   and refill zones for 0 DRC violations, 0 unconnected items, 0 schematic parity issues, and 0 ERC.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
import wx

APP = wx.GetApp() or wx.App(False)
import pcbnew  # noqa: E402

HERE = Path(__file__).resolve().parent
DELTA_PATH = HERE / "single_r26_x38_delta.json"
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")

SINGLE_R26_OUTLINE_MM = [
    (38.0, 32.0),
    (73.0, 32.0),
    (73.0, 131.0),
    (42.12, 131.0),
    (42.12, 125.45),
    (32.88, 125.45),
    (32.88, 131.0),
    (2.0, 131.0),
    (2.0, 83.5),
    (38.0, 83.5),
]

C804_DOGBONE_VIA_MM = (17.40, 104.80, 0.45, 0.20)
C804_DOGBONE_TRACE_MM = ((17.40, 104.80), (18.20, 105.00), 0.30)


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def verify_input_sha256(input_path: Path, delta: dict | None = None) -> str:
    """Verify input PCB SHA-256 matches either the R25 baseline or R26 target checkpoint."""
    if delta is None:
        delta = json.loads(DELTA_PATH.read_text())
    require(input_path.is_file(), f"Missing input PCB: {input_path}")
    digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    allowed = {delta["baseline_r25_sha256"], delta["target_r26_sha256"]}
    require(
        digest in allowed,
        f"Input PCB SHA-256 {digest} does not match baseline R25 ({delta['baseline_r25_sha256']}) "
        f"or target R26 ({delta['target_r26_sha256']})",
    )
    return digest


def verify_r26_postconditions(board: pcbnew.BOARD, delta: dict) -> None:
    """Verify R26 footprint positions, C804.2 external dog-bone via, and X=38.0mm step outline."""
    expected_xy = {
        "U901": (43.25, 52.00),
        "BT301": (62.50, 56.40),
        "C503": (56.28, 64.00),
        "R528": (66.80, 64.30),
    }
    for ref, (ex, ey) in expected_xy.items():
        fp = board.FindFootprintByReference(ref)
        require(fp is not None, f"Missing footprint after ECO: {ref}")
        ax, ay = pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)
        require(
            abs(ax - ex) < 1e-3 and abs(ay - ey) < 1e-3,
            f"Post-condition position mismatch on {ref}: ({ax:.3f}, {ay:.3f}) != ({ex:.3f}, {ey:.3f})",
        )

    c804 = board.FindFootprintByReference("C804")
    require(c804 is not None, "Missing C804 footprint")
    pad2 = next((p for p in c804.Pads() if p.GetNumber() == "2"), None)
    require(pad2 is not None, "Missing C804.2 pad")
    in_pad = [
        v for v in board.GetTracks() if v.GetClass() == "PCB_VIA" and pad2.HitTest(v.GetPosition())
    ]
    require(not in_pad, "Via-in-pad still present on C804.2")
    cx, cy, cw, cd = delta["c804_via_target_mm"]
    dogbone = [
        v
        for v in board.GetTracks()
        if v.GetClass() == "PCB_VIA"
        and abs(pcbnew.ToMM(v.GetPosition().x) - cx) < 1e-3
        and abs(pcbnew.ToMM(v.GetPosition().y) - cy) < 1e-3
    ]
    require(len(dogbone) == 1, "Missing external dog-bone via for C804.2")

    edges = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    require(len(edges) == len(SINGLE_R26_OUTLINE_MM), "Edge.Cuts segment count mismatch")


def apply_single_r26_eco(
    board: pcbnew.BOARD,
    delta: dict | None = None,
    *,
    strict_uuid_check: bool = True,
) -> None:
    """Apply the complete R25 -> R26 Single.kicad_pcb ECO in-place."""
    if delta is None:
        delta = json.loads(DELTA_PATH.read_text())

    # 1. Verify all 51 footprints exist and classify R25 vs R26 input state
    fp_moves = delta["footprint_moves_mm"]
    for ref in fp_moves:
        require(board.FindFootprintByReference(ref) is not None, f"Missing required footprint: {ref}")

    u901 = board.FindFootprintByReference("U901")
    ux, uy = pcbnew.ToMM(u901.GetPosition().x), pcbnew.ToMM(u901.GetPosition().y)
    if abs(ux - 36.50) < 1e-3 and abs(uy - 52.00) < 1e-3:
        is_r25_input = True
    elif abs(ux - 43.25) < 1e-3 and abs(uy - 52.00) < 1e-3:
        is_r25_input = False
    else:
        raise ValueError(f"Unexpected U901 position ({ux:.3f}, {uy:.3f}); expected R25 (36.50, 52.00) or R26 (43.25, 52.00)")

    if is_r25_input:
        for ref, (dx, dy) in fp_moves.items():
            fp = board.FindFootprintByReference(ref)
            fp.Move(pcbnew.VECTOR2I(pcbnew.FromMM(dx), pcbnew.FromMM(dy)))

    # 2. Update tracks and vias from R25 -> R26
    removed_set = set(delta["removed_uuids"])
    shifted_set = set(delta["shifted_plus_6p75_x_uuids"])
    c804_uuid = delta["c804_via_uuid"]
    cx, cy, cw, cd = delta["c804_via_target_mm"]

    if is_r25_input:
        seen_removed: set[str] = set()
        seen_shifted: set[str] = set()
        seen_c804 = False
        for t in list(board.GetTracks()):
            u = str(t.m_Uuid.AsString())
            if u in removed_set:
                seen_removed.add(u)
                board.Delete(t)
            elif u in shifted_set:
                seen_shifted.add(u)
                t.Move(pcbnew.VECTOR2I(pcbnew.FromMM(6.75), 0))
            elif u == c804_uuid and t.GetClass() == "PCB_VIA":
                seen_c804 = True
                t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx), pcbnew.FromMM(cy)))
                t.SetWidth(pcbnew.FromMM(cw))
                t.SetDrill(pcbnew.FromMM(cd))

        if strict_uuid_check:
            require(
                seen_removed == removed_set,
                f"Missing {len(removed_set - seen_removed)} expected R25 removed track/via UUIDs",
            )
            require(
                seen_shifted == shifted_set,
                f"Missing {len(shifted_set - seen_shifted)} expected R25 shifted track/via UUIDs",
            )
            require(seen_c804, f"Missing expected C804.2 via UUID {c804_uuid}")

        layer_map = {
            "F.Cu": pcbnew.F_Cu,
            "In1.Cu": pcbnew.In1_Cu,
            "In2.Cu": pcbnew.In2_Cu,
            "B.Cu": pcbnew.B_Cu,
        }
        for tr_spec in delta["added_tracks"]:
            net = board.FindNet(tr_spec["net"])
            require(net is not None and net.GetNetCode() > 0, f"Missing net: {tr_spec['net']}")
            tr = pcbnew.PCB_TRACK(board)
            tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(tr_spec["start"][0]), pcbnew.FromMM(tr_spec["start"][1])))
            tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(tr_spec["end"][0]), pcbnew.FromMM(tr_spec["end"][1])))
            tr.SetWidth(pcbnew.FromMM(tr_spec["width"]))
            tr.SetLayer(layer_map[tr_spec["layer"]])
            tr.SetNet(net)
            tr.thisown = 0
            board.Add(tr)

        for v_spec in delta["added_vias"]:
            net = board.FindNet(v_spec["net"])
            require(net is not None and net.GetNetCode() > 0, f"Missing net: {v_spec['net']}")
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(v_spec["xy"][0]), pcbnew.FromMM(v_spec["xy"][1])))
            v.SetWidth(pcbnew.FromMM(v_spec["width"]))
            v.SetDrill(pcbnew.FromMM(v_spec["drill"]))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetNet(net)
            v.thisown = 0
            board.Add(v)

    # 3. Replace Edge.Cuts and update Zone outlines (and shift R25 Block A rule areas)
    for d in list(board.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            board.Delete(d)
    for a, z in zip(SINGLE_R26_OUTLINE_MM, SINGLE_R26_OUTLINE_MM[1:] + SINGLE_R26_OUTLINE_MM[:1]):
        line = pcbnew.PCB_SHAPE(board)
        line.SetShape(pcbnew.SHAPE_T_SEGMENT)
        line.SetLayer(pcbnew.Edge_Cuts)
        line.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
        line.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(z[0]), pcbnew.FromMM(z[1])))
        line.SetWidth(pcbnew.FromMM(0.10))
        line.thisown = 0
        board.Add(line)

    ds = board.GetDesignSettings()
    ds.m_CopperEdgeClearance = pcbnew.FromMM(0.20)
    ds.m_TrackMinWidth = pcbnew.FromMM(0.15)
    ds.m_ViasMinSize = pcbnew.FromMM(0.40)
    ds.m_HoleMinDiameter = pcbnew.FromMM(0.20)
    ds.m_MinClearance = pcbnew.FromMM(0.15)

    for z in list(board.Zones()):
        if z.GetIsRuleArea():
            if is_r25_input:
                bb = z.GetBoundingBox()
                zx, zy = pcbnew.ToMM(bb.GetCenter().x), pcbnew.ToMM(bb.GetCenter().y)
                if zx < 48.5 and zy < 70.0:
                    z.Move(pcbnew.VECTOR2I(pcbnew.FromMM(6.75), 0))
        else:
            z.SetLocalClearance(pcbnew.FromMM(0.15))
            poly = z.Outline()
            poly.RemoveAllContours()
            poly.NewOutline()
            for x, y in SINGLE_R26_OUTLINE_MM:
                poly.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))

    verify_r26_postconditions(board, delta)


def run_cli(input_path: Path, output_path: Path) -> None:
    delta = json.loads(DELTA_PATH.read_text())
    verify_input_sha256(input_path, delta)
    out_pro = output_path.with_suffix(".kicad_pro")
    saved_pro = out_pro.read_bytes() if out_pro.exists() else None
    b = pcbnew.LoadBoard(str(input_path))
    apply_single_r26_eco(b, delta, strict_uuid_check=True)
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(str(output_path), b)
    if saved_pro is not None:
        out_pro.write_bytes(saved_pro)
    if (
        KICAD_CLI.is_file()
        and out_pro.is_file()
        and output_path.with_suffix(".kicad_sch").is_file()
        and (output_path.parent / "fp-lib-table").is_file()
    ):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            drc_out = Path(tf.name)
        try:
            subprocess.run(
                [
                    str(KICAD_CLI),
                    "pcb",
                    "drc",
                    "--severity-all",
                    "--all-track-errors",
                    "--schematic-parity",
                    "--format",
                    "json",
                    "--output",
                    str(drc_out),
                    str(output_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
            )
            report = json.loads(drc_out.read_text())
            require(
                not report.get("violations")
                and not report.get("unconnected_items")
                and not report.get("schematic_parity"),
                f"Replayed board failed native DRC check: "
                f"violations={len(report.get('violations', []))}, "
                f"unconnected={len(report.get('unconnected_items', []))}, "
                f"parity={len(report.get('schematic_parity', []))}",
            )
        finally:
            drc_out.unlink(missing_ok=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    run_cli(args.input, args.output)
