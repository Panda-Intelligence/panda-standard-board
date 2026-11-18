"""eco_cost.py in.kicad_pcb netlist_v026.json out.kicad_pcb fp_dir old_silk.json new_silk.json: v0.2.5 -> v0.2.6 (KiCad Python).
Smaller footprints in place for C207 / C208 / C525 (0805 -> 0603) and C203 (1206 -> 0805): same position and
rotation, same pad nets. Every track end and via that sat on an old pad must still sit on the new pad of that net,
otherwise the script stops. Old printed texts are dropped (info_silk_v02x.py prints the new set) and the title block set."""
import json, sys, pcbnew as P
MM, T = P.FromMM, P.ToMM
b = P.LoadBoard(sys.argv[1]); parts = json.load(open(sys.argv[2]))['parts']; LIB = sys.argv[4]; KEEP = []
STD = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Capacitor_SMD.pretty'
P.FootprintSave(LIB, P.FootprintLoad(STD, 'C_0805_2012Metric'))
for ref in ('C207', 'C208', 'C525', 'C203'):
    part = parts[ref]; old = b.FindFootprintByReference(ref)
    pos, rot = old.GetPosition(), old.GetOrientationDegrees()
    if ref in ('C207', 'C208'):                  # 0603 pads sit 0.025 mm further out: keep the ground pad where it was (3V3 track below)
        pos = P.VECTOR2I(pos.x, pos.y - MM(0.025))
    oldpads = {p.GetNumber(): (p.GetPosition(), p.GetNetname(), p) for p in old.Pads()}
    hits = []                                    # copper that relied on the old pads
    for t in b.GetTracks():
        for num, (pp, net, pad) in oldpads.items():
            if t.GetNetname() != net: continue
            if t.GetClass() == 'PCB_VIA':
                if pad.HitTest(t.GetPosition()): hits.append((num, t.GetPosition()))
            elif t.GetLayer() == P.F_Cu:
                hits += [(num, e) for e in (t.GetStart(), t.GetEnd()) if pad.HitTest(e)]
    b.Remove(old); KEEP.append(old)
    f = P.FootprintLoad(LIB, part['footprint']); f.SetReference(ref); b.Add(f)
    f.SetFPID(P.LIB_ID('Panda47v2', part['footprint'])); f.SetPosition(pos); f.SetOrientationDegrees(rot)
    f.Reference().SetVisible(False); f.Value().SetVisible(False); f.SetValue(part['value'])
    for k, v in part['fields'].items():
        if k not in ('Reference', 'Value'): f.SetField(k, str(v))
    new = {}
    for p in f.Pads():
        p.SetNet(b.FindNet(part['pins'][p.GetNumber()])); new[p.GetNumber()] = p
        op = oldpads[p.GetNumber()][0]
        assert abs(T(p.GetPosition().x - op.x)) < 0.5 and abs(T(p.GetPosition().y - op.y)) < 0.5, (ref, p.GetNumber(), 'pad moved to the other side')
    lost = [(num, T(e.x), T(e.y)) for num, e in hits if not new[num].HitTest(e)]
    assert not lost, (ref, 'copper no longer on the pad', lost)
    print(ref, part['footprint'], 'pads', {n: (round(T(p.GetPosition().x), 3), round(T(p.GetPosition().y), 3)) for n, p in new.items()}, 'copper ends kept', len(hits))
for ref in ('H2', 'H3'):
    f = b.FindFootprintByReference(ref)
    for k, v in parts[ref]['fields'].items():
        if k not in ('Reference', 'Value'): f.SetField(k, str(v))
texts = {t['text'] for a in sys.argv[5:7] for t in json.load(open(a))['texts']} | {'Main board v0.2.5 / E09'}
for d in list(b.GetDrawings()):
    if d.GetClass() == 'PCB_TEXT' and d.GetText() in texts: b.Remove(d); KEEP.append(d)
tb = b.GetTitleBlock(); tb.SetRevision('v0.2.6 / E10'); tb.SetDate('2026-11-17')
tb.SetComment(0, '63 x 48 mm, 4-layer 0.8 mm; v0.2.5 with smaller capacitors and 1.0 mm nuts')
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[3])
