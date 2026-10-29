"""CHIP_PU R25 ECO 的纯文本回归测试。"""

import tempfile
import unittest
from pathlib import Path

from chip_pu_reset_eco import _rename_pin_labels, apply_schematic


def _symbol(name, pins, ref, x):
    definition = (
        f'(symbol "Panda7:{name}" (symbol "{name}_0_1")'
        '(rectangle(start -10 5)(end 10 -5)(stroke(width .1)(type default))'
        '(fill(type background)))'
        f'(symbol "{name}_1_1"'
        + "".join(
            f'(pin passive line (at {x} 0 {angle}) (length 2.54) '
            f'(name "{number}" (effects (font (size .8 .8))))'
            f'(number "{number}" (effects (font (size .8 .8)))))'
            for number, x, angle in pins
        )
        + '))'
    )
    instance = (
        f'(symbol(lib_id "Panda7:{name}")(at {x} 100 0)(unit 1)(in_bom yes)'
        f'(on_board yes)(dnp no)(uuid "{ref}-uuid")'
        f'(property "Reference" "{ref}" (at {x} 100 0) (effects (font (size .8 .8))))'
        f'(property "Value" "{name}" (at {x} 102 0) (effects (font (size .8 .8))))'
        f'(property "Footprint" "Panda47:{ref}_Core" (at {x} 100 0) (hide yes)'
        '(effects (font (size .8 .8))))'
        f'(instances(project "Core"(path "/root"(reference "{ref}")(unit 1)))))'
    )
    return definition, instance


def _fixture():
    definitions = []
    instances = []
    labels = []
    for name, pins, ref, x in [
        ("U501", [("4", -12.7, 0)], "U501", 100),
        ("R510", [("1", -12.7, 0), ("2", 12.7, 180)], "R510", 150),
        ("C510", [("1", -12.7, 0), ("2", 12.7, 180)], "C510", 200),
        ("TP18", [("1", -12.7, 0)], "TP18", 250),
        ("J503", [("1", -12.7, 0)], "J503", 300),
    ]:
        definition, instance = _symbol(name, pins, ref, x)
        definitions.append(definition)
        instances.append(instance)
    # 左 pin = x-12.7，右 pin = x+12.7。
    for ref, x, net in [
        ("U501", 87.3, "CHIP_PU"),
        ("R510", 137.3, "3V3_AON"),
        ("R510", 162.7, "CHIP_PU"),
        ("C510", 187.3, "CHIP_PU"),
        ("TP18", 237.3, "CHIP_PU"),
        ("J503", 287.3, "CHIP_PU"),
    ]:
        labels.append(
            f'(global_label "{net}" (shape passive) (at {x} 100 0) '
            f'(effects (font (size .8 .8))(justify left))(uuid "{ref}-{x}"))'
        )
    return '(kicad_sch(version 20250114)(lib_symbols ' + ''.join(definitions) + ')' + ''.join(instances + labels) + ')\n'


class ChipPuResetEcoTests(unittest.TestCase):
    def test_pin_labels_split_without_guessing(self):
        text = _fixture()
        changed, count = _rename_pin_labels(text)
        self.assertEqual(count, 5)
        self.assertEqual(changed.count('"CHIP_PU_MCU"'), 4)
        self.assertEqual(changed.count('"CHIP_PU_DEBUG"'), 1)

    def test_native_schematic_adds_series_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'Core.kicad_sch'
            output = Path(directory) / 'Core-eco.kicad_sch'
            source.write_text(_fixture())
            report = apply_schematic(source, output, r533_position=(200.0, 200.0))
            self.assertEqual(report['added_ref'], 'R533')
            result = output.read_text()
            self.assertIn('Panda7:R533', result)
            self.assertIn('(reference "R533")', result)
            self.assertIn('CHIP_PU_DEBUG', result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
