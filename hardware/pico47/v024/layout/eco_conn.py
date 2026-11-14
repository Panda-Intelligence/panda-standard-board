"""eco_conn.py in out fp_dir: connectors instead of hand-soldered wires (user, 2026-11-14).
- J302: JST BM03B-ACHSS at (33.6, 70.05), turned 180 deg, at the top edge next to the cell. 1 = B+, 2 = B-, 3 = NTC.
  B+ goes through two vias to a 0.8 mm B.Cu track that joins the existing BAT_CONN_P trunk at (39.11, 73.39).
- J507: MHF4 receptacle (Kinghelm KH-IPEX4-2020, land pattern from its drawing 113-0000-007), signal pad towards C531.
- R515 moves to (39.0, 69.0). FL_PWM and the local part of BQ_TS are laid again by the grid router
  (layout/spec_conn.json)."""
import sys, pcbnew as P
from ecolib import remove, trk, via, move
MM, T = P.FromMM, P.ToMM
b = P.LoadBoard(sys.argv[1]); LIBDIR = sys.argv[3]; KEEP = []
for ref in ('J302', 'J507'):
    f = b.FindFootprintByReference(ref); b.Remove(f); KEEP.append(f)
for t in list(b.GetTracks()):
    if t.GetNetname() == 'FL_PWM': b.Remove(t); KEEP.append(t)
remove(b, [('BAT_CONN_P', (54.0, 78.8), (54.0, 76.7)), ('BAT_CONN_P', (54.0, 76.7), (55.0, 75.7)), ('BAT_CONN_P', (55.0, 75.7), (55.337, 75.0)),
           ('BQ_TS', (50.0, 78.8), (49.16, 78.8)), ('BQ_TS', (50.0, 78.8), (50.0, 77.61)), ('BQ_TS', (49.5, 77.61), (50.0, 77.61)),
           ('RF_ANT', (36.32, 90.35), (34.3, 90.35))])
# the old landing pad joined two BQ_TS tracks: link them directly
trk(b, 'BQ_TS', 'F.Cu', 0.127, [(49.16, 78.8), (49.5, 78.46), (49.5, 77.61)])
t = P.PCB_TRACK(b); t.SetNet(b.FindNet('RF_ANT')); t.SetLayer(P.F_Cu); t.SetWidth(MM(0.17)); t.SetLocked(True)
t.SetStart(P.VECTOR2I(MM(36.32), MM(90.35))); t.SetEnd(P.VECTOR2I(MM(35.72), MM(90.95))); b.Add(t)
t2 = P.PCB_TRACK(b); t2.SetNet(b.FindNet('RF_ANT')); t2.SetLayer(P.F_Cu); t2.SetWidth(MM(0.17)); t2.SetLocked(True)
t2.SetStart(P.VECTOR2I(MM(35.72), MM(90.95))); t2.SetEnd(P.VECTOR2I(MM(35.3), MM(90.95))); b.Add(t2)
# battery header
j = P.FootprintLoad(LIBDIR, 'JST_ACH_BM03B-ACHSS-GAN-ETF_1x03-1MP_P1.20mm_Vertical'); j.SetReference('J302'); j.SetValue('BM03B-ACHSS / pack'); b.Add(j)
j.SetFPID(P.LIB_ID('Panda47v2', 'JST_ACH_BM03B-ACHSS-GAN-ETF_1x03-1MP_P1.20mm_Vertical'))
# courtyard: 0.25 mm beyond the pads in y (library copy: 0.5 mm), so the header fits between the board edge and D905
for g in list(j.GraphicalItems()):
    if g.GetLayer() in (P.F_CrtYd, P.F_SilkS): j.Remove(g); KEEP.append(g)   # no silk outline: it would touch D905's
