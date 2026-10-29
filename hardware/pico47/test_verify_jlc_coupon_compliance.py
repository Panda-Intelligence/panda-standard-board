#!/usr/bin/env python3
"""Unit tests for JLCPCB / JLC EDA 10x10cm coupon compliance verification."""
import unittest
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from verify_jlc_coupon_compliance import (
    polygon_area,
    trace_single_closed_outline,
    parse_stackup_policy,
)


class TestJlcCouponCompliance(unittest.TestCase):
    def test_single_closed_outline_core_sub10cm(self):
        pts = [
            (36.0, 32.0),
            (73.0, 32.0),
            (73.0, 131.0),
            (42.12, 131.0),
            (42.12, 125.45),
            (32.88, 125.45),
            (32.88, 131.0),
            (2.0, 131.0),
            (2.0, 121.0),
            (40.0, 121.0),
            (40.0, 70.0),
            (36.0, 70.0),
        ]
        segs = list(zip(pts, pts[1:] + pts[:1]))
        loop = trace_single_closed_outline(segs)
        xs = [p[0] for p in loop]
        ys = [p[1] for p in loop]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        self.assertEqual(w, 71.0)
        self.assertEqual(h, 99.0)
        self.assertTrue(10.0 <= w <= 100.0 and 10.0 <= h <= 100.0)
        self.assertAlmostEqual(polygon_area(loop), 3747.716, places=2)

    def test_reject_disjoint_panelized_outline(self):
        segs = [
            ((0.0, 0.0), (20.0, 0.0)),
            ((20.0, 0.0), (20.0, 20.0)),
            ((20.0, 20.0), (0.0, 20.0)),
            ((0.0, 20.0), (0.0, 0.0)),
            ((30.0, 0.0), (50.0, 0.0)),
        ]
        with self.assertRaises(ValueError):
            trace_single_closed_outline(segs)

    def test_parse_stackup_policy_green_enig(self):
        sample = """
        (kicad_pcb
          (title_block
            (title "PANDA47 Core 71x99mm 4L-GREEN-ENIG SINGLE-BOARD")
            (rev "E02-R25-JLC10X10-CORE-20261029")
            (comment 2 "Unique Build ID: P47-CORE-20261029-7684F0CC")
          )
          (setup
            (stackup
              (layer "F.Mask" (type "Top Solder Mask") (color "Green"))
              (layer "B.Mask" (type "Bottom Solder Mask") (color "Green"))
              (copper_finish "ENIG")
            )
          )
        )
        """
        st = parse_stackup_policy(sample)
        self.assertTrue(st["four_layer_green_mask_compliant"])
        self.assertTrue(st["enig_or_osp_ready"])
        self.assertEqual(st["copper_finish"], "ENIG")
        self.assertIn("Unique Build ID:", st["unique_build_comment"])


if __name__ == "__main__":
    unittest.main()
