"""eco_a03.py in.kicad_pcb netlist_v029.json out.kicad_pcb lib_dir: v0.2.8 board -> v0.2.9 placement (KiCad Python).
Panel E0470A03: 34-pin tail, 17.5 mm wide, 38 mm long, on the centre line of the glass (board x 32.0). The tail folds
back once in its first single-layer zone (0-5.7 mm from the glass) and runs up the component side, so the connector
J820 sits at (32.0, 76.6) with its mouth down at y 78.5. That place held the front-light boost, the right half of the
3.3 V buck and the fuel gauge:
- 3.3 V buck re-laid 0.85 mm to the left of its old place (U902, L401, C401..C404, R401, R402; C503 beside them),
- fuel gauge U903 with C903 / C304 above the connector, beside the battery connector,
- front light: two AW9967 stages (U905 warm, U906 cool) in the bottom-right area the old 40-pin connector left.
Hot loops (buck input, both switch nodes) are laid by hand here; every other link is left to the grid router."""
import json, math, sys, pcbnew as P
from ecolib import trk, via, move
MM, T = P.FromMM, P.ToMM
b = P.LoadBoard(sys.argv[1]); parts = json.load(open(sys.argv[2]))['parts']; LIB = sys.argv[4]; KEEP = []
F = 'F.Cu'
nets_new = {n for p in parts.values() for n in p['pins'].values() if n}
RIP = ['P47_D%d' % i for i in range(8)] + ['P47_XCL', 'P47_XLE', 'P47_XOE', 'P47_XSTL', 'P47_CKV', 'P47_SPV', 'P47_MODE', 'P47_BORDER_REVIEW',
       'FL_PWM', 'FUEL_GPOUT', 'FUEL_VDD', 'FUEL_VCELL', 'BUCK_FB', 'BUCK_LX', 'GPIO45_STRAP']
n = 0
for t in list(b.GetTracks()):
    if t.GetNetname() and (t.GetNetname() not in nets_new or t.GetNetname() in RIP): b.Remove(t); KEEP.append(t); n += 1
print('copper of removed and re-routed nets deleted:', n)
for ref in ('Q901', 'R601'):
    assert ref not in parts
    f = b.FindFootprintByReference(ref); b.Remove(f); KEEP.append(f); print('footprint removed', ref)

def strip(f):
    k = 0
    for t in list(b.GetTracks()):
        for p in f.Pads():
            if t.GetNetname() != p.GetNetname() or not p.GetNetname(): continue
            hit = p.HitTest(t.GetPosition()) if t.GetClass() == 'PCB_VIA' else (t.GetLayer() == P.F_Cu and (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd())))
            if hit: b.Remove(t); KEEP.append(t); k += 1; break
    return k
MOVED = []
def place(ref, x, y, rot, fp=None):
    part = parts[ref]; old = b.FindFootprintByReference(ref)
    if old is not None and fp is None:
        strip(old); move(b, ref, x, y, rot); f = old
    else:
        if old is not None: strip(old); b.Remove(old); KEEP.append(old)
        f = P.FootprintLoad(LIB, fp or part['footprint']); f.SetReference(ref); b.Add(f)
        f.SetFPID(P.LIB_ID('Panda47v2', fp or part['footprint']))
        f.SetPosition(P.VECTOR2I(MM(x), MM(y))); f.SetOrientationDegrees(rot)
        f.Reference().SetVisible(False); f.Value().SetVisible(False)
    f.SetValue(part['value'])
    for k, v in part['fields'].items():
        if k not in ('Reference', 'Value'): f.SetField(k, str(v))
    for p in f.Pads():
        nn = part['pins'].get(p.GetNumber(), '')
        if nn:
            ni = b.FindNet(nn)
            if ni is None: ni = P.NETINFO_ITEM(b, nn); b.Add(ni)
            p.SetNet(ni)
        else: p.SetNetCode(0)
    MOVED.append(ref); return f
def pad(ref, pin):
    f = b.FindFootprintByReference(ref)
    for p in f.Pads():
        if p.GetNumber() == pin: return (round(T(p.GetPosition().x), 3), round(T(p.GetPosition().y), 3))
