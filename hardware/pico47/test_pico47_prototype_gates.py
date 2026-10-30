"""Staged readiness policy fixtures, not approval of the actual hardware."""
import copy
import unittest
from pico47_prototype_gates import assess_prototype_stages, REVIEW_FACTS, STAGES


def clean_native():
    return {board: {'drc_errors': 0, 'drc_warnings': 0, 'open': 0, 'parity': 0, 'erc': 0}
            for board in ('Core', 'Display')}


def accepted_facts():
    return {fact: True for fact in REVIEW_FACTS}


class PrototypeStageGates(unittest.TestCase):
    def test_current_single_native_and_stage_blockers(self):
        native = {'Single': clean_native()['Core']}
        result = assess_prototype_stages(native, {})
        self.assertFalse(result['stages']['bare_pcb_sample']['requirements_met'])
        native['Single']['open'] = 1
        result = assess_prototype_stages(native, accepted_facts())
        self.assertEqual(result['stages']['bare_pcb_sample']['blockers'][0]['id'], 'Single.open')

    def test_zero_rule_errors_do_not_hide_unconnected_items(self):
        native = clean_native(); native['Core']['open'] = 1
        result = assess_prototype_stages(native, accepted_facts())
        self.assertFalse(result['stages']['bare_pcb_sample']['requirements_met'])
        self.assertEqual(result['stages']['bare_pcb_sample']['blockers'][0]['id'], 'Core.open')

    def test_clean_native_counts_alone_do_not_authorize_sampling(self):
        result = assess_prototype_stages(clean_native(), {})
        self.assertFalse(result['stages']['bare_pcb_sample']['requirements_met'])
        self.assertTrue(all(row['state'] == 'not_established'
                            for row in result['stages']['bare_pcb_sample']['blockers']))

    def test_evt_is_after_first_prototype_not_a_circular_prerequisite(self):
        facts = accepted_facts()
        for fact in STAGES['production_qualification']['requires']:
            facts[fact] = False
        result = assess_prototype_stages(clean_native(), facts)['stages']
        self.assertTrue(result['bare_pcb_sample']['requirements_met'])
        self.assertTrue(result['assembled_board_sample']['requirements_met'])
        self.assertFalse(result['production_qualification']['requirements_met'])

    def test_unknown_pack_does_not_block_an_independently_qualified_bare_board(self):
        facts = accepted_facts(); facts['exact_battery_identity_and_interface'] = None
        result = assess_prototype_stages(clean_native(), facts)['stages']
        self.assertTrue(result['bare_pcb_sample']['requirements_met'])
        self.assertFalse(result['specified_device_prototype']['requirements_met'])
        self.assertFalse(result['first_battery_charge']['requirements_met'])

    def test_as_built_checks_do_not_precede_fabrication(self):
        facts = accepted_facts(); facts['as_built_visual_and_short_check'] = False
        result = assess_prototype_stages(clean_native(), facts)['stages']
        self.assertTrue(result['bare_pcb_sample']['requirements_met'])
        self.assertFalse(result['first_current_limited_board_power']['requirements_met'])

    def test_assembly_does_not_imply_correct_finished_device_stack(self):
        facts = accepted_facts(); facts['finished_positive_tolerance_stack_review'] = False
        result = assess_prototype_stages(clean_native(), facts)['stages']
        self.assertTrue(result['assembled_board_sample']['requirements_met'])
        self.assertFalse(result['specified_device_prototype']['requirements_met'])

    def test_ground_continuity_is_a_separate_gate(self):
        facts = accepted_facts(); facts['all_native_ground_pads_connected'] = False
        result = assess_prototype_stages(clean_native(), facts)['stages']
        self.assertFalse(result['bare_pcb_sample']['requirements_met'])

    def test_missing_board_is_rejected(self):
        native = clean_native(); del native['Display']
        with self.assertRaises(ValueError): assess_prototype_stages(native, accepted_facts())

    def test_missing_counter_is_rejected(self):
        native = clean_native(); del native['Core']['erc']
        with self.assertRaises(ValueError): assess_prototype_stages(native, accepted_facts())

    def test_boolean_or_nonfinite_counts_are_not_valid_evidence(self):
        for value in (True, False, '0', -1, 0.0, float('nan'), None):
            native = clean_native(); native['Core']['open'] = value
            with self.assertRaises(ValueError): assess_prototype_stages(native, accepted_facts())

    def test_unknown_review_fact_is_rejected(self):
        with self.assertRaises(ValueError): assess_prototype_stages(clean_native(), {'ready': True})

    def test_truthy_review_strings_are_rejected(self):
        for value in ('true', 'accepted', 1, 0, [], {}):
            with self.assertRaises(ValueError):
                assess_prototype_stages(clean_native(), {'schematic_and_power_design_review': value})

    def test_rule_warnings_and_parity_are_not_ignored(self):
        for key in ('drc_errors', 'drc_warnings', 'parity', 'erc'):
            native = clean_native(); native['Display'][key] = 1
            result = assess_prototype_stages(native, accepted_facts())
            self.assertFalse(result['stages']['bare_pcb_sample']['requirements_met'])

    def test_success_is_an_assessment_not_an_order_or_power_command(self):
        result = assess_prototype_stages(clean_native(), accepted_facts())
        self.assertTrue(all(stage['requirements_met'] for stage in result['stages'].values()))
        self.assertFalse(result['orders_submitted'])
        self.assertEqual(result['scope'], 'assessment_only_not_fabrication_or_power_authorization')
        self.assertNotIn('manufacturing_release', result)

    def test_inputs_are_immutable(self):
        data = (clean_native(), accepted_facts()); before = copy.deepcopy(data)
        assess_prototype_stages(*data)
        self.assertEqual(data, before)

    def test_failed_prerequisite_propagates(self):
        facts = accepted_facts(); facts['gerber_drill_and_cam_review'] = False
        result = assess_prototype_stages(clean_native(), facts)['stages']
        self.assertFalse(any(stage['requirements_met'] for stage in result.values()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
