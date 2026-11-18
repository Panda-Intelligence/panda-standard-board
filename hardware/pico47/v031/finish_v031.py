"""finish_v031.py in.kicad_pcb out.kicad_pcb old_silk.json new_silk.json: last touches for the v0.3.1 board (KiCad Python).
- drops the printed texts of the base board and of the new spec (info_silk_v02x.py must not remove texts itself),
- sets the title block."""
import json, sys, pcbnew as P
T = P.ToMM
b = P.LoadBoard(sys.argv[1]); KEEP = []
texts = {t['text'] for f in sys.argv[3:5] for t in json.load(open(f))['texts']}
n = 0
for d in list(b.GetDrawings()):
    if d.GetClass() == 'PCB_TEXT' and d.GetText() in texts:
        b.Remove(d); KEEP.append(d); n += 1
tb = b.GetTitleBlock(); tb.SetTitle('Panda Standard 4.26 main board'); tb.SetRevision('v0.3.1 / E13'); tb.SetDate('2026-11-18')
tb.SetComment(0, '63 x 48 mm, 4-layer 0.8 mm; 4.26-inch 800 x 480 SPI panel with front light and touch; derived from v0.2.8')
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2]); print('old texts removed', n)
