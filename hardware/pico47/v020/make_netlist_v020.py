"""Panda47 v0.2.0 netlist: the v0.1.3 (R50) netlist rewritten to the reference-style architecture.

usage: make_netlist_v020.py r50.json r49.json out.json
  r50.json / r49.json come from dump_pcb.py (KiCad Python) run on v0.1.3 and v0.1.2 Single.kicad_pcb.

Decisions (user, 2026-11-10): EPD data straight to GPIO, 1-bit SDMMC, no SGM330A muxes, one XL9535,
SC7A20HTR accelerometer, BM8563 RTC, keep NS4168 speaker, SY7636ARMC (consigned) on the R49 circuit,
mainland buck SY8089A1AAC for 3V3. GPIO map follows the reference design so its EPD/SD/I2C drivers fit unchanged.
"""
import json
import os
import sys

VARIANT = os.environ.get('PANDA47_VARIANT', 'v020')

r50 = json.load(open(sys.argv[1]))
r49 = json.load(open(sys.argv[2]))


def pins_of(src, ref):
    out = {}
    for net, nodes in src['nets'].items():
        for r, p in nodes:
            if r == ref:
                out[p] = '' if net.startswith('unconnected-') else net
    return out


parts = {}
for ref, c in r50['comps'].items():
    parts[ref] = dict(value=c['value'], lib='Panda47', footprint=c['fpid'], fields=dict(c['fields']),
                      dnp=c['dnp'], pins=pins_of(r50, ref))

# ---------------------------------------------------------------- removals
REMOVE = """
U710 U711 C710 C711 R732
U811 C542 C817 R813
U403 U404 U405 C507 C509 C511 C516 C534 C535 C536 R507 R508 R515 R516 R605 R606
U906 C204 R600 R610 R611 R528 R301 R302 R305 C514 C515
J503 R533
R540 R541 R542 R543 R544 R545 C537 C538 C540 C541
R517 R518 R519 R520 R521 R522 R514
R710 R711 R712 R713 R714 R715 R716 R717 R718 R719 R720 R721 R722 R723 R724 R725 R727 R728 R729 R730
Q907 Q908 R930 R931 R932 R933 R607 R922 C922
BT301 D306 R509
TP5 TP6 TP7 TP8 TP13 TP14 TP16 TP19 TP712 TPG2 TPG3 TPG4 TPG5 TPG6
""".split()
for r in REMOVE:
    del parts[r]

# ------------------------------------------------------------- PMIC: R49 SY7636A circuit
for ref, c in r49['comps'].items():
    if c['fpid'].endswith('_Display') and ref in parts and ref[0] in 'URCLD':
        parts[ref].update(value=c['value'], fields=dict(c['fields']), dnp=c['dnp'], pins=pins_of(r49, ref))
parts['U810']['pins'] = pins_of(r49, 'U810')
parts['R805']['dnp'] = False

# ------------------------------------------------------------- MCU pin map (reference GPIO plan)
MCU = {
    '5': 'KEY_POWER_MCU',   # GPIO0 boot strap + power key (R511 pull-up, SW201)
    '6': 'EXP_INT',         # GPIO1 RTC GPIO: deep-sleep wake from XL9535 / BM8563 INT
    '7': 'I2S_BCLK',        # GPIO2
    '8': 'P47_XLE',         # GPIO3 (JTAG strap, R512 pull-down)
    '21': 'P47_D11', '22': 'P47_D12', '23': 'P47_D13', '24': 'P47_D14',   # GPIO15..18
    '27': 'P47_XCL_SRC',    # GPIO21 -> R726 22R -> P47_XCL
    '28': '',
    '29': 'VDD_SPI', '30': 'FLASH_HD', '31': 'FLASH_WP', '32': 'FLASH_CS', '33': 'FLASH_CLK',
    '34': 'FLASH_Q', '35': 'FLASH_D',
    '36': 'P47_CKV',        # GPIO48
    '37': 'P47_SPV',        # GPIO47
    '43': 'SD_CLK',         # GPIO38
    '44': 'I2C_SDA',        # GPIO39
    '45': 'I2C_SCL',        # GPIO40
    '47': 'I2S_LRCLK',      # GPIO41
    '48': 'SD_CMD',         # GPIO42
    '49': 'I2S_DIN',        # GPIO43
    '50': 'SD_D0',          # GPIO44
    '51': 'P47_D15',        # GPIO45 VDD_SPI strap, R731 pull-down keeps 3.3 V flash
    '52': 'P47_XSTL',       # GPIO46 boot strap, R513 pull-down
}
for i, pin in enumerate(range(9, 20)):  # GPIO4..14 -> D0..D10
    MCU[str(pin)] = f'P47_D{i}'
