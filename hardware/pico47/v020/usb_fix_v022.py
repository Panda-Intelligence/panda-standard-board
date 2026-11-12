"""Hand fix of the USB-C D+/D- crossing on the v0.2.2 Freerouting result (KiCad Python).
usage: usb_fix_v022.py in.kicad_pcb out.kicad_pcb
D+ (A6) drops to In2 through a via at (31.75, 108.0); D- (A7) runs up between the two D+ vias and joins the B7 D- track;
CC1 is re-laid right of A7 (F) and above the new D+ via (B); R206 moves 0.35 mm up; its GND pad joins the F.Cu pour."""
import sys
import pcbnew as P
MM, T = P.FromMM, P.ToMM
b = P.LoadBoard(sys.argv[1])
net = lambda n: b.FindNet(n)
L = {n: b.GetLayerID(n) for n in ('F.Cu', 'In2.Cu', 'B.Cu')}


def same(p, q):
    return abs(T(p.x) - q[0]) < 0.003 and abs(T(p.y) - q[1]) < 0.003


def seg_is(t, a, c):
    s, e = t.GetStart(), t.GetEnd()
    return (same(s, a) and same(e, c)) or (same(s, c) and same(e, a))


DROP = [('USB_DP', (32.752, 108.096), (31.962, 108.096)), ('USB_DP', (31.962, 108.096), (31.75, 108.308)),
        ('USB_CC1', (31.81, 107.0), (32.355, 107.545)), ('USB_CC1', (32.355, 107.545), (33.303, 107.545)),
        ('USB_CC1', (33.303, 107.545), (33.504, 107.745)), ('USB_CC1', (32.5, 106.31), (31.81, 107.0)),
        ('GND', (30.79, 107.0), (30.79, 106.285)),
        ('USB_CC1', (33.504, 107.745), (33.334, 107.575)), ('USB_CC1', (31.265, 107.575), (30.75, 108.09)),
        ('USB_CC1', (33.334, 107.575), (31.265, 107.575))]
dropped = 0
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA':
        if t.GetNetname() == 'GND' and same(t.GetPosition(), (30.79, 106.285)):
            b.Delete(t); dropped += 1
        continue
    if any(t.GetNetname() == n and seg_is(t, a, c) for n, a, c in DROP):
        b.Delete(t); dropped += 1
fp = b.FindFootprintByReference('R206')
fp.SetPosition(P.VECTOR2I(MM(31.3), MM(106.65)))


def trk(n, ly, pts, w=0.127):
    for a, c in zip(pts, pts[1:]):
        t = P.PCB_TRACK(b); t.SetLayer(L[ly]); t.SetNet(net(n)); t.SetWidth(MM(w))
        t.SetStart(P.VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(P.VECTOR2I(MM(c[0]), MM(c[1]))); b.Add(t)


def via(n, x, y):
    v = P.PCB_VIA(b); v.SetNet(net(n)); v.SetPosition(P.VECTOR2I(MM(x), MM(y)))
    v.SetWidth(MM(0.55)); v.SetDrill(MM(0.3)); v.SetLayerPair(b.GetLayerID('F.Cu'), b.GetLayerID('B.Cu')); b.Add(v)


trk('USB_DP', 'F.Cu', [(31.75, 108.308), (31.75, 108.0)]); via('USB_DP', 31.75, 108.0)
trk('USB_DP', 'In2.Cu', [(31.75, 108.0), (31.75, 108.585)])
trk('USB_DM', 'F.Cu', [(32.25, 109.05), (32.25, 107.3), (31.269, 107.3)])
trk('USB_CC1', 'F.Cu', [(33.504, 107.745), (32.65, 107.45), (32.65, 106.65), (31.81, 106.65)])
trk('USB_CC1', 'F.Cu', [(32.5, 106.31), (32.65, 106.46), (32.65, 106.65)])
trk('USB_CC1', 'B.Cu', [(30.75, 108.09), (31.44, 107.4), (33.16, 107.4), (33.504, 107.745)])
b.Save(sys.argv[2])
print('dropped', dropped)
