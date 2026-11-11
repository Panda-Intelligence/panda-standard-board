"""Readable multi-sheet schematic for Panda47 v0.2.0 (plain Python; calls kicad-cli).

usage: build_v020_sch.py netlist_v020.json project_dir
project_dir holds Panda47-v020.kicad_pcb; writes Panda47-v020.kicad_sch + Panda47-v020-*.kicad_sch + Panda7.kicad_sym
and checks that the readable sheets keep the flat netlist exactly.
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import make_flat_sch_v020 as FLAT  # noqa: E402
import variant_v02x as VAR  # noqa: E402
import readable_schematic as RS  # noqa: E402

CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
STEM = VAR.STEM

RS.PROJECT = STEM
RS.PRODUCT = 'Pico-class'
RS.BOARD_DESC = VAR.BOARD
RS.REVISION = {'version': VAR.VERSION, 'revision': VAR.REVISION, 'date': VAR.DATE}
RS.POWER_NETS = ['GND', 'VBUS_USB', 'VSYS_RAW', '3V3_AON', '3V3_RF', 'VDD_SPI', '3V3_SD']
RS.SUPPLY = set(RS.POWER_NETS) - {'GND'}
RS.SHEETS = {
    '2': ('usb', 'USB_Input', 'USB-C 接口与 ESD 防护'),
    '3': ('rtc', 'RTC', 'RTC（BM8563）与 32.768 kHz 晶振'),
    '4': ('power3v3', 'Power_3V3', '3V3 降压（SY8089）与 microSD 电源开关'),
    '5': ('mcu', 'MCU', 'ESP32-S3、Flash、加速度计与 microSD'),
    '6': ('io', 'IO_Expander', 'IO 扩展 XL9535'),
    '7': ('epdbus', 'EPD_Bus', '墨水屏总线上下拉与 XCL 串联电阻'),
    '8': ('epd', 'EPD_PMIC', '墨水屏电源 SY7636A 与面板、触摸接口'),
    '9': ('power', 'Charger_Power', '充电、电量计、电池保护、音频与前光'),
}


def nets(path):
    root = ET.parse(path).getroot()
    return {frozenset((x.get('ref'), x.get('pin')) for x in n.iter('node')): n.get('name') for n in root.iter('net')}


def main(netlist, proj):
    proj = Path(proj)
    work = proj / '_sch_build'
    work.mkdir(exist_ok=True)
    flat = work / f'{STEM}.flat.kicad_sch'
    FLAT.PROJECT = STEM
    FLAT.main(netlist, flat)
    before, after = work / 'flat-net.xml', work / 'readable-net.xml'
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml', '--output', str(before), str(flat)], check=True,
                   capture_output=True)
    out = proj / f'{STEM}.kicad_sch'
    RS.main(str(flat), str(before), str(out), str(proj / f'{STEM}.kicad_pcb'))
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml', '--output', str(after), str(out)], check=True,
                   capture_output=True)
    a, b = nets(before), nets(after)
    if a != b:
        raise SystemExit(f'readable schematic changed the netlist: {len(set(a) ^ set(b))} differing nets')
    print('netlist identical:', len(a), 'nets')


if __name__ == '__main__':
    main(*sys.argv[1:3])