parts['U501']['pins'].update(MCU)
for p in ('38', '39', '40', '41', '42'):
    parts['U501']['pins'][p] = ''
parts['U506']['pins'].update({'1': 'FLASH_CS', '2': 'FLASH_Q', '3': 'FLASH_WP', '5': 'FLASH_D', '6': 'FLASH_CLK', '7': 'FLASH_HD'})
parts['R512']['pins'] = {'1': 'P47_XLE', '2': 'GND'} if parts['R512']['pins'].get('1') == 'P47_D8_SRC' else {k: ('P47_XLE' if v == 'P47_D8_SRC' else v) for k, v in parts['R512']['pins'].items()}
parts['R513']['pins'] = {k: ('P47_XSTL' if v == 'P47_BUS_SELECT' else v) for k, v in parts['R513']['pins'].items()}
parts['R731']['pins'] = {k: ('P47_D15' if v == 'P47_XSTL_SRC' else v) for k, v in parts['R731']['pins'].items()}
parts['R511']['pins'] = {k: ('KEY_POWER_MCU' if v == 'GPIO0' else v) for k, v in parts['R511']['pins'].items()}

# ------------------------------------------------------------- IO expander (single XL9535, address 0x20)
parts['U601']['pins'].update({
    '4': 'EN_3V3_SD', '5': 'P47_HV_EN', '6': 'P47_VCOM_EN', '7': 'P47_MODE', '8': 'P47_XOE',
    '9': 'FL_HWEN', '10': 'AUDIO_EN', '11': 'TOUCH_RST',
    '13': 'TOUCH_INT', '14': 'P47_PGOOD', '15': 'BQ_INT', '16': 'FUEL_GPOUT', '17': 'IMU_INT1',
    '18': 'SD_CD', '19': '', '20': ''})

# ------------------------------------------------------------- SD card, 1-bit SDMMC
parts['J501']['pins'].update({'1': 'SD_D2', '2': 'SD_D3', '3': 'SD_CMD', '5': 'SD_CLK', '7': 'SD_D0', '8': 'SD_D1'})
for ref, net in (('R523', 'SD_CMD'), ('R524', 'SD_D0'), ('R525', 'SD_D1'), ('R526', 'SD_D2'), ('R527', 'SD_D3')):
    parts[ref]['pins'] = {k: (net if v.startswith('SDMMC_') else v) for k, v in parts[ref]['pins'].items()}

# ------------------------------------------------------------- rails merged after removing load switches
MERGE = {'3V3_TOUCH': '3V3_AON', '3V3_EPD_LOGIC': '3V3_AON', 'VSYS_AUDIO': 'VSYS_RAW',
         '3V3_SD_SW': '3V3_SD', '3V3_AON_SRC': '3V3_AON', '3V3_EPD_LOGIC_SW': '3V3_AON'}
for p in parts.values():
    p['pins'] = {k: MERGE.get(v, v) for k, v in p['pins'].items()}
parts['U904']['pins']['1'] = 'AUDIO_EN'          # NS4168 CTRL: low = shutdown

