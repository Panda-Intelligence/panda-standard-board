"""Mutation tests of real source intent. No supplier receipt or physical test is implied."""
import json
import unittest
from pico47_contract import CONTRACT, validate, mux_target, GPIO_PACKAGE, PANEL_PINS, EXPECTED_MUX_CHANNELS


def fixture():
    return json.loads(CONTRACT.read_text())


class ContractTests(unittest.TestCase):
    def test_valid_source(self):
        self.assertTrue(validate(fixture()))

    def test_json_roundtrip(self):
        self.assertTrue(validate(json.loads(json.dumps(fixture()))))

    def test_independent_pin_facts(self):
        self.assertEqual(GPIO_PACKAGE[47], 37)
        self.assertEqual(GPIO_PACKAGE[48], 36)
        self.assertEqual(len(PANEL_PINS), 40)
        self.assertEqual(PANEL_PINS[13:21], ['P47_D'+str(i) for i in range(8)])
        self.assertEqual(PANEL_PINS[22:30], ['P47_D'+str(i) for i in range(8,16)])

    def test_r25_authorized_mux_pin_map(self):
        plan = fixture()
        self.assertEqual(plan['mux']['channels'], EXPECTED_MUX_CHANNELS)
        self.assertEqual(plan['gpio']['5']['net'], 'P47_MUX6')
        self.assertEqual(plan['gpio']['44']['net'], 'P47_MUX3')
        self.assertTrue(plan['mux']['r25_routing_eco']['four_layer'])
        self.assertEqual(plan['mux']['r25_routing_eco']['ground_plane_layer'], 'In1.Cu')

    def test_mux_truth_table(self):
        for channel in range(8):
            self.assertEqual(mux_target(False, False, channel), 'SD_OR_UART')
            self.assertEqual(mux_target(True, False, channel), 'EPD')
            self.assertIsNone(mux_target(False, True, channel))
            self.assertIsNone(mux_target(True, True, channel))

    def test_invalid_mux_arguments(self):
        for args in [(1,False,0), (True,0,0), (True,False,True),
                     (True,False,-1), (True,False,8), (True,False,1.1)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                mux_target(*args)


def mutation_test(path, value):
    def test(self):
        p = fixture()
        node = p
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = value
        with self.assertRaises(ValueError):
            validate(p)
    return test


MUTATIONS = [
    (['manufacturing_release'], True), (['orders_submitted'], True),
    (['user_requirement','whole_device_maximum_mm'], 7.3),
    (['user_requirement','two_boards'], False),
    (['user_requirement','keep_touch_frontlight_audio_imu_microsd_rtc'], False),
    (['panel','diagonal_inch'], 4.26), (['panel','portrait_pixels'], [480,800]),
    (['panel','interface'], 'SPI'), (['panel','data_width'], 8),
    (['panel','source_family_pinmap','40'], 'GND'),
    (['panel','source_family_pinmap','14'], 'P47_D1'),
    (['panel','pico_full_suffix_verified'], True),
    (['panel','assembly_max_xyz_mm'], [62,113,1]),
    (['battery','capacity_mah'], 1100), (['battery','exact_pico_pack_required'], False),
    (['battery','pico_battery_mpn'], 'UNKNOWN-PACK'),
    (['battery','charge_termination_v'], 4.2), (['battery','charge_enable_allowed'], True),
    (['gpio','47','package_pin'], 36), (['gpio','48','package_pin'], 37),
    (['gpio','2','net'], 'I2C_PERMIT'), (['gpio','14','net'], 'SOME_OTHER_NET'),
    (['mux','source_terminal_pins',0], [4,3,2]),
    (['mux','channels',0,'select_0_net'], 'SDMMC_CLK'),
    (['mux','disables_all_before_select'], False),
    (['mux','sd_uart_and_refresh_mutually_exclusive'], False),
    (['mux','electrical_timing_qualified'], True),
    (['interconnect','40','2'], 'P47_D0'),
    (['interconnect','20','1'], '3V3_AON'),
    (['interconnect','20','16'], 'GND'),
    (['pmic','exposed_pad_ground_forbidden'], False), (['pmic','vgh_target_v'], 25),
    (['pmic','direct_enable','source_gpio'], 46),
    (['pmic','direct_enable','expander_p00_role'], 'OUTPUT'),
    (['pmic','direct_enable','cpu_frozen_high_detected'], True),
    (['power_stage','inductors','mpn'], 'SWPA3012S4R7MT'),
    (['power_stage','inductors','pads',0,3], .8),
    (['power_stage','inductors','source_current_columns','heading'], ['Min.','Typ.']),
    (['power_stage','inductors','hot_short_circuit_margin_qualified'], True),
    (['physical_study','battery_fit_proven'], True),
    (['physical_study','frontlight_stack_fit_proven'], True),
    (['physical_study','native_routing_complete'], True),
    (['power_stage','display_solid_ground_pads','C806'], ['1']),
    (['power_stage','display_solid_ground_pads','J1'], ['4','12','22']),
]
for i, (path, value) in enumerate(MUTATIONS):
    setattr(ContractTests, f'test_reject_mutation_{i+1:02d}', mutation_test(path, value))

if __name__ == '__main__':
    unittest.main(verbosity=2)
