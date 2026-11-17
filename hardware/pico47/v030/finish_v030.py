"""finish_v030.py in.kicad_pcb out.kicad_pcb old_silk.json new_silk.json: last touches for the v0.3.0 board (KiCad Python).
- removes the two 3V3_AON stubs that ended on the removed 40-pin connector,
- drops the v0.2.4 printed texts that the v0.3.0 silkscreen spec does not repeat,
- sets the title block."""
import json, sys, pcbnew as P
T = P.ToMM
b = P.LoadBoard(sys.argv[1]); KEEP = []
old = {t['text'] for t in json.load(open(sys.argv[3]))['texts']}
for t in list(b.GetTracks()):
    if t.GetClass() != 'PCB_VIA' and t.GetNetname() == '3V3_AON' and t.GetLayer() == P.F_Cu and T(t.GetStart().y) > 110 and T(t.GetEnd().y) > 110 \
            and T(t.GetLength()) < 0.3 and any(abs(T(p.x) - x) < 0.2 and abs(T(p.y) - y) < 0.3 for p in (t.GetStart(), t.GetEnd()) for x, y in ((45.3, 110.85), (56.95, 110.6))):
        print('stub removed', T(t.GetStart().x), T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y)); b.Remove(t); KEEP.append(t)
n = 0
for d in list(b.GetDrawings()):
    if d.GetClass() == 'PCB_TEXT' and d.GetText() in old:
        b.Remove(d); KEEP.append(d); n += 1
tb = b.GetTitleBlock(); tb.SetTitle('Panda Standard 4.26 main board'); tb.SetRevision('v0.3.0 / E08'); tb.SetDate('2026-11-17')
tb.SetComment(0, '63 x 48 mm, 4-layer 0.8 mm; 4.26-inch 800 x 480 SPI panel; derived from v0.2.4')
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2]); print('old texts removed', n)