c = P.PCB_SHAPE(j); c.SetShape(P.SHAPE_T_RECT); c.SetLayer(P.F_CrtYd); c.SetWidth(MM(0.05))
c.SetStart(P.VECTOR2I(MM(-3.25), MM(-2.55))); c.SetEnd(P.VECTOR2I(MM(3.25), MM(2.55))); j.Add(c)
jl = P.FOOTPRINT(j); jl.SetReference('REF**'); P.FootprintSave(LIBDIR, jl)
j.SetPosition(P.VECTOR2I(MM(33.6), MM(70.05))); j.SetOrientationDegrees(180)
for p in j.Pads(): p.SetNet(b.FindNet({'1': 'BAT_CONN_P', '2': 'GND', '3': 'BQ_TS', 'MP': 'GND'}[p.GetNumber()]))
j.Reference().SetVisible(False); j.Value().SetVisible(False)
# MHF4 receptacle: signal pad 0.60 x 0.55 at the edge, two side ground pads 0.50 x 1.58, one end ground pad 0.50 x 0.50
m = P.FOOTPRINT(b); m.SetFPID(P.LIB_ID('Panda47v2', 'MHF4_KH-IPEX4-2020'))
m.SetLibDescription('MHF4 receptacle 2.0 x 2.0 x 0.6 mm, Kinghelm KH-IPEX4-2020, land pattern per drawing 113-0000-007')
def smd(num, x, y, w, h):
    p = P.PAD(m); p.SetNumber(num); p.SetAttribute(P.PAD_ATTRIB_SMD); p.SetShape(P.F_Cu, P.PAD_SHAPE_RECT)
    p.SetSize(P.F_Cu, P.VECTOR2I(MM(w), MM(h))); p.SetPosition(P.VECTOR2I(MM(x), MM(y))); p.SetLayerSet(P.PAD.SMDMask()); m.Add(p)
smd('1', 0.0, -0.975, 0.60, 0.55); smd('2', -1.0, 0.0, 0.50, 1.58); smd('2', 1.0, 0.0, 0.50, 1.58); smd('2', 0.0, 1.0, 0.50, 0.50)
for layer, hw, w in ((P.F_Fab, 1.0, 0.1), (P.F_CrtYd, 1.3, 0.05)):
    s = P.PCB_SHAPE(m); s.SetShape(P.SHAPE_T_RECT); s.SetLayer(layer); s.SetWidth(MM(w))
    s.SetStart(P.VECTOR2I(MM(-hw), MM(-hw))); s.SetEnd(P.VECTOR2I(MM(hw), MM(hw))); m.Add(s)
m.SetAttributes(P.FP_SMD); m.Reference().SetVisible(False); m.Value().SetVisible(False); m.Reference().SetLayer(P.F_Fab); m.Value().SetLayer(P.F_Fab)
lib = P.FOOTPRINT(m); lib.SetReference('REF**'); P.FootprintSave(LIBDIR, lib)
m.SetReference('J507'); m.SetValue('MHF4 receptacle'); b.Add(m)
m.SetPosition(P.VECTOR2I(MM(34.3), MM(90.95))); m.SetOrientationDegrees(270)
for p in m.Pads(): p.SetNet(b.FindNet({'1': 'RF_ANT', '2': 'GND'}[p.GetNumber()]))
for p in m.Pads():
    if p.GetNumber() == '2': p.SetLocalZoneConnection(P.ZONE_CONNECTION_FULL)   # ground pads solid in the pour
for ref in ('J302', 'J507'):
    for p in b.FindFootprintByReference(ref).Pads(): print(ref, p.GetNumber(), p.GetNetname(), round(T(p.GetPosition().x), 3), round(T(p.GetPosition().y), 3))
# copper
move(b, 'R515', 39.0, 69.0)
trk(b, 'BAT_CONN_P', 'F.Cu', 0.6, [(34.8, 71.925), (35.7, 71.925), (36.6, 71.925)])
via(b, 'BAT_CONN_P', 35.7, 71.925, 0.6, 0.3); via(b, 'BAT_CONN_P', 36.6, 71.925, 0.6, 0.3)
remove(b, [('BAT_CONN_P', (42.243, 73.389), (39.11, 73.39))])
trk(b, 'BAT_CONN_P', 'B.Cu', 0.8, [(35.7, 71.925), (36.6, 71.925), (38.065, 73.39), (42.243, 73.389)])
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
