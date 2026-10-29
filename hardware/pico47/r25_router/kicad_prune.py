"""Iteratively remove copper that KiCad DRC reports as dangling; revert a pass if unconnected items increase.
usage: kicad_prune.py board.kicad_pcb [max_passes]   (board is modified in place; run on a copy)
"""
import json, subprocess, sys

K = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
KPY = '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'
pcb = sys.argv[1]
passes = int(sys.argv[2]) if len(sys.argv) > 2 else 10


def drc():
    rep = pcb + '.drc.json'
    subprocess.run([K, 'pcb', 'drc', '--refill-zones', '--severity-all', '--format', 'json', '-o', rep, pcb],
                   check=True, capture_output=True)
    return json.load(open(rep))


REMOVE = r'''
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); ids = set(sys.argv[2].split(','))
n = 0
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString() in ids:
        b.Remove(t); n += 1
b.Save(sys.argv[1]); print(n)
'''
cur = drc()
for i in range(passes):
    ids = {it['uuid'] for v in cur['violations'] if v['type'] in ('track_dangling', 'via_dangling') for it in v['items']}
    if not ids:
        break
    backup = open(pcb, 'rb').read()
    out = subprocess.run([KPY, '-c', REMOVE, pcb, ','.join(ids)], capture_output=True, text=True)
    nxt = drc()
    if len(nxt['unconnected_items']) > len(cur['unconnected_items']):
        open(pcb, 'wb').write(backup)
        print(f'pass {i + 1}: reverted (unconnected {len(cur["unconnected_items"])} -> {len(nxt["unconnected_items"])})')
        break
    print(f'pass {i + 1}: removed {out.stdout.strip()} dangling items; violations {len(nxt["violations"])}, '
          f'unconnected {len(nxt["unconnected_items"])}')
    cur = nxt
