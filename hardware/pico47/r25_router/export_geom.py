"""Export Core copper geometry (pads, tracks, vias, holes, outline) to JSON. Run with KiCad python."""
import json, sys
import pcbnew

src, out = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(src)
MM = 1e-6
names = {l: b.GetLayerName(l) for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)}


def poly_of(shape_poly):
    res = []
    for i in range(shape_poly.OutlineCount()):
        o = shape_poly.Outline(i)
        res.append([[o.CPoint(j).x * MM, o.CPoint(j).y * MM] for j in range(o.PointCount())])
    return res


pads = []
for fp in b.GetFootprints():
    for p in fp.Pads():
        layers = [names[l] for l in names if p.IsOnLayer(l)]
        polys = {}
        for l in names:
            if not p.IsOnLayer(l) or not p.FlashLayer(l):
                continue
            sp = pcbnew.SHAPE_POLY_SET()
            p.TransformShapeToPolygon(sp, l, 0, 2000, pcbnew.ERROR_INSIDE)
            polys[names[l]] = poly_of(sp)
        drill = None
        if p.HasHole():
            ds = p.GetDrillSize()
            drill = [ds.x * MM, ds.y * MM]
        pads.append(dict(ref=fp.GetReference(), num=p.GetNumber(), net=p.GetNetname(),
                         x=p.GetPosition().x * MM, y=p.GetPosition().y * MM,
                         layers=layers, polys=polys, drill=drill,
                         attr=int(p.GetAttribute()), uuid=p.m_Uuid.AsString()))
tracks, vias = [], []
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        vias.append(dict(x=t.GetPosition().x * MM, y=t.GetPosition().y * MM,
                         d=t.GetWidth(pcbnew.F_Cu) * MM, drill=t.GetDrill() * MM,
                         net=t.GetNetname(), uuid=t.m_Uuid.AsString()))
    elif t.GetClass() == 'PCB_TRACK':
        tracks.append(dict(x1=t.GetStart().x * MM, y1=t.GetStart().y * MM,
                           x2=t.GetEnd().x * MM, y2=t.GetEnd().y * MM, w=t.GetWidth() * MM,
                           layer=b.GetLayerName(t.GetLayer()), net=t.GetNetname(),
                           uuid=t.m_Uuid.AsString()))
    else:
        raise SystemExit('unsupported track item ' + t.GetClass())
outline = pcbnew.SHAPE_POLY_SET()
b.GetBoardPolygonOutlines(outline, False)
zones = []
all_zones = list(b.Zones()) + [z for fp in b.GetFootprints() for z in fp.Zones()]
for z in all_zones:
    zones.append(dict(net=z.GetNetname(), rule=bool(z.GetIsRuleArea()),
                      layers=[b.GetLayerName(l) for l in z.GetLayerSet().Seq()],
                      outline=poly_of(z.Outline()),
                      no_tracks=bool(z.GetIsRuleArea() and z.GetDoNotAllowTracks()),
                      no_vias=bool(z.GetIsRuleArea() and z.GetDoNotAllowVias())))
json.dump(dict(pads=pads, tracks=tracks, vias=vias, outline=poly_of(outline), zones=zones),
          open(out, 'w'))
print(len(pads), len(tracks), len(vias), len(zones))
