"""2026-10-30 Codex：明确输入缺失或变化时不能重放不同的单板。"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from build_pico47_single import verify_inputs, SPEC


class SingleInputTests(unittest.TestCase):
    def fixture(self, path):
        names = ['Single'+s for s in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru')]
        names += ['Panda7.kicad_sym','fp-lib-table','sym-lib-table','Panda47.pretty/U501.kicad_mod']
        bindings = {}
        for name in names:
            f = path / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(name)
            bindings[name] = hashlib.sha256(f.read_bytes()).hexdigest()
        return {'input_sha256':bindings}

    def test_changed_cad_or_rule_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.fixture(root)
            verify_inputs(root, spec)
            for name in ('Single.kicad_pcb','Single.kicad_sch','Single.kicad_pro','Single.kicad_dru'):
                before = (root/name).read_bytes()
                (root/name).write_bytes(before+b'changed')
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Source differs'):
                    verify_inputs(root, spec)
                (root/name).write_bytes(before)

    def test_added_or_missing_footprint_library_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.fixture(root)
            extra = root/'Panda47.pretty/extra.kicad_mod'
            extra.write_text('extra')
            with self.assertRaisesRegex(ValueError, 'inventory differs'):
                verify_inputs(root, spec)
            extra.unlink()
            (root/'Panda47.pretty/U501.kicad_mod').unlink()
            with self.assertRaisesRegex(ValueError, 'inventory differs'):
                verify_inputs(root, spec)

    def test_missing_project_binding_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.fixture(root)
            del spec['input_sha256']['Single.kicad_pro']
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                verify_inputs(root, spec)

    def test_real_single_source_has_all_required_native_files(self):
        spec = json.loads(SPEC.read_text())
        self.assertEqual(spec['required_ground_pad_count'], 173)
        self.assertTrue(spec['via_in_pad']['supplier_process_accepted'])
        self.assertEqual(spec['via_in_pad']['process'], 'STANDARD_4L_TENTED_THERMAL_VIAS')
        self.assertEqual(spec['usb_connector']['mpn'], 'U22401-17')
        self.assertEqual(sum(x['count'] for x in spec['via_in_pad']['targets']), 9)
        self.assertEqual(len(spec['via_in_pad']['external_dogbone_vias']), 1)
        self.assertEqual(spec['battery_bay_clearance']['overlap_area_mm2'], 0.0)


if __name__ == '__main__':
    unittest.main()
