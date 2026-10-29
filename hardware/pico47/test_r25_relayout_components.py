"""R25 器件重排工具的纯几何回归测试。"""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "r25_router"))
try:
    from relayout_components import relayout
except ModuleNotFoundError as exc:
    if exc.name != "shapely":
        raise
    relayout = None


@unittest.skipIf(relayout is None, "该几何测试需要 shapely")
class RelayoutComponents(unittest.TestCase):
    def setUp(self):
        self.geometry = {
            "outline": [[[0, 0], [20, 0], [20, 20], [0, 20]]],
            "pads": [
                {"ref": "U710", "num": "1", "net": "SIG", "x": 5, "y": 5,
                 "polys": {"F.Cu": [[[4.8, 4.8], [5.2, 4.8], [5.2, 5.2], [4.8, 5.2]]]}},
                {"ref": "U710", "num": "8", "net": "GND", "x": 5, "y": 6,
                 "polys": {"F.Cu": [[[4.8, 5.8], [5.2, 5.8], [5.2, 6.2], [4.8, 6.2]]]}},
                {"ref": "J503", "num": "1", "net": "SIG2", "x": 10, "y": 5,
                 "polys": {"F.Cu": [[[9.8, 4.8], [10.2, 4.8], [10.2, 5.2], [9.8, 5.2]]]}},
            ],
            "tracks": [
                {"uuid": "sig-old", "layer": "F.Cu", "net": "SIG", "w": .15,
                 "x1": 5, "y1": 5, "x2": 6, "y2": 5},
                {"uuid": "gnd-keep", "layer": "B.Cu", "net": "GND", "w": .15,
                 "x1": 5, "y1": 6, "x2": 6, "y2": 6},
            ],
            "vias": [],
            "zones": [],
        }

    def test_move_preserves_pad_identity_and_rips_local_signal(self):
        before = {(p["ref"], p["num"]): p for p in self.geometry["pads"]}
        result, removed = relayout(self.geometry, {"U710": {"x": 8, "y": 8, "old_rot": 0, "rot": 0}})
        after = {(p["ref"], p["num"]): p for p in result["pads"]}
        self.assertEqual(set(before), set(after))
        moved = {(p["ref"], p["num"]): p for p in result["pads"]}
        self.assertEqual(moved[("U710", "1")]["net"], "SIG")
        self.assertIn("sig-old", removed)
        self.assertEqual(len(result["tracks"]), 1)
        self.assertEqual(result["tracks"][0]["net"], "GND")

    def test_in1_signal_is_rejected(self):
        bad = copy.deepcopy(self.geometry)
        bad["tracks"].append({"uuid": "bad", "layer": "In1.Cu", "net": "SIG", "w": .15,
                               "x1": 1, "y1": 1, "x2": 2, "y2": 2})
        with self.assertRaises(ValueError):
            relayout(bad, {"U710": {"x": 8, "y": 8, "old_rot": 0, "rot": 0}})

    def test_outline_adjustment_is_explicit(self):
        outline = [[[0, 0], [20, 0], [20, 20], [0, 20]]]
        result, _ = relayout(
            self.geometry,
            {"U710": {"x": 8, "y": 8, "old_rot": 0, "rot": 0}},
            outline=outline,
        )
        self.assertEqual(result["outline"], outline)

    def test_moved_pad_cannot_overlap_fixed_footprint(self):
        bad = copy.deepcopy(self.geometry)
        bad["pads"].append({
            "ref": "C999", "num": "1", "net": "OTHER", "x": 8, "y": 8,
            "polys": {"F.Cu": [[[7.8, 7.8], [8.2, 7.8], [8.2, 8.2], [7.8, 8.2]]]},
        })
        with self.assertRaises(ValueError):
            relayout(bad, {"U710": {"x": 8, "y": 8, "old_rot": 0, "rot": 0}})


if __name__ == "__main__":
    unittest.main()
