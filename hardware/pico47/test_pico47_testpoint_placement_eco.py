"""Exact source-ECO and native-identity fixtures; not physical access approval."""
import copy
import json
import unittest
from pico47_testpoint_placement_eco import (
    expected_spec, validate_testpoint_eco, normalize_testpoint_groups,
    EXPECTED_IDENTITIES, NETS,
)


def groups(phase):
    return [[json.dumps(row, separators=(',', ':'))]
            for row in EXPECTED_IDENTITIES[phase].values()]


class ExactTestpointPlacement(unittest.TestCase):
    def test_exact_spec_accepted_without_release(self):
        spec = expected_spec()
        self.assertTrue(validate_testpoint_eco(spec))
        self.assertFalse(spec['manufacturing_release'])
        self.assertFalse(spec['new_copper_or_vias_required'])

    def test_exact_migration_normalizes_the_two_physical_pads(self):
        before = normalize_testpoint_groups(groups('before'), 'before', expected_spec())
        after = normalize_testpoint_groups(groups('after'), 'after', expected_spec())
        self.assertEqual(before, after)

    def test_other_pad_identity_must_remain_verbatim(self):
        data = groups('after')
        extra = json.dumps(['J820', '1', 3, 4, 'P47_D0', ['F.Cu']], separators=(',', ':'))
        data.append([extra])
        self.assertEqual(normalize_testpoint_groups(data, 'after', expected_spec())[-1], frozenset({extra}))

    def test_new_connection_may_join_a_previously_isolated_testpoint(self):
        data = groups('after')
        existing = json.dumps(['U810', '35', 5, 6, 'P47_VGH', ['F.Cu']], separators=(',', ':'))
        data[0].append(existing)
        result = normalize_testpoint_groups(data, 'after', expected_spec())
        self.assertEqual(len(result[0]), 2)
        self.assertIn(existing, result[0])

    def test_wrong_source_layout_binding_rejected(self):
        spec = expected_spec(); spec['previous_source_layout_sha256'] = '0' * 64
        with self.assertRaises(ValueError): validate_testpoint_eco(spec)

    def test_position_drift_rejected(self):
        spec = expected_spec(); spec['after']['TP803'][0] += 0.01
        with self.assertRaises(ValueError): validate_testpoint_eco(spec)

    def test_side_change_rejected(self):
        spec = expected_spec(); spec['after']['TP801'][3] = 'F.Cu'
        with self.assertRaises(ValueError): validate_testpoint_eco(spec)

    def test_signal_mapping_change_rejected(self):
        spec = expected_spec(); spec['pin_nets']['TP803']['1'] = 'P47_VNEG'
        with self.assertRaises(ValueError): validate_testpoint_eco(spec)

    def test_unapproved_release_rejected(self):
        for field in ('manufacturing_release', 'physical_probe_access_qualified'):
            spec = expected_spec(); spec[field] = True
            with self.assertRaises(ValueError): validate_testpoint_eco(spec)

    def test_integer_false_not_a_boolean_review_state(self):
        spec = expected_spec(); spec['manufacturing_release'] = 0
        with self.assertRaises(ValueError): validate_testpoint_eco(spec)

    def test_unreviewed_extra_field_rejected(self):
        spec = expected_spec(); spec['allow_any_pose'] = True
        with self.assertRaises(ValueError): validate_testpoint_eco(spec)

    def test_missing_testpoint_evidence_rejected(self):
        with self.assertRaises(ValueError): normalize_testpoint_groups(groups('after')[:1], 'after', expected_spec())

    def test_duplicate_native_identity_rejected(self):
        data = groups('after'); data.append(list(data[0]))
        with self.assertRaises(ValueError): normalize_testpoint_groups(data, 'after', expected_spec())

    def test_old_pose_cannot_be_asserted_as_new(self):
        with self.assertRaises(ValueError): normalize_testpoint_groups(groups('before'), 'after', expected_spec())

    def test_changed_native_pad_net_rejected(self):
        data = groups('after'); row = json.loads(data[0][0]); row[4] = 'GND'; data[0][0] = json.dumps(row)
        with self.assertRaises(ValueError): normalize_testpoint_groups(data, 'after', expected_spec())

    def test_evidence_is_not_mutated(self):
        data = groups('after'); before = copy.deepcopy(data)
        normalize_testpoint_groups(data, 'after', expected_spec())
        self.assertEqual(data, before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
