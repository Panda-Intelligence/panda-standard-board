"""Widen current-carrying tracks as far as the design rules allow (KiCad Python; calls kicad-cli DRC).

usage: widen_v023.py in.kicad_pcb out.kicad_pcb
Every track of a listed net is set to its target width. KiCad DRC is then run; each track named in a clearance,
short, hole or edge violation steps one rung down the ladder (never below its routed width). Repeat until clean."""
import collections, fnmatch, json, subprocess, sys
import pcbnew as P
MM, T = P.FromMM, P.ToMM
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
TARGET = [('VBUS_USB', 0.8), ('BAT_*', 0.8), ('VSYS_RAW', 0.6), ('3V3_AON', 0.6), ('SGM41513_SW', 0.7), ('SGM41513_PMID', 0.5),
          ('BUCK_LX', 0.5), ('FL_SW', 0.5), ('FL_VOUT', 0.5), ('P47_VP_LX', 0.6), ('P47_VN_LX', 0.6), ('P47_VP', 0.5), ('P47_VN', 0.5),
          ('3V3_RF', 0.4), ('3V3_SD', 0.4), ('VDD_SPI', 0.4), ('SPK_*', 0.4), ('P47_VPOS', 0.3), ('P47_VNEG', 0.3), ('P47_VGH', 0.3),
          ('P47_VGL', 0.3), ('P47_VCOM', 0.3), ('SGM41513_REGN', 0.3), ('P47_VEE_*', 0.3), ('P47_VGH_*', 0.3), ('P47_PUMP_*', 0.3), ('GND', 0.4)]
LADDER = [0.8, 0.7, 0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.17, 0.15, 0.127]
BAD = {'clearance', 'shorting_items', 'hole_clearance', 'copper_edge_clearance', 'tracks_crossing', 'solder_mask_bridge', 'track_width'}


def target(net):
    for pat, w in TARGET:
        if fnmatch.fnmatch(net, pat):
            return w
    return None


board = P.LoadBoard(sys.argv[1]); out = sys.argv[2]
orig, cur = {}, {}
for t in board.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        continue
    w = target(t.GetNetname())
    if w and T(t.GetWidth()) < w - 1e-6:
        u = t.m_Uuid.AsString(); orig[u] = T(t.GetWidth()); cur[u] = w; t.SetWidth(MM(w))
byid = {t.m_Uuid.AsString(): t for t in board.GetTracks()}
print('tracks to widen', len(cur))
for it in range(30):
    P.ZONE_FILLER(board).Fill(board.Zones()); board.Save(out)
    subprocess.run([CLI, 'pcb', 'drc', '--format', 'json', '--severity-all', '--output', out + '.drc.json', out], capture_output=True)
    d = json.load(open(out + '.drc.json'))
    hit = set()
    for v in d['violations']:
        if v['type'] in BAD:
            for i in v['items']:
                if i.get('uuid') in cur:
                    hit.add(i['uuid'])
    if not hit:
        break
    for u in hit:
        lower = [w for w in LADDER if w < cur[u] - 1e-6 and w >= orig[u] - 1e-6]
        cur[u] = lower[0] if lower else orig[u]
        if not lower:
            cur[u] = orig[u]
        byid[u].SetWidth(MM(cur[u]))
    print(f'  pass {it}: {len(hit)} tracks stepped down')
left = collections.Counter(v['type'] for v in d['violations'] if v['type'] in BAD)
print('widened', sum(1 for u in cur if cur[u] > orig[u] + 1e-6), 'of', len(cur), '; remaining rule hits', dict(left), '; unconnected', len(d['unconnected_items']))
