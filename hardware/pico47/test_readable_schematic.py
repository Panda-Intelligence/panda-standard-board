"""2026-11-06 Claude：常规画法原理图生成器的纯几何检查（不需要 KiCad）。"""
import math
import unittest
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import readable_schematic as R


class FakeDesign:
    """Just enough of readable_schematic.Design for Baked parts."""

    def __init__(self, parts):
        self.parts, self.lib, self.pin_net = {}, {}, {}
        for ref, value, pins in parts:
            self.parts[ref] = dict(ref=ref, lib='Panda7:' + ref, value=value)
            self.lib['Panda7:' + ref] = dict(props=[('Reference', ref), ('Value', value), ('Footprint', '')],
                                             pins={n: dict(type='passive', name=nm, x=0, y=0) for n, nm in pins})
            for n, _ in pins:
                self.pin_net[(ref, n)] = f'{ref}_{n}'
        self.net_pins = defaultdict(list)

    def pins(self, ref):
        lib = self.lib[self.parts[ref]['lib']]['pins']
        return {n: dict(lib[n], num=n, net=self.pin_net[(ref, n)]) for n in lib}


class Spec(unittest.TestCase):
    def test_value_before_the_role(self):
        self.assertEqual(R.spec_of('100nF 25V X7R / U501 VDD_SPI'), '100nF 25V X7R')
        self.assertEqual(R.spec_of('10k'), '10k')

    def test_long_values_are_cut_on_a_word(self):
        s = R.spec_of('MF52D-103F3435-100 10k B3435 external NTC')
        self.assertLessEqual(len(s), 22)
        self.assertTrue('MF52D-103F3435-100 10k B3435 external NTC'.startswith(s))


class Geometry(unittest.TestCase):
    def setUp(self):
        self.D = FakeDesign([('R1', '10k', [('1', ''), ('2', '')]), ('D1', 'B5819W', [('1', 'K'), ('2', 'A')]),
                             ('TP1', 'X', [('1', '1')]), ('C1', '1u', [('1', ''), ('2', '')])])

    def test_stock_pins_sit_on_the_connection_grid(self):
        for name, (_, pins) in R.STOCK.items():
            for num, x, y, ang, ln in pins:
                for v in (x, y):
                    self.assertAlmostEqual(v / 1.27, round(v / 1.27), places=6, msg=f'{name}.{num}')

    def test_two_pin_parts_point_where_asked(self):
        for ref in ('R1', 'D1', 'C1'):
            for a in ('1', '2'):
                for d in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    b = R.Baked(self.D, ref, a, d)
                    at = (10.16, 20.32)
                    e = b.other_end(at)
                    L = math.dist(at, e)
                    self.assertGreater(L, 5.0)
                    self.assertAlmostEqual((e[0] - at[0]) / L, d[0], places=6)
                    self.assertAlmostEqual((e[1] - at[1]) / L, d[1], places=6)

    def test_rotated_pins_keep_numbers_and_point_into_the_body(self):
        b = R.Baked(self.D, 'D1', '2', (0, 1))           # anode on top, cathode below
        self.assertEqual({p['num'] for p in b.pins}, {'1', '2'})
        top = max(b.pins, key=lambda p: p['y'])
        self.assertEqual(top['num'], '2')
        self.assertEqual(top['ang'], 270)                 # a top pin points down into the body

    def test_test_point_body_goes_away_from_its_pin(self):
        up = R.Baked(self.D, 'TP1', '1', (0, -1))
        down = R.Baked(self.D, 'TP1', '1', (0, 1))
        self.assertLess(up.box[1], -1.0)                  # screen y up is negative
        self.assertGreater(down.box[3], 1.0)

    def test_primitive_rotation_is_exact(self):
        p = '(polyline (pts (xy 1.27 0) (xy 0 2.54)))'
        self.assertEqual(R.rot_prim(p, 1), '(polyline (pts (xy 0 1.27) (xy -2.54 0)))')
        self.assertEqual(R.rot_prim(R.rot_prim(p, 2), 2), p)


if __name__ == '__main__':
    unittest.main()