# ------------------------------------------------------------- charger / front light permits removed
parts['U901']['pins'].update({'9': 'GND', '3': '', '4': ''})   # CE tied low: charging on by default
parts['U905']['pins']['A1'] = 'GND'                            # PWM unused, brightness over I2C

# ------------------------------------------------------------- new / replaced parts
def new(ref, value, lib, fp, mfr, mpn, lcsc, desc, pins):
    parts[ref] = dict(value=value, lib=lib, footprint=fp, dnp=False, pins=pins,
                      fields={'Manufacturer': mfr, 'MPN': mpn, 'LCSC': lcsc, 'Description': desc,
                              'Datasheet': f'https://www.lcsc.com/product-detail/{lcsc}.html'})

new('U302', 'BM8563EMA', 'Package_SO', 'MSOP-8_3x3mm_P0.65mm', 'GATEMODE', 'BM8563EMA', 'C269878',
    'GATEMODE BM8563 I2C RTC (PCF8563 register set), address 0x51, INT open drain to EXP_INT',
    {'1': 'RTC_OSCI', '2': 'RTC_OSCO', '3': 'EXP_INT', '4': 'GND', '5': 'I2C_SDA', '6': 'I2C_SCL', '7': '', '8': '3V3_AON'})
new('Y301', '32.768kHz 12.5pF', 'Crystal', 'Crystal_SMD_3215-2Pin_3.2x1.5mm', 'YXC', 'X321532768KGD2SI', 'C620155',
    'YXC 32.768 kHz 12.5 pF +/-20 ppm 3215 crystal for BM8563', {'1': 'RTC_OSCI', '2': 'RTC_OSCO'})
new('U503', 'SC7A20HTR', 'Package_LGA', 'LGA-12_2x2mm_P0.5mm', 'Hangzhou Silan Microelectronics', 'SC7A20HTR', 'C19274408',
    'Silan SC7A20H 3-axis accelerometer, I2C address 0x19 (SDO open), CS tied high for I2C',
    {'1': '', '2': 'I2C_SDA', '3': '3V3_AON', '4': 'GND', '5': 'IMU_INT1', '6': '', '7': '3V3_AON',
     '8': 'GND', '9': 'GND', '10': '3V3_AON', '11': '', '12': 'I2C_SCL'})
new('U902', 'SY8089A1AAC', 'Package_TO_SOT_SMD', 'SOT-23-5', 'Silergy', 'SY8089A1AAC', 'C479074',
    'Silergy SY8089A1 2 A 1.5 MHz buck with 100% dropout, VSYS_RAW -> 3V3_AON (0.6 V x (1 + 100k/22.1k) = 3.31 V)',
    {'1': 'VSYS_RAW', '2': 'GND', '3': 'BUCK_LX', '4': 'VSYS_RAW', '5': 'BUCK_FB'})
new('L401', '1uH', 'Inductor_SMD', 'L_Murata_DFE201610P', 'Sunlord', 'WPN201610H1R0MT', 'C97002',
    'Sunlord 1 uH 2.05 A 70 mOhm 2016 x 1.0 mm power inductor for SY8089', {'1': 'BUCK_LX', '2': '3V3_AON'})
new('R401', '100k', 'Resistor_SMD', 'R_0402_1005Metric', 'UNI-ROYAL(Uniroyal Elec)', '0402WGF1003TCE', 'C25741',
    'SY8089 RH 100k 1% 0402', {'1': '3V3_AON', '2': 'BUCK_FB'})
new('R402', '22.1k', 'Resistor_SMD', 'R_0402_1005Metric', 'UNI-ROYAL(Uniroyal Elec)', '0402WGF2212TCE', 'C25960',
    'SY8089 RL 22.1k 1% 0402', {'1': 'BUCK_FB', '2': 'GND'})
new('C404', '22pF', 'Capacitor_SMD', 'C_0402_1005Metric', 'Samsung Electro-Mechanics', 'CL05C220JB5NNNC', 'C1555',
    'SY8089 feed-forward 22 pF C0G 0402 across RH', {'1': '3V3_AON', '2': 'BUCK_FB'})

