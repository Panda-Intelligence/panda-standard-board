"""Exact R801 migration fixtures; synthetic evidence is not native acceptance."""
import copy
import json
import unittest
from pathlib import Path
from pico47_r801_placement_eco import (
    BEFORE, AFTER, EXPECTED_PAD_IDENTITIES, validate_r801_eco, normalize_r801_groups,
)


def spec():
    return json.loads(Path(__file__).with_name('ordered_core_layout.json').read_text())['display_r801_placement_eco']


def identity(row):
    return json.dumps(row, separators=(',', ':'))


def fixture(phase):
    a = EXPECTED_PAD_IDENTITIES[phase]
    cap = identity(['C809', '1', 26000000, 93000000, 'P47_VGH', ['F.Cu']])
    low = identity(['R802', '1', 26000000, 100000000, 'P47_VGH_FB', ['F.Cu']])
    return [frozenset([identity(a['1'])]), frozenset([cap]),
            frozenset([identity(a['2']), low])]


def preserved(before, after):
    return all(any(old <= new for new in after) for old in before)


class R801PlacementEco(unittest.TestCase):
    def test_exact_source_spec_passes(self):
        self.assertTrue(validate_r801_eco(spec()))

    def test_known_two_pad_move_can_preserve_logical_connections(self):
        old = normalize_r801_groups(fixture('before'), 'before', spec())
        new = normalize_r801_groups(fixture('after'), 'after', spec())
        self.assertEqual(old, new)

    def test_new_vgh_connection_preserves_previous_separate_groups(self):
        old = normalize_r801_groups(fixture('before'), 'before', spec())
        new = normalize_r801_groups(fixture('after'), 'after', spec())
        joined = [new[0] | new[1], new[2]]
        self.assertTrue(preserved(old, joined))

    def test_broken_feedback_is_still_detected(self):
        old = normalize_r801_groups(fixture('before'), 'before', spec())
        new = normalize_r801_groups(fixture('after'), 'after', spec())
        split = [new[0], new[1]] + [frozenset([x]) for x in new[2]]
        self.assertFalse(preserved(old, split))

    def test_unrelated_pad_movement_is_not_normalized_away(self):
        old = normalize_r801_groups(fixture('before'), 'before', spec())
        groups = fixture('after')
        changed = json.loads(next(iter(groups[1]))); changed[2] += 100000
        groups[1] = frozenset([identity(changed)])
        new = normalize_r801_groups(groups, 'after', spec())
        self.assertFalse(preserved(old, new))

    def test_unreviewed_coordinate_is_rejected(self):
        groups = fixture('after'); row = list(EXPECTED_PAD_IDENTITIES['after']['1']); row[2] += 1
        groups[0] = frozenset([identity(row)])
        with self.assertRaises(ValueError): normalize_r801_groups(groups, 'after', spec())

    def test_wrong_side_is_rejected(self):
        groups = fixture('after'); row = copy.deepcopy(EXPECTED_PAD_IDENTITIES['after']['1']); row[-1] = ['F.Cu']
        groups[0] = frozenset([identity(row)])
        with self.assertRaises(ValueError): normalize_r801_groups(groups, 'after', spec())

    def test_swapped_pin_net_is_rejected(self):
        groups = fixture('after'); row = copy.deepcopy(EXPECTED_PAD_IDENTITIES['after']['1']); row[4] = 'GND'
        groups[0] = frozenset([identity(row)])
        with self.assertRaises(ValueError): normalize_r801_groups(groups, 'after', spec())

    def test_missing_r801_pad_fails_closed(self):
        groups = fixture('after'); groups.pop(0)
        with self.assertRaises(ValueError): normalize_r801_groups(groups, 'after', spec())

    def test_duplicate_r801_identity_rejected(self):
        groups = fixture('after'); groups.append(groups[0])
        with self.assertRaises(ValueError): normalize_r801_groups(groups, 'after', spec())

    def test_old_physical_evidence_cannot_claim_new_side(self):
        with self.assertRaises(ValueError): normalize_r801_groups(fixture('before'), 'after', spec())

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError): normalize_r801_groups(fixture('after'), 'any', spec())

    def test_wrong_reference_not_a_general_eco_permission(self):
        data = spec(); data['reference'] = 'U810'
        with self.assertRaises(ValueError): validate_r801_eco(data)

    def test_previous_layout_hash_is_mandatory(self):
        data = spec(); data['previous_source_layout_sha256'] = '0' * 64
        with self.assertRaises(ValueError): validate_r801_eco(data)

    def test_proposed_alternative_pose_is_not_implicitly_authorized(self):
        data = spec(); data['after'][0] += 0.1
        with self.assertRaises(ValueError): validate_r801_eco(data)

    def test_manufacturing_claim_cannot_be_added_to_source_spec(self):
        for key in ['assembly_height_and_process_qualified', 'manufacturing_release']:
            data = spec(); data[key] = True
            with self.assertRaises(ValueError): validate_r801_eco(data)

    def test_numeric_truthy_flags_rejected(self):
        data = spec(); data['requires_two_sided_assembly'] = 1
        with self.assertRaises(ValueError): validate_r801_eco(data)

    def test_extra_scope_key_rejected(self):
        data = spec(); data['other_moved_components'] = ['R802']
        with self.assertRaises(ValueError): validate_r801_eco(data)

    def test_inputs_are_not_modified(self):
        groups, data = fixture('after'), spec(); previous = copy.deepcopy((groups, data))
        normalize_r801_groups(groups, 'after', data)
        self.assertEqual((groups, data), previous)

    def test_missing_malformed_groups_rejected(self):
        for groups in [None, [], [frozenset()], [['not-json']]]:
            with self.assertRaises((ValueError, TypeError)):
                normalize_r801_groups(groups, 'after', spec())


if __name__ == '__main__':
    unittest.main(verbosity=2)
