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
import json
from pathlib import Path
import wx

APP = wx.GetApp() or wx.App(False)
import pcbnew  # noqa: E402

HERE = Path(__file__).resolve().parent
DELTA_PATH = HERE / "single_r26_x38_delta.json"

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


def apply_single_r26_eco(board: pcbnew.BOARD, delta: dict | None = None) -> None:
    """Apply the complete R25 -> R26 Single.kicad_pcb ECO in-place."""
    if delta is None:
        delta = json.loads(DELTA_PATH.read_text())

    # 1. Move the 51 footprints (if still at R25 coordinates)
    fp_moves = delta["footprint_moves_mm"]
    u901 = board.FindFootprintByReference("U901")
    is_r25_input = u901 is not None and pcbnew.ToMM(u901.GetPosition().x) < 40.0
    if is_r25_input:
        for ref, (dx, dy) in fp_moves.items():
            fp = board.FindFootprintByReference(ref)
            if fp is not None:
                fp.Move(pcbnew.VECTOR2I(pcbnew.FromMM(dx), pcbnew.FromMM(dy)))

    # 2. Update tracks and vias from R25 -> R26
    removed_set = set(delta["removed_uuids"])
    shifted_set = set(delta["shifted_plus_6p75_x_uuids"])
    c804_uuid = delta["c804_via_uuid"]
    cx, cy, cw, cd = delta["c804_via_target_mm"]

    if is_r25_input:
        for t in list(board.GetTracks()):
            u = str(t.m_Uuid.AsString())
            if u in removed_set:
                board.Delete(t)
            elif u in shifted_set:
                t.Move(pcbnew.VECTOR2I(pcbnew.FromMM(6.75), 0))
            elif u == c804_uuid and t.GetClass() == "PCB_VIA":
                t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx), pcbnew.FromMM(cy)))
                t.SetWidth(pcbnew.FromMM(cw))
                t.SetDrill(pcbnew.FromMM(cd))

        layer_map = {
            "F.Cu": pcbnew.F_Cu,
            "In1.Cu": pcbnew.In1_Cu,
            "In2.Cu": pcbnew.In2_Cu,
            "B.Cu": pcbnew.B_Cu,
        }
        for tr_spec in delta["added_tracks"]:
            tr = pcbnew.PCB_TRACK(board)
            tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(tr_spec["start"][0]), pcbnew.FromMM(tr_spec["start"][1])))
            tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(tr_spec["end"][0]), pcbnew.FromMM(tr_spec["end"][1])))
            tr.SetWidth(pcbnew.FromMM(tr_spec["width"]))
            tr.SetLayer(layer_map[tr_spec["layer"]])
            tr.SetNet(board.FindNet(tr_spec["net"]))
            tr.thisown = 0
            board.Add(tr)

        for v_spec in delta["added_vias"]:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(v_spec["xy"][0]), pcbnew.FromMM(v_spec["xy"][1])))
            v.SetWidth(pcbnew.FromMM(v_spec["width"]))
            v.SetDrill(pcbnew.FromMM(v_spec["drill"]))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetNet(board.FindNet(v_spec["net"]))
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


def run_cli(input_path: Path, output_path: Path) -> None:
    out_pro = output_path.with_suffix(".kicad_pro")
    saved_pro = out_pro.read_bytes() if out_pro.exists() else None
    b = pcbnew.LoadBoard(str(input_path))
    apply_single_r26_eco(b)
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(str(output_path), b)
    if saved_pro is not None:
        out_pro.write_bytes(saved_pro)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    run_cli(args.input, args.output)