# Front light: AW99703CSR (WLCSP, 0.15 mm via-in-pad, 35 pcs stock) -> SGMICRO SGM3732 boost.
# Warm/cool strings are selected by Q901/Q902 from the expander; brightness is PWM on CTRL (GPIO0).
for r in ('C921', 'R920'):
    del parts[r]
new('U905', 'SGM3732YTN6G/TR', 'Package_TO_SOT_SMD', 'TSOT-23-6', 'SGMICRO', 'SGM3732YTN6G/TR', 'C116578',
    'SGMICRO SGM3732 1.1 MHz WLED boost, 200 mV FB, 38 V OVP; CTRL = PWM dimming (500k internal pull-down)',
    {'1': 'FL_SW', '2': 'GND', '3': 'FL_FB', '4': 'FL_PWM', '5': 'FL_VOUT', '6': 'VSYS_RAW'})
q = r50['comps']['Q907']
for ref, drain, gate in (('Q901', 'FL_W_N', 'FL_W_EN'), ('Q902', 'FL_C_N', 'FL_C_EN')):
    parts[ref] = dict(value=q['value'], lib='Panda47', footprint=q['fpid'], fields=dict(q['fields']), dnp=False,
                      pins={'1': gate, '2': drain, '3': 'FL_FB'})
new('R921', '10R 1%', 'Resistor_SMD', 'R_0402_1005Metric', 'UNI-ROYAL(Uniroyal Elec)', '0402WGF100JTCE', 'C25077',
    'SGM3732 RSET: 0.2 V / 10 R = 20 mA total front-light current (tune to the panel FL spec)', {'1': 'FL_FB', '2': 'GND'})
parts['R601']['pins'] = {'1': 'FL_W_EN', '2': 'GND'}
new('R602', '100k', 'Resistor_SMD', 'R_0402_1005Metric', 'UNI-ROYAL(Uniroyal Elec)', '0402WGF1003TCE', 'C25741',
    'FL_C_EN gate pull-down', {'1': 'FL_C_EN', '2': 'GND'})
parts['U501']['pins']['5'] = 'FL_PWM'                          # GPIO0 strap (R511 pull-up) doubles as FL PWM
parts['R511']['pins'] = {k: ('FL_PWM' if v == 'KEY_POWER_MCU' else v) for k, v in parts['R511']['pins'].items()}
parts['SW201']['pins']['1'] = 'KEY_POWER'
parts['TP19'] = dict(value='GPIO0 / BOOT', lib='Panda47', footprint=r50['comps']['TP18']['fpid'],
                     fields={'Description': 'short to GND during reset for ROM download mode'}, dnp=False, pins={'1': 'FL_PWM'})
new('R528', '100k', 'Resistor_SMD', 'R_0402_1005Metric', 'UNI-ROYAL(Uniroyal Elec)', '0402WGF1003TCE', 'C25741',
    'KEY_POWER pull-up', {'1': '3V3_AON', '2': 'KEY_POWER'})

# Expander moves to the 4 x 4 QFN-24 (XL9535QF24). TSSOP pin n -> QFN n-3 for n >= 4; INT/A1/A2 -> 22/23/24.
tssop = parts['U601']['pins']
tssop.update({'9': 'FL_W_EN', '19': 'FL_C_EN', '20': 'KEY_POWER'})
qfn = {('22', '23', '24')[int(n) - 1] if int(n) <= 3 else str(int(n) - 3): net for n, net in tssop.items()}
qfn['25'] = 'GND'
parts['U601'] = dict(value='XL9535QF24', lib='Package_DFN_QFN', footprint='QFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm',
                     dnp=False, pins=qfn, fields={'Manufacturer': 'XINLUDA', 'MPN': 'XL9535QF24', 'LCSC': 'C5444301',
                     'Description': 'XINLUDA XL9535 16-bit I2C GPIO expander, QFN-24 4x4, address 0x20, EP to GND',
                     'Datasheet': 'https://www.lcsc.com/product-detail/C5444301.html'})

