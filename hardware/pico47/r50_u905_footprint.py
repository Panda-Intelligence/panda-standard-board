"""Write Panda47:U905_Core for AWINIC AW99703CSR (pin-compatible TI LM3697YFQ), WLCSP 1.64 x 1.24 mm, 0.4 mm pitch.
Used by build_pico47_single_r50.py (footprint_text()).
Datasheet AW99703 V1.2 p38-39: body 1.640 x 1.240 +/-0.025, 0.638 max height, 12 x dia 0.265 balls, land dia 0.240.
Top view: rows A..D along y (A top), columns 1..3 along x (1 left), pitch 0.400.
"""
import sys, uuid

PITCH = 0.4
LAND = 0.25
NAMES = {'A1': 'PWM', 'A2': 'SDA', 'A3': 'HWEN', 'B1': 'HVLED1', 'B2': 'SCL', 'B3': 'VIN',
         'C1': 'HVLED2', 'C2': 'AGND', 'C3': 'PGND', 'D1': 'HVLED3', 'D2': 'OUT', 'D3': 'SW'}
_count = [0]


def uid():
    _count[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'panda47-r50-u905-aw99703-{_count[0]}'))


def prop(name, value, at, layer='F.Fab', hide=True, size=1.0):
    return (f'\t(property "{name}" "{value}"\n\t\t(at {at[0]} {at[1]} 0)\n\t\t(layer "{layer}")\n'
            + ('\t\t(hide yes)\n' if hide else '')
            + f'\t\t(uuid "{uid()}")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n')


def line(x1, y1, x2, y2, layer, w):
    return (f'\t(fp_line\n\t\t(start {x1:.3f} {y1:.3f})\n\t\t(end {x2:.3f} {y2:.3f})\n\t\t(stroke\n\t\t\t(width {w})\n\t\t\t(type solid)\n\t\t)\n'
            f'\t\t(layer "{layer}")\n\t\t(uuid "{uid()}")\n\t)\n')


def rect(x0, y0, x1, y1, layer, w):
    return line(x0, y0, x1, y0, layer, w) + line(x1, y0, x1, y1, layer, w) + line(x1, y1, x0, y1, layer, w) + line(x0, y1, x0, y0, layer, w)


def footprint_text():
    _count[0] = 0
    out = ['(footprint "U905_Core"\n\t(version 20260206)\n\t(generator "pcbnew")\n\t(generator_version "10.0")\n\t(layer "F.Cu")\n',
           '\t(descr "AWINIC AW99703CSR WLCSP-12 1.64x1.24 mm 0.4 mm pitch (TI LM3697YFQ pin-compatible); datasheet V1.2 land 0.24 mm, NSMD")\n',
           '\t(tags "AW99703 LM3697 WLCSP12 DSBGA12 0.4mm")\n',
           prop('Reference', 'U905', (0, -1.6)), prop('Value', 'AW99703CSR', (0, 1.6)),
           prop('Datasheet', 'https://www.lcsc.com/product-detail/C5162547.html', (0, 0)),
           prop('Description', 'AWINIC AW99703 I2C boost white-LED driver, 3 HV sinks (2 used: cool/warm)', (0, 0)),
           '\t(attr smd)\n']
    BW, BH = 1.24, 1.64          # x span (3 columns) and y span (4 rows) of the body
    out.append(rect(-BW / 2, -BH / 2, BW / 2, BH / 2, 'F.Fab', 0.05))
    out.append(rect(-BW / 2 - 0.2, -BH / 2 - 0.2, BW / 2 + 0.2, BH / 2 + 0.2, 'F.CrtYd', 0.05))
    s = 0.1                      # silk outside the body, pin-1 corner open
    out.append(line(-BW / 2 - s, -BH / 2 + 0.35, -BW / 2 - s, BH / 2 + s, 'F.SilkS', 0.1))
    out.append(line(-BW / 2 - s, BH / 2 + s, BW / 2 + s, BH / 2 + s, 'F.SilkS', 0.1))
    out.append(line(BW / 2 + s, BH / 2 + s, BW / 2 + s, -BH / 2 - s, 'F.SilkS', 0.1))
    out.append(line(BW / 2 + s, -BH / 2 - s, -BW / 2 + 0.35, -BH / 2 - s, 'F.SilkS', 0.1))
    out.append(f'\t(fp_circle\n\t\t(center {-BW / 2 - 0.25:.3f} {-BH / 2 - 0.25:.3f})\n\t\t(end {-BW / 2 - 0.2:.3f} {-BH / 2 - 0.25:.3f})\n'
               f'\t\t(stroke\n\t\t\t(width 0.1)\n\t\t\t(type solid)\n\t\t)\n\t\t(fill yes)\n\t\t(layer "F.SilkS")\n\t\t(uuid "{uid()}")\n\t)\n')
    for r, row in enumerate('ABCD'):
        for c in range(3):
            num = f'{row}{c + 1}'
            x, y = (c - 1) * PITCH, (r - 1.5) * PITCH
            out.append(f'\t(pad "{num}" smd circle\n\t\t(at {x:.3f} {y:.3f})\n\t\t(size {LAND} {LAND})\n'
                       f'\t\t(layers "F.Cu" "F.Mask" "F.Paste")\n\t\t(solder_mask_margin 0.035)\n'
                       f'\t\t(pinfunction "{NAMES[num]}")\n\t\t(pintype "passive")\n\t\t(uuid "{uid()}")\n\t)\n')
    out.append('\t(embedded_fonts no)\n)\n')
    return ''.join(out)


if __name__ == '__main__':
    open(sys.argv[1], 'w').write(footprint_text())
