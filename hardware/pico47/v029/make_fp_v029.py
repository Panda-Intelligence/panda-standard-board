"""make_fp_v029.py lib_dir: writes the two footprints v0.2.9 adds to the library.
- FPC_XKB_X05A10H34G: land pattern from the XKB X05A10H drawing (A1, 2024-12-13), 34 poles: A 19.00, C 16.50, D 18.38;
  signal lands 0.30 x 0.80, anchors 0.40 x 0.80, rows 2.5 mm apart (same rule as the 6-pin footprint of this library).
  Pads at the top, mouth at the bottom (y +1.9); pad 1 on the left. Connector height 1.0 mm.
- DFN-6-1EP_2x2mm_P0.65mm_EP1x1.6mm: copy of the KiCad library footprint (AW9967DNR land pattern: 6 x 0.35, pitch 0.65,
  exposed pad 1.0 x 1.6)."""
import shutil, sys, uuid
lib = sys.argv[1]
def u(): return str(uuid.uuid4())
def prop(n, v, y):
    return f'''\t(property "{n}" "{v}"\n\t\t(at 0 {y} 0)\n\t\t(layer "F.Fab")\n\t\t(hide yes)\n\t\t(uuid "{u()}")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n'''
def rect(x0, y0, x1, y1, w, layer):
    return f'''\t(fp_rect\n\t\t(start {x0} {y0})\n\t\t(end {x1} {y1})\n\t\t(stroke\n\t\t\t(width {w})\n\t\t\t(type solid)\n\t\t)\n\t\t(fill no)\n\t\t(layer "{layer}")\n\t\t(uuid "{u()}")\n\t)\n'''
def pad(n, x, y, w, h):
    return f'''\t(pad "{n}" smd rect\n\t\t(at {x:g} {y:g})\n\t\t(size {w} {h})\n\t\t(layers "F.Cu" "F.Mask" "F.Paste")\n\t\t(uuid "{u()}")\n\t)\n'''
s = '(footprint "FPC_XKB_X05A10H34G"\n\t(version 20260206)\n\t(generator "pcbnew")\n\t(generator_version "10.0")\n\t(layer "F.Cu")\n'
s += '\t(descr "XKB X05A10H34G: 34-pin dual-contact back-flip FPC connector, 0.5 mm pitch, 0.3 mm FPC, 1.0 mm high. Signal lands 0.3x0.8, anchors 0.4x0.8 at 18.38 mm, rows 2.5 mm apart.")\n'
s += '\t(tags "XKB X05A10H34G FPC 34pin 0.5mm")\n'
s += prop('Reference', 'J820', -3) + prop('Value', 'X05A10H34G', 3) + prop('Datasheet', '', 0) + prop('Description', '', 0)
s += '\t(attr smd)\n'
s += rect(-9.75, -1.9, 9.75, 2.15, 0.05, 'F.CrtYd') + rect(-9.5, -1.65, 9.5, 1.9, 0.1, 'F.Fab')
s += f'''\t(fp_circle\n\t\t(center -8.675 -1.986)\n\t\t(end -8.525 -1.986)\n\t\t(stroke\n\t\t\t(width 0.1)\n\t\t\t(type solid)\n\t\t)\n\t\t(fill no)\n\t\t(layer "F.SilkS")\n\t\t(uuid "{u()}")\n\t)\n'''
for i in range(34):
    s += pad(i + 1, -8.25 + 0.5 * i, -1.25, 0.3, 0.8)
s += pad('S1', -9.19, 1.25, 0.4, 0.8) + pad('S2', 9.19, 1.25, 0.4, 0.8)
s += '\t(embedded_fonts no)\n)\n'
open(f'{lib}/FPC_XKB_X05A10H34G.kicad_mod', 'w').write(s)
shutil.copy('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Package_DFN_QFN.pretty/DFN-6-1EP_2x2mm_P0.65mm_EP1x1.6mm.kicad_mod', lib)
print('footprints written')
