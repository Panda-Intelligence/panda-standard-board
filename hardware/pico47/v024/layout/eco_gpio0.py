"""eco_gpio0.py in out fp_dir: FL_PWM moves from GPIO0 (U501 pin 5) to GPIO2 (pin 7); I2S_BCLK takes GPIO0.
R511 (boot pull-up) and TP19 stay on GPIO0, now I2S_BCLK. New R515 100k pulls FL_PWM down. All copper of the two
nets is removed here; the grid router lays both again (layout/spec_gpio0.json)."""
import sys, pcbnew as P
MM = P.FromMM
b = P.LoadBoard(sys.argv[1]); KEEP = []
for t in list(b.GetTracks()):
    if t.GetNetname() in ('FL_PWM', 'I2S_BCLK'): b.Remove(t); KEEP.append(t)
def setnet(ref, num, net):
    p = next(p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num); p.SetNet(b.FindNet(net))
setnet('U501', '5', 'I2S_BCLK'); setnet('U501', '7', 'FL_PWM'); setnet('R511', '2', 'I2S_BCLK'); setnet('TP19', '1', 'I2S_BCLK')
f = P.FootprintLoad(sys.argv[3], 'R_0402_1005Metric'); f.SetReference('R515'); f.SetValue('100k / FL_PWM_PD'); b.Add(f)
f.SetFPID(P.LIB_ID('Panda47v2', 'R_0402_1005Metric')); f.SetPosition(P.VECTOR2I(MM(35.8), MM(71.0))); f.SetOrientationDegrees(0)
for p in f.Pads(): p.SetNet(b.FindNet({'1': 'FL_PWM', '2': 'GND'}[p.GetNumber()]))
f.Reference().SetVisible(False); f.Value().SetVisible(False)
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
