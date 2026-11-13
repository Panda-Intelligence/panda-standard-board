"""Hand layout of the v0.2.4 critical blocks (v0.2.3 blocks plus the pack landing, audio and RTC moves).
usage: design_v024.py padlib.json sizes.json out.json preview_dir usb_window.json [placement.json]"""
import json
import sys
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/v023')
from handlib import Design  # noqa: E402

D = Design(sys.argv[1], sys.argv[2])
VIEWS = {}


def charger():
    """SGM41513 buck charger: PMID cap at pin 23, boot cap at BTST, SW straight into the inductor, SYS and BAT wide."""
    D.place('U901', 53.0, 85.2, 180)
    D.place('L402', 58.9, 88.25, 0)
    D.place('C201', 57.45, 85.0, 0)
    D.place('C203', 57.35, 83.2, 0)
    D.place('C202', 54.6, 81.75, 90)
    D.place('C207', 58.1, 92.1, 270)
    D.place('C208', 55.9, 92.1, 270)
    D.place('C206', 50.4, 89.1, 180)
    D.place('C303', 51.85, 90.9, 0)
    D.track('SGM41513_SW', 0.7, [(54.9, 86.2), (56.9, 86.2), (57.4, 86.75)])
    D.track('SGM41513_SW', 0.3, ['C201.2', (58.2, 85.7), (57.6, 86.5)])
    D.track('SGM41513_BTST', 0.2, ['U901.21', (56.1, 85.45), (56.4, 85.3)])
    D.track('SGM41513_PMID', 0.24, ['U901.23', (55.3, 84.45), (55.75, 84.0)])
    D.track('SGM41513_REGN', 0.2, ['U901.22', (55.75, 84.9)])
    D.via('SGM41513_REGN', 55.75, 84.9)
    D.track('VBUS_USB', 0.3, ['U901.24', (55.05, 83.95), (55.05, 83.0), (54.6, 82.55)])
    D.track('VBUS_USB', 0.24, ['U901.1', (54.25, 82.9), (54.6, 82.55)])
    D.track('VBUS_USB', 0.5, [(54.6, 82.55), 'C202.1'])
    D.track('VSYS_RAW', 0.8, ['L402.2', (60.4, 90.85), (55.3, 90.85), (53.0, 88.6)])
    D.track('VSYS_RAW', 0.6, [(53.0, 88.6), (53.0, 87.1)])
    D.track('GND', 0.3, ['C203.2', (57.35, 83.2)])
    D.via('GND', 57.35, 83.2)
    D.track('GND', 0.24, ['U901.9', (52.0, 84.95)])
    D.track('BAT_PACKP', 0.5, [(52.0, 87.1), (52.0, 88.3), (51.35, 89.1), 'C206.1'])
    D.track('BAT_PACKP', 0.3, [(51.35, 89.1), (51.35, 90.9), 'C303.1'])
    VIEWS['charger'] = (47, 79, 63.6, 94)


def buck(x=21.0, y=76.6):
    """SY8089 3V3 buck: IN is pin 4, so CIN sits at pin 4 with its GND straight under the IC to pin 2; LX is 1 mm long."""
    D.place('U902', x, y, 0)
    D.place('C401', x + 2.9, y + 0.5, 90)
    D.place('L401', x - 1.0, y + 3.1, 0)
    D.place('C402', x + 1.2, y + 3.35, 270)
    D.place('C403', x + 2.7, y + 3.35, 270)
    D.place('R402', x + 1.9, y - 2.7, 0)
    D.place('R401', x + 3.9, y - 1.6, 180)
    D.place('C404', x + 3.9, y - 2.7, 180)
    D.track('VSYS_RAW', 0.5, ['U902.4', 'C401.1'])
    D.track('GND', 0.5, ['C401.2', (x + 2.0, y), 'U902.2'])
    D.track('BUCK_LX', 0.5, ['U902.3', (x - 1.5, y + 1.6), 'L401.1'])
    D.track('3V3_AON', 0.6, ['L401.2', (x - 0.275, y + 2.6), 'C402.1', 'C403.1', (x + 4.38, y + 2.6)])
    D.track('3V3_AON', 0.2, [(x + 4.38, y + 2.6), 'R401.1', 'C404.1'])
    D.track('BUCK_FB', 0.2, ['U902.5', (x + 1.8, y - 0.95), (x + 2.45, y - 1.6), 'R401.2', 'C404.2'])
    D.track('BUCK_FB', 0.2, ['U902.5', (x + 1.42, y - 1.7), 'R402.1'])
    D.track('VSYS_RAW', 0.2, ['U902.1', (x - 2.2, y - 0.95)])
    D.via('VSYS_RAW', x - 2.2, y - 0.95)
    VIEWS['buck'] = (x - 5, 72, x + 20, 83)


