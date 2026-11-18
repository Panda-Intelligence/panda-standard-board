"""finish_v029.py in.kicad_pcb out.kicad_pcb old_silk.json new_silk.json: drops the printed texts of the base board and of
the new spec (info_silk_v02x.py must not remove texts itself) and sets the title block (KiCad Python)."""
import json, sys, pcbnew as P
b = P.LoadBoard(sys.argv[1]); KEEP = []
texts = {t['text'] for f in sys.argv[3:5] for t in json.load(open(f))['texts']} | {'FLV'}          # 'FLV' was the label of TP5 at its old place
n = 0
for d in list(b.GetDrawings()):
    if d.GetClass() == 'PCB_TEXT' and d.GetText() in texts:
        b.Remove(d); KEEP.append(d); n += 1
tb = b.GetTitleBlock(); tb.SetTitle('Panda Standard 4.7 main board'); tb.SetRevision('v0.2.9 / E14'); tb.SetDate('2026-11-18')
tb.SetComment(0, '63 x 48 mm, 4-layer 0.8 mm; E0470A03 panel on a 34-pin connector, two front-light drivers; derived from v0.2.8')
P.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[2]); print('old texts removed', n)
