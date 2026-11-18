"""eco_conn.py in.kicad_pcb netlist_v031.json out.kicad_pcb fp_dir: front-light and touch connectors matched to the
drawing of the 4.26" module with front light and touch (KiCad Python). Board x of the tails, with the panel centred on
the USB-C axis (x 32.0): front light 10.0-13.5 mm from the left panel edge -> centre x 12.57; touch 10.0-13.5 mm from
the right edge -> centre x 51.44; both have pin 1 on the left seen from the front.
- J804 (front light, 24.35 mm plain tail): the tail lands on the microSD socket, so it is Z-folded: up over the socket,
  back down into J804 at the bottom edge. J804 is turned 180 deg (mouth up, at y 109.0); connector pin n meets tail
  pin 7 - n, which the v0.3.0 pin assignment already equals. The connector has contacts on both faces.
- J803 (touch, about 26 mm with the controller and a steel stiffener 10-20 mm from the glass): single fold, mouth down
  at y 95.3 right of the MCU. The stiffened part then lies over the flash and the area below it.
- To make room: flash U506 1.55 mm down, C523 to (49.05, 96.75), C543 beside flash pin 8, fiducial FID3 to (56.0, 104.6),
  C513 to (6.0, 111.5).
Copper on the pads of moved parts is removed; the grid router lays those nets (spec_display.json)."""
import json, sys, pcbnew as P
MM, T = P.FromMM, P.ToMM
b = P.LoadBoard(sys.argv[1]); parts = json.load(open(sys.argv[2]))['parts']; KEEP = []

def strip(ref):
    f = b.FindFootprintByReference(ref); n = 0
    for t in list(b.GetTracks()):
        for p in f.Pads():
            if t.GetNetname() != p.GetNetname() or not p.GetNetname(): continue
            hit = p.HitTest(t.GetPosition()) if t.GetClass() == 'PCB_VIA' else (t.GetLayer() == P.F_Cu and (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd())))
            if hit: b.Remove(t); KEEP.append(t); n += 1; break
    return f, n
def put(ref, x, y, rot=None):
    f, n = strip(ref); f.SetPosition(P.VECTOR2I(MM(x), MM(y)))
    if rot is not None: f.SetOrientationDegrees(rot)
    for p in f.Pads():
        net = parts[ref]['pins'].get(p.GetNumber(), '')
        if net and p.GetNetname() != net: p.SetNet(b.FindNet(net))
    print(ref, '->', (x, y, f.GetOrientationDegrees()), 'copper removed', n,
          {p.GetNumber(): (round(T(p.GetPosition().x), 2), round(T(p.GetPosition().y), 2), p.GetNetname()) for p in f.Pads() if p.GetNumber() in ('1', '6')})
    return f

put('C513', 6.0, 111.5, 0)
put('J804', 12.57, 110.95, 180)          # mouth at y 109.0, facing up
u = b.FindFootprintByReference('U506'); put('U506', T(u.GetPosition().x), T(u.GetPosition().y) + 1.55)
put('C543', 60.4, 96.44, 0)             # beside flash pin 8
put('C523', 49.05, 96.75, -90)
put('J803', 51.44, 93.45, 0)             # mouth at y 95.4, facing down
f = b.FindFootprintByReference('FID3'); f.SetPosition(P.VECTOR2I(MM(56.0), MM(104.6)))
for z in b.Zones():                      # the fiducial's keep-out moves with it, if it has one
    if z.GetIsRuleArea() and z.GetBoundingBox().Contains(P.VECTOR2I(MM(54.3), MM(101.6))) and T(z.GetBoundingBox().GetWidth()) < 4:
        z.Move(P.VECTOR2I(MM(56.0 - 54.3), MM(104.6 - 101.6))); print('FID3 keep-out moved')
# copper of other nets that now lies on a moved pad is removed; the router reconnects those nets
hit = {}
for ref in ('C513', 'J804', 'U506', 'C543', 'C523', 'J803'):
    f = b.FindFootprintByReference(ref)
    for p in f.Pads():
        box = p.GetBoundingBox(); box.Inflate(MM(0.14))
        for t in list(b.GetTracks()):
            if t.GetNetname() == p.GetNetname() or t.GetNetname() == 'GND': continue
            if t.GetClass() != 'PCB_VIA' and t.GetLayer() != P.F_Cu: continue
            if t.GetClass() == 'PCB_VIA':
                d = (t.GetPosition() - p.GetPosition()).EuclideanNorm() - t.GetWidth(P.F_Cu) // 2
                near = d < max(p.GetSize().x, p.GetSize().y) // 2 + MM(0.3)
            else:
                sh = t.GetEffectiveShape(); near = p.GetEffectiveShape(P.F_Cu).Collide(sh, MM(0.14))
            if near: hit[t.GetNetname()] = hit.get(t.GetNetname(), 0) + 1; b.Remove(t); KEEP.append(t)
print('foreign copper removed at moved pads:', hit)
j = b.FindFootprintByReference('J804')
assert {p.GetNumber(): p.GetNetname() for p in j.Pads() if p.GetNumber() in '1256'} == {'1': 'FL_W_N', '2': 'FL_VOUT', '5': 'FL_C_N', '6': 'FL_VOUT'}
p1 = [p for p in j.Pads() if p.GetNumber() == '1'][0]; p6 = [p for p in j.Pads() if p.GetNumber() == '6'][0]
assert T(p6.GetPosition().x) < T(p1.GetPosition().x), 'turned connector: pin 6 must be on the left, where tail pin 1 (C+) arrives'
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[3])
