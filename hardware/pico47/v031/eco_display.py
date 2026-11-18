"""eco_display.py in.kicad_pcb netlist_v031.json out.kicad_pcb fp_dir: places the 4.26" SPI panel circuit (KiCad Python).
v0.3.1 copy of v030/eco_display.py for the v0.2.8 base: C834 sits 1.3 mm higher, clear of the recessed microSD socket.
- J830 (24-pin FPC) centred on the USB-C axis at (32.0, 100.05), mouth towards the bottom edge, pin 1 left: the panel
  tail is centred on the glass and folds straight back onto the board.
- Boost stage (L831, Q831, D831..D833, C831..C834, R831, R832) in the area the SY7636A block left, hand-laid.
- C524 moves 0.4 mm up, R510 moves to L507; C510 and C209 become 0402 parts and move out of the connector's way.
Signals and the remaining panel rails are laid by the grid router afterwards (spec_display.json)."""
import json, math, sys, pcbnew as P
from ecolib import remove, trk, via, move
MM, T = P.FromMM, P.ToMM
b = P.LoadBoard(sys.argv[1]); parts = json.load(open(sys.argv[2]))['parts']; LIB = sys.argv[4]; KEEP = []
STD = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/'

# ---- footprints new to the library
for lib, name in ((STD + 'Package_TO_SOT_SMD.pretty', 'SOT-323_SC-70'), (STD + 'Resistor_SMD.pretty', 'R_0603_1608Metric')):
    P.FootprintSave(LIB, P.FootprintLoad(lib, name))
m = P.FOOTPRINT(b); m.SetFPID(P.LIB_ID('Panda47v2', 'FPC_XKB_X05A10L24G'))
m.SetLibDescription('XKB X05A10L24G, 0.5 mm 24-pin flip-lock FPC connector, bottom contact; land pattern scaled from the 40-pin part of the same series')
def smd(num, x, y, w, h):
    p = P.PAD(m); p.SetNumber(num); p.SetAttribute(P.PAD_ATTRIB_SMD); p.SetShape(P.F_Cu, P.PAD_SHAPE_RECT)
    p.SetSize(P.F_Cu, P.VECTOR2I(MM(w), MM(h))); p.SetPosition(P.VECTOR2I(MM(x), MM(y))); p.SetLayerSet(P.PAD.SMDMask()); m.Add(p)
for n in range(1, 25): smd(str(n), (n - 12.5) * 0.5, -2.3, 0.3, 0.65)
smd('MP', -6.635, 0.565, 0.3, 1.3); smd('MP', 6.635, 0.565, 0.3, 1.3)
for layer, box, w in ((P.F_Fab, (-6.93, -1.97, 6.93, 1.47), 0.1), (P.F_CrtYd, (-7.16, -2.725, 7.16, 1.7), 0.05)):
    s = P.PCB_SHAPE(m); s.SetShape(P.SHAPE_T_RECT); s.SetLayer(layer); s.SetWidth(MM(w))
    s.SetStart(P.VECTOR2I(MM(box[0]), MM(box[1]))); s.SetEnd(P.VECTOR2I(MM(box[2]), MM(box[3]))); m.Add(s)
m.SetAttributes(P.FP_SMD); m.Reference().SetLayer(P.F_Fab); m.Value().SetLayer(P.F_Fab); m.Reference().SetVisible(False); m.Value().SetVisible(False)
lib = P.FOOTPRINT(m); lib.SetReference('REF**'); P.FootprintSave(LIB, lib)

def place(ref, x, y, rot, fp=None):
    part = parts[ref]
    old = b.FindFootprintByReference(ref)
    if old is not None and fp is None:
        move(b, ref, x, y, rot); f = old
    else:
        if old is not None: b.Remove(old); KEEP.append(old)
        f = P.FootprintLoad(LIB, fp or part['footprint']); f.SetReference(ref); b.Add(f)
        f.SetFPID(P.LIB_ID('Panda47v2', fp or part['footprint']))
        f.SetPosition(P.VECTOR2I(MM(x), MM(y))); f.SetOrientationDegrees(rot)
        f.Reference().SetVisible(False); f.Value().SetVisible(False)
    f.SetValue(part['value'])
    for k, v in part['fields'].items():
        if k in ('Reference', 'Value'): continue
        f.SetField(k, str(v))
    for p in f.Pads():
        n = part['pins'].get(p.GetNumber(), '')
        if n:
            ni = b.FindNet(n)
            if ni is None: ni = P.NETINFO_ITEM(b, n); b.Add(ni)
            p.SetNet(ni)
        else: p.SetNetCode(0)
    return f

# ---- copper that is in the way
def seg_d(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)
def drop(net, pred):
    n = 0
    for t in list(b.GetTracks()):
        if t.GetNetname() == net and pred(t): b.Remove(t); KEEP.append(t); n += 1
    return n
