"""Exhaustive small-graph and negative fixtures for native pad-group repair."""
import unittest
from pico47_route_groups import repair_pairs


def partitions(items):
    if not items:
        yield []
        return
    first, *rest = items
    for remaining in partitions(rest):
        yield [{first}] + [set(group) for group in remaining]
        for index in range(len(remaining)):
            groups = [set(group) for group in remaining]
            groups[index].add(first)
            yield groups


class RepairTargetSelection(unittest.TestCase):
    def test_only_restore_broken_original_group(self):
        self.assertEqual(repair_pairs([{'a','b'},{'c'}], [{'a'},{'b'},{'c'}]), [(1,0)])

    def test_newly_joined_preexisting_open_does_not_hide_a_break(self):
        self.assertEqual(repair_pairs([{'a','b'},{'c'}], [{'a','c'},{'b'}]), [(1,0)])

    def test_fully_preserved_groups_need_no_repair(self):
        self.assertEqual(repair_pairs([{'a','b'},{'c'}], [{'a','b'},{'c'}]), [])

    def test_additional_connection_is_not_a_regression(self):
        self.assertEqual(repair_pairs([{'a','b'},{'c'}], [{'a','b','c'}]), [])

    def test_already_open_pins_not_implicitly_requested(self):
        self.assertEqual(repair_pairs([{'a'},{'b'},{'c'}], [{'a'},{'b'},{'c'}]), [])

    def test_three_fragments_all_repair_pairs(self):
        self.assertEqual(repair_pairs([{'a','b','c'}], [{'a'},{'b'},{'c'}]), [(1,0),(2,0),(2,1)])

    def test_group_order_changes_not_physical_connection(self):
        self.assertEqual(repair_pairs([{'a','b'},{'c'}], [{'c'},{'a','b'}]), [])

    def test_missing_pad_is_rejected(self):
        with self.assertRaises(ValueError): repair_pairs([{'a','b'}], [{'a'}])

    def test_extra_pad_is_rejected(self):
        with self.assertRaises(ValueError): repair_pairs([{'a'}], [{'a'},{'b'}])

    def test_missing_original_evidence_is_rejected(self):
        with self.assertRaises(ValueError): repair_pairs([], [{'a'}])

    def test_empty_group_is_rejected(self):
        with self.assertRaises(ValueError): repair_pairs([{'a'},set()], [{'a'}])

    def test_overlapping_original_groups_are_rejected(self):
        with self.assertRaises(ValueError): repair_pairs([{'a','b'},{'b'}], [{'a','b'}])

    def test_overlapping_live_groups_are_rejected(self):
        with self.assertRaises(ValueError): repair_pairs([{'a','b'}], [{'a','b'},{'b'}])

    def test_strings_not_accepted_as_pad_sets(self):
        with self.assertRaises(ValueError): repair_pairs(['a'], [{'a'}])

    def test_nonstring_pad_identity_is_rejected(self):
        with self.assertRaises(ValueError): repair_pairs([{1}], [{1}])

    def test_empty_pad_identity_is_rejected(self):
        with self.assertRaises(ValueError): repair_pairs([{''}], [{''}])

    def test_frozen_sets_are_supported(self):
        self.assertEqual(repair_pairs([frozenset({'a','b'})], [frozenset({'a'}),frozenset({'b'})]), [(1,0)])

    def test_exhaustive_five_pad_partitions(self):
        all_groups = list(partitions(list('abcde')))
        self.assertEqual(len(all_groups), 52)
        for original in all_groups:
            for live in all_groups:
                pairs = repair_pairs(original, live)
                preserved = all(any(group <= now for now in live) for group in original)
                self.assertEqual(not pairs, preserved, (original, live))
                expected = {(i,j) for i in range(len(live)) for j in range(i)
                            if any(group & live[i] and group & live[j] for group in original)}
                self.assertEqual(set(pairs), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
