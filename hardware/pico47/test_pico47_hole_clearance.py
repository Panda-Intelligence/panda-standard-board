"""Regressions for the native J503 NPTH/via clearance failure."""
import math
import unittest
from pico47_hole_clearance import npth_annulus_allowance, round_npth_copper_clearance


class NpthClearance(unittest.TestCase):
    def test_core_045_025_annulus(self):
        self.assertAlmostEqual(npth_annulus_allowance(.45,.25),.10)
    def test_display_060_030_annulus(self):
        self.assertAlmostEqual(npth_annulus_allowance(.60,.30),.15)
    def test_diameter_cannot_equal_drill(self):
        with self.assertRaises(ValueError):npth_annulus_allowance(.25,.25)
    def test_drill_cannot_exceed_copper(self):
        with self.assertRaises(ValueError):npth_annulus_allowance(.25,.45)
    def test_invalid_diameters_rejected(self):
        for value in (0,-1,True,'0.45',math.nan,math.inf,-math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):npth_annulus_allowance(value,.25)
                with self.assertRaises(ValueError):npth_annulus_allowance(.45,value)
    def test_original_j503_violation_matches_native_rounding(self):
        gap=round_npth_copper_clearance(math.dist((54.175,100.3),(54.54,99.5)),.9906,.45)
        self.assertAlmostEqual(gap,.159,places=3)
        self.assertLess(gap,.25)
    def test_drill_gap_would_falsely_appear_valid(self):
        distance=math.dist((54.175,100.3),(54.54,99.5))
        drill_gap=distance-(.9906+.25)/2
        copper_gap=round_npth_copper_clearance(distance,.9906,.45)
        self.assertGreater(drill_gap,.25)
        self.assertLess(copper_gap,.25)
        self.assertAlmostEqual(drill_gap-copper_gap,npth_annulus_allowance(.45,.25))
    def test_exact_native_hole_clearance_boundary(self):
        self.assertAlmostEqual(round_npth_copper_clearance(.9703,.9906,.45),.25)
    def test_reviewed_offset_clears_hole_not_other_obstacles(self):
        # The PCB transaction must still check the nearby power trace separately.
        gap=round_npth_copper_clearance(math.dist((54.175,100.425),(54.54,99.5)),.9906,.45)
        self.assertGreater(gap,.25)
    def test_overlapping_copper_returns_negative_gap(self):
        self.assertLess(round_npth_copper_clearance(.1,.99,.45),0)
    def test_concentric_returns_negative_gap(self):
        self.assertAlmostEqual(round_npth_copper_clearance(0,1,.5),-.75)
    def test_invalid_center_distances_rejected(self):
        for value in (-.1,True,'1',math.nan,math.inf):
            with self.assertRaises(ValueError):round_npth_copper_clearance(value,1,.5)
    def test_invalid_hole_or_via_diameters_rejected(self):
        for value in (0,-.1,True,'1',math.nan,math.inf):
            with self.assertRaises(ValueError):round_npth_copper_clearance(1,value,.5)
            with self.assertRaises(ValueError):round_npth_copper_clearance(1,1,value)
    def test_extra_annulus_is_scale_invariant(self):
        for scale in (.5,1,2,10):
            self.assertAlmostEqual(npth_annulus_allowance(.45*scale,.25*scale),.1*scale)


if __name__=='__main__':unittest.main(verbosity=2)