def frontlight(x=33.8, y=77.6):
    """SGM3732 LED boost: L905 -> SW pin and diode in 1 mm, output cap at the diode; VIN and GND drop under the body."""
    D.place('U905', x, y, 0)
    D.place('L905', x - 3.7, y - 1.2, 0)
    D.place('D905', x - 1.5, y - 3.7, 180)
    D.place('C923', x + 3.4, y - 2.3, 270)
    D.place('C920', x - 6.4, y - 1.2, 270)
    D.track('FL_SW', 0.5, ['L905.2', (x - 2.875, y - 0.95), 'U905.1'])
    D.track('FL_SW', 0.5, ['L905.2', (x - 2.875, y - 2.9), 'D905.2'])
    D.track('FL_VOUT', 0.5, ['D905.1', (x + 2.6, y - 3.7)])
    D.track('FL_VOUT', 0.2, [(x + 1.0, y - 3.7), (x + 2.2, y - 2.5), (x + 2.2, y - 0.4), (x + 1.8, y), 'U905.5'])
    D.track('VSYS_RAW', 0.5, ['C920.1', 'L905.1'])
    D.track('VSYS_RAW', 0.3, ['U905.6', (x + 0.1, y - 0.95)])
    D.via('VSYS_RAW', x + 0.1, y - 0.95)
    D.track('GND', 0.3, ['U905.2', (x - 0.15, y + 0.15)])
    D.via('GND', x - 0.15, y + 0.15)
    VIEWS['frontlight'] = (x - 8, 72, x + 7, 83)


def mcu_rf():
    """ESP32-S3 crystal and antenna: both crystal lines planar on F.Cu, RF on F.Cu at 0.17 mm (50 ohm on 0.1 mm prepreg)."""
    D.place('U501', 44.0, 96.3, 0)
    D.place('Y501', 42.4, 87.9, 0)
    D.place('C528', 39.35, 87.9, 90)
    D.place('C529', 45.45, 87.9, 90)
    D.place('C526', 40.8, 90.95, 0)
    D.place('C502', 45.6, 90.95, 0)
    D.place('L506', 42.25, 90.97, 90)
    D.place('L508', 38.65, 91.3, 90)
    D.place('C530', 36.8, 92.25, 0)
    D.place('C531', 36.8, 90.35, 0)
    D.place('J507', 34.3, 90.35, 90)
    D.track('XTAL_P_SOC', 0.127, ['U501.54', (42.2, 91.9), (42.25, 91.85), 'L506.1'])
    D.track('XTAL_P', 0.127, ['L506.2', (42.25, 90.2), (41.6, 89.55), (41.6, 89.2)])
    D.track('XTAL_P', 0.127, ['Y501.1', (40.524, 87.974), (39.756, 87.974), 'C528.1'])
    D.track('XTAL_N', 0.127, ['U501.53', (42.6, 92.0), (42.85, 91.75), (42.85, 90.0), (42.4, 89.55), (42.4, 87.9), (42.9, 87.4), 'Y501.3'])
    D.track('XTAL_N', 0.127, ['Y501.3', (44.408, 87.958), (45.028, 87.958), 'C529.1'])
    D.track('LNA_IN', 0.17, ['U501.1', (40.09, 93.7), (38.65, 92.26), 'L508.1'])
    D.track('LNA_IN', 0.17, ['L508.1', (37.622, 92.813), (36.883, 92.813), 'C530.1'])
    D.track('RF_ANT', 0.17, ['L508.2', (38.567, 90.898), (36.868, 90.898), 'C531.1', 'J507.1'])
    D.keepouts.append([33.3, 88.3, 35.3, 92.4])
    VIEWS['mcu_rf'] = (32, 85, 48, 95)


