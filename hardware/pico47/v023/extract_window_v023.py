"""Copy the hand-verified USB-C fan-out copper of v0.2.2 (KiCad Python).
usage: extract_window_v023.py v022.kicad_pcb out.json
Keeps tracks and vias of the USB / CC / VBUS nets that lie fully inside the window around J201."""
import sys, json, pcbnew as P
T = P.ToMM
b = P.LoadBoard(sys.argv[1]); X0, Y0, X1, Y1 = 28.3, 103.6, 36.4, 109.8
NETS = {'USB_DP', 'USB_DM', 'USB_CC1', 'USB_CC2', 'VBUS_USB', 'USB_DP_MCU', 'USB_DM_MCU'}
WHOLE = {'USB_DP', 'USB_DM', 'USB_DP_MCU', 'USB_DM_MCU'}       # the data pair is copied end to end
ins = lambda p: X0 <= T(p.x) <= X1 and Y0 <= T(p.y) <= Y1
tracks, vias = [], []
for t in b.GetTracks():
    if t.GetNetname() not in NETS: continue
    if t.GetClass() == 'PCB_VIA':
        if ins(t.GetPosition()) or t.GetNetname() in WHOLE: vias.append([t.GetNetname(), round(T(t.GetPosition().x), 4), round(T(t.GetPosition().y), 4)])
    elif (ins(t.GetStart()) and ins(t.GetEnd())) or t.GetNetname() in WHOLE:
        tracks.append([t.GetNetname(), b.GetLayerName(t.GetLayer()), round(T(t.GetWidth()), 3),
                       [[round(T(t.GetStart().x), 4), round(T(t.GetStart().y), 4)], [round(T(t.GetEnd().x), 4), round(T(t.GetEnd().y), 4)]]])
pose = {r: [round(T(b.FindFootprintByReference(r).GetPosition().x), 3), round(T(b.FindFootprintByReference(r).GetPosition().y), 3), b.FindFootprintByReference(r).GetOrientationDegrees()] for r in ('J201', 'D201', 'D202', 'R206', 'R207', 'R529', 'R530')}
json.dump(dict(tracks=tracks, vias=vias, pose=pose), open(sys.argv[2], 'w'), indent=0)
print(len(tracks), 'tracks', len(vias), 'vias', pose)
