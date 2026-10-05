"""Reject obsolete whole-product visuals until the actual <=7mm relayout exists.

The earlier 22mm nominal study is retained in Git history, not accepted as the
product. Passing a source-allocation budget cannot authorize a populated render.
"""
from pathlib import Path
import argparse
import json
import math
import sys
import unittest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R/'hardware/thin18-compact'))
from seven_mm_layout import block_obsolete_product_export
CONTRACT = R/'hardware/thin18-compact/split-c1-prototype-enclosure.json'


def screen(c, metadata=None):
    dims = c.get('outer_dimensions_mm', [])
    if len(dims) != 3 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v <= 0 for v in dims):
        raise ValueError('Invalid native product dimensions')
    if dims[2] > 7:
        raise ValueError('Rejected product: enclosure thickness exceeds the user maximum of 7mm. Do not scale the existing 22mm scene.')
    planes = [c.get('front_top_z_mm'), c.get('rear_bottom_z_mm')]
    if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in planes) or abs(planes[0]-planes[1]-dims[2]) > 1e-8:
        raise ValueError('A thickness label is not the actual shell-plane separation')
    block_obsolete_product_export()


class Tests(unittest.TestCase):
    def test_22mm_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exceeds'):screen({'outer_dimensions_mm':[112,75,22]})
    def test_scaled_label_rejected(self):
        with self.assertRaisesRegex(ValueError, 'plane'):screen({'outer_dimensions_mm':[75,112,7], 'front_top_z_mm':12,'rear_bottom_z_mm':-10})
    def test_nominal_7_is_not_implementation(self):
        with self.assertRaisesRegex(ValueError, 'not implemented'):screen({'outer_dimensions_mm':[75,112,7],'front_top_z_mm':7,'rear_bottom_z_mm':0})
    def test_nan_rejected(self):
        with self.assertRaises(ValueError):screen({'outer_dimensions_mm':[75,112,float('nan')]})
    def test_missing_planes_rejected(self):
        with self.assertRaises(ValueError):screen({'outer_dimensions_mm':[75,112,7]})


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--output', type=Path)
    args=parser.parse_args()
    if args.test:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        raise SystemExit(0 if result.wasSuccessful() else 1)
    try:
        screen(json.loads(CONTRACT.read_text()), json.loads(args.metadata.read_text()) if args.metadata else None)
    except ValueError as error:
        print(str(error));raise SystemExit(2)