# Flash stays GD25Q128ESIG SOP-8: the WSON-8 GD25Q128EWIGR is $2.57 against $0.96.
# v0.2.2 (user, 2026-11-12: lowest component height): WSON-8 6x5 x 0.8 mm max (GD datasheet 10.4) instead of the
# ~2 mm SOP-8. JLC 2026-11-12: C2982923 $3.31 / 1902 in stock against C2758105 $1.77. The exposed pad is floating
# (GD note 2), so the footprint EP is an unnumbered pad without a net.
if VARIANT in ('v022', 'v023', 'v024'):
    parts['U506'].update(value='GD25Q128EWIGR', lib='Panda47v2', footprint='WSON-8-1EP_6x5mm_P1.27mm_EP3.4x4mm')
    parts['U506']['fields'].update({'Manufacturer': 'GigaDevice', 'MPN': 'GD25Q128EWIGR', 'LCSC': 'C2982923',
                                    'Description': 'GigaDevice GD25Q128E 128 Mbit QSPI NOR flash, WSON-8 6x5 mm, 0.8 mm max',
                                    'Datasheet': 'https://www.lcsc.com/product-detail/C2982923.html'})

# v0.2.2 (user, 2026-11-12): one status LED on the SGM41513 STAT pin (open drain, pin 4). Hardware: on while charging,
# off when done, 1 Hz blink on a fault; firmware can also set on / blink via STAT_SET when EN_ICHG_MON = 01.
# Fed from VSYS_RAW (3.4..4.4 V) through 1k: about 0.7..1.7 mA with Vf ~2.7 V. Shines through a 1 mm hole in the shell.
if VARIANT in ('v022', 'v023', 'v024'):
    parts['U901']['pins']['4'] = 'CHG_STAT'
    new('D203', 'Green side-view LED', 'Panda47v2', 'LED_SideView_TJ-S1706', 'TOGIALED', 'TJ-S1706SW6TGLC2G-A5', 'C273616',
        'TOGIALED 0603 side-view green LED, 1.7 x 0.6 x 1.1 mm; status LED on SGM41513 STAT (pin 1 cathode)',
        {'1': 'CHG_STAT', '2': 'CHG_LED_A'})
    new('R208', '1k', 'Resistor_SMD', 'R_0402_1005Metric', 'UNI-ROYAL(Uniroyal Elec)', '0402WGF1001TCE', 'C11702',
        'Status LED series resistor 1k 1% 0402', {'1': 'VSYS_RAW', '2': 'CHG_LED_A'})

# v0.2.4 (user, 2026-11-13): the cell pack carries its own protection board (3.0 x 57 x 79 mm class, PCM + NTC), so the
# on-board protection (U907, R940, C940) goes. One 3-pad landing takes the pack: J302 = NTC, cell -, cell +.
if VARIANT == 'v024':
    for r in ('U907', 'R940', 'C940', 'J301'):
        del parts[r]
    parts['J302']['pins'] = {'1': 'BQ_TS', '2': 'GND', '3': 'BAT_CONN_P'}
    parts['J302']['value'] = 'PACK LANDING: NTC / B- / B+'

# SY7636A boost inductors: 7 x 9 mm MWSA0618 -> 4 x 4 x 1.2 mm Sunlord WPN4012H4R7MT (1.9 A, 138 mOhm).
for r in ('L801', 'L802'):
    parts[r].update(value='4.7uH', lib='Inductor_SMD', footprint='L_Changjiang_FNR4012S')
    parts[r]['fields'] = {'Manufacturer': 'Sunlord', 'MPN': 'WPN4012H4R7MT', 'LCSC': 'C370623',
                          'Description': 'Sunlord 4.7 uH 1.9 A 138 mOhm 4x4x1.2 mm power inductor (SY7636A VP/VN)',
                          'Datasheet': 'https://www.lcsc.com/product-detail/C370623.html'}