def place_pad1(ref, x, y, side, fp=None):
    """places a two-pad part at (x, y) with pad 1 towards side: 'L', 'R', 'U' or 'D'."""
    for rot in (0, 90, 180, 270):
        f = place(ref, x, y, rot, fp); px, py = pad(ref, '1'); fp = None if b.FindFootprintByReference(ref) is not None else fp
        if {'L': px < x - 0.1, 'R': px > x + 0.1, 'U': py < y - 0.1, 'D': py > y + 0.1}[side]: return f
    raise SystemExit('no rotation for ' + ref)
def drop(pred):
    k = 0
    for t in list(b.GetTracks()):
        if pred(t): b.Remove(t); KEEP.append(t); k += 1
    return k
def ends(t): return [(T(t.GetPosition().x), T(t.GetPosition().y))] if t.GetClass() == 'PCB_VIA' else [(T(t.GetStart().x), T(t.GetStart().y)), (T(t.GetEnd().x), T(t.GetEnd().y))]

# ---- 1. old 3.3 V buck copper on the front layer and the vias that fall under new pads
BOX = (16.6, 72.0, 25.35, 81.1)
k = drop(lambda t: t.GetClass() != 'PCB_VIA' and t.GetLayer() == P.F_Cu and t.GetNetname() in ('VSYS_RAW', '3V3_AON', 'GND')
         and all(BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3] for x, y in ends(t)))
k += drop(lambda t: t.GetNetname() == '3V3_AON' and t.GetClass() != 'PCB_VIA' and t.GetLayer() == P.F_Cu and
          any(abs(x - 25.41) < 0.05 and abs(y - 75.0) < 0.05 for x, y in ends(t)))                       # old FB sense branch
k += drop(lambda t: t.GetNetname() == 'VSYS_RAW' and t.GetClass() != 'PCB_VIA' and t.GetLayer() == P.F_Cu and
          any(abs(x - 27.4) < 0.05 and abs(y - 75.0) < 0.05 for x, y in ends(t)))                        # feed of the old front-light input capacitor
k += drop(lambda t: t.GetClass() == 'PCB_VIA' and any(math.hypot(ends(t)[0][0] - x, ends(t)[0][1] - y) < 0.05 for x, y in
          ((24.83, 75.92), (18.8, 75.65), (18.8, 76.6), (23.05, 76.35), (23.41, 73.19), (26.28, 77.35))))
k += drop(lambda t: t.GetNetname() == 'VSYS_RAW' and t.GetClass() != 'PCB_VIA' and t.GetLayer() != P.F_Cu and
          any(math.hypot(x - a, y - c) < 0.05 for x, y in ends(t) for a, c in ((18.8, 75.65), (24.83, 75.92))) and T(t.GetLength()) < 1.6)
print('buck area: copper items removed', k)

# ---- 2. panel connector
place('J820', 32.0, 76.6, 0, 'FPC_XKB_X05A10H34G')
assert pad('J820', '1') == (23.75, 75.35) and pad('J820', '34') == (40.25, 75.35)
for pin, vy in (('3', 74.45), ('7', 74.45), ('9', 74.45), ('26', 74.45), ('32', 76.6)):       # 32: under the body, the battery trunk runs on the back above the row                                                      # ground pins between signal pins: own via above the pad row
    x, y = pad('J820', pin); via(b, 'GND', x, vy); trk(b, 'GND', F, 0.2, [(x, y), (x, vy)])

