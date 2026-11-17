"""eco_flush.py in.kicad_pcb netlist_v028.json out.kicad_pcb fp_dir silk.json...: v0.2.6 -> v0.2.8 (KiCad Python).
Hanbo TF-019 (1.45 mm push-push) for J501 with the body front at x = 1.30: a latched card (2.40 mm in front of the
body) ends at x = -1.10, 0.4 mm inside the 67 mm body outline (x = -1.5). Card centre line unchanged (y 99.25).
Land pattern, pin order and keep-outs as in v027/eco_sd.py; the courtyard follows the body and the rear pads.
The parts behind the socket make room:
- R524 0.15 mm up, TH801 0.45 mm up, C806 0.8 mm down, R809 0.2 mm down;
- Q901 + Q902 (two SOT-23) become one dual MOSFET Q901 (SOT-363) at the old Q902 place;
- C513 moves to the strip below the socket.
Copper on the pads of moved parts is removed; their nets and the SD nets are laid by the grid router (spec_flush.json).
C923 becomes 0805 as in v0.2.7."""
import json, math, sys, pcbnew as P
from ecolib import trk, via
from gndvia import gnd_via
MM, T = P.FromMM, P.ToMM
b = P.LoadBoard(sys.argv[1]); parts = json.load(open(sys.argv[2]))['parts']; LIB = sys.argv[4]; KEEP = []
STD = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/'
P.FootprintSave(LIB, P.FootprintLoad(STD + 'Capacitor_SMD.pretty', 'C_0805_2012Metric'))
P.FootprintSave(LIB, P.FootprintLoad(STD + 'Package_TO_SOT_SMD.pretty', 'SOT-363_SC-70-6'))

def fields(f, part):
    f.SetValue(part['value'])
    for k, v in part['fields'].items():
        if k not in ('Reference', 'Value'): f.SetField(k, str(v))
def setnets(f, part):
    for p in f.Pads():
        n = part['pins'].get(p.GetNumber(), '')
        p.SetNet(b.FindNet(n)) if n else p.SetNetCode(0)
def strip(ref):
    """remove front-layer track segments that end on the pads of ref, and vias in those pads"""
    f = b.FindFootprintByReference(ref); n = 0
    for t in list(b.GetTracks()):
        for p in f.Pads():
            if t.GetNetname() != p.GetNetname() or not p.GetNetname(): continue
            hit = p.HitTest(t.GetPosition()) if t.GetClass() == 'PCB_VIA' else (t.GetLayer() == P.F_Cu and (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd())))
            if hit: b.Remove(t); KEEP.append(t); n += 1; break
    return f, n
def add(ref, fp, x, y, rot):
    f = P.FootprintLoad(LIB, fp); f.SetReference(ref); b.Add(f); f.SetFPID(P.LIB_ID('Panda47v2', fp))
    f.SetPosition(P.VECTOR2I(MM(x), MM(y))); f.SetOrientationDegrees(rot); f.Reference().SetVisible(False); f.Value().SetVisible(False)
    fields(f, parts[ref]); setnets(f, parts[ref]); return f

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
g = P.PCB_SHAPE(m); g.SetShape(P.SHAPE_T_RECT); g.SetLayer(P.F_Fab); g.SetWidth(MM(0.1))
g.SetStart(P.VECTOR2I(MM(0.525 - OX), MM(-1.25 - OY))); g.SetEnd(P.VECTOR2I(MM(14.665 - OX), MM(12.55 - OY))); m.Add(g)
CY = [(-0.25, -1.5), (15.69, -1.5), (15.69, 12.8), (13.66, 12.8), (13.66, 14.2), (11.66, 14.2), (11.66, 12.8), (5.88, 12.8), (5.88, 14.2),
      (3.88, 14.2), (3.88, 12.8), (1.4, 12.8), (1.4, 13.93), (-0.25, 13.93)]      # body and side pads, then the rear pads only
for (x1, y1), (x2, y2) in zip(CY, CY[1:] + CY[:1]):
    g = P.PCB_SHAPE(m); g.SetShape(P.SHAPE_T_SEGMENT); g.SetLayer(P.F_CrtYd); g.SetWidth(MM(0.05))
    g.SetStart(P.VECTOR2I(MM(x1 - OX), MM(y1 - OY))); g.SetEnd(P.VECTOR2I(MM(x2 - OX), MM(y2 - OY))); m.Add(g)
m.SetAttributes(P.FP_SMD); m.Reference().SetLayer(P.F_Fab); m.Value().SetLayer(P.F_Fab); m.Reference().SetVisible(False); m.Value().SetVisible(False)
lib = P.FOOTPRINT(m); lib.SetReference('REF**'); P.FootprintSave(LIB, lib)

# ---- old socket out, with the ground stubs on its pads and the via of the old DET_A pad
old = b.FindFootprintByReference('J501'); oldpads = [p for p in old.Pads() if p.GetNetname() == 'GND']
for t in list(b.GetTracks()):
    if t.GetNetname() != 'GND': continue
    if t.GetClass() == 'PCB_VIA':
        if abs(T(t.GetPosition().x) - 10.88) < 0.03 and abs(T(t.GetPosition().y) - 92.47) < 0.03: b.Remove(t); KEEP.append(t)
    elif t.GetLayer() == P.F_Cu and any(p.HitTest(e) for p in oldpads for e in (t.GetStart(), t.GetEnd())): b.Remove(t); KEEP.append(t)
