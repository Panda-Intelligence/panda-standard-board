"""eco_mount.py in out fp_dir: board fixing and locating features (user, 2026-11-14).
- H1 (23.6, 112.9) left of USB-C, H2 (28.0, 70.0), H3 (57.1, 69.9): SMT nuts M1.6, plated 2.5 mm hole, 4.2 mm GND pad.
- MH1: 1.2 mm NPTH datum hole at (26.6, 107.3), 6 mm from the USB-C centre line. MH2: 1.2 x 1.6 mm NPTH slot at
  (62.3, 111.0), long axis towards MH1. Shell pins of 1.1 mm go through them.
- D203 and R208 move 1.0 mm left to clear H1 (the LED light hole in the shell moves with them); the 3V3_AON trunk
  goes round H1; FID3 moves to (54.3, 101.6). R208 is turned 180 deg. CHG_STAT is re-laid by the grid router afterwards
  (layout/spec_mount.json)."""
import sys, math, pcbnew as P
from ecolib import remove, trk, via, move
MM, T = P.FromMM, P.ToMM
b = P.LoadBoard(sys.argv[1]); LIBDIR = sys.argv[3]

def circle(fp, layer, r, w=0.1):
    s = P.PCB_SHAPE(fp); s.SetShape(P.SHAPE_T_CIRCLE); s.SetLayer(layer); s.SetWidth(MM(w))
    s.SetStart(P.VECTOR2I(0, 0)); s.SetEnd(P.VECTOR2I(MM(r), 0)); fp.Add(s)

def make(name, descr):
    fp = P.FOOTPRINT(b); fp.SetFPID(P.LIB_ID('Panda47v2', name)); fp.SetLibDescription(descr)
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False); fp.Reference().SetLayer(P.F_Fab); fp.Value().SetLayer(P.F_Fab)
    return fp

def pad(fp, num, attr, shape, size, drill, layers):
    p = P.PAD(fp); p.SetNumber(num); p.SetAttribute(attr); p.SetShape(P.F_Cu, shape)
    p.SetSize(P.F_Cu, P.VECTOR2I(MM(size[0]), MM(size[1]))); p.SetDrillSize(P.VECTOR2I(MM(drill[0]), MM(drill[1])))
    if drill[0] != drill[1]: p.SetDrillShape(P.PAD_DRILL_SHAPE_OBLONG)
    p.SetLayerSet(layers); fp.Add(p); return p

def nut(ref, x, y):
    fp = make('SMTSO_M1.6_L1', 'Reflow nut M1.6 x 1.0, 3.18 hex, hole 2.5 plated, pad 4.2 (Sinhoo SMTSO1610MTJ)')
    p = pad(fp, '1', P.PAD_ATTRIB_PTH, P.PAD_SHAPE_CIRCLE, (4.2, 4.2), (2.5, 2.5), P.PAD.PTHMask())
    p.SetLocalZoneConnection(P.ZONE_CONNECTION_FULL)
    circle(fp, P.F_Fab, 1.83); circle(fp, P.F_CrtYd, 2.0, 0.05)
    fp.SetAttributes(P.FP_SMD); fp.SetReference(ref); fp.SetValue('M1.6 SMT nut'); b.Add(fp)
    fp.SetPosition(P.VECTOR2I(MM(x), MM(y))); p.SetNet(b.FindNet('GND')); return fp

def hole(ref, name, x, y, drill, rot=0.0):
    fp = make(name, 'Board locating hole, non-plated, for a 1.1 mm shell pin')
    pad(fp, '', P.PAD_ATTRIB_NPTH, P.PAD_SHAPE_OVAL if drill[0] != drill[1] else P.PAD_SHAPE_CIRCLE, drill, drill, P.PAD.UnplatedHoleMask())
    fp.SetAttributes(P.FP_BOARD_ONLY | P.FP_EXCLUDE_FROM_POS_FILES | P.FP_EXCLUDE_FROM_BOM)
    fp.SetReference(ref); fp.SetValue('Locating hole'); b.Add(fp)
    fp.SetPosition(P.VECTOR2I(MM(x), MM(y))); fp.SetOrientationDegrees(rot); return fp

# 1. clear the H1 spot
V, A = 'VSYS_RAW', '3V3_AON'
remove(b, [(V, (20.59, 112.9), (20.59, 112.325)), (V, (20.59, 112.325), (20.773, 112.142)),
           ('CHG_STAT', (20.161, 113.897), (20.1, 113.958)), ('CHG_STAT', (20.1, 114.5), (20.1, 113.958)), ('CHG_STAT', (20.877, 113.897), (20.161, 113.897)),
           ('CHG_LED_A', (21.61, 113.668), (21.61, 112.9)), ('CHG_LED_A', (21.9, 114.5), (21.9, 113.958)), ('CHG_LED_A', (21.9, 113.958), (21.61, 113.668)),
           (A, (22.297, 111.378), (24.45, 109.225)), (A, (20.162, 111.378), (22.297, 111.378))])
move(b, 'D203', 20.0, 114.5); move(b, 'R208', 20.45, 112.9, 180)
trk(b, V, 'F.Cu', 0.4, [(20.96, 112.9), (20.773, 112.55), (20.773, 112.142)])
trk(b, 'CHG_LED_A', 'F.Cu', 0.127, [(19.94, 112.9), (19.94, 113.5), (20.9, 114.46), (20.9, 114.5)])
trk(b, A, 'F.Cu', 0.6, [(20.162, 111.378), (21.24, 110.3), (23.375, 110.3), (24.45, 109.225)])
# 2. FID3 and its keep-out zone
f3 = b.FindFootprintByReference('FID3'); old = f3.GetPosition(); new = P.VECTOR2I(MM(54.3), MM(101.6)); f3.SetPosition(new)
for z in b.Zones():
    if z.GetZoneName().startswith('FID3'): z.Move(P.VECTOR2I(new.x - old.x, new.y - old.y))
# 3. nuts and locating holes
for ref, x, y in (('H1', 23.6, 112.9), ('H2', 28.0, 70.0), ('H3', 57.1, 69.9)): nut(ref, x, y)   # H1 is removed again by eco_two_screws.py
hole('MH1', 'LocHole_NPTH_1.2', 26.6, 107.3, (1.2, 1.2))
ang = math.degrees(math.atan2(111.0 - 107.3, 62.3 - 26.6))
hole('MH2', 'LocSlot_NPTH_1.2x1.6', 62.3, 111.0, (1.6, 1.2), -ang)
for name in ('SMTSO_M1.6_L1', 'LocHole_NPTH_1.2', 'LocSlot_NPTH_1.2x1.6'):
    src = next(f for f in b.GetFootprints() if f.GetFPID().GetUniStringLibItemName() == name)
    c = P.FOOTPRINT(src); c.SetParent(None); c.SetPosition(P.VECTOR2I(0, 0)); c.SetOrientationDegrees(0); c.SetReference('REF**')
    P.FootprintSave(LIBDIR, c)
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2])
