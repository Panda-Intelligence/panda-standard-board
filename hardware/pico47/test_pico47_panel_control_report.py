"""Panel-control report regressions; synthetic fixtures are not native signoff."""
import copy
import unittest
from pico47_panel_control_report import LINKS, summarize_panel_controls


def evidence(connected=('P47_CKV', 'P47_XLE')):
    pads, groups = [], []
    for net, identities in LINKS.items():
        uuids = []
        for ref, pin in identities:
            uid = ref + '.' + pin
            uuids.append(uid)
            pads.append({'uuid': uid, 'ref': ref, 'pin': pin, 'net': net})
        groups.extend([uuids] if net in connected else [[uid] for uid in uuids])
    return pads, groups


class PanelControlReport(unittest.TestCase):
    def test_ckv_closure_does_not_imply_spv(self):
        report = summarize_panel_controls(*evidence())
        self.assertTrue(report['P47_CKV']['connected'])
        self.assertTrue(report['P47_XLE']['connected'])
        self.assertFalse(report['P47_SPV']['connected'])

    def test_identical_net_names_do_not_imply_copper_connection(self):
        report = summarize_panel_controls(*evidence(connected=()))
        self.assertFalse(any(row['connected'] for row in report.values()))

    def test_all_three_may_be_reported_complete_without_release_claim(self):
        report = summarize_panel_controls(*evidence(connected=tuple(LINKS)))
        self.assertTrue(all(row['connected'] for row in report.values()))
        self.assertTrue(all(row['scope'] == 'connectivity_only_not_timing_or_fabrication'
                            for row in report.values()))
        self.assertNotIn('manufacturing_release', report)

    def test_exact_connector_pin_mapping(self):
        report = summarize_panel_controls(*evidence())
        self.assertEqual((report['P47_CKV']['from_pad'], report['P47_CKV']['to_pad']),
                         ('R729.2', 'J601.39'))
        self.assertEqual(report['P47_SPV']['to_pad'], 'J601.40')
        self.assertEqual(report['P47_XLE']['to_pad'], 'J601.35')

    def test_pin_swap_is_rejected(self):
        pads, groups = evidence(); pads[1]['pin'] = '40'
        with self.assertRaises(ValueError): summarize_panel_controls(pads, groups)

    def test_missing_pad_inventory_is_rejected(self):
        pads, groups = evidence(); pads.pop()
        with self.assertRaises(ValueError): summarize_panel_controls(pads, groups)

    def test_missing_native_group_evidence_is_rejected(self):
        pads, _ = evidence()
        with self.assertRaises(ValueError): summarize_panel_controls(pads, [])

    def test_omitted_disconnected_pad_is_not_silently_ignored(self):
        pads, groups = evidence(); groups.pop(2)
        with self.assertRaises(ValueError): summarize_panel_controls(pads, groups)

    def test_duplicated_native_identity_is_rejected(self):
        pads, groups = evidence(); pads[1]['uuid'] = pads[0]['uuid']
        with self.assertRaises(ValueError): summarize_panel_controls(pads, groups)

    def test_overlapping_groups_are_rejected(self):
        pads, groups = evidence(); groups.append([pads[0]['uuid']])
        with self.assertRaises(ValueError): summarize_panel_controls(pads, groups)

    def test_short_between_different_nets_is_rejected(self):
        pads, groups = evidence(); groups[0].extend(groups.pop(1))
        with self.assertRaises(ValueError): summarize_panel_controls(pads, groups)

    def test_unknown_uuid_is_rejected(self):
        pads, groups = evidence(); groups[0].append('unknown-native-pad')
        with self.assertRaises(ValueError): summarize_panel_controls(pads, groups)

    def test_input_order_does_not_change_physical_report(self):
        pads, groups = evidence()
        self.assertEqual(summarize_panel_controls(pads, groups),
                         summarize_panel_controls(list(reversed(pads)), list(reversed(groups))))

    def test_report_does_not_mutate_evidence(self):
        data = evidence(); before = copy.deepcopy(data)
        summarize_panel_controls(*data)
        self.assertEqual(data, before)

    def test_malformed_or_repeated_group_is_rejected(self):
        for malformed in ('R729.2', [], ['R729.2', 'R729.2']):
            pads, groups = evidence(); groups[0] = malformed
            with self.assertRaises(ValueError): summarize_panel_controls(pads, groups)

    def test_regenerated_uuids_keep_logical_report_identical(self):
        pads, groups = evidence(); expected = summarize_panel_controls(pads, groups)
        for pad in pads: pad['uuid'] = 'rebuilt-' + pad['uuid']
        groups = [['rebuilt-' + uid for uid in group] for group in groups]
        self.assertEqual(summarize_panel_controls(pads, groups), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
