"""Copy Manufacturer / MPN / LCSC / Description / Datasheet from netlist_v020.json onto the board (KiCad Python).

usage: set_fields_v020.py netlist_v020.json board.kicad_pcb
"""
import json
import sys

import pcbnew as P

nl = json.load(open(sys.argv[1]))['parts']
board = P.LoadBoard(sys.argv[2])
n = 0
for fp in board.GetFootprints():
    part = nl.get(fp.GetReference())
    if not part:
        continue
    for k in ('Manufacturer', 'MPN', 'LCSC', 'Description', 'Datasheet'):
        v = part['fields'].get(k)
        if v and (not fp.HasField(k) or fp.GetFieldText(k) != v):
            fp.SetField(k, str(v))
            n += 1
board.Save(sys.argv[2])
print('fields updated', n)