# Stocked, mainland catalogue parts for the R49 PMIC passives (JLC API 2026-11-10; 1% accepted by the user).
def stock(ref, mfr, mpn, lcsc, value=None):
    parts[ref]['fields'].update({'Manufacturer': mfr, 'MPN': mpn, 'LCSC': lcsc,
                                 'Datasheet': f'https://www.lcsc.com/product-detail/{lcsc}.html'})
    if value:
        parts[ref]['value'] = value

UR = 'UNI-ROYAL(Uniroyal Elec)'
stock('U810', 'Silergy', 'SY7636ARMC', 'C22451321')   # JLC stock 0: consigned
stock('R801', UR, '0402WGF4423TCE', 'C5101', '442k/1%')
stock('R802', UR, '0402WGF2102TCE', 'C25766', '21k/1%')
stock('R803', UR, '0402WGF7503TCE', 'C122545', '750k/1%')
stock('R804', UR, '0402WGF5902TCE', 'C32297', '59k/1%')
stock('R807', UR, '0402WGF1002TCE', 'C25744', '10k')
for r in ('C801', 'C803', 'C816'):
    stock(r, 'Samsung Electro-Mechanics', 'CL21A106KAYNNNE', 'C15850', '10u/25V/0805')
parts['R402']['fields'].update({'MPN': '0402WGF2212TCE', 'LCSC': 'C43473',
                                'Datasheet': 'https://www.lcsc.com/product-detail/C43473.html'})
parts['L402'].update(value='1uH', lib='Inductor_SMD', footprint='L_Changjiang_FNR4012S')
parts['L402']['fields'] = {'Manufacturer': 'Sunlord', 'MPN': 'WPN4012H1R0MT', 'LCSC': 'C316330',
                           'Description': 'Sunlord 1 uH 3.2 A 59 mOhm 4x4x1.2 mm, SGM41513 buck inductor',
                           'Datasheet': 'https://www.lcsc.com/product-detail/C316330.html'}

# EPD PMIC block shrunk to 0603 / SOD-323 (same ratings: 50 V on the VGH/VGL pumps, 25 V on the +/-15 V rails).
SAM = 'Samsung Electro-Mechanics'
PMIC_CAPS = {
    ('C802', 'C804', 'C805', 'C806', 'C813', 'C814'): ('4.7u/25V/0603', 'CCTC', 'TCC0603X5R475M250CT', 'C20539423'),
    ('C807', 'C809', 'C810', 'C812'): ('1u/50V/0603', SAM, 'CL10A105KB8NNNC', 'C15849'),
    ('C808', 'C811'): ('47n/50V/0603', SAM, 'CL10B473KB8NNNC', 'C1622'),
    ('C801', 'C803', 'C816'): ('10u/25V/0603', SAM, 'CL10A106MA8NRNC', 'C96446'),
}
for refs, (val, mfr, mpn, lcsc) in PMIC_CAPS.items():
    for r in refs:
        parts[r].update(value=val, lib='Capacitor_SMD', footprint='C_0603_1608Metric')
        parts[r]['fields'] = {'Manufacturer': mfr, 'MPN': mpn, 'LCSC': lcsc, 'Description': f'{val} SY7636A PMIC capacitor',
                              'Datasheet': f'https://www.lcsc.com/product-detail/{lcsc}.html'}
for r in ('D801', 'D802'):    # pin 1 cathode, pin 2 anode (same pin nets as the SOD-123 MBR0530)
    parts[r].update(value='1N5819WS', lib='Diode_SMD', footprint='D_SOD-323')
    parts[r]['fields'] = {'Manufacturer': 'Guangdong Hottech', 'MPN': '1N5819WS', 'LCSC': 'C191023',
                          'Description': '40 V 1 A Schottky SOD-323, SY7636A VP boost / VN inverter rectifier',
                          'Datasheet': 'https://www.lcsc.com/product-detail/C191023.html'}

