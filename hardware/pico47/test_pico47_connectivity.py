"""Tests for connectivity acceptance logic, not mock supplier/hardware results."""
import unittest
from prune_pico47_stubs import preserves_groups


def groups(*values):
    return [frozenset(v) for v in values]


class ConnectivityGuardTests(unittest.TestCase):
    def test_identical(self):
        self.assertTrue(preserves_groups(groups('ab','c'),groups('ab','c')))

    def test_reordering(self):
        self.assertTrue(preserves_groups(groups('ab','cd'),groups('dc','ba')))

    def test_added_connection_allowed(self):
        self.assertTrue(preserves_groups(groups('ab','c'),groups('abc')))

    def test_disconnect_rejected(self):
        self.assertFalse(preserves_groups(groups('abc'),groups('ab','c')))

    def test_lost_pad_rejected(self):
        self.assertFalse(preserves_groups(groups('ab','c'),groups('ab')))

    def test_extra_pad_rejected(self):
        self.assertFalse(preserves_groups(groups('ab'),groups('ab','c')))

    def test_component_count_is_not_enough(self):
        self.assertFalse(preserves_groups(groups('ab','cd'),groups('ac','bd')))

    def test_no_merge_can_hide_another_disconnect(self):
        self.assertFalse(preserves_groups(groups('ab','cd','e'),groups('a','bcde')))

    def test_empty(self):
        self.assertTrue(preserves_groups([],[]))
        self.assertFalse(preserves_groups(groups('a'),[]))


if __name__=='__main__':
    unittest.main(verbosity=2)
