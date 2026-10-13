#!/usr/bin/env python3
"""Positive/negative evidence guards. These tests never execute manufacturing tools."""
from pathlib import Path
import tempfile
import unittest
import capture_pico47_checkpoint as capture


def counts(opens=4, warnings=2):
    return dict(drc_errors=0, drc_warnings=warnings, open=opens, parity=0, erc=0)


def reports():
    return ({'violations': [{'severity': 'warning'}], 'unconnected_items': [{}],
             'schematic_parity': []}, {'sheets': [{'violations': []}]})


class NativeEvidence(unittest.TestCase):
    def test_exact_separate_counts(self):
        d, e = reports()
        d['violations'].append({'severity': 'error'})
        d['schematic_parity'] = [{}, {}]
        e['sheets'].append({'violations': [{}]})
        self.assertEqual(capture.counts_from_reports(d, e),
                         dict(drc_errors=1, drc_warnings=1, open=1, parity=2, erc=1))
    def test_unconnected_items_are_not_hidden_in_zero_drc(self):
        d, e = reports(); d['violations'] = []
        self.assertEqual(capture.counts_from_reports(d, e)['open'], 1)
    def test_missing_drc_field_is_not_zero(self):
        for key in ('violations', 'unconnected_items', 'schematic_parity'):
            with self.subTest(key=key):
                d, e = reports(); del d[key]
                with self.assertRaises(ValueError): capture.counts_from_reports(d, e)
    def test_wrong_drc_field_type(self):
        for key in ('violations', 'unconnected_items', 'schematic_parity'):
            d, e = reports(); d[key] = {}
            with self.assertRaises(ValueError): capture.counts_from_reports(d, e)
    def test_unknown_severity_is_not_ignored(self):
        for severity in ('ignore', 'info', None):
            d, e = reports(); d['violations'][0]['severity'] = severity
            with self.assertRaises(ValueError): capture.counts_from_reports(d, e)
    def test_missing_erc_sheets(self):
        d, _ = reports()
        with self.assertRaises(ValueError): capture.counts_from_reports(d, {})
    def test_empty_erc_sheets(self):
        d, _ = reports()
        with self.assertRaises(ValueError): capture.counts_from_reports(d, {'sheets': []})
    def test_missing_sheet_violations(self):
        d, _ = reports()
        with self.assertRaises(ValueError): capture.counts_from_reports(d, {'sheets': [{}]})
    def test_wrong_sheet_violation_type(self):
        d, _ = reports()
        with self.assertRaises(ValueError):
            capture.counts_from_reports(d, {'sheets': [{'violations': 0}]})


class NonRegression(unittest.TestCase):
    def test_actual_improvement_can_be_a_partial_checkpoint(self):
        self.assertTrue(capture.require_progress(counts(), counts(3, 1), True))
    def test_equal_counts_allowed_for_unchanged_second_board(self):
        self.assertTrue(capture.require_progress(counts(), counts(), True))
    def test_zero_counts_are_only_engineering_acceptance(self):
        self.assertTrue(capture.require_progress(counts(), counts(0, 0), True))
    def test_lower_opens_do_not_excuse_lost_pad_connections(self):
        with self.assertRaises(ValueError): capture.require_progress(counts(), counts(0, 0), False)
    def test_truthy_values_do_not_replace_native_continuity(self):
        for value in (1, 'true', None):
            with self.assertRaises(ValueError): capture.require_progress(counts(), counts(), value)
    def test_more_opens_rejected_even_with_fewer_warnings(self):
        with self.assertRaises(ValueError): capture.require_progress(counts(), counts(5, 0), True)
    def test_more_warnings_rejected_even_with_fewer_opens(self):
        with self.assertRaises(ValueError): capture.require_progress(counts(), counts(0, 3), True)
    def test_errors_parity_erc_block_even_zero_opens(self):
        for key in ('drc_errors', 'parity', 'erc'):
            after = counts(0, 0); after[key] = 1
            with self.assertRaises(ValueError): capture.require_progress(counts(), after, True)
    def test_bad_baseline_also_rejected(self):
        for key in ('drc_errors', 'parity', 'erc'):
            before = counts(); before[key] = 1
            with self.assertRaises(ValueError): capture.require_progress(before, counts(), True)
    def test_missing_count_rejected(self):
        after = counts(); del after['open']
        with self.assertRaises(ValueError): capture.require_progress(counts(), after, True)
    def test_bool_negative_fraction_string_counts_rejected(self):
        for value in (True, -1, 1.5, '0'):
            after = counts(); after['open'] = value
            with self.assertRaises(ValueError): capture.require_progress(counts(), after, True)




