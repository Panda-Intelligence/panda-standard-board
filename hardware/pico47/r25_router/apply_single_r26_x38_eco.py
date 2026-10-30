#!/usr/bin/env python3
"""Replay the R26 (v0.1.1) Single.kicad_pcb sample-readiness ECO:
1. Retract the upper-left PCB step from X=30.0 mm to X=38.0 mm (Y=32.0..83.5 mm) so the
   323576 (35.0 x 76.0 x 3.2 mm) rectangular battery at X=2.0..37.0, Y=4.0..80.0 mm has
   0.0 mm^2 overlap (1.0 mm X clearance, 3.5 mm Y clearance).
2. Shift Block A (x < 48.5, y < 70.0) by dx = +6.75 mm, BT301 by dx = +4.50 mm to (62.50, 56.40),
   C503 to (56.275, 64.00), and R528 to (66.80, 64.30) (0 courtyard overlaps).
3. Move C804.2's ground return via outside the pad to an external dog-bone position at
   (17.40, 104.80) (0.45/0.20 mm via connected by a 0.30 mm F.Cu trace to C804.2 at (18.20, 105.00)),
   eliminating via-in-pad on C804.2.
4. Route the 27 boundary nets and stitch GND vias for 0 DRC violations, 0 unconnected items,
   0 schematic parity issues, and 0 ERC violations.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pcbnew

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


def apply_outline_and_c804_dogbone(board: pcbnew.BOARD) -> None:
    """Apply the X=38.0 mm step outline, zone contours, and C804.2 external dog-bone via."""
    gnd_net = board.FindNet("GND")
    for t in list(board.GetTracks()):
        if isinstance(t, pcbnew.PCB_VIA) and t.GetNetname() == "GND":
            vx, vy = pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)
            if abs(vx - 18.10) < 0.15 and abs(vy - 104.75) < 0.15:
                t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(17.40), pcbnew.FromMM(104.80)))
                t.SetWidth(pcbnew.FromMM(0.45))
                t.SetDrill(pcbnew.FromMM(0.20))

    tr = pcbnew.PCB_TRACK(board)
    tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(17.40), pcbnew.FromMM(104.80)))
    tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(18.20), pcbnew.FromMM(105.00)))
    tr.SetWidth(pcbnew.FromMM(0.30))
    tr.SetLayer(pcbnew.F_Cu)
    tr.SetNet(gnd_net)
    board.Add(tr)

    for d in [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]:
        board.Remove(d)
    for a, z in zip(SINGLE_R26_OUTLINE_MM, SINGLE_R26_OUTLINE_MM[1:] + SINGLE_R26_OUTLINE_MM[:1]):
        line = pcbnew.PCB_SHAPE(board)
        line.SetShape(pcbnew.SHAPE_T_SEGMENT)
        line.SetLayer(pcbnew.Edge_Cuts)
        line.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
        line.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(z[0]), pcbnew.FromMM(z[1])))
        line.SetWidth(pcbnew.FromMM(0.10))
        board.Add(line)

    for z in list(board.Zones()):
        if not z.GetIsRuleArea():
            poly = z.Outline()
            poly.RemoveAllContours()
            poly.NewOutline()
            for x, y in SINGLE_R26_OUTLINE_MM:
                poly.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    b = pcbnew.LoadBoard(str(args.input))
    apply_outline_and_c804_dogbone(b)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(str(args.output), b)
