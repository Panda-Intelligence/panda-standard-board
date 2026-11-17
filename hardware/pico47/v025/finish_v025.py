"""finish_v025.py in.kicad_pcb out.kicad_pcb old_silk.json new_silk.json: drops every printed text of both specs
(info_silk_v02x.py prints the new set; it must not remove texts itself, pcbnew then loses its footprint proxies) and
sets the title block (KiCad Python)."""
import json, sys, pcbnew as P
b = P.LoadBoard(sys.argv[1]); KEEP = []
old = {t['text'] for t in json.load(open(sys.argv[3]))['texts']} | {t['text'] for t in json.load(open(sys.argv[4]))['texts']}
for d in list(b.GetDrawings()):
    if d.GetClass() == 'PCB_TEXT' and d.GetText() in old: b.Remove(d); KEEP.append(d)
tb = b.GetTitleBlock(); tb.SetTitle('Panda Standard 4.7 main board'); tb.SetRevision('v0.2.5 / E09'); tb.SetDate('2026-11-17')
tb.SetCompany('Panda Intelligence'); tb.SetComment(0, '63 x 48 mm, 4-layer 0.8 mm; v0.2.4 plus the three E09 review fixes'); tb.SetComment(1, '')
b.Save(sys.argv[2])
