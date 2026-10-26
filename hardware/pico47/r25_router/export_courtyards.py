"""Export footprint courtyards (F/B), positions, rotations and pad offsets. Run with KiCad python.
usage: export_courtyards.py board.kicad_pcb out.json"""
import json, sys
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
MM = 1e-6
out = {}
for fp in b.GetFootprints():
    polys = {}
    for side, L in (('F', pcbnew.F_CrtYd), ('B', pcbnew.B_CrtYd)):
        sp = fp.GetCourtyard(L)
        res = []
        for i in range(sp.OutlineCount()):
            o = sp.Outline(i)
            res.append([[o.CPoint(j).x * MM, o.CPoint(j).y * MM] for j in range(o.PointCount())])
        if res:
            polys[side] = res
    p = fp.GetPosition()
    out[fp.GetReference()] = dict(x=p.x * MM, y=p.y * MM, rot=fp.GetOrientationDegrees(), side='B' if fp.IsFlipped() else 'F',
                                  courtyard=polys, value=fp.GetValue(),
                                  pads=[dict(num=pd.GetNumber(), net=pd.GetNetname(), dx=(pd.GetPosition().x - p.x) * MM,
                                             dy=(pd.GetPosition().y - p.y) * MM) for pd in fp.Pads()])
json.dump(out, open(sys.argv[2], 'w'))
print(len(out), 'footprints;', sum(1 for v in out.values() if v['courtyard']), 'with courtyards')
