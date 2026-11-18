"""fix_thermals.py in.kicad_pcb out.kicad_pcb: pads that KiCad's DRC reports as starved thermals (the ground pour reaches
them with fewer than two spokes) get a solid pour connection. Runs kicad-cli DRC, then pcbnew in its own process; repeats
until none is reported (new solid pads can change the fill around their neighbours)."""
import json, os, shutil, subprocess, sys
if sys.argv[1] == '--set':
    import pcbnew as P
    ids = set(json.load(open(sys.argv[4]))); b = P.LoadBoard(sys.argv[2]); n = 0
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.m_Uuid.AsString() in ids:
                assert p.GetNetname() == 'GND', (f.GetReference(), p.GetNumber()); p.SetLocalZoneConnection(P.ZONE_CONNECTION_FULL); n += 1
    P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[3]); print(n); sys.exit(0)
K = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
src, dst = sys.argv[1:3]; pro = src[:-10] + '.kicad_pro'; ids_f = dst[:-10] + '.ids.json'
shutil.copy(src, dst); total = 0
for rnd in range(6):
    out = dst[:-10] + '.drc.json'
    subprocess.run([K, 'pcb', 'drc', '--format', 'json', '--severity-all', '--output', out, dst], capture_output=True)
    v = [x for x in json.load(open(out))['violations'] if x['type'] == 'starved_thermal']
    if not v: break
    json.dump(sorted({i['uuid'] for x in v for i in x['items']}), open(ids_f, 'w'))
    r = subprocess.run([sys.executable, __file__, '--set', dst, dst, ids_f], capture_output=True, text=True)
    n = int(r.stdout.strip().splitlines()[-1]); assert n, r.stderr[-400:]; total += n
else:
    raise SystemExit('starved thermals remain after 6 rounds')
if os.path.exists(ids_f): os.remove(ids_f)
print('solid ground connection set on', total, 'pads')
