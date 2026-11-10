"""JLC order pack for Panda47 v0.2.0 (KiCad Python; calls kicad-cli).

usage: export_orderpack_v020.py project_dir out_dir
Writes gerber/ + drill, JLCPCB_Panda47-v020_Gerber_4L_ENIG.zip, BOM_JLCPCB.csv, CPL_JLCPCB.csv,
REQUIRED-VIA-IN-PAD.csv, CONSIGNED-PARTS.csv and README-ORDER.md.
"""
import csv
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pcbnew as P

CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
STEM = 'Panda47-v020'
TO = P.ToMM
CONSIGN = {'U810': 'SY7636ARMC (Silergy, LCSC C22451321, JLC stock 0)'}

proj, out = Path(sys.argv[1]), Path(sys.argv[2])
pcb = proj / f'{STEM}.kicad_pcb'
if out.exists():
    shutil.rmtree(out)
gdir = out / 'gerber'
gdir.mkdir(parents=True)
subprocess.run([CLI, 'pcb', 'export', 'gerbers', '--layers',
                'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts',
                '--no-protel-ext', '--output', str(gdir) + '/', str(pcb)], check=True, capture_output=True)
subprocess.run([CLI, 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-units', 'mm', '--generate-map',
                '--map-format', 'gerberx2', '--output', str(gdir) + '/', str(pcb)], check=True, capture_output=True)
zpath = out / f'JLCPCB_{STEM}_Gerber_4L_0.8mm_ENIG.zip'
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(gdir.iterdir()):
        z.write(f, f.name)

board = P.LoadBoard(str(pcb))
groups, cpl, consigned = {}, [], []
for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
    ref = fp.GetReference()
    attrs = fp.GetAttributes()
    if fp.IsDNP() or attrs & P.FP_EXCLUDE_FROM_POS_FILES or attrs & P.FP_EXCLUDE_FROM_BOM:
        continue
    pos = fp.GetPosition()
    cpl.append([ref, f'{TO(pos.x):.4f}mm', f'{-TO(pos.y):.4f}mm', 'Bottom' if fp.IsFlipped() else 'Top',
                f'{fp.GetOrientationDegrees() % 360:.2f}'])
    lcsc = fp.GetFieldText('LCSC') if fp.HasField('LCSC') else ''
    mpn = fp.GetFieldText('MPN') if fp.HasField('MPN') else fp.GetValue()
    key = lcsc or mpn
    g = groups.setdefault(key, dict(mpn=mpn, fp=fp.GetFPIDAsString().split(':')[-1], lcsc=lcsc, refs=[]))
    g['refs'].append(ref)
    if ref in CONSIGN:
        consigned.append([ref, CONSIGN[ref]])
with open(out / 'BOM_JLCPCB.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
    for g in sorted(groups.values(), key=lambda g: g['refs'][0]):
        w.writerow([g['mpn'], ','.join(g['refs']), g['fp'], g['lcsc']])
with open(out / 'CPL_JLCPCB.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    w.writerows(cpl)

# vias inside a copper pad of the same net (need resin fill + plated cap, IPC-4761 Type VII)
pads = [(fp.GetReference(), p) for fp in board.GetFootprints() for p in fp.Pads() if p.IsOnLayer(P.F_Cu)]
vip = []
for t in board.GetTracks():
    if t.GetClass() != 'PCB_VIA':
        continue
    for ref, p in pads:
        if p.GetNetname() == t.GetNetname() and p.HitTest(t.GetPosition()):
            vip.append([ref, p.GetNumber(), t.GetNetname(), f'{TO(t.GetPosition().x):.3f}', f'{TO(t.GetPosition().y):.3f}',
                        f'{TO(t.GetWidth(P.F_Cu)):.2f}', f'{TO(t.GetDrill()):.2f}'])
            break
with open(out / 'REQUIRED-VIA-IN-PAD.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Ref', 'Pad', 'Net', 'X_mm', 'Y_mm', 'Via_mm', 'Drill_mm'])
    w.writerows(vip)
with open(out / 'CONSIGNED-PARTS.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Designator', 'Part'])
    w.writerows(consigned)

vias = [t for t in board.GetTracks() if t.GetClass() == 'PCB_VIA']
drills = sorted({round(TO(v.GetDrill()), 2) for v in vias})
bb = board.GetBoardEdgesBoundingBox()
(out / 'README-ORDER.md').write_text(f"""# Panda47 v0.2.0 order pack

Not a manufacturing release: the panel / touch / front-light FPC connector poses still need checking against the
supplier drawing, and U810 is consigned.

| PCB option | Value |
|---|---|
| Layers | 4 (F / In1 GND / In2 / B) |
| Size (bounding box) | {TO(bb.GetWidth()):.1f} x {TO(bb.GetHeight()):.1f} mm, L-shaped outline with a USB-C notch |
| Thickness | 0.8 mm |
| Surface finish | ENIG |
| Min track / space | 0.09 / 0.127 mm (0.0952 mm necks at fine-pitch pins) |
| Vias | {len(vias)}, drill {', '.join(f'{d} mm' for d in drills)} (no small-hole option needed) |
| Via-in-pad | {len(vip)} vias in exposed pads (see REQUIRED-VIA-IN-PAD.csv): choose resin plug + plated cap |
| Assembly | top side only, {len(cpl)} placements, {len(groups)} BOM lines |
| Consigned | {', '.join(f'{r} {p}' for r, p in consigned)} |

Files: `{zpath.name}`, `BOM_JLCPCB.csv`, `CPL_JLCPCB.csv`.
""")
print(f'gerber zip {zpath.name}; {len(cpl)} placements; {len(groups)} BOM lines; {len(vias)} vias; via-in-pad {len(vip)}; '
      f'consigned {len(consigned)}')