def usb(window):
    """USB-C fan-out and the D+/D- pair: the copper verified on v0.2.2, copied unchanged."""
    w = json.load(open(window))
    for r, p in w['pose'].items():
        D.place(r, *p)
    D.raw(w['tracks'], w['vias'])
    VIEWS['usb'] = (27, 99, 48, 111)


def trunks():
    """Charge-current paths as 0.8 mm tracks on B.Cu (1 oz): VBUS from the USB-C side to the charger, battery to BAT."""
    for tp, x, y in (('TP804', 47.6, 103.2), ('TP806', 49.6, 103.2), ('TPG1', 45.6, 82.4), ('TP1', 61.4, 84.6), ('TP11', 48.6, 83.5), ('TP12', 48.6, 86.6), ('TP2', 61.4, 92.6)):
        D.place(tp, x, y, 0)
    # VBUS: USB-C fan-out via -> along y 107.1 -> column x 59.3 (clear of the key posts) -> charger pins 1 / 24
    D.track('VBUS_USB', 0.6, [(34.5569, 107.8596), (34.5569, 107.1)], 'B.Cu')
    D.track('GND', 0.25, [(35.35, 109.05), (35.35, 108.105)])
    D.track('GND', 0.25, [(35.05, 109.05), (35.35, 108.105)])
    D.via('GND', 35.35, 108.105)
    D.track('VBUS_USB', 0.8, [(34.5569, 107.1), (57.6, 107.1), (59.3, 105.4), (59.3, 83.0), (58.3, 82.0), (55.3, 82.0)], 'B.Cu')
    D.via('VBUS_USB', 55.3, 82.0)
    D.via('VBUS_USB', 55.95, 81.45)
    D.track('VBUS_USB', 0.8, [(55.3, 82.0), (55.95, 81.45)], 'B.Cu')
    D.track('VBUS_USB', 0.4, ['C202.1', (55.3, 82.0), (55.95, 81.45)])
    D.track('VBUS_USB', 0.4, [(59.3, 84.6), (61.4, 84.6)], 'B.Cu')          # test point TP1
    D.place('J302', 52.0, 78.8, 0)
    D.place('R306', 56.8, 75.0, 0)
    # pack +: landing J302.3 -> shunt R306 on F.Cu
    D.track('BAT_CONN_P', 0.8, ['J302.3', (54.0, 76.7), (55.0, 75.7), 'R306.1'])
    # shunt -> charger BAT pins 13 / 14: B.Cu along y 78.3, then down x 50.6
    D.track('BAT_PACKP', 0.6, [(58.26, 75.5), (59.6, 76.2), (59.6, 77.0)])
    D.via('BAT_PACKP', 59.6, 76.2)
    D.via('BAT_PACKP', 59.6, 77.0)
    D.track('BAT_PACKP', 0.8, [(59.6, 76.2), (59.6, 78.3), (50.6, 78.3), (50.6, 88.0), (51.35, 90.05)], 'B.Cu')
    D.via('BAT_PACKP', 50.6, 88.0)
    D.via('BAT_PACKP', 51.35, 90.05)
    D.track('BAT_PACKP', 0.4, [(50.6, 88.0), (51.3, 88.7)])
    VIEWS['trunks'] = (30, 72, 63.6, 110)


def moved():
    """Speaker notch at the top-left corner (x < 16.6, y 67.4..79): amplifier and speaker landing next to it; RTC and
    accelerometer take the space of the removed cell protection."""
    D.place('U601', 11.3, 86.6, 0)
    D.place('U904', 4.2, 83.2, 0)
    D.place('J502', 11.3, 81.2, 0)
    D.place('U302', 48.95, 75.4, 0)
    D.place('Y301', 44.3, 75.6, 90)
    D.place('U503', 45.6, 79.6, 0)
    VIEWS['moved'] = (0, 72, 22, 93)



charger()
buck()
frontlight()
mcu_rf()
moved()
if __name__ == '__main__':
    if len(sys.argv) > 5:
        usb(sys.argv[5])
        trunks()
    if len(sys.argv) > 6:
        D.load_others(sys.argv[6])
    iss = D.check()
    print(len(iss), 'issues'); [print('  ', i) for i in iss[:40]]
    D.export(sys.argv[3])
    if len(sys.argv) > 4:
        for name, v in VIEWS.items():
            D.svg(f'{sys.argv[4]}/{name}.svg', *v)
