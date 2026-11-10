"""Specctra round trip for Freerouting (KiCad Python).

usage:
  specctra_v020.py export board.kicad_pcb out.dsn
  specctra_v020.py import board.kicad_pcb in.ses out.kicad_pcb
"""
import sys

import pcbnew as P

mode, pcb = sys.argv[1], sys.argv[2]
board = P.LoadBoard(pcb)
if mode == 'export':
    ok = P.ExportSpecctraDSN(board, sys.argv[3])
    print('dsn exported' if ok else 'DSN export FAILED')
else:
    ok = P.ImportSpecctraSES(board, sys.argv[3])
    print('ses imported' if ok else 'SES import FAILED')
    outline = [z for z in board.Zones() if z.GetLayer() == P.In1_Cu][0].Outline()
    gnd = board.FindNet('GND')
    have = {z.GetLayer() for z in board.Zones()}
    for layer in (P.F_Cu, P.B_Cu):
        if layer in have:
            continue
        z = P.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.Outline().AddOutline(outline.COutline(0))
        z.SetLocalClearance(P.FromMM(0.2))
        z.SetMinThickness(P.FromMM(0.15))
        z.SetPadConnection(P.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(P.FromMM(0.2))
        z.SetThermalReliefSpokeWidth(P.FromMM(0.25))
        z.SetIslandRemovalMode(P.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(z)
    filler = P.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(sys.argv[4])
    print('saved', sys.argv[4], len(board.GetTracks()), 'tracks/vias')
