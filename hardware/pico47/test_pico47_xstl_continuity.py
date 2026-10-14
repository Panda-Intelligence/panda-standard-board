"""Explicit XSTL endpoint tests for the coordinated connector fanout.
Synthetic native-group fixtures do not substitute for KiCad acceptance.
"""
import unittest
from pico47_panel_control_report import summarize_panel_controls


def native_fixture():
    endpoints = [
        ('P47_CKV', 'R729', '2', 'J601', '39'),
        ('P47_SPV', 'R730', '2', 'J601', '40'),
        ('P47_XLE', 'R727', '2', 'J601', '35'),
        ('P47_XSTL', 'R728', '2', 'J601', '37'),
    ]
    pads, groups = [], []
    for net, ra, pa, rb, pb in endpoints:
        group = []
        for ref, pin in ((ra, pa), (rb, pb)):
            uid = ref + '.' + pin
            pads.append({'uuid': uid, 'ref': ref, 'pin': pin, 'net': net})
            group.append(uid)
        groups.append(group)
    return pads, groups


class CoordinatedXstlContinuity(unittest.TestCase):
    def test_all_four_exact_controls_and_eight_pads(self):
        pads, groups = native_fixture()
        self.assertEqual(len(pads), 8)
        result = summarize_panel_controls(pads, groups)
        self.assertEqual(set(result), {'P47_CKV', 'P47_SPV', 'P47_XLE', 'P47_XSTL'})
        self.assertTrue(all(row['connected'] for row in result.values()))
        self.assertEqual(result['P47_XSTL']['from_pad'], 'R728.2')
        self.assertEqual(result['P47_XSTL']['to_pad'], 'J601.37')

    def test_spv_success_does_not_hide_lost_xstl(self):
        pads, groups = native_fixture()
        old = groups.pop()
        groups.extend([[uid] for uid in old])
        result = summarize_panel_controls(pads, groups)
        self.assertTrue(result['P47_SPV']['connected'])
        self.assertFalse(result['P47_XSTL']['connected'])

    def test_wrong_net_on_header_37_is_rejected(self):
        pads, groups = native_fixture()
        pads[-1]['net'] = 'P47_CKV'
        with self.assertRaises(ValueError):
            summarize_panel_controls(pads, groups)

    def test_old_six_pad_evidence_cannot_omit_xstl(self):
        pads, groups = native_fixture()
        with self.assertRaises(ValueError):
            summarize_panel_controls(pads[:-2], groups[:-1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
