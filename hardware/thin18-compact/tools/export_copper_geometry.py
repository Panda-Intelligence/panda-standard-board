#!/usr/bin/env python3
"""Export native KiCad copper geometry for a controlled routing search."""
import wx
APP = wx.App(False)
import pcbnew
from pathlib import Path
import hashlib, json, sys

pcb, output = map(Path, sys.argv[1:3])
b = pcbnew.LoadBoard(str(pcb))
layers = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
def xy(p): return [pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)]
def polygons(item, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(ps, layer, 0,
        pcbnew.FromMM(0.001), pcbnew.ERROR_OUTSIDE)
    return [[xy(ps.Outline(i).CPoint(j))
        for j in range(ps.Outline(i).PointCount())]
        for i in range(ps.OutlineCount())]
items = []
holes = []
for f in b.GetFootprints():
    for p in f.Pads():
        ls = [l for l in layers if p.IsOnLayer(l)]
        for l in ls:
            items.append({"type":"pad", "ref":f.GetReference(),
                "pad":p.GetNumber(), "net":p.GetNetname(),
                "layer":b.GetLayerName(l), "position":xy(p.GetPosition()),
                "polygons":polygons(p,l), "uuid":p.m_Uuid.AsString()})
        drill = p.GetDrillSize()
        if drill.x:
            holes.append({"position":xy(p.GetPosition()),
                "size":xy(drill), "ref":f.GetReference()})
for t in b.GetTracks():
    via = isinstance(t, pcbnew.PCB_VIA)
    ls = [l for l in layers if t.IsOnLayer(l)]
    for l in ls:
        row = {"type":"via" if via else "track", "net":t.GetNetname(),
            "layer":b.GetLayerName(l), "polygons":polygons(t,l),
            "uuid":t.m_Uuid.AsString()}
        if via: row["position"] = xy(t.GetPosition())
        else:
            row["start"],row["end"] = xy(t.GetStart()),xy(t.GetEnd())
        items.append(row)
    if via:
        holes.append({"position":xy(t.GetPosition()),
            "size":[pcbnew.ToMM(t.GetDrill())]*2})
edge = b.GetBoardEdgesBoundingBox()
result = {"pcb":str(pcb), "pcb_sha256":hashlib.sha256(pcb.read_bytes()).hexdigest(), "layers":[b.GetLayerName(l) for l in layers],
    "items":items, "holes":holes,
    "outline_bbox":[xy(edge.GetOrigin()),xy(edge.GetEnd())],
    "thickness_mm":pcbnew.ToMM(b.GetDesignSettings().GetBoardThickness())}
output.write_text(json.dumps(result))
print("geometry:",len(items),"items",len(holes),"holes",result["layers"])
