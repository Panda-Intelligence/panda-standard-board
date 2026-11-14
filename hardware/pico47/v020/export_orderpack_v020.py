"""JLC order pack for Panda47 v0.2.x (KiCad Python; calls kicad-cli). PANDA47_VARIANT selects the board.

usage: export_orderpack_v020.py project_dir out_dir
Writes gerber/ + drill, JLCPCB_Panda47-v020_Gerber_4L_ENIG.zip, BOM_JLCPCB.csv, CPL_JLCPCB.csv,
REQUIRED-VIA-IN-PAD.csv, CONSIGNED-PARTS.csv and README-ORDER.md.
"""
import collections
import csv
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pcbnew as P

sys.path.insert(0, str(Path(__file__).resolve().parent))
import variant_v02x as VAR  # noqa: E402

CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
STEM = VAR.STEM
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
subprocess.run([CLI, 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-units', 'mm', '--excellon-separate-th', '--generate-map',
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
npth = [(fp.GetReference(), p) for fp in board.GetFootprints() for p in fp.Pads() if p.GetAttribute() == P.PAD_ATTRIB_NPTH]
npth_txt = ', '.join(f'{n} x {d} mm ({", ".join(sorted({r for r, p in npth if round(TO(p.GetDrillSize().x), 2) == d}))})'
                     for d, n in sorted(collections.Counter(round(TO(p.GetDrillSize().x), 2) for _, p in npth).items()))
bb = board.GetBoardEdgesBoundingBox()
OUTLINE = {'v020': 'L-shaped outline with a USB-C notch', 'v021': 'rectangular outline with a USB-C notch',
           'v022': 'rectangle with R4 bottom corners (Edge.Cuts arcs) and a USB-C notch',
           'v023': 'rectangle with R4 bottom corners (Edge.Cuts arcs) and a USB-C notch',
           'v024': 'R4 bottom corners (Edge.Cuts arcs), a USB-C notch and a 16.1 x 11.6 mm speaker notch in the '
                   'top-left corner'}[VAR.STEM[-4:]]
V = VAR.STEM[-4:]
SILK = ('pin-1 marks only (designators are on the assembly drawing, not printed)' if V < 'v022' else
        'top: pin-1 marks only; bottom: product / revision / date text, test-point names and the JLCJLCJLCJLC '
        'order-number marker (please print the order number there)')
EXTRA = '' if V < 'v022' else '''
Parts to check in the placement preview (since v0.2.2):
- D203 TJ-S1706SW6TGLC2G-A5 (C273616) is a SIDE-VIEW LED. Its lens must face the bottom board edge (towards the
  USB-C edge, +y in the board view, -Y in CPL coordinates); pin 1 = cathode on the left. Please confirm the
  lens direction in the preview, since the JLC library body may be drawn in another orientation.
- U506 GD25Q128EWIGR is WSON-8 6x5 with an exposed pad that is electrically floating (GigaDevice note); the EP
  land is soldered but has no net.
- J501 microSD (TF-122-CCP9) is rotated so the card mouth faces the left board edge.
'''
HAS_U907 = board.FindFootprintByReference('U907') is not None
U907 = '''- U907 XB7608AJ: CPC5 land per the XySemi datasheet, drawn as the datasheet top view rotated 180 deg: the three
  narrow leads face the top of the board view, pin 1 VDD at the right end of that row (silk dot). Please check
  the part orientation in the placement preview.
''' if HAS_U907 else ''
PIN1_U907 = 'U907, ' if HAS_U907 else ''
nfid = sum(1 for fp in board.GetFootprints() if fp.GetReference().startswith('FID'))
FID = f'\n| Fiducials | {nfid} on the top side, 1 mm copper in a 2 mm mask opening |' if nfid else ''
EXTRA24 = '' if V != 'v024' else '''
v0.2.4 notes:
- Via-in-pad is not only under QFN exposed pads: C504 pad 2 (0402), C817 pad 2 (0603) and U904 pin 7 each carry
  one GND via, and the L802 ground pad carries two. All vias in pads need the resin plug + plated cap.
- J302 (JST BM03B-ACHSS) takes the cell pack lead and J507 (MHF4) the antenna pigtail; both are plugged in at final
  assembly. Only the two speaker leads are soldered by hand, to J502.
- H2 and H3 are reflow-soldered M1.6 nuts (Sinhoo SMTSO1610MTJ, C2928167) in plated 2.5 mm holes with a 4.2 mm pad.
  The nut body sits on the top side; its pilot goes into the hole. Please confirm these can be placed on a 0.8 mm
  board, and that paste is printed on the ring pad.
- MH1 (1.2 mm round) and MH2 (1.2 x 1.6 mm slot) are non-plated locating holes for the enclosure pins: keep them
  non-plated and to drill tolerance.
'''
(out / 'README-ORDER.md').write_text(f"""# Panda47 {VAR.VERSION} order pack

Not a manufacturing release: the panel / touch / front-light FPC connector poses still need checking against the
supplier drawing, and U810 is consigned.

| PCB option | Value |
|---|---|
| Layers | 4 (F / In1 GND / In2 / B) |
| Size (bounding box) | {TO(bb.GetWidth()):.1f} x {TO(bb.GetHeight()):.1f} mm, {OUTLINE} |
| Thickness | 0.8 mm |
| Surface finish | ENIG |
| Min track / space | 0.09 / 0.127 mm (0.0952 mm necks at fine-pitch pins) |
| Vias | {len(vias)}, drill {', '.join(f'{d} mm' for d in drills)} (no small-hole option needed) |
| Non-plated holes | {npth_txt or 'none'} |
| Silkscreen | {SILK} |
| Via-in-pad | {len(vip)} vias in pads (see REQUIRED-VIA-IN-PAD.csv): choose resin plug + plated cap |{FID}
| Assembly | top side only, {len(cpl)} placements, {len(groups)} BOM lines |
| Consigned | {', '.join(f'{r} {p}' for r, p in consigned)} |

Files: `{zpath.name}`, `BOM_JLCPCB.csv`, `CPL_JLCPCB.csv`.

Assembly notes (from JLC DFM on the earlier board, order Y4, all fixed here):
{U907}- SW201 / SW202 TS-1186E: locating-post holes provided (0.75 mm NPTH), place the switch with its posts.
- J820 X05A10L40G: hold-down pads per the XKB recommended layout.
- Pin 1 of U501, U810, U904, {PIN1_U907}Q901, Q902, J803, J804 and J820 is marked by a 0.3 mm silk dot; the other
  ICs carry the pin-1 mark of their standard footprint.
{EXTRA}{EXTRA24}""")
print(f'gerber zip {zpath.name}; {len(cpl)} placements; {len(groups)} BOM lines; {len(vias)} vias; via-in-pad {len(vip)}; '
      f'consigned {len(consigned)}')
