"""Exact TP805 source-layout/continuity tests; native capture is independently required."""
import copy
import json
import unittest
from pico47_vcom_testpoint_eco import (
    expected_spec, validate_vcom_testpoint_eco, normalize_vcom_testpoint_groups,
    EXPECTED_IDENTITIES, PREVIOUS_LAYOUT_SHA256,
)


def identity(row):
    return json.dumps(row, separators=(',', ':'))


class VcomTestpointEco(unittest.TestCase):
    def test_reviewed_source_change_is_exact(self):
        spec = expected_spec()
        self.assertTrue(validate_vcom_testpoint_eco(spec))
        self.assertEqual(spec['before'], {'TP805': [22.75, 108.0, 0.0, 'F.Cu']})
        self.assertEqual(spec['after'], {'TP805': [12.5, 103.0, 180.0, 'B.Cu']})
        self.assertEqual(spec['pin_nets'], {'TP805': {'1': 'P47_VCOM'}})
        self.assertTrue(spec['new_copper_or_vias_required'])
        self.assertFalse(spec['manufacturing_release'])

    def test_wrong_previous_layout_is_rejected(self):
        spec = expected_spec(); spec['previous_source_layout_sha256'] = '0' * 64
        with self.assertRaises(ValueError): validate_vcom_testpoint_eco(spec)
        self.assertEqual(len(PREVIOUS_LAYOUT_SHA256), 64)

    def test_any_other_pose_is_rejected(self):
        for field, position in [('before', [22.8,108,0,'F.Cu']), ('after',[12.6,103,180,'B.Cu']),
                                ('after',[12.5,103,0,'B.Cu']), ('after',[12.5,103,180,'F.Cu'])]:
            spec=expected_spec(); spec[field]['TP805']=position
            with self.assertRaises(ValueError):validate_vcom_testpoint_eco(spec)

    def test_manufacturing_and_probe_flags_cannot_be_self_approved(self):
        for field in ['manufacturing_release', 'physical_probe_access_qualified']:
            spec=expected_spec(); spec[field]=True
            with self.assertRaises(ValueError):validate_vcom_testpoint_eco(spec)

    def test_boolean_pose_or_integer_review_flag_is_rejected(self):
        spec=expected_spec(); spec['after']['TP805'][2]=True
        with self.assertRaises(ValueError):validate_vcom_testpoint_eco(spec)
        spec=expected_spec(); spec['new_copper_or_vias_required']=1
        with self.assertRaises(ValueError):validate_vcom_testpoint_eco(spec)

    def test_no_extra_moved_testpoint_is_allowed(self):
        spec=expected_spec(); spec['after']['TP803']=[1,2,0,'F.Cu']
        with self.assertRaises(ValueError):validate_vcom_testpoint_eco(spec)

    def test_wrong_electrical_net_is_rejected(self):
        spec=expected_spec(); spec['pin_nets']['TP805']['1']='GND'
        with self.assertRaises(ValueError):validate_vcom_testpoint_eco(spec)

    def test_normalizes_only_the_exact_moved_pad(self):
        other=identity(['U810','15',14100000,98950000,'P47_VCOM',['F.Cu']])
        a=[[identity(EXPECTED_IDENTITIES['before']['TP805']),other]]
        b=[[identity(EXPECTED_IDENTITIES['after']['TP805']),other]]
        self.assertEqual(normalize_vcom_testpoint_groups(a,'before',expected_spec()),
                         normalize_vcom_testpoint_groups(b,'after',expected_spec()))
        self.assertIn(other,normalize_vcom_testpoint_groups(b,'after',expected_spec())[0])

    def test_unreviewed_testpoint_identity_is_rejected(self):
        row=copy.deepcopy(EXPECTED_IDENTITIES['after']['TP805']);row[2]+=1000
        with self.assertRaises(ValueError):normalize_vcom_testpoint_groups([[identity(row)]],'after',expected_spec())

    def test_missing_or_duplicate_moved_pad_is_rejected(self):
        other=identity(['R1','1',0,0,'GND',['F.Cu']])
        with self.assertRaises(ValueError):normalize_vcom_testpoint_groups([[other]],'before',expected_spec())
        pad=identity(EXPECTED_IDENTITIES['before']['TP805'])
        with self.assertRaises(ValueError):normalize_vcom_testpoint_groups([[pad],[pad]],'before',expected_spec())

    def test_source_groups_remain_separate_until_native_route_joins_them(self):
        other=identity(['U810','15',14100000,98950000,'P47_VCOM',['F.Cu']])
        before=[[identity(EXPECTED_IDENTITIES['before']['TP805'])],[other]]
        normalized=normalize_vcom_testpoint_groups(before,'before',expected_spec())
        self.assertEqual(len(normalized),2)

    def test_malformed_groups_or_phase_are_rejected(self):
        pad=identity(EXPECTED_IDENTITIES['before']['TP805'])
        for groups,phase in [([], 'before'),([[]],'before'),([[pad]],'unknown'),([['not-json']],'before')]:
            with self.assertRaises((ValueError,json.JSONDecodeError)):normalize_vcom_testpoint_groups(groups,phase,expected_spec())

    def test_validation_and_normalization_do_not_mutate_input(self):
        spec=expected_spec();groups=[[identity(EXPECTED_IDENTITIES['before']['TP805'])]];old=copy.deepcopy((spec,groups))
        validate_vcom_testpoint_eco(spec);normalize_vcom_testpoint_groups(groups,'before',spec)
        self.assertEqual((spec,groups),old)


if __name__ == '__main__':unittest.main(verbosity=2)
