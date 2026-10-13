"""Separate actual native ground connectivity from zone-mode configuration."""
import copy
import math
import unittest
from pico47_ground_returns import summarize_ground_returns as summarize


def pads():
    return [
        {'uuid': 'a', 'ref': 'C804', 'pin': '2', 'net': 'GND', 'position_mm': [18.2, 105]},
        {'uuid': 'b', 'ref': 'J820', 'pin': 'MP', 'net': 'GND', 'position_mm': [6.865, 115.61]},
        {'uuid': 'c', 'ref': 'J820', 'pin': 'MP', 'net': 'GND', 'position_mm': [28.135, 115.61]},
    ]


class GroundReturnReport(unittest.TestCase):
    def test_all_ground_pads_connected(self):
        result = summarize(pads(), [['a', 'b', 'c']], 'C804', '2')
        self.assertTrue(result['all_ground_pads_connected_to_reference'])
        self.assertEqual(result['unconnected_ground_pad_count'], 0)
        self.assertEqual(result['groups_not_connected_to_reference'], [])

    def test_same_net_does_not_prove_same_physical_group(self):
        result = summarize(pads(), [['a', 'b'], ['c']], 'C804', '2')
        self.assertFalse(result['all_ground_pads_connected_to_reference'])
        self.assertEqual(result['ground_group_count'], 2)
        self.assertEqual(result['unconnected_ground_pad_count'], 1)
        self.assertEqual(result['groups_not_connected_to_reference'][0][0]['uuid'], 'c')

    def test_solid_zone_mode_is_not_a_connection(self):
        records = pads()
        for record in records:
            record['zone_connection'] = 'solid'
        result = summarize(records, [['a'], ['b', 'c']], 'C804', '2')
        self.assertFalse(result['all_ground_pads_connected_to_reference'])

    def test_duplicate_mounting_pad_numbers_remain_distinct(self):
        result = summarize(pads(), [['a', 'b'], ['c']], 'C804', '2')
        isolated = result['groups_not_connected_to_reference'][0][0]
        self.assertEqual((isolated['ref'], isolated['pin']), ('J820', 'MP'))
        self.assertEqual(isolated['position_mm'], [28.135, 115.61])

    def test_reference_group_not_assumed_to_be_largest(self):
        result = summarize(pads(), [['a'], ['b', 'c']], 'C804', '2')
        self.assertEqual(result['reference_group_pad_count'], 1)
        self.assertEqual(result['unconnected_ground_pad_count'], 2)

    def test_input_order_does_not_change_report(self):
        first = summarize(pads(), [['a'], ['b'], ['c']], 'C804', '2')
        second = summarize(list(reversed(pads())), [['c'], ['b'], ['a']], 'C804', '2')
        self.assertEqual(first, second)

    def test_no_input_mutation(self):
        records = pads(); groups = [['a', 'b'], ['c']]
        before = copy.deepcopy((records, groups))
        summarize(records, groups, 'C804', '2')
        self.assertEqual((records, groups), before)

    def test_connected_report_does_not_grant_release(self):
        result = summarize(pads(), [['a', 'b', 'c']], 'C804', '2')
        self.assertEqual(result['scope'], 'connectivity_only_not_physical_qualification')
        self.assertNotIn('manufacturing_release', result)

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError): summarize([], [], 'C804', '2')

    def test_missing_group_evidence_rejected(self):
        with self.assertRaises(ValueError): summarize(pads(), [], 'C804', '2')

    def test_missing_ground_pad_in_groups_rejected(self):
        with self.assertRaises(ValueError): summarize(pads(), [['a', 'b']], 'C804', '2')

    def test_unknown_native_pad_rejected(self):
        with self.assertRaises(ValueError): summarize(pads(), [['a', 'b', 'c', 'x']], 'C804', '2')

    def test_repeated_uuid_in_group_rejected(self):
        with self.assertRaises(ValueError): summarize(pads(), [['a', 'b', 'b', 'c']], 'C804', '2')

    def test_overlapping_groups_rejected(self):
        with self.assertRaises(ValueError): summarize(pads(), [['a', 'b'], ['b', 'c']], 'C804', '2')

    def test_duplicated_inventory_uuid_rejected(self):
        records = pads(); records.append(copy.deepcopy(records[0]))
        with self.assertRaises(ValueError): summarize(records, [['a', 'b', 'c']], 'C804', '2')

    def test_ambiguous_reference_pad_rejected(self):
        with self.assertRaises(ValueError): summarize(pads(), [['a', 'b', 'c']], 'J820', 'MP')

    def test_unknown_reference_pad_rejected(self):
        with self.assertRaises(ValueError): summarize(pads(), [['a', 'b', 'c']], 'U999', '1')

    def test_non_ground_pad_rejected(self):
        records = pads(); records[2]['net'] = 'P47_VNEG'
        with self.assertRaises(ValueError): summarize(records, [['a', 'b'], ['c']], 'C804', '2')

    def test_invalid_coordinates_rejected(self):
        for coordinates in (None, [1], [1, 2, 3], [math.nan, 0], [math.inf, 0], [True, 0], ['1', 0]):
            with self.subTest(coordinates=coordinates):
                records = pads(); records[0]['position_mm'] = coordinates
                with self.assertRaises(ValueError): summarize(records, [['a', 'b', 'c']], 'C804', '2')

    def test_malformed_identity_and_group_rejected(self):
        for group in (['a', 'b', 'c'], [], 7, ['a', None, 'b', 'c']):
            evidence = group if group == ['a', 'b', 'c'] else [group]
            with self.assertRaises(ValueError): summarize(pads(), evidence, 'C804', '2')
        for field in ('uuid', 'ref', 'pin'):
            records = pads(); records[0][field] = ''
            with self.assertRaises(ValueError): summarize(records, [['a', 'b', 'c']], 'C804', '2')

    def test_set_groups_supported(self):
        result = summarize(pads(), [frozenset({'a', 'b'}), {'c'}], 'C804', '2')
        self.assertEqual(result['ground_group_count'], 2)

    def test_added_ground_connection_reduces_disconnected_count(self):
        before = summarize(pads(), [['a', 'b'], ['c']], 'C804', '2')
        after = summarize(pads(), [['a', 'b', 'c']], 'C804', '2')
        self.assertEqual(before['unconnected_ground_pad_count'] - after['unconnected_ground_pad_count'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
