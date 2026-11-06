"""2026-11-06 Claude：R49 只把前光升压输入 VSYS_FL_IN 并入 VSYS_RAW。"""
import json
import math
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DELTA = json.loads((HERE / 'r25_router' / 'single_r49_frontlight_supply_delta.json').read_text())


class R49FrontlightSupplyDelta(unittest.TestCase):
    def test_scope_is_the_frontlight_input_only(self):
        self.assertEqual(DELTA['baseline_revision'], 'R48')
        self.assertFalse(DELTA['manufacturing_release'])
        self.assertEqual({(e['ref'], e['pad']) for e in DELTA['pad_net_edits']},
                         {('L905', '1'), ('R920', '1'), ('C920', '1')})
        for e in DELTA['pad_net_edits'] + DELTA['schematic_global_label_renames']:
            self.assertEqual((e['from_net'], e['to_net']), ('VSYS_FL_IN', 'VSYS_RAW'))
        self.assertEqual(len(DELTA['schematic_global_label_renames']), 3)

    def test_added_copper_is_power_width_on_signal_layers(self):
        self.assertTrue(DELTA['added_tracks'] and DELTA['added_vias'])
        for t in DELTA['added_tracks']:
            self.assertEqual(t['width_nm'], 400_000)
            self.assertIn(t['layer'], ('F.Cu', 'In2.Cu', 'B.Cu'))   # never In1, the ground plane
        for v in DELTA['added_vias']:
            self.assertEqual((v['diameter_nm'], v['drill_nm']), (400_000, 200_000))
        length = sum(math.dist(t['start_nm'], t['end_nm']) for t in DELTA['added_tracks']) / 1e6
        self.assertLess(length, 35.0)

    def test_fingerprints_bind_both_ends(self):
        for key in ('baseline_semantic_fingerprint', 'target_semantic_fingerprint',
                    'baseline_copper_fingerprint', 'target_copper_fingerprint'):
            self.assertRegex(DELTA[key], r'^[0-9a-f]{64}$')
        self.assertNotEqual(DELTA['baseline_copper_fingerprint'], DELTA['target_copper_fingerprint'])


if __name__ == '__main__':
    unittest.main()