b.Remove(old); KEEP.append(old)

# ---- neighbours
for ref, dx, dy in (('R524', 0, -0.15), ('TH801', 0, -0.45), ('C806', 0, 0.8), ('R809', 0, 0.2)):
    f, n = strip(ref); f.SetPosition(P.VECTOR2I(f.GetPosition().x + MM(dx), f.GetPosition().y + MM(dy))); print('moved', ref, (dx, dy), 'copper removed', n)
for ref in ('Q901', 'Q902'):
    f, n = strip(ref); b.Remove(f); KEEP.append(f)
add('Q901', 'SOT-363_SC-70-6', float(sys.argv[7]), float(sys.argv[8]), float(sys.argv[9]))
f, n = strip('C513'); f.SetPosition(P.VECTOR2I(MM(float(sys.argv[10])), MM(float(sys.argv[11])))); f.SetOrientationDegrees(float(sys.argv[12]))

# ---- socket
XM = 1.30                                    # body front; latched card end at XM - 2.40
X0, Y0 = XM + 1.25 + OY, 99.25 + (7.955 - OX)
m.SetReference('J501'); b.Add(m); m.SetPosition(P.VECTOR2I(MM(X0), MM(Y0))); m.SetOrientationDegrees(90); fields(m, parts['J501']); setnets(m, parts['J501'])
pp = {p.GetNumber(): (round(T(p.GetPosition().x), 3), round(T(p.GetPosition().y), 3)) for p in m.Pads() if p.GetNumber() != 'SH'}
print('J501 at', (round(X0, 3), round(Y0, 3)), 'terminal 1', pp['1'], 'terminal 8', pp['8'], 'detect', pp['9'])
assert pp['1'][1] > pp['8'][1], 'terminal 1 (DAT2) must be at the larger y, as on TF-122'
def keepout(x0p, y0p, x1p, y1p, name):
    z = P.ZONE(b); z.SetIsRuleArea(True); z.SetLayer(P.F_Cu); z.SetZoneName(name)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    o = z.Outline(); o.NewOutline()
    for xp, yp in ((x0p, y0p), (x1p, y0p), (x1p, y1p), (x0p, y1p)): o.Append(MM(X0 + (yp - OY)), MM(Y0 - (xp - OX)))
    b.Add(z)
keepout(4.08, 6.25, 13.30, 9.65, 'J501 pattern-prohibited area'); keepout(14.95, 8.75, 15.45, 11.15, 'J501 switch keep-out')

# Old SD copper in the socket area goes (the router lays these nets again); then the ground via of terminal 6.
SDN = {'SD_D0', 'SD_D1', 'SD_D2', 'SD_D3', 'SD_CMD', 'SD_CLK', 'SD_CD', '3V3_SD'}
n = 0
for t in list(b.GetTracks()):
    if t.GetNetname() not in SDN: continue
    pts = [t.GetPosition()] if t.GetClass() == 'PCB_VIA' else [t.GetStart(), t.GetEnd()]
    if (t.GetClass() == 'PCB_VIA' or t.GetLayer() == P.F_Cu) and any(-1.0 <= T(q.x) <= 16.9 and 91.5 <= T(q.y) <= 107.6 for q in pts):
        b.Remove(t); KEEP.append(t); n += 1
print('old SD copper removed in the socket area:', n)
P.ZONE_FILLER(b).Fill(b.Zones())
gnd_via(b, *pp['6'], w=0.3, rmax=3.0, rmin=1.1)

# ---- C923 in place, 0.2 mm left (the 0805 pad is wider across; I2C_SDA runs on the right)
part = parts['C923']; old = b.FindFootprintByReference('C923'); pos, rot = old.GetPosition(), old.GetOrientationDegrees()
opad = {p.GetNumber(): p for p in old.Pads()}; hits = []
for t in b.GetTracks():
    for num, pad in opad.items():
        if t.GetNetname() != pad.GetNetname(): continue
        if t.GetClass() == 'PCB_VIA':
            if pad.HitTest(t.GetPosition()): hits.append((num, t.GetPosition(), MM(0.4)))
        elif t.GetLayer() == P.F_Cu: hits += [(num, e, t.GetWidth()) for e in (t.GetStart(), t.GetEnd()) if pad.HitTest(e)]
b.Remove(old); KEEP.append(old)
f = add('C923', part['footprint'], T(pos.x) - 0.2, T(pos.y), rot); new = {p.GetNumber(): p for p in f.Pads()}
for num, e, w in hits:
    if not new[num].HitTest(e):
        c = new[num].GetPosition(); trk(b, new[num].GetNetname(), 'F.Cu', T(w), [(T(e.x), T(e.y)), (T(c.x), T(c.y))])

texts = {t['text'] for a in sys.argv[5:7] for t in json.load(open(a))['texts']}
for d in list(b.GetDrawings()):
    if d.GetClass() == 'PCB_TEXT' and d.GetText() in texts: b.Remove(d); KEEP.append(d)
tb = b.GetTitleBlock(); tb.SetRevision('v0.2.8 / E12'); tb.SetDate('2026-11-17')
tb.SetComment(0, '63 x 48 mm, 4-layer 0.8 mm; v0.2.6 with a recessed 1.45 mm microSD socket')
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[3])