def ends(t): return [(T(t.GetPosition().x), T(t.GetPosition().y))] if t.GetClass() == 'PCB_VIA' else [(T(t.GetStart().x), T(t.GetStart().y)), (T(t.GetEnd().x), T(t.GetEnd().y))]
inbox = lambda box: (lambda t: any(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in ends(t)))
# dead SY7636A supply branch on the front layer (its vias and inner tracks go with prune_stubs.py afterwards)
print('VSYS_RAW front tracks removed', drop('VSYS_RAW', lambda t: t.GetClass() != 'PCB_VIA' and t.GetLayer() == P.F_Cu and inbox((17.5, 84.0, 26.6, 102.0))(t)))
print('VSYS_RAW vias removed', drop('VSYS_RAW', lambda t: t.GetClass() == 'PCB_VIA' and inbox((17.5, 84.0, 26.6, 102.0))(t)))
drop('I2C_SCL', lambda t: t.GetClass() != 'PCB_VIA' and t.GetLayer() == P.F_Cu and inbox((22.2, 96.3, 23.0, 97.2))(t) and not inbox((21.8, 97.3, 22.1, 97.7))(t))
drop('FL_FB', lambda t: t.GetClass() != 'PCB_VIA' and t.GetLayer() == P.F_Cu and inbox((29.5, 93.9, 30.3, 99.7))(t))   # re-laid by the router
drop('FL_FB', lambda t: t.GetClass() == 'PCB_VIA' and inbox((29.9, 99.5, 30.2, 99.8))(t))
drop('CHIP_PU_MCU', lambda t: t.GetClass() == 'PCB_VIA' and inbox((39.2, 101.0, 39.5, 101.2))(t))
drop('CHIP_PU_MCU', lambda t: t.GetClass() != 'PCB_VIA' and t.GetLayer() == P.F_Cu and T(t.GetStart().x) > 35 and T(t.GetStart().y) > 96.5)
# ground stubs and vias of removed parts that sit under new pads or in the connector's escape field
GV = [(31.51, 89.435), (30.875, 87.23), (27.245, 92.9), (27.93, 90.075), (17.43, 92.625), (30.33, 97.175), (19.755, 94.1), (21.3, 89.755),
      (30.18, 100.675), (35.78, 100.425)]
STUB_END = GV + [(27.38, 97.62), (26.5, 98.88)]
drop('GND', lambda t: t.GetClass() == 'PCB_VIA' and any(math.hypot(ends(t)[0][0] - x, ends(t)[0][1] - y) < 0.05 for x, y in GV))
drop('GND', lambda t: t.GetClass() != 'PCB_VIA' and t.GetLayer() == P.F_Cu and any(math.hypot(ex - x, ey - y) < 0.05 for ex, ey in ends(t) for x, y in STUB_END))
remove(b, [('3V3_AON', (34.55, 95.338), (34.55, 96.51)), ('3V3_AON', (34.55, 96.51), (36.3, 98.26)),
           ('3V3_AON', (30.8, 94.44), (32.362, 92.878)), ('3V3_AON', (33.653, 94.44), (30.8, 94.44)),
           ('3V3_RF', (37.72, 96.47), (37.72, 97.2)), ('GND', (38.68, 97.2), (38.96, 96.525)),
           ('VBUS_USB', (33.175, 102.1), (33.175, 102.304)), ('VBUS_USB', (33.175, 102.304), (34.871, 104.0)),
           ('3V3_SD', (24.2, 98.24), (24.962, 99.002)), ('3V3_SD', (24.962, 99.002), (24.962, 101.299)), ('3V3_SD', (24.962, 101.299), None)])

# ---- parts
place('J830', 32.0, 100.05, 0, 'FPC_XKB_X05A10L24G')
place('C524', 38.2, 96.8, 0)
place('R510', 32.5, 95.6, 0)
place('C510', 32.5, 96.7, 180, 'C_0402_1005Metric')
place('C209', 33.75, 103.0, 0, 'C_0402_1005Metric')
move(b, "TP6", 24.8, 101.3)                                   # 0.2 mm left: clear of the connector's hold-down pad
for ref, x, y, rot in (('Q831', 27.0, 94.1, 90), ('L831', 28.6, 90.25, 270), ('C831', 28.2, 87.1, 0), ('D831', 23.1, 91.75, 0),
                       ('C833', 19.95, 91.75, 180), ('C832', 23.1, 93.6, 180), ('D832', 19.7, 93.6, 180), ('D833', 20.6, 95.6, 0),
                       ('C834', 17.3, 92.0, 90), ('R831', 29.75, 94.8, 0), ('R832', 24.9, 94.99, 180), ('C836', 29.03, 96.4, 0),
                       ('C840', 33.15, 93.5, 90), ('C835', 22.0, 102.6, 180), ('C837', 22.0, 104.3, 180), ('C838', 22.0, 106.0, 180),
                       ('C839', 22.6, 100.9, 180)):
    place(ref, x, y, rot)
