"""Final touch-ups after widening (KiCad Python). usage: touchup_v023.py in.kicad_pcb drc.json out.kicad_pcb
- (dangling stubs are left to prune_dangling_v020.py and trim_dangling_v020.py);
- steps a widened track named in a clearance report down to the next width;
- gives a GND pad with a starved thermal relief a solid pour connection."""
import json, sys
import pcbnew as P
MM, T = P.FromMM, P.ToMM
LADDER = [0.8, 0.7, 0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.17, 0.15, 0.127]
b = P.LoadBoard(sys.argv[1]); d = json.load(open(sys.argv[2]))
byid = {t.m_Uuid.AsString(): t for t in b.GetTracks()}
pads = {p.m_Uuid.AsString(): p for fp in b.GetFootprints() for p in fp.Pads()}
n = [0, 0, 0]
for v in d['violations']:
    ids = [i.get('uuid') for i in v['items']]
    if v['type'] == 'track_dangling':
        for u in ids:
            t = byid.get(u)
            if t is not None and t.GetClass() != 'PCB_VIA' and T(t.GetLength()) < 0.0:
                b.Delete(t); n[0] += 1
    elif v['type'] == 'clearance':
        for u in ids:
            t = byid.get(u)
            if t is not None and t.GetClass() != 'PCB_VIA' and T(t.GetWidth()) > 0.13:
                lower = [w for w in LADDER if w < T(t.GetWidth()) - 1e-6]
                t.SetWidth(MM(lower[0])); n[1] += 1
    elif v['type'] == 'starved_thermal':
        for u in ids:
            if u in pads:
                pads[u].SetLocalZoneConnection(P.ZONE_CONNECTION_FULL); n[2] += 1
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[3])
print('stubs removed', n[0], 'tracks narrowed', n[1], 'solid pad connections', n[2])