# ---- 3. 3.3 V buck
place('U902', 20.15, 76.6, 0); place('L401', 18.2, 79.94, 0)
assert abs(pad('U902', '4')[0] - 21.29) < 0.02 and abs(pad('U902', '4')[1] - 77.55) < 0.02 and pad('L401', '1')[0] < 18.2, (pad('U902', '4'), pad('L401', '1'))
place_pad1('C401', 20.7, 78.8, 'R'); place_pad1('C402', 20.55, 80.6, 'U'); place_pad1('C403', 21.75, 80.6, 'U')
place_pad1('R402', 21.35, 73.85, 'D'); place_pad1('R401', 20.25, 73.85, 'U'); place_pad1('C404', 19.2, 73.85, 'U'); place_pad1('C503', 18.1, 73.85, 'U')
trk(b, 'VSYS_RAW', F, 0.5, [pad('U902', '4'), pad('C401', '1')])                                   # input capacitor on the IN pin
via(b, 'VSYS_RAW', 22.0, 76.6); trk(b, 'VSYS_RAW', F, 0.5, [pad('U902', '4'), (21.85, 77.3), (22.0, 76.6)])
trk(b, 'VSYS_RAW', 'B.Cu', 0.5, [(22.0, 76.6), (22.0, 75.65)])                                     # to the back-side trunk at y 75.65
via(b, 'VSYS_RAW', 17.83, 75.65); trk(b, 'VSYS_RAW', F, 0.4, [pad('U902', '1'), (17.83, 75.65)])   # EN = IN
trk(b, 'VSYS_RAW', 'B.Cu', 0.5, [(18.8, 75.65), (17.83, 75.65)]); trk(b, 'VSYS_RAW', 'In2.Cu', 0.5, [(17.83, 76.62), (17.83, 75.65)])
trk(b, 'BUCK_LX', F, 0.5, [pad('U902', '3'), (17.9, 77.7), (17.47, 78.3), pad('L401', '1')])
via(b, 'GND', 20.15, 76.6); trk(b, 'GND', F, 0.4, [pad('U902', '2'), (20.15, 76.6)])               # ground via under the IC body
via(b, 'GND', 20.15, 77.55); trk(b, 'GND', F, 0.3, [pad('C401', '2'), (19.95, 78.4), (20.15, 77.55)])    # between the LX and IN pads
trk(b, '3V3_AON', F, 0.4, [(18.93, 80.45), (20.45, 80.2)])                                         # inductor to the output capacitors
trk(b, '3V3_AON', F, 0.6, [pad('C402', '1'), pad('C403', '1'), (24.9, 79.85)]); trk(b, '3V3_AON', F, 0.4, [(24.9, 79.85), (25.38, 79.76)])     # ... and on to the east trunk
trk(b, 'GND', F, 0.4, [pad('C402', '2'), pad('C403', '2'), (22.2, 81.2), (22.86, 80.7)])           # to the existing via
trk(b, '3V3_AON', F, 0.3, [pad('C503', '1'), pad('C404', '1'), pad('R401', '1')])
move(b, 'TPG2', 22.9, 69.7)

# ---- 4. fuel gauge, test pads
place('U903', 40.6, 69.45, 90); place_pad1('C304', 44.3, 68.3, 'L'); place_pad1('C903', 45.0, 69.9, 'L')
place('TP4', 48.3, 69.2, 0); place('TP5', 43.6, 111.6, 0)
trk(b, 'GND', F, 0.2, [pad('U903', '6'), (41.6, pad('U903', '6')[1])])                                # pin 6 to the exposed pad

# ---- 5. front light: two boost stages, IC at (cx, cy), turned 180 deg (VIN / CTRL / SW on the left)
def stage(c, u, l, d, co, ci, r, cx, cy):
    place(u, cx, cy, 180, 'DFN-6-1EP_2x2mm_P0.65mm_EP1x1.6mm'); assert abs(pad(u, '4')[0] - (cx - 1.05)) < 0.02 and abs(pad(u, '4')[1] - (cy - 0.65)) < 0.02, pad(u, '4')
    place_pad1(l, cx - 3.4, cy - 0.65, 'L'); place_pad1(d, cx - 2.9, cy - 3.0, 'L', 'D_SOD-323')
    place_pad1(co, cx - 6.4, cy - 3.0, 'R'); place_pad1(ci, cx - 6.05, cy - 0.2, 'D'); place_pad1(r, cx + 2.7, cy + 0.65, 'L')
    sw, vp = f'FL_{c}_SW', f'FL_{c}_P'
    trk(b, sw, F, 0.4, [pad(u, '4'), pad(l, '2')]); trk(b, sw, F, 0.4, [(cx - 2.4, cy - 1.5), (cx - 1.9, cy - 2.85), pad(d, '2')])
    trk(b, vp, F, 0.4, [pad(d, '1'), pad(co, '1')])
    trk(b, 'VSYS_RAW', F, 0.5, [(cx - 5.4, cy + 0.5), (cx - 4.3, cy + 0.1)])
    trk(b, 'VSYS_RAW', F, 0.4, [(cx - 5.6, cy + 1.0), (cx - 1.9, cy + 1.0), (cx - 1.3, cy + 0.7)])
    trk(b, f'FL_{c}_FB', F, 0.25, [pad(u, '1'), pad(r, '1')])
    trk(b, 'GND', F, 0.3, [pad(u, '3'), (cx + 0.3, cy - 0.5)]); via(b, 'GND', cx + 2.25, cy - 0.65); trk(b, 'GND', F, 0.3, [pad(u, '3'), (cx + 2.25, cy - 0.65)])
    via(b, 'GND', cx - 7.75, cy - 1.55); trk(b, 'GND', F, 0.4, [pad(co, '2'), (cx - 7.75, cy - 1.55)]); trk(b, 'GND', F, 0.4, [pad(ci, '2'), (cx - 7.3, cy - 1.3), (cx - 7.75, cy - 1.55)])
    via(b, 'GND', cx + 3.2, cy + 1.45); trk(b, 'GND', F, 0.3, [pad(r, '2'), (cx + 3.2, cy + 1.45)])
