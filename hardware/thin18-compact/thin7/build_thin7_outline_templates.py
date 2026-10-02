#!/usr/bin/env python3
"""Build two EMPTY KiCad mechanical templates. Never fabricate these templates."""
import json
from pathlib import Path
import wx
APP=wx.App(False)
import pcbnew
ROOT=Path(__file__).resolve().parent
c=json.loads((ROOT/'thin7-mechanical-contract.json').read_text())
def point(xy): return pcbnew.VECTOR2I(pcbnew.FromMM(xy[0]),pcbnew.FromMM(xy[1]))
for name,data in c['boards'].items():
    board=pcbnew.BOARD()
    board.SetCopperLayerCount(data['copper_layers'])
    board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(data['thickness_mm']))
    pts=data['outline_xy_mm']
    for i,a in enumerate(pts):
        seg=pcbnew.PCB_SHAPE(board);seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(point(a));seg.SetEnd(point(pts[(i+1)%len(pts)]))
        seg.SetLayer(pcbnew.Edge_Cuts);seg.SetWidth(pcbnew.FromMM(.1));board.Add(seg)
    for text,xy in [(name+' / MECHANICAL OUTLINE ONLY',[min(x for x,y in pts)+1,max(y for x,y in pts)-3]),('NO COMPONENTS OR COPPER / DO NOT FABRICATE',[min(x for x,y in pts)+1,max(y for x,y in pts)-1.5])]:
        t=pcbnew.PCB_TEXT(board);t.SetText(text);t.SetPosition(point(xy))
        t.SetLayer(pcbnew.Dwgs_User);t.SetTextSize(point([.8,.8]));t.SetTextThickness(pcbnew.FromMM(.12))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT);board.Add(t)
    dest=ROOT/(name+'-OUTLINE-ONLY.kicad_pcb')
    pcbnew.SaveBoard(str(dest),board)
    reopened=pcbnew.LoadBoard(str(dest))
    if len(list(reopened.GetFootprints())) or len(list(reopened.GetTracks())) or reopened.GetAreaCount():
        raise ValueError('Outline template unexpectedly contains electrical content')
    print(name,'empty template saved; copper layers',reopened.GetCopperLayerCount(),'thickness',pcbnew.ToMM(reopened.GetDesignSettings().GetBoardThickness()))