for ref in ('TP801', 'TP802', 'TP803'):
    f = b.FindFootprintByReference(ref); f.SetValue(parts[ref]['value'])
pos = {(f.GetReference(), p.GetNumber()): (round(T(p.GetPosition().x), 3), round(T(p.GetPosition().y), 3), p.GetNetname())
       for f in b.GetFootprints() for p in f.Pads()}
def at(ref, pin, net):
    x, y, n = pos[(ref, pin)]; assert n == net, (ref, pin, n, net); return (x, y)

def gnd_via(x0, y0, w=0.4, rmax=1.8, rmin=0.75):
    """GND via at the nearest spot to (x0, y0) that clears every other net on all layers, with a straight front-layer link."""
    VR, DR = 0.275, 0.15; near = []
    for t in b.GetTracks():
        e = ends(t)
        if min(math.hypot(x - x0, y - y0) for x, y in e) > rmax + 6 and t.GetClass() == 'PCB_VIA': continue
        near.append(t)
    padl = [(p, p.GetBoundingBox()) for f in b.GetFootprints() for p in f.Pads()
            if abs(T(p.GetPosition().x) - x0) < rmax + 4 and abs(T(p.GetPosition().y) - y0) < rmax + 4]
    def box_d(bb, x, y):
        dx = max(T(bb.GetX()) - x, 0, x - T(bb.GetRight())); dy = max(T(bb.GetY()) - y, 0, y - T(bb.GetBottom())); return math.hypot(dx, dy)
    best = None
    for i in range(-36, 37):
        for j in range(-36, 37):
            x, y = x0 + i * 0.05, y0 + j * 0.05; d = math.hypot(x - x0, y - y0)
            if d > rmax or d < rmin or (best and d >= best[0]): continue
            ok = True
            for t in near:
                gnd = t.GetNetname() == 'GND'
                if t.GetClass() == 'PCB_VIA':
                    dd = math.hypot(T(t.GetPosition().x) - x, T(t.GetPosition().y) - y)
                    if dd < 2 * DR + 0.27 or (not gnd and dd < 2 * VR + 0.14): ok = False; break
                elif not gnd:
                    e = ends(t); hw = T(t.GetWidth()) / 2
                    if seg_d(x, y, *e[0], *e[1]) < max(VR + 0.14, DR + 0.26) + hw: ok = False; break
                    if t.GetLayer() == P.F_Cu:      # the link track must clear it too (sampled)
                        if any(seg_d(x0 + (x - x0) * k / 8, y0 + (y - y0) * k / 8, *e[0], *e[1]) < w / 2 + hw + 0.14 for k in range(9)): ok = False; break
            if not ok: continue
            for p, bb in padl:
                dd = box_d(bb, x, y)
                if p.GetNetname() == 'GND':
                    if dd < VR + 0.1: ok = False; break
                else:
                    if dd < max(VR + 0.14, DR + 0.26): ok = False; break
                    if p.IsOnLayer(P.F_Cu) and any(box_d(bb, x0 + (x - x0) * k / 8, y0 + (y - y0) * k / 8) < w / 2 + 0.14 for k in range(9)): ok = False; break
            if ok: best = (d, round(x, 3), round(y, 3))
    assert best, ('no via spot', x0, y0)
    trk(b, 'GND', 'F.Cu', w, [(x0, y0), best[1:]]); via(b, 'GND', *best[1:]); print('GND via', best[1:], 'for', (x0, y0)); return best[1:]

