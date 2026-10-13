"""Named target regressions for the eight-ground continuation, not power approval."""
import copy
import unittest
from pico47_ground_returns import summarize_ground_returns


def inventory():
    return [
        {'uuid':'ref','ref':'C804','pin':'2','net':'GND','position_mm':[18.2,105]},
        {'uuid':'a','ref':'U810','pin':'32','net':'GND','position_mm':[18.45,95.4]},
        {'uuid':'b','ref':'U810','pin':'41','net':'GND','position_mm':[16.1,93.05]},
        {'uuid':'c','ref':'R810','pin':'2','net':'GND','position_mm':[23.26,112]},
    ]


def summarize(groups, targets, pads=None):
    return summarize_ground_returns(inventory() if pads is None else pads,
                                    groups, 'C804', '2', targets)


class RequiredGroundTargets(unittest.TestCase):
    def test_complete_targets(self):
        result=summarize([['ref','a','b','c']], [('U810','32'),('U810','41')])
        self.assertTrue(result['all_required_ground_targets_connected'])
        self.assertEqual(result['connected_required_ground_target_count'],2)
        self.assertEqual(result['required_ground_target_count'],2)

    def test_targets_joined_to_each_other_not_reference_are_incomplete(self):
        result=summarize([['ref','c'],['a','b']], [('U810','32'),('U810','41')])
        self.assertFalse(result['all_required_ground_targets_connected'])
        self.assertEqual(result['connected_required_ground_target_count'],0)

    def test_partial_success_is_individual_not_aggregate_guess(self):
        result=summarize([['ref','b'],['a'],['c']], [('U810','32'),('U810','41'),('R810','2')])
        states={(v['ref'],v['pin']):v['connected_to_reference'] for v in result['required_ground_targets']}
        self.assertEqual(states,{('U810','32'):False,('U810','41'):True,('R810','2'):False})
        self.assertEqual(result['connected_required_ground_target_count'],1)

    def test_completed_subset_does_not_imply_all_ground_connected(self):
        result=summarize([['ref','a','b'],['c']], [('U810','32'),('U810','41')])
        self.assertTrue(result['all_required_ground_targets_connected'])
        self.assertFalse(result['all_ground_pads_connected_to_reference'])
        self.assertNotIn('manufacturing_release',result)

    def test_unknown_target_rejected_instead_of_assumed_connected(self):
        with self.assertRaises(ValueError):summarize([['ref','a','b','c']], [('J820','999')])

    def test_ambiguous_physical_target_rejected(self):
        records=inventory(); records.append({**records[1],'uuid':'other','position_mm':[20,95.4]})
        with self.assertRaises(ValueError):summarize([['ref','a','b','c','other']], [('U810','32')],records)

    def test_duplicate_required_target_rejected(self):
        with self.assertRaises(ValueError):summarize([['ref','a','b','c']], [('U810','32'),('U810','32')])

    def test_explicit_empty_or_malformed_target_list_rejected(self):
        for targets in ([],(),'',False,{'U810':'32'}):
            with self.subTest(targets=targets):
                with self.assertRaises(ValueError):summarize([['ref','a','b','c']],targets)

    def test_bad_target_identity_rejected(self):
        for target in (('U810',),('U810','32','extra'),('U810',32),('', '32'),'U810.32'):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):summarize([['ref','a','b','c']],[target])

    def test_deterministic_target_order(self):
        a=summarize([['ref','b'],['a'],['c']], [('U810','32'),('U810','41'),('R810','2')])
        b=summarize([['c'],['a'],['ref','b']], [('R810','2'),('U810','41'),('U810','32')])
        self.assertEqual(a,b)

    def test_inputs_remain_unchanged(self):
        pads=inventory();groups=[['ref','b'],['a'],['c']];targets=[['U810','32'],['U810','41']]
        before=copy.deepcopy((pads,groups,targets));summarize(groups,targets,pads)
        self.assertEqual((pads,groups,targets),before)

    def test_default_report_stays_backward_compatible(self):
        result=summarize_ground_returns(inventory(),[['ref','a','b','c']],'C804','2')
        self.assertNotIn('required_ground_targets',result)
        self.assertTrue(result['all_ground_pads_connected_to_reference'])


if __name__=='__main__':unittest.main(verbosity=2)
