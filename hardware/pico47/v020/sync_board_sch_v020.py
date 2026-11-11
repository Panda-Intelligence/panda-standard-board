"""Bring the board in line with the generated schematic for parity (KiCad Python).

usage: sync_board_sch_v020.py project_dir
- no-connect pins: the schematic names them unconnected-(...); the pads get the same net
- hidden Spec field copied from the schematic symbols
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew as P

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import readable_schematic as RS  # noqa: E402
sys.path.insert(0, str(HERE))
import variant_v02x as VAR  # noqa: E402

STEM = VAR.STEM
proj = Path(sys.argv[1])
pcb = proj / f'{STEM}.kicad_pcb'
board = P.LoadBoard(str(pcb))
root = ET.parse(proj / '_sch_build' / 'readable-net.xml').getroot()
nc = {}
for n in root.iter('net'):
    if n.get('name', '').startswith('unconnected-'):
        for x in n.iter('node'):
            nc[(x.get('ref'), x.get('pin'))] = n.get('name')
nets = {}
done = 0
for fp in board.GetFootprints():
    for pad in fp.Pads():
        name = nc.get((fp.GetReference(), pad.GetNumber()))
        if name and pad.GetNetname() != name:
            if name not in nets:
                ni = P.NETINFO_ITEM(board, name)
                board.Add(ni)
                ni.thisown = 0
                nets[name] = ni
            pad.SetNet(nets[name])
            done += 1
specs = RS.footprint_specs(proj, stem=STEM)
for fp in board.GetFootprints():
    text = specs.get(fp.GetReference())
    if text is not None:
        fp.SetField('Spec', text)
        fp.GetField('Spec').SetVisible(False)
P.ZONE_FILLER(board).Fill(board.Zones())
board.Save(str(pcb))
print('no-connect pads named', done, '; Spec synced on', len(specs), 'footprints')
