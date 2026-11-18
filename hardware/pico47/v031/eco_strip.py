"""eco_strip.py in.kicad_pcb netlist_v030.json out.kicad_pcb: v0.2.4 board -> v0.3.0 starting point (KiCad Python).
Removes every footprint that is not in the v0.3.0 netlist and all copper of the SY7636A / 16-bit bus nets (P47_*),
then gives the remaining pads their v0.3.0 nets. Nothing else moves."""
import json, sys, pcbnew as P
b = P.LoadBoard(sys.argv[1]); parts = json.load(open(sys.argv[2]))['parts']; KEEP = []
n_fp = n_trk = 0
bridges = []
for f in list(b.GetFootprints()):
    r = f.GetReference()
    if r not in parts and (r[0] in 'CDJLQRU' or r.startswith('TP') or r.startswith('TH')) and not r.startswith('TPG'):
        # A removed pad may be the only junction between two tracks of a net that lives on: link their ends directly.
        for p in f.Pads():
            n = p.GetNetname()
            if not n or n.startswith('P47_') or n == 'GND': continue
            for ly in (P.F_Cu, P.B_Cu):
                if not p.IsOnLayer(ly): continue
                ends = {}
                for t in b.GetTracks():
                    if t.GetClass() == 'PCB_VIA' or t.GetNetname() != n or t.GetLayer() != ly: continue
                    for e in (t.GetStart(), t.GetEnd()):
                        if p.HitTest(e): ends[(e.x, e.y)] = min(ends.get((e.x, e.y), 10**9), t.GetWidth())
                pts = sorted(ends)
                have = {frozenset(((t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y))) for t in b.GetTracks()
                        if t.GetClass() != 'PCB_VIA' and t.GetNetname() == n and t.GetLayer() == ly}
                for a, c in zip(pts, pts[1:]):
                    if frozenset((a, c)) in have: continue
                    bridges.append((n, ly, a, c, min(ends[a], ends[c]), r + '.' + p.GetNumber()))
        b.Remove(f); KEEP.append(f); n_fp += 1
for n, ly, a, c, w, src in bridges:
    t = P.PCB_TRACK(b); t.SetNet(b.FindNet(n)); t.SetLayer(ly); t.SetWidth(w)
    t.SetStart(P.VECTOR2I(*a)); t.SetEnd(P.VECTOR2I(*c)); b.Add(t)
    print('bridge', src, n, P.ToMM(a[0]), P.ToMM(a[1]), '->', P.ToMM(c[0]), P.ToMM(c[1]), P.ToMM(w))
for t in list(b.GetTracks()):
    if t.GetNetname().startswith('P47_'):
        b.Remove(t); KEEP.append(t); n_trk += 1
def net(name):
    if not name: return b.FindNet('')  if False else None
    n = b.FindNet(name)
    if n is None:
        n = P.NETINFO_ITEM(b, name); b.Add(n)
    return n
chg = []
for f in b.GetFootprints():
    r = f.GetReference()
    if r not in parts: continue
    for p in f.Pads():
        want = parts[r]['pins'].get(p.GetNumber(), None)
        if want is None: continue
        if p.GetNetname() != want and not (want == '' and p.GetNetname().startswith('unconnected-')):
            chg.append((r, p.GetNumber(), p.GetNetname(), want))
            p.SetNetCode(net(want).GetNetCode() if want else 0)
for f in b.GetFootprints():
    r = f.GetReference()
    if r in parts and f.GetValue() != parts[r]['value']: f.SetValue(parts[r]['value'])
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[3])
print('footprints removed', n_fp, 'tracks removed', n_trk, 'pads renamed', len(chg))
for c in chg: print(' ', *c)
