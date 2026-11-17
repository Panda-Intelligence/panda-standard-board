"""eco_sd.py in.kicad_pcb netlist_v027.json out.kicad_pcb fp_dir silk.json...: v0.2.6 -> v0.2.7 (KiCad Python).
- J501: XUNPU TF-122 (about 2.0 mm) -> Hanbo TF-019 (1.45 mm), both push-push, card mouth at the left edge.
  Land pattern from the Hanbo drawing (pattern frame: x across the card, y from the terminal tips towards the rear):
  terminals 1..8 at x = 4.82 + 1.10 n, 0.80 x 1.25; the body front is 1.25 mm in front of the terminal tips.
  Terminal 1 is on the left seen from above with the mouth up; that puts DAT2 at the larger board y, as on TF-122.
  The card centre keeps its board y (99.25). Body front at x = -0.36 (0.86 mm over the board edge), so no neighbour moves.
- C923: 1206 -> 0805 in place.
SD nets are laid again by the grid router (spec_sd.json); old ground stubs to the removed socket pads go."""
import json, math, sys, pcbnew as P
from ecolib import trk, via
from gndvia import gnd_via
MM, T = P.FromMM, P.ToMM
b = P.LoadBoard(sys.argv[1]); parts = json.load(open(sys.argv[2]))['parts']; LIB = sys.argv[4]; KEEP = []
STD = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Capacitor_SMD.pretty'

def fields(f, part):
    f.SetValue(part['value'])
    for k, v in part['fields'].items():
        if k not in ('Reference', 'Value'): f.SetField(k, str(v))

# ---- TF-019 footprint, origin at the body centre of the pattern frame (7.595, 6.975)
OX, OY = 7.595, 6.975
m = P.FOOTPRINT(b); m.SetFPID(P.LIB_ID('Panda47v2', 'TF_Hanbo_TF-019'))
m.SetLibDescription('Hanbo TF-019 microSD push-push socket, 1.45 mm; land pattern per the maker drawing (terminals at the card mouth)')
def smd(num, xp, yp, w, h):
    p = P.PAD(m); p.SetNumber(num); p.SetAttribute(P.PAD_ATTRIB_SMD); p.SetShape(P.F_Cu, P.PAD_SHAPE_RECT)
    p.SetSize(P.F_Cu, P.VECTOR2I(MM(w), MM(h))); p.SetPosition(P.VECTOR2I(MM(xp - OX), MM(yp - OY))); p.SetLayerSet(P.PAD.SMDMask()); m.Add(p)
for n in range(8): smd(str(n + 1), 4.82 + 1.10 * n, 0.625, 0.80, 1.25)
smd('9', 14.46, 3.25, 1.16, 1.25)                                   # detect
for xp, yp, w, h in ((0.575, 1.25, 1.15, 2.50), (0.575, 12.58, 1.15, 2.20), (14.865, 1.10, 1.15, 2.20), (14.46, 12.25, 1.16, 1.20),
                     (4.88, 13.375, 1.50, 1.15), (12.66, 13.375, 1.50, 1.15)):
    smd('SH', xp, yp, w, h)
for layer, box, w in ((P.F_Fab, (0.525, -1.25, 14.665, 12.55), 0.1), (P.F_CrtYd, (-0.25, -1.5, 15.69, 14.2), 0.05)):
    s = P.PCB_SHAPE(m); s.SetShape(P.SHAPE_T_RECT); s.SetLayer(layer); s.SetWidth(MM(w))
    s.SetStart(P.VECTOR2I(MM(box[0] - OX), MM(box[1] - OY))); s.SetEnd(P.VECTOR2I(MM(box[2] - OX), MM(box[3] - OY))); m.Add(s)
m.SetAttributes(P.FP_SMD); m.Reference().SetLayer(P.F_Fab); m.Value().SetLayer(P.F_Fab); m.Reference().SetVisible(False); m.Value().SetVisible(False)
lib = P.FOOTPRINT(m); lib.SetReference('REF**'); P.FootprintSave(LIB, lib)
P.FootprintSave(LIB, P.FootprintLoad(STD, 'C_0805_2012Metric'))

# ---- remove the old socket and the ground stubs that ended on its pads
old = b.FindFootprintByReference('J501'); oldpads = [p for p in old.Pads() if p.GetNetname() == 'GND']
n = 0
for t in list(b.GetTracks()):
    if t.GetClass() != 'PCB_VIA' and t.GetNetname() == 'GND' and t.GetLayer() == P.F_Cu and any(p.HitTest(e) for p in oldpads for e in (t.GetStart(), t.GetEnd())):
        b.Remove(t); KEEP.append(t); n += 1
for t in list(b.GetTracks()):               # the via of the old DET_A ground pad sits in the new switch keep-out
    if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND' and abs(T(t.GetPosition().x) - 10.88) < 0.03 and abs(T(t.GetPosition().y) - 92.47) < 0.03:
        b.Remove(t); KEEP.append(t); n += 1
b.Remove(old); KEEP.append(old); print('old socket removed with', n, 'ground stubs / vias')

