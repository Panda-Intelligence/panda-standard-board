"""Dump parts and pad nets of a KiCad board to JSON (KiCad Python): input of make_netlist_v020.py.

usage: dump_pcb_v020.py board.kicad_pcb out.json   (run on v0.1.3 and v0.1.2 Single.kicad_pcb)
"""
import pcbnew, json, sys, collections
b = pcbnew.LoadBoard(sys.argv[1])
comps, nets = {}, collections.defaultdict(list)
for fp in b.GetFootprints():
    ref = fp.GetReference()
    flds = {f.GetName(): f.GetText() for f in fp.GetFields()}
    pos = fp.GetPosition()
    bb = fp.GetCourtyard(pcbnew.F_Cu if not fp.IsFlipped() else pcbnew.B_Cu).BBox() if hasattr(fp,'GetCourtyard') else None
    comps[ref] = dict(value=fp.GetValue(), fpid=str(fp.GetFPID().GetLibItemName()), x=pos.x/1e6, y=pos.y/1e6,
                      rot=fp.GetOrientationDegrees(), side='B' if fp.IsFlipped() else 'F', fields=flds,
                      dnp=fp.IsDNP(), pads=len(fp.Pads()),
                      cy=[bb.GetX()/1e6, bb.GetY()/1e6, bb.GetWidth()/1e6, bb.GetHeight()/1e6] if bb else None)
    for p in fp.Pads():
        n = p.GetNetname()
        if n: nets[n].append((ref, p.GetNumber()))
json.dump(dict(comps=comps, nets=nets), open(sys.argv[2], 'w'), indent=0)
print(len(comps), 'comps', len(nets), 'nets')
