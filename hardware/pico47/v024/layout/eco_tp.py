"""eco_tp.py in out fp_dir: three more back-side test pads, each centred on an existing via of its net.
TP5 FL_VOUT (1.5 mm), TP6 3V3_SD (1.0 mm), TPG2 GND (1.5 mm)."""
import sys, pcbnew as P
MM = P.FromMM
b = P.LoadBoard(sys.argv[1])
for ref, net, fpn, x, y, flip in (('TP5', 'FL_VOUT', 'TP11_Core', 34.84, 73.76, False), ('TP6', '3V3_SD', 'TP801_Display', 24.96, 101.3, True),
                                  ('TPG2', 'GND', 'TP11_Core', 23.41, 73.19, False)):
    vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == net
            and abs(P.ToMM(t.GetPosition().x) - x) < 0.01 and abs(P.ToMM(t.GetPosition().y) - y) < 0.01]
    assert len(vias) == 1, (ref, len(vias))
    f = P.FootprintLoad(sys.argv[3], fpn); f.SetReference(ref); f.SetValue(net); b.Add(f)
    f.SetPosition(vias[0].GetPosition())
    if flip: f.Flip(f.GetPosition(), P.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetFPID(P.LIB_ID('Panda47v2', fpn))
    for p in f.Pads(): p.SetNet(b.FindNet(net)); print(ref, net, [b.GetLayerName(l) for l in p.GetLayerSet().Seq()], P.ToMM(p.GetSize().x))
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