X0, Y0 = -0.36 + 1.25 + OY, 99.25 + (7.955 - OX)
m.SetReference('J501'); b.Add(m); m.SetPosition(P.VECTOR2I(MM(X0), MM(Y0))); m.SetOrientationDegrees(90); fields(m, parts['J501'])
for p in m.Pads(): p.SetNet(b.FindNet(parts['J501']['pins'][p.GetNumber()]))
pp = {p.GetNumber(): (round(T(p.GetPosition().x), 3), round(T(p.GetPosition().y), 3)) for p in m.Pads() if p.GetNumber() != 'SH'}
print('J501 at', (round(X0, 3), round(Y0, 3)), pp)
assert pp['1'][1] > pp['8'][1] and all(0.8 < v[0] < 2.3 for k, v in pp.items() if k != '9'), 'terminal 1 must be at the larger y, terminals at the mouth'
# copper keep-outs of the drawing: pattern-prohibited area under the body and the switch keep-out
def keepout(x0p, y0p, x1p, y1p, name):
    z = P.ZONE(b); z.SetIsRuleArea(True); z.SetLayer(P.F_Cu); z.SetZoneName(name)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    o = z.Outline(); o.NewOutline()
    for xp, yp in ((x0p, y0p), (x1p, y0p), (x1p, y1p), (x0p, y1p)): o.Append(MM(X0 + (yp - OY)), MM(Y0 - (xp - OX)))
    b.Add(z)
keepout(4.08, 6.25, 13.30, 9.65, 'J501 pattern-prohibited area'); keepout(14.95, 8.75, 15.45, 11.15, 'J501 switch keep-out')

# Old SD copper inside the socket area goes now (the router lays these nets again), so that the ground vias of
# terminal 6 (VSS, between two signal terminals) and of the shell pad at the detect corner can be placed first.
SDN = {'SD_D0', 'SD_D1', 'SD_D2', 'SD_D3', 'SD_CMD', 'SD_CLK', 'SD_CD', '3V3_SD'}
n = 0
for t in list(b.GetTracks()):
    if t.GetNetname() not in SDN: continue
    pts = [t.GetPosition()] if t.GetClass() == 'PCB_VIA' else [t.GetStart(), t.GetEnd()]
    if (t.GetClass() == 'PCB_VIA' or t.GetLayer() == P.F_Cu) and any(-1.0 <= T(q.x) <= 15.1 and 91.5 <= T(q.y) <= 107.5 for q in pts):
        b.Remove(t); KEEP.append(t); n += 1
print('old SD copper removed in the socket area:', n)
P.ZONE_FILLER(b).Fill(b.Zones())
for p in m.Pads():
    x, y = T(p.GetPosition().x), T(p.GetPosition().y)
    if p.GetNumber() == '6': gnd_via(b, x, y, w=0.3, rmax=3.0, rmin=1.1)
    elif p.GetNumber() == 'SH' and abs(x - 13.14) < 0.05 and abs(y - 92.745) < 0.05: gnd_via(b, x, y, w=0.3, rmax=3.0, rmin=1.0)

# ---- C923 in place
part = parts['C923']; old = b.FindFootprintByReference('C923'); pos, rot = old.GetPosition(), old.GetOrientationDegrees()
opad = {p.GetNumber(): p for p in old.Pads()}; hits = []
for t in b.GetTracks():
    for num, pad in opad.items():
        if t.GetNetname() != pad.GetNetname(): continue
        if t.GetClass() == 'PCB_VIA':
            if pad.HitTest(t.GetPosition()): hits.append((num, t.GetPosition(), MM(0.4)))
        elif t.GetLayer() == P.F_Cu: hits += [(num, e, t.GetWidth()) for e in (t.GetStart(), t.GetEnd()) if pad.HitTest(e)]
b.Remove(old); KEEP.append(old)
f = P.FootprintLoad(LIB, part['footprint']); f.SetReference('C923'); b.Add(f); f.SetFPID(P.LIB_ID('Panda47v2', part['footprint']))
pos = P.VECTOR2I(pos.x - MM(0.2), pos.y)     # 0.2 mm left: the 0805 pad is wider across than the 1206 one, I2C_SDA runs on the right
f.SetPosition(pos); f.SetOrientationDegrees(rot); f.Reference().SetVisible(False); f.Value().SetVisible(False); fields(f, part)
new = {}
for p in f.Pads(): p.SetNet(b.FindNet(part['pins'][p.GetNumber()])); new[p.GetNumber()] = p
links = 0
for num, e, w in hits:                      # copper that sat on the longer 1206 pad: link it to the 0805 pad
    if not new[num].HitTest(e):
        c = new[num].GetPosition(); trk(b, new[num].GetNetname(), 'F.Cu', T(w), [(T(e.x), T(e.y)), (T(c.x), T(c.y))]); links += 1
print('C923', {k: (round(T(p.GetPosition().x), 3), round(T(p.GetPosition().y), 3)) for k, p in new.items()}, 'copper ends', len(hits), 'links added', links)

texts = {t['text'] for a in sys.argv[5:] for t in json.load(open(a))['texts']}
for d in list(b.GetDrawings()):
    if d.GetClass() == 'PCB_TEXT' and d.GetText() in texts: b.Remove(d); KEEP.append(d)
tb = b.GetTitleBlock(); tb.SetRevision('v0.2.7 / E11'); tb.SetDate('2026-11-17')
tb.SetComment(0, '63 x 48 mm, 4-layer 0.8 mm; v0.2.6 with a 1.45 mm microSD socket and an 0805 front-light capacitor')
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[3])
