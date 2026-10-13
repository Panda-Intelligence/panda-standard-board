"""Negative controls: connected copper is not manufacturing/SI/PI acceptance."""
import copy
import unittest
from audit_seven_mm_prototype import evaluate

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.core = {'nets': {}, 'thermal_pads': {'U501': {'ground_vias_in_exposed_pad': 9}}}
        self.layout = {'evidence': {'mechanical_tolerance_stack_verified': False}}
    def issues(self):
        return {x['id']: x for x in evaluate(self.core, self.layout)}
    def test_missing_power_is_blocked(self):
        self.assertEqual(self.issues()['POWER_WIDTH_3V3_AON']['status'], 'BLOCKED')
    def test_narrow_power_is_blocked(self):
        self.core['nets']['3V3_AON'] = {'widths_mm': [.15]}
        self.assertEqual(self.issues()['POWER_WIDTH_3V3_AON']['status'], 'BLOCKED')
    def test_wide_fragment_is_not_qualified_path(self):
        self.core['nets']['3V3_AON'] = {'widths_mm': [.15, .635]}
        self.assertEqual(self.issues()['POWER_WIDTH_3V3_AON']['status'], 'OPEN')
    def test_rf_supply_width(self):
        self.core['nets']['3V3_RF'] = {'widths_mm': [.15, .4]}
        self.assertEqual(self.issues()['POWER_WIDTH_3V3_RF']['status'], 'BLOCKED')
    def test_eight_thermal_vias_rejected(self):
        self.core['thermal_pads']['U501']['ground_vias_in_exposed_pad'] = 8
        self.assertEqual(self.issues()['MCU_GROUND_VIAS']['status'], 'BLOCKED')
    def test_nine_vias_only_closes_that_review_item(self):
        self.assertNotIn('MCU_GROUND_VIAS', self.issues())
        self.assertIn('USB_DIFFERENTIAL', self.issues())
    def test_switch_via_remains_open(self):
        self.core['nets']['SGM41513_SW'] = {'via_count': 1, 'gross_copper_length_mm': 4}
        self.assertEqual(self.issues()['CHARGER_SWITCH_LOOP']['status'], 'OPEN')
    def test_long_switch_loop_remains_open(self):
        self.core['nets']['SGM41513_SW'] = {'via_count': 0, 'gross_copper_length_mm': 27}
        self.assertIn('CHARGER_SWITCH_LOOP', self.issues())
    def test_sdio_layer_crossing_blocked(self):
        self.core['nets']['SDMMC_CLK'] = {'via_count': 2, 'layers': ['F.Cu', 'B.Cu']}
        self.assertEqual(self.issues()['SDIO_LAYER_CHANGES']['status'], 'BLOCKED')
    def test_single_layer_not_usb_or_impedance_proof(self):
        self.core['nets']['SDMMC_CLK'] = {'via_count': 0, 'layers': ['F.Cu']}
        self.assertNotIn('SDIO_LAYER_CHANGES', self.issues())
        self.assertIn('STACKUP_AND_SMT', self.issues())
    def test_whole_device_not_qualified_by_budget(self):
        self.assertEqual(self.issues()['WHOLE_DEVICE_7MM']['status'], 'OPEN')
    def test_read_only_evaluation(self):
        before = copy.deepcopy((self.core, self.layout))
        self.issues()
        self.assertEqual((self.core, self.layout), before)

if __name__ == '__main__':
    unittest.main(verbosity=2)