class CrossBuildContinuity(unittest.TestCase):
    def test_regenerated_uuids_preserve_same_physical_connection(self):
        old = capture.relabel_groups([['a','b']], {'a':'U1.1@0,0:A','b':'R1.2@1,0:A'})
        new = capture.relabel_groups([['x','y']], {'x':'U1.1@0,0:A','y':'R1.2@1,0:A'})
        self.assertTrue(capture.preserves_groups(old, new))
    def test_ground_island_split_rejected_despite_same_pad_inventory(self):
        identities = {'a':'J601.32:GND','b':'U501.EP:GND'}
        old = capture.relabel_groups([['a','b']], identities)
        new = capture.relabel_groups([['a'],['b']], identities)
        self.assertFalse(capture.preserves_groups(old, new))
    def test_new_connection_merges_groups_without_loss(self):
        identities = {'a':'U1.1:A','b':'J1.1:A'}
        self.assertTrue(capture.preserves_groups(capture.relabel_groups([['a'],['b']], identities),
                                                capture.relabel_groups([['a','b']], identities)))
    def test_position_or_net_identity_change_rejected(self):
        a = capture.relabel_groups([['a']], {'a':'U1.1@0,0:A'})
        b = capture.relabel_groups([['b']], {'b':'U1.1@0,1:B'})
        self.assertFalse(capture.preserves_groups(a, b))
    def test_missing_identity_rejected(self):
        with self.assertRaises(ValueError): capture.relabel_groups([['a','b']], {'a':'U1.1'})
    def test_duplicate_physical_identity_rejected(self):
        with self.assertRaises(ValueError): capture.relabel_groups([['a','b']], {'a':'U1.1','b':'U1.1'})
    def test_repeated_number_at_distinct_positions_stays_distinct(self):
        groups = capture.relabel_groups([['a'],['b']], {'a':'U1.EP@0,0','b':'U1.EP@1,0'})
        self.assertEqual(len(groups), 2)
    def test_empty_groups_are_not_success(self):
        with self.assertRaises(ValueError): capture.relabel_groups([], {})
    def test_overlapping_groups_are_not_valid_evidence(self):
        with self.assertRaises(ValueError): capture.relabel_groups([['a'],['a']], {'a':'U1.1'})
    def test_extra_unmeasured_pad_is_rejected(self):
        with self.assertRaises(ValueError): capture.relabel_groups([['a']], {'a':'U1.1','b':'U1.2'})


class LibraryDefinition(unittest.TestCase):
    def test_regenerated_library_uuid_is_metadata(self):
        a = '(pad "1" (uuid "00000000-0000-0000-0000-000000000001"))'
        b = a.replace('000000000001', '000000000002')
        self.assertEqual(capture.library_definition(a), capture.library_definition(b))
    def test_library_editor_lock_only_is_metadata(self):
        a = '(footprint "F"\n\t(locked yes)\n\t(layer "F.Cu")\n)'
        self.assertEqual(capture.library_definition(a), a.replace('\t(locked yes)\n', ''))
    def test_pad_number_is_not_metadata(self):
        self.assertNotEqual(capture.library_definition('(pad "1" (size 1 2))'),
                            capture.library_definition('(pad "2" (size 1 2))'))
    def test_pad_geometry_is_not_metadata(self):
        self.assertNotEqual(capture.library_definition('(pad "1" (size 1 2))'),
                            capture.library_definition('(pad "1" (size 1 3))'))
    def test_drill_geometry_is_not_metadata(self):
        self.assertNotEqual(capture.library_definition('(pad "1" (drill 0.3))'),
                            capture.library_definition('(pad "1" (drill 0.4))'))
    def test_mpn_change_is_not_metadata(self):
        self.assertNotEqual(capture.library_definition('(property "MPN" "A")'),
                            capture.library_definition('(property "MPN" "B")'))
    def prop(self, layer='F.Fab', hide='yes', thickness='0.15'):
        return ('(property "Reference" "U1"\n\t\t(layer "' + layer + '")\n'
                '\t\t(hide ' + hide + ')\n\t\t(effects (font\n'
                '\t\t\t\t(thickness ' + thickness + ')\n)))')
    def test_hidden_fab_default_font_serialization_is_metadata(self):
        a = self.prop(); b = a.replace('\t\t\t\t(thickness 0.15)\n', '')
        self.assertEqual(capture.library_definition(a), capture.library_definition(b))
    def test_visible_silkscreen_font_is_not_metadata(self):
        a = self.prop('F.SilkS', 'no'); b = a.replace('0.15', '0.2')
        self.assertNotEqual(capture.library_definition(a), capture.library_definition(b))
    def test_other_hidden_font_thickness_is_not_ignored(self):
        a = self.prop(thickness='0.2'); b = a.replace('\t\t\t\t(thickness 0.2)\n', '')
        self.assertNotEqual(capture.library_definition(a), capture.library_definition(b))


class FileSafety(unittest.TestCase):
    def test_existing_output_refused_without_touching_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); marker = root / 'keep.txt'; marker.write_text('unchanged')
            with self.assertRaises(ValueError): capture.capture(root, root, root, root, root)
            self.assertEqual(marker.read_text(), 'unchanged')
    def test_output_below_input_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); out = root / 'nested'
            with self.assertRaises(ValueError): capture.capture(root, root, root, root, out)
            self.assertFalse(out.exists())
    def test_generated_output_in_source_tree_refused(self):
        out = capture.REPO / 'hardware' / 'pico47' / 'not-a-source-checkpoint'
        with self.assertRaises(ValueError): capture.capture('/tmp/input', '/tmp/c', '/tmp/d', '/tmp/base', out)
        self.assertFalse(out.exists())
    def test_missing_footprint_library_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError): capture.library_hashes(Path(directory))
    def test_library_byte_changes_change_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); lib = root / 'Panda47.pretty'; lib.mkdir()
            for name in ('Panda7.kicad_sym', 'fp-lib-table', 'sym-lib-table'):
                (root / name).write_text('fixture')
            mod = lib / 'one.kicad_mod'; mod.write_text('first')
            before = capture.library_hashes(root); mod.write_text('second')
            self.assertNotEqual(before, capture.library_hashes(root))


if __name__ == '__main__':
    unittest.main(verbosity=2)
