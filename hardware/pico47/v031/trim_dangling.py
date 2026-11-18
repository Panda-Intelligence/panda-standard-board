"""trim_dangling.py in.kicad_pcb out.kicad_pcb: remove the tracks and vias that KiCad's own DRC reports as dangling
(KiCad Python; runs kicad-cli). One round = DRC, remove the reported items, DRC again. A round is kept only if the
number of unconnected items did not rise (a dangling track can still carry a T-junction on its body); otherwise the
round is undone and the script stops with an error. Ends when nothing is reported."""
import json, os, shutil, subprocess, sys
if sys.argv[1] == '--remove':                      # own process per round: pcbnew returns bare proxies after a DRC subprocess
    import pcbnew as P
    ids = set(json.load(open(sys.argv[4]))); b = P.LoadBoard(sys.argv[2]); keep = [t for t in b.GetTracks() if t.m_Uuid.AsString() in ids]
    for t in keep: b.Remove(t)
    P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[3]); print(len(keep)); sys.exit(0)
K = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
src, dst = sys.argv[1:3]; tmp = dst[:-10] + '_t.kicad_pcb'; pro = src[:-10] + '.kicad_pro'
if os.path.exists(pro): shutil.copy(pro, tmp[:-10] + '.kicad_pro')
def drc(path):
    out = path[:-10] + '.drc.json'
    subprocess.run([K, 'pcb', 'drc', '--format', 'json', '--severity-all', '--output', out, path], capture_output=True)
    d = json.load(open(out))
    return [v for v in d['violations'] if v['type'] in ('track_dangling', 'via_dangling')], len(d['unconnected_items'])
shutil.copy(src, dst); total = 0
for rnd in range(60):
    dang, unc = drc(dst)
    if not dang: break
    ids = {i['uuid'] for v in dang for i in v['items']}
    json.dump(sorted(ids), open(tmp[:-10] + '.ids.json', 'w'))
    r = subprocess.run([sys.executable, __file__, '--remove', dst, tmp, tmp[:-10] + '.ids.json'], capture_output=True, text=True)
    n = int(r.stdout.strip().splitlines()[-1]); assert n, r.stderr[-400:]
    d2, u2 = drc(tmp)
    assert u2 <= unc, 'removing dangling items opened a net: round %d, %d -> %d unconnected' % (rnd, unc, u2)
    shutil.copy(tmp, dst); total += n
else:
    raise SystemExit('dangling items remain after 60 rounds')
for f in (tmp, tmp[:-10] + '.kicad_pro', tmp[:-10] + '.drc.json', tmp[:-10] + '.kicad_prl', tmp[:-10] + '.ids.json'):
    if os.path.exists(f): os.remove(f)
print('dangling items removed:', total)