# ---- hand copper, front layer
F = 'F.Cu'
trk(b, '3V3_SD', F, 0.25, [(24.2, 98.24), (24.8, 98.84), (24.8, 101.3)]); via(b, "3V3_SD", 24.8, 101.3)
trk(b, '3V3_RF', F, 0.4, [(37.72, 96.47), at('C524', '1', '3V3_RF')])
trk(b, 'GND', F, 0.4, [at('C524', '2', 'GND'), (38.96, 96.525)])
trk(b, '3V3_AON', F, 0.5, [(32.362, 92.878), (32.362, 93.4), (33.4, 94.44), (33.653, 94.44)])       # RF supply feed, moved off R831
trk(b, '3V3_AON', F, 0.25, [at('R510', '1', '3V3_AON'), (31.99, 94.3), (32.362, 93.9), (32.362, 93.4)])
trk(b, '3V3_AON', F, 0.25, [(34.55, 95.6), (34.55, 96.3), (33.75, 97.1), at('J830', '16', '3V3_AON')])
trk(b, '3V3_AON', F, 0.3, [at('J830', '15', '3V3_AON'), at('J830', '16', '3V3_AON')])
trk(b, 'CHIP_PU_MCU', F, 0.2, [at('R510', '2', 'CHIP_PU_MCU'), at('C510', '1', 'CHIP_PU_MCU')])
trk(b, 'GND', F, 0.3, [at('C840', '2', 'GND'), (33.005, 92.5), (33.005, 91.75)])
trk(b, 'VBUS_USB', F, 0.5, [at('C209', '1', 'VBUS_USB'), (33.27, 103.35), (33.92, 104.0), (34.871, 104.0)])
trk(b, 'GND', F, 0.4, [(34.725, 102.1), at('C209', '2', 'GND')])
# boost stage
trk(b, 'EPD_LX', F, 0.45, [(27.0, 92.0), at('Q831', '3', 'EPD_LX')])
trk(b, 'EPD_LX', F, 0.45, [at('D831', '2', 'EPD_LX'), (26.9, 91.75)])
trk(b, 'EPD_LX', F, 0.4, [at('D831', '2', 'EPD_LX'), (24.15, 93.325), at('C832', '1', 'EPD_LX')])
trk(b, '3V3_AON', F, 0.5, [at('C831', '1', '3V3_AON'), (27.425, 88.4)])
trk(b, '3V3_AON', F, 0.5, [(30.2, 88.75), (30.45, 88.75), (30.714, 88.486), (30.714, 85.099)])
gnd_via(*at('C831', '2', 'GND'))
trk(b, 'EPD_PREVGH', F, 0.4, [at('D831', '1', 'EPD_PREVGH'), at('C833', '1', 'EPD_PREVGH')])
trk(b, 'GND', F, 0.4, [at('C833', '2', 'GND'), (18.6, 91.175), (18.6, 90.07)])                    # to the existing via at (17.895, 90.07)
trk(b, 'GND', F, 0.3, [at('C834', '2', 'GND'), (18.6, 91.17)])                                    # to the ground track of the via at (17.89, 90.07)
trk(b, 'EPD_PUMP', F, 0.4, [at('C832', '2', 'EPD_PUMP'), at('D832', '1', 'EPD_PUMP')])
trk(b, 'EPD_PUMP', F, 0.4, [at('C832', '2', 'EPD_PUMP'), (22.325, 94.4), (21.65, 95.075), at('D833', '2', 'EPD_PUMP')])
trk(b, 'EPD_PREVGL', F, 0.4, [at('D832', '2', 'EPD_PREVGL'), (18.0, 93.6), at('C834', '1', 'EPD_PREVGL')])
trk(b, 'GND', F, 0.4, [at('D833', '1', 'GND'), (18.9, 95.6), (18.375, 96.125)])                   # to the existing via at (17.48, 96.125)
trk(b, 'EPD_GDR', F, 0.2, [at('J830', '2', 'EPD_GDR'), (26.75, 96.0), (26.35, 95.6), at('Q831', '1', 'EPD_GDR')])
trk(b, 'EPD_GDR', F, 0.2, [at('R832', '1', 'EPD_GDR'), at('Q831', '1', 'EPD_GDR')])
gnd_via(*at('R832', '2', 'GND'), w=0.3)
trk(b, 'EPD_RESE', F, 0.4, [at('Q831', '2', 'EPD_RESE'), (27.84, 94.8), at('R831', '1', 'EPD_RESE')])
trk(b, 'EPD_RESE', F, 0.25, [at('Q831', '2', 'EPD_RESE'), (27.65, 95.6), (27.25, 96.0), at('J830', '3', 'EPD_RESE')])
trk(b, 'GND', F, 0.4, [at('R831', '2', 'GND'), (30.675, 93.9), (30.675, 93.18)])                   # existing via
gnd_via(*at('R831', '2', 'GND'))
trk(b, 'EPD_VSH2', F, 0.3, [at('C836', '1', 'EPD_VSH2'), at('J830', '5', 'EPD_VSH2')])
trk(b, 'GND', F, 0.3, [at('J830', '8', 'GND'), at('C836', '2', 'GND')])
v = gnd_via(*at('C836', '2', 'GND'), w=0.3, rmax=2.4)
trk(b, 'GND', F, 0.25, [at('C510', '2', 'GND'), v])
trk(b, 'GND', F, 0.2, [at('J830', '17', 'GND'), (34.25, 100.75), (34.725, 101.23)])
trk(b, 'GND', F, 0.3, [(25.365, 100.2), (26.0, 99.9)])
for k in sorted(pos):
    if k[0] in ('L831', 'C831', 'R510', 'C510', 'C209', 'R831') and k[1] in ('1', '2'): print(k[0], k[1], *pos[k])
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[3])
