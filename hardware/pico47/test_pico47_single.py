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
        self.assertFalse(spec['via_in_pad']['supplier_process_accepted'])
        self.assertEqual(
            spec['via_in_pad']['process'],
            'FILLED_AND_COPPER_CAPPED_OR_SUPPLIER_APPROVED_EQUIVALENT',
        )
        self.assertEqual(spec['usb_connector']['mpn'], 'U22401-17')
        self.assertEqual(sum(x['count'] for x in spec['via_in_pad']['targets']), 9)
        self.assertEqual(len(spec['via_in_pad']['external_dogbone_vias']), 1)
        bay = spec['battery_bay_clearance']
        self.assertEqual(bay['overlap_area_mm2'], 0.0)
        envelopes = bay['battery_assembly_envelopes_mm']
        self.assertEqual(
            set(envelopes),
            {
                'BATTERY_PACK',
                'BATTERY_SEAL',
                'BATTERY_TABS',
                'BATTERY_PCM',
                'BATTERY_WIRE_RED',
                'BATTERY_WIRE_BLK',
                'BATTERY_WIRE_NTC',
            },
        )
        for name, (bx1, by1, bx2, by2) in envelopes.items():
            with self.subTest(part=name):
                self.assertLessEqual(bx2, bay['upper_left_pcb_step_min_x_mm'])
                self.assertLessEqual(by2, bay['upper_left_pcb_step_max_y_mm'])

    def test_apply_single_r26_x38_eco_replays_full_delta_without_crash(self):
        try:
            import wx  # noqa: F401
            import pcbnew
        except ImportError:
            self.skipTest('pcbnew not available in non-KiCad Python')
        from r25_router.apply_single_r26_x38_eco import DELTA_PATH, apply_single_r26_eco

        delta = json.loads(DELTA_PATH.read_text())
        self.assertEqual(len(delta['footprint_moves_mm']), 51)
        self.assertEqual(len(delta['removed_uuids']), 891)
        self.assertEqual(len(delta['shifted_plus_6p75_x_uuids']), 431)
        self.assertEqual(len(delta['added_tracks']), 657)
        self.assertEqual(len(delta['added_vias']), 106)

        spec = json.loads(SPEC.read_text())
        src_pcb = Path(spec['input_checkpoint']) / 'Single.kicad_pcb'
        if not src_pcb.is_file():
            self.skipTest('Single.kicad_pcb checkpoint not present')

        board = pcbnew.LoadBoard(str(src_pcb))
        for ref, (dx, dy) in delta['footprint_moves_mm'].items():
            fp = board.FindFootprintByReference(ref)
            self.assertIsNotNone(fp)
            fp.Move(pcbnew.VECTOR2I(pcbnew.FromMM(-dx), pcbnew.FromMM(-dy)))

        # Verify U901 is back at its R25 X=36.50 position before replay
        u901 = board.FindFootprintByReference('U901')
        self.assertAlmostEqual(pcbnew.ToMM(u901.GetPosition().x), 36.50, places=3)

        apply_single_r26_eco(board, delta)
        self.assertAlmostEqual(pcbnew.ToMM(u901.GetPosition().x), 43.25, places=3)
        self.assertAlmostEqual(pcbnew.ToMM(u901.GetPosition().y), 52.00, places=3)
        bt301 = board.FindFootprintByReference('BT301')
        self.assertAlmostEqual(pcbnew.ToMM(bt301.GetPosition().x), 62.50, places=3)
        c503 = board.FindFootprintByReference('C503')
        self.assertAlmostEqual(pcbnew.ToMM(c503.GetPosition().x), 56.28, places=3)
        self.assertAlmostEqual(pcbnew.ToMM(c503.GetPosition().y), 64.00, places=3)

        with tempfile.TemporaryDirectory() as d:
            out_pcb = Path(d) / 'Replayed.kicad_pcb'
            pcbnew.SaveBoard(str(out_pcb), board)
            self.assertTrue(out_pcb.is_file())


if __name__ == '__main__':
    unittest.main()
