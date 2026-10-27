"""Source-level E0 constraints. Passing is NOT physical qualification."""
from pathlib import Path
import json
import math

CONTRACT = Path(__file__).with_name('design.json')
GPIO_PACKAGE = {
    **{g: g + 5 for g in range(15)},
    15: 21, 16: 22, 17: 23, 18: 24, 19: 25, 20: 26, 21: 27,
    38: 43, 39: 44, 40: 45, 41: 47, 42: 48, 43: 49,
    44: 50, 45: 51, 46: 52, 47: 37, 48: 36,
}
PANEL_PINS = [
    'P47_VGL', '', 'P47_VGH', '', '3V3_EPD_LOGIC', 'P47_MODE',
    'P47_CKV', 'P47_SPV', 'GND', 'P47_VCOM', '3V3_EPD_LOGIC',
    'GND', 'P47_XCL', *['P47_D' + str(i) for i in range(8)], 'GND',
    *['P47_D' + str(i) for i in range(8, 16)], 'P47_XSTL', 'P47_XLE',
    'P47_XOE', '3V3_EPD_LOGIC', '', 'P47_VPOS', '', 'P47_VNEG', '',
    'P47_BORDER_REVIEW',
]

EXPECTED_NETS = {
    0: 'GPIO0', 1: 'KEY_POWER_MCU', 2: 'HW_ARM_GPIO', 3: 'P47_D8_SRC',
    4: 'EXP_INT', 5: 'P47_MUX6', 6: 'P47_MUX7', 7: 'P47_MUX4',
    8: 'P47_MUX0', 9: 'P47_MUX1', 10: 'P47_MUX2', 11: 'P47_D13_SRC',
    12: 'P47_CKV_SRC', 13: 'P47_XLE_SRC', 14: 'P47_XCL_SRC', 15: 'I2C_SDA',
    16: 'I2C_SCL', 17: 'I2S_DIN', 18: 'I2S_LRCLK', 19: 'USB_DM_MCU',
    20: 'USB_DP_MCU', 21: 'I2S_BCLK', 38: 'P47_D10_SRC', 39: 'P47_D11_SRC',
    40: 'P47_D15_SRC', 41: 'P47_D9_SRC', 42: 'P47_D14_SRC', 43: 'P47_MUX5',
    44: 'P47_MUX3', 45: 'P47_XSTL_SRC', 46: 'P47_BUS_SELECT',
    47: 'P47_D12_SRC', 48: 'P47_SPV_SRC',
}
EXPECTED_MUX_CHANNELS = [
    {'channel': 0, 'gpio': 8, 'package_pin': 13, 'common_net': 'P47_MUX0',
     'select_0_net': 'SDMMC_D0', 'select_1_net': 'P47_D0_SRC'},
    {'channel': 1, 'gpio': 9, 'package_pin': 14, 'common_net': 'P47_MUX1',
     'select_0_net': 'SDMMC_D1', 'select_1_net': 'P47_D2_SRC'},
    {'channel': 2, 'gpio': 43, 'package_pin': 49, 'common_net': 'P47_MUX5',
     'select_0_net': 'UART0_TX', 'select_1_net': 'P47_D3_SRC'},
    {'channel': 3, 'gpio': 44, 'package_pin': 50, 'common_net': 'P47_MUX3',
     'select_0_net': 'UART0_RX', 'select_1_net': 'P47_D1_SRC'},
    {'channel': 4, 'gpio': 7, 'package_pin': 12, 'common_net': 'P47_MUX4',
     'select_0_net': 'SDMMC_CLK', 'select_1_net': 'P47_D5_SRC'},
    {'channel': 5, 'gpio': 10, 'package_pin': 15, 'common_net': 'P47_MUX2',
     'select_0_net': 'SDMMC_D3', 'select_1_net': 'P47_D6_SRC'},
    {'channel': 6, 'gpio': 5, 'package_pin': 10, 'common_net': 'P47_MUX6',
     'select_0_net': 'SDMMC_CMD', 'select_1_net': 'P47_D4_SRC'},
    {'channel': 7, 'gpio': 6, 'package_pin': 11, 'common_net': 'P47_MUX7',
     'select_0_net': 'SDMMC_D2', 'select_1_net': 'P47_D7_SRC'},
]
EXPECTED_INTER40 = {str(i+1): ('P47_D' + str(i//2) if i % 2 == 0 else 'GND')
                    for i in range(32)}
EXPECTED_INTER40.update({str(k): v for k, v in {
    33: 'P47_XCL', 34: 'GND', 35: 'P47_XLE', 36: 'GND', 37: 'P47_XSTL',
    38: 'GND', 39: 'P47_CKV', 40: 'P47_SPV',
}.items()})
EXPECTED_INTER20 = {str(i+1): n for i, n in enumerate([
    'VSYS_RAW', 'VSYS_RAW', 'GND', 'GND', '3V3_AON', '3V3_AON', 'GND', 'GND',
    '3V3_EPD_LOGIC', '3V3_EPD_LOGIC', 'GND', 'GND', 'I2C_SCL', 'I2C_SDA',
    'EXP_INT', 'HW_ARM_GPIO', 'P47_PGOOD', 'GND', 'GND', 'GND',
])}


def require(value, message):
    if not value:
        raise ValueError(message)


def validate(p):
    require(p['schema'] == 'panda-pico47-redesign-v1' and p['revision'] == 'E0',
            'Unknown physical revision')
    require(p['manufacturing_release'] is False and p['orders_submitted'] is False,
            'No manufacturing or purchase authorization')
    r = p['user_requirement']
    require(r['whole_device_maximum_mm'] == 7.0 and r['two_boards'] is True,
            'Do not relax user envelope or architecture')
    require(r['keep_touch_frontlight_audio_imu_microsd_rtc'] is True
            and r['mainland_components'] is True, 'Required features lost')
    panel = p['panel']
    require(panel['family'] == 'E0470A01' and panel['diagonal_inch'] == 4.7
            and panel['portrait_pixels'] == [684, 1216]
            and panel['scan_pixels'] == [1216, 684], 'Wrong display')
    require(panel['interface'] == 'RAW_PARALLEL_NOT_SPI'
            and panel['data_width'] == 16 and panel['connector_contacts'] == 40
            and panel['connector_pitch_mm'] == .5, 'Wrong display interface')
    require(panel['source_family_pinmap'] ==
            {str(i + 1): n for i, n in enumerate(PANEL_PINS)}, 'Wrong panel pin map')
    require(math.isclose(panel['nominal_ppi_by_marketed_diagonal'],
                         math.hypot(684, 1216) / 4.7, abs_tol=1e-7), 'Wrong PPI')
    for k in ['pico_full_suffix_verified', 'border_drive_accepted',
              'waveform_qualification']:
        require(panel[k] is False, 'Unverified panel acceptance: ' + k)
    require(panel['selected_full_module_mpn'] is None
            and panel['assembly_max_xyz_mm'] is None, 'Invented module envelope')
    battery = p['battery']
    require(battery['capacity_mah'] == 2050 and battery['chemistry'] == 'LCO'
            and battery['replaceable_pack_required'] is True
            and battery['exact_pico_pack_required'] is True, 'Wrong pack requirement')
    for k in ['pico_battery_vendor', 'pico_battery_mpn', 'pico_pack_xyz_mm',
              'nominal_voltage_v', 'charge_termination_v', 'protection_topology',
              'ntc_connector_pinout']:
        require(battery[k] is None, 'Unverified pack property: ' + k)
    require(battery['charge_enable_allowed'] is False
            and battery['old_1100mah_cell_rejected_for_new_revision'] is True,
            'Battery gate lost')
    require(set(p['gpio']) == set(map(str, GPIO_PACKAGE)), 'Reserved GPIO used')
    require(len({v['net'] for v in p['gpio'].values()}) == 33, 'GPIO collision')
    for g, pin in GPIO_PACKAGE.items():
        require(p['gpio'][str(g)]['package_pin'] == pin, 'Wrong QFN GPIO map')
    for g, n in EXPECTED_NETS.items():
        require(p['gpio'][str(g)]['net'] == n, 'GPIO function changed without review')
    mux = p['mux']
    require(mux['mpn'] == 'SGM330A-YTS/TR' and mux['logic_supply_v'] == 3.3
            and mux['select_gpio'] == 46, 'Wrong mux')
    require(mux['source_terminal_pins'] ==
            [[2, 3, 4], [5, 6, 7], [11, 10, 9], [14, 13, 12]], 'Wrong mux pads')
    refs = ['SDMMC_D0', 'SDMMC_D1', 'UART0_TX', 'UART0_RX', 'SDMMC_CLK',
            'SDMMC_D3', 'SDMMC_CMD', 'SDMMC_D2']
    require(len(mux['channels']) == 8, 'Missing mux channel')
    for c, expected in zip(mux['channels'], EXPECTED_MUX_CHANNELS):
        require(c == expected, 'Wrong mux channel')
    require(mux['reset_select'] == 0 and mux['reset_oe_n'] == 0
            and mux['disable_signal'] == 'P47_BUS_OE_N'
            and mux['disable_expander'] == 'U601.P15/pin18', 'Wrong mux reset')
    require(mux['disables_all_before_select'] is True
            and mux['sd_uart_and_refresh_mutually_exclusive'] is True
            and mux['audio_gpio_independent'] is True, 'Unsafe bus-sharing policy')
    require(mux['break_before_make_hardware_guaranteed'] is False
            and mux['electrical_timing_qualified'] is False, 'Unproven mux timing')
    inter = p['interconnect']
    require(inter['40'] == EXPECTED_INTER40 and inter['20'] == EXPECTED_INTER20,
            'FFC logical function changed')
    for count in [40, 20]:
        require(set(inter[str(count)]) == set(map(str, range(1, count + 1))),
                'Incomplete FFC')
    for i in range(16):
        require(inter['40'][str(2*i+1)] == 'P47_D' + str(i)
                and inter['40'][str(2*i+2)] == 'GND', 'Data return missing')
    require(inter['20']['16'] == 'HW_ARM_GPIO'
            and inter['20']['17'] == 'P47_PGOOD'
            and inter['new_pinout_incompatible_with_D'] is True, 'Wrong FFC revision')
    pm = p['pmic']
    require(pm['mpn'] == 'SY7636ARMC' and pm['exposed_pad_ground_forbidden'] is True,
            'Wrong PMIC or dangerous EP connection')
    require(pm['vgh_target_v'] == 22 and pm['vgh_panel_allowed_v'] == [21, 23]
            and pm['reference_default_vgh_25v_prohibited'] is True, 'Wrong VGH')
    require(pm['vgl_target_v'] == -20 and pm['source_rails_v'] == [15, -15], 'Wrong rails')
    en = pm['direct_enable']
    require(en['source_gpio'] == 2 and en['source_net'] == 'HW_ARM_GPIO'
            and en['series_resistor_ref'] == 'R813' and en['series_ohm'] == 1000
            and en['pmic_enable_net'] == 'P47_HV_EN'
            and en['enable_pulldown_ohm'] == 100000, 'Direct inhibit path changed')
    require(en['expander_p00_role'] == 'INPUT_ONLY_MONITOR'
            and en['cpu_frozen_high_detected'] is False, 'Expander contention or imaginary watchdog')
    power = p['power_stage']
    ind = power['inductors']
    require(power['display_solid_ground_pads'] == {'C806':['2'],'C817':['2'],'R802':['2'],'R808':['2'],'R809':['2'],'J1':['5','13','23']}, 'Unreviewed ground plane connection policy')
    require(ind['mpn'] == 'MWSA0618S-4R7MT' and ind['catalog_code'] == 'C408421'
            and ind['inductance_uh'] == 4.7, 'Wrong inductor')
    require(ind['pads'] == [['1', -3.025, 0, 2.35, 3.5], ['2', 3.025, 0, 2.35, 3.5]]
            and ind['height_max_mm'] == 1.8 and ind['body_max_xy_mm'] == [7.3, 6.8],
            'Wrong inductor geometry')
    require(ind['source_current_columns'] == {'heading': ['Max.', 'Typ.'],
            'saturation_A': [4., 5.], 'heat_rating_A': [3.5, 4.]}, 'Wrong current headings')
    require(ind['hot_short_circuit_margin_qualified'] is False
            and power['rectifier_current_qualified'] is False, 'Power stage unqualified')
    study = p['physical_study']
    require(study['maximum_thickness_requirement_mm'] == 7
            and study['trial_is_not_approved_mechanical_envelope'] is True, 'Unapproved product envelope')
    require(study['battery_fit_proven'] is False
            and study['frontlight_stack_fit_proven'] is False
            and study['native_routing_complete'] is False, 'Unproven routing or fit')
    return True


def mux_target(select, disabled, channel):
    """Logic truth table, NOT a delay/electrical simulation."""
    require(type(select) is bool and type(disabled) is bool, 'Boolean logic required')
    require(type(channel) is int and 0 <= channel < 8, 'Invalid channel')
    if disabled:
        return None
    return 'EPD' if select else 'SD_OR_UART'


if __name__ == '__main__':
    validate(json.loads(CONTRACT.read_text()))
    print('E0 source contract valid; not a fabrication release')