# v0.2.4: the VN reservoir C804 sits at U810 pin 4, 9 mm and two vias from the rectifier D802. C817 (same part) goes
# right at the D802 anode so the pulsed diode current closes next to the switch.
if VARIANT == 'v024':
    parts['C817'] = json.loads(json.dumps(parts['C804']))
    parts['C817']['fields']['Reference'] = 'C817'
    parts['C817']['fields']['Description'] = '4.7u/25V/0603 SY7636A VN capacitor at the rectifier D802'
    # C818: input capacitor right at the inverting-converter supply pin (U810 pin 24); the 10 uF caps are 4-6 mm away.
    # Same part as C304 (2.2 uF / 10 V 0402); VSYS is at most 4.4 V.
    parts['C818'] = json.loads(json.dumps(parts['C304']))
    parts['C818'].update(value='2.2u/10V/0402', lib=parts['C404']['lib'], footprint=parts['C404']['footprint'],
                         pins={'1': 'VSYS_RAW', '2': 'GND'})
    parts['C818']['fields']['Reference'] = 'C818'
    parts['C818']['fields']['Description'] = '2.2u/10V/0402 SY7636A inverter input capacitor at U810 pin 24'
    # C816 (10 uF) sat right of L802 and was fed by a track under the inductor; with C818 at the pin and C801 / C803
    # on the same rail it is dropped.
    del parts['C816']
    # Three more fixture pads on the back: front-light boost output, switched SD rail, a second ground.
    for ref, net, src, desc in (('TP5', 'FL_VOUT', 'TP11', 'Front-light boost output test pad'),
                                ('TP6', '3V3_SD', 'TP801', 'Switched microSD 3.3 V rail test pad'),
                                ('TPG2', 'GND', 'TP11', 'Second ground fixture pad')):
        parts[ref] = json.loads(json.dumps(parts[src]))
        parts[ref].update(value=net, pins={'1': net})
        parts[ref]['fields'] = {'Datasheet': '', 'Description': desc, 'LCSC': '', 'MPN': 'NOT_A_PURCHASED_PART',
                                'Manufacturer': 'PCB fabricated terminal', 'Reference': ref, 'Value': net}
    # GPIO0 (U501 pin 5) has the 10 k boot pull-up R511, so the front-light boost was enabled during reset, boot and
    # download mode with both LED switches off (open load, output at the over-voltage limit). FL_PWM moves to GPIO2
    # (pin 7) with a pull-down R515; I2S_BCLK takes GPIO0, where an idle-high input does no harm.
    assert parts['U501']['pins']['5'] == 'FL_PWM' and parts['U501']['pins']['7'] == 'I2S_BCLK'
    parts['U501']['pins']['5'], parts['U501']['pins']['7'] = 'I2S_BCLK', 'FL_PWM'
    parts['R511']['pins']['2'] = 'I2S_BCLK'; parts['TP19']['pins']['1'] = 'I2S_BCLK'
    parts['R515'] = json.loads(json.dumps(parts['R528']))
    parts['R515'].update(value='100k / FL_PWM_PD', lib='Resistor_SMD', footprint='R_0402_1005Metric', pins={'1': 'FL_PWM', '2': 'GND'})
    parts['R515']['fields'].update(Reference='R515', Value='100k / FL_PWM_PD',
                                   Description='Front-light boost CTRL pull-down: boost off while the MCU pin is not driven')
    # Assembly (user, 2026-11-14: no hand-soldered wires where a connector fits). The pack plugs into a keyed JST ACH
    # header (1.4 mm high, 2 A per contact at AWG28); the antenna pigtail plugs into an MHF4 receptacle (1.2 mm mated).
    # The pack is still fitted at the factory, not by the user. Speaker leads stay soldered to J502.
    parts['J302'].update(lib='Panda47v2', footprint='JST_ACH_BM03B-ACHSS-GAN-ETF_1x03-1MP_P1.20mm_Vertical',
                         value='BM03B-ACHSS / pack', pins={'1': 'BAT_CONN_P', '2': 'GND', '3': 'BQ_TS', 'MP': 'GND'})
    parts['J302']['fields'] = {'Datasheet': 'https://www.lcsc.com/product-detail/C5118705.html', 'LCSC': 'C5118705',
                               'Description': 'Pack connector: 1 = B+, 2 = B-, 3 = NTC. Mates with ACHR-03V-S (C274397) on the pack lead',
                               'MPN': 'BM03B-ACHSS-GAN-ETF(LF)(SN)', 'Manufacturer': 'JST', 'Reference': 'J302',
                               'Value': 'BM03B-ACHSS / pack'}
    parts['J507'].update(lib='Panda47v2', footprint='MHF4_KH-IPEX4-2020', value='MHF4 receptacle',
                         pins={'1': 'RF_ANT', '2': 'GND'})
    parts['J507']['fields'] = {'Datasheet': 'https://www.lcsc.com/product-detail/C530666.html', 'LCSC': 'C530666',
                               'Description': 'MHF4 RF receptacle for the 2.4 GHz FPC antenna pigtail (0.81 mm cable plug: 1.2 mm mated)',
                               'MPN': 'KH-IPEX4-2020', 'Manufacturer': 'Kinghelm', 'Reference': 'J507', 'Value': 'MHF4 receptacle'}
    # Board fixing (user, 2026-11-14): two reflow-soldered M1.6 nuts at the top edge; screws come in from the back of the rear shell.
    # Sinhoo SMTSO1620MTJ: 3.18 mm hex, 2.0 mm above the board, 2.5 mm board hole, 4.19 mm minimum pad (maker table).
    # The 1.0 mm version (C2928167) had 5 pieces in JLC stock on 2026-11-14; the 2.0 mm one had 1983 and gives more thread.
    # (H1, left of USB-C, was dropped the same day: a second shell lip holds that side instead.)
    for ref in ('H2', 'H3'):
        parts[ref] = {'dnp': False, 'lib': 'Panda47v2', 'footprint': 'SMTSO_M1.6_L1', 'value': 'M1.6 SMT nut', 'pins': {'1': 'GND'},
                      'fields': {'Datasheet': 'https://www.lcsc.com/product-detail/C2916317.html',
                                 'Description': 'Reflow-soldered M1.6 x 2.0 mm nut (SMTSO), board fixing screw from the rear shell',
                                 'LCSC': 'C2916317', 'MPN': 'SMTSO1620MTJ', 'Manufacturer': 'Sinhoo', 'Reference': ref,
                                 'Value': 'M1.6 SMT nut'}}

parts['C401']['pins'] = {'1': 'VSYS_RAW', '2': 'GND'}
for r in ('C402', 'C403'):
    parts[r]['pins'] = {'1': '3V3_AON', '2': 'GND'}
parts['C539']['pins'] = {'1': '3V3_AON', '2': 'GND'}
for p in parts.values():
    for k, v in p['pins'].items():
        if v in ('SGM62125_SW1', 'SGM62125_SW2'):
            raise SystemExit('stale U902 net')

# ------------------------------------------------------------- checks
nets = {}
for ref, p in parts.items():
    for pin, net in p['pins'].items():
        if net:
            nets.setdefault(net, []).append((ref, pin))
single = sorted(n for n, ns in nets.items() if len(ns) == 1 and not n.startswith('TP'))
json.dump(dict(revision='v0.2.0', parts=parts, nets=nets), open(sys.argv[3], 'w'), indent=1, sort_keys=True)
print(len(parts), 'parts', len(nets), 'nets')
print('single-pin nets:', single)