stage('W', 'U905', 'L905', 'D905', 'C923', 'C920', 'R921', 55.2, 106.2)
stage('C', 'U906', 'L906', 'D906', 'C924', 'C921', 'R922', 55.2, 112.3)
place_pad1('R515', 44.3, 103.0, 'L'); place_pad1('R602', 44.3, 104.2, 'L'); place('R726', 46.0, 109.9, 0)                         # CTRL pull-downs (0402, under the tail)
f = b.FindFootprintByReference('FID3'); f.SetPosition(P.VECTOR2I(MM(43.9), MM(106.4)))
for z in b.Zones():
    if z.GetIsRuleArea() and z.GetBoundingBox().Contains(P.VECTOR2I(MM(54.3), MM(101.6))) and T(z.GetBoundingBox().GetWidth()) < 4:
        z.Move(P.VECTOR2I(MM(43.9 - 54.3), MM(106.4 - 101.6))); print('FID3 keep-out moved')
for ref in ('R731', 'U501', 'U601', 'J804'):                                                        # pad nets that changed without a move
    f = b.FindFootprintByReference(ref)
    for p in f.Pads():
        nn = parts[ref]['pins'].get(p.GetNumber(), '')
        if p.GetNetname() != nn and not (nn == '' and p.GetNetname().startswith('unconnected')):
            if nn:
                ni = b.FindNet(nn)
                if ni is None: ni = P.NETINFO_ITEM(b, nn); b.Add(ni)
                p.SetNet(ni)
            else: p.SetNetCode(0)

# ---- 6. copper of other nets that now lies on a new or moved pad
hit = {}
for ref in MOVED:
    for p in b.FindFootprintByReference(ref).Pads():
        for t in list(b.GetTracks()):
            if t.GetNetname() == p.GetNetname(): continue
            if t.GetClass() == 'PCB_VIA':
                near = (t.GetPosition() - p.GetPosition()).EuclideanNorm() - t.GetWidth(P.F_Cu) // 2 < max(p.GetSize().x, p.GetSize().y) // 2 + MM(0.25) \
                       and p.GetEffectiveShape(P.F_Cu).Collide(t.GetEffectiveShape(P.F_Cu), MM(0.14))
            else:
                near = t.GetLayer() == P.F_Cu and p.GetEffectiveShape(P.F_Cu).Collide(t.GetEffectiveShape(), MM(0.14))
            if near: hit[t.GetNetname()] = hit.get(t.GetNetname(), 0) + 1; b.Remove(t); KEEP.append(t)
print('foreign copper removed at new pads:', hit)
if not any(t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND' and abs(T(t.GetPosition().x) - 22.86) < 0.05 and abs(T(t.GetPosition().y) - 80.7) < 0.05 for t in b.GetTracks()):
    via(b, 'GND', 22.86, 80.7); print('ground via of the buck output capacitors restored at (22.86, 80.7)')
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[3])
