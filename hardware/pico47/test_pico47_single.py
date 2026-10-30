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
        repo_root = SPEC.resolve().parent.parent.parent
        v011_dir = repo_root / spec['version_directory']
        v010_dir = repo_root / spec['baseline_version_directory']
        verify_inputs(v011_dir, spec)
        v010_spec = {'input_sha256': dict(spec['input_sha256'])}
        v010_spec['input_sha256']['Single.kicad_pcb'] = spec['baseline_r25_pcb_sha256']
        verify_inputs(v010_dir, v010_spec)
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
        self.assertTrue(bay['study_only_not_supplier_qualified'])
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
        expected_wh = {
            'BATTERY_PACK': (35.0, 76.0),
            'BATTERY_SEAL': (35.8, 74.0),
            'BATTERY_TABS': (18.0, 1.6),
            'BATTERY_PCM': (30.0, 3.8),
            'BATTERY_WIRE_RED': (3.7, 1.5),
            'BATTERY_WIRE_BLK': (3.7, 1.5),
            'BATTERY_WIRE_NTC': (3.7, 1.5),
        }
        for name, (bx1, by1, bx2, by2) in envelopes.items():
            with self.subTest(part=name):
                self.assertGreaterEqual(bx1, 1.1)
                self.assertGreaterEqual(by1, 1.1)
                self.assertLessEqual(bx2, bay['upper_left_pcb_step_min_x_mm'])
                self.assertLessEqual(by2, bay['upper_left_pcb_step_max_y_mm'])
                ew, eh = expected_wh[name]
                self.assertAlmostEqual(bx2 - bx1, ew, places=3)
                self.assertAlmostEqual(by2 - by1, eh, places=3)
        ur_bay = spec['upper_right_support_bay']
        self.assertTrue(ur_bay['study_only_not_supplier_qualified'])
        self.assertEqual(ur_bay['option'], 'option_1_structural_grid_poron_speaker_antenna')
        self.assertEqual(ur_bay['pcb_overlap_area_mm2'], 0.0)
        self.assertEqual(ur_bay['battery_overlap_area_mm2'], 0.0)
        self.assertAlmostEqual(ur_bay['coplanar_support_top_z_mm'], 3.95, places=3)
        ur_xy = ur_bay['envelopes_xy_mm']
        ur_z = ur_bay['envelopes_z_mm']
        self.assertEqual(
            set(ur_xy),
            {'UPPER_RIGHT_RIB_GRID', 'UPPER_RIGHT_PORON_PAD', 'SPEAKER_BOX_1511', 'FPC_ANTENNA_2G4'},
        )
        for name, (ux1, uy1, ux2, uy2) in ur_xy.items():
            with self.subTest(ur_part=name):
                self.assertGreaterEqual(ux1, ur_bay['battery_right_edge_max_x_mm'] + 1.0)
                self.assertLessEqual(uy2, ur_bay['pcb_top_edge_min_y_mm'] - 0.8)
                self.assertLessEqual(ux2, 73.9)
                self.assertGreaterEqual(uy1, 1.1)
                uz1, uz2 = ur_z[name]
                self.assertGreaterEqual(uz1, 0.55)
                self.assertLessEqual(uz2, ur_bay['coplanar_support_top_z_mm'])
        self.assertAlmostEqual(ur_z['UPPER_RIGHT_PORON_PAD'][1], 3.95, places=3)
        self.assertAlmostEqual(ur_xy['SPEAKER_BOX_1511'][2] - ur_xy['SPEAKER_BOX_1511'][0], 15.0, places=3)
        self.assertAlmostEqual(ur_xy['SPEAKER_BOX_1511'][3] - ur_xy['SPEAKER_BOX_1511'][1], 11.0, places=3)

    def test_apply_single_r26_x38_eco_replays_full_delta_without_crash(self):
        try:
            import wx  # noqa: F401
            import pcbnew
        except ImportError:
            self.skipTest('pcbnew not available in non-KiCad Python')
        from r25_router.apply_single_r26_x38_eco import (
            DELTA_PATH,
            apply_single_r26_eco,
            verify_input_sha256,
        )

        delta = json.loads(DELTA_PATH.read_text())
        self.assertEqual(len(delta['footprint_moves_mm']), 51)
        self.assertEqual(len(delta['removed_uuids']), 891)
        self.assertEqual(len(delta['shifted_plus_6p75_x_uuids']), 431)
        self.assertEqual(len(delta['added_tracks']), 657)
        self.assertEqual(len(delta['added_vias']), 106)

        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / 'bad.kicad_pcb'
            bad.write_text('not a valid r25 or r26 pcb')
            with self.assertRaisesRegex(ValueError, 'does not match baseline R25'):
                verify_input_sha256(bad, delta)

        spec = json.loads(SPEC.read_text())
        repo_root = SPEC.resolve().parent.parent.parent
        src_pcb = repo_root / spec['version_directory'] / 'Single.kicad_pcb'
        self.assertTrue(src_pcb.is_file())
        self.assertEqual(verify_input_sha256(src_pcb, delta), delta['target_r26_sha256'])

        board = pcbnew.LoadBoard(str(src_pcb))
        for ref, (dx, dy) in delta['footprint_moves_mm'].items():
            fp = board.FindFootprintByReference(ref)
            self.assertIsNotNone(fp)
            fp.Move(pcbnew.VECTOR2I(pcbnew.FromMM(-dx), pcbnew.FromMM(-dy)))

        # Verify U901 is back at its R25 X=36.50 position before replay
        u901 = board.FindFootprintByReference('U901')
        self.assertAlmostEqual(pcbnew.ToMM(u901.GetPosition().x), 36.50, places=3)

        # Strict UUID check must reject synthetic board missing R25 removed UUIDs
        with self.assertRaisesRegex(ValueError, 'Missing .* expected R25'):
            apply_single_r26_eco(board, delta, strict_uuid_check=True)

        # Replay footprint moves and outline on synthetic board with strict_uuid_check=False
        board = pcbnew.LoadBoard(str(src_pcb))
        for ref, (dx, dy) in delta['footprint_moves_mm'].items():
            fp = board.FindFootprintByReference(ref)
            fp.Move(pcbnew.VECTOR2I(pcbnew.FromMM(-dx), pcbnew.FromMM(-dy)))
        apply_single_r26_eco(board, delta, strict_uuid_check=False)
        u901 = board.FindFootprintByReference('U901')
        self.assertAlmostEqual(pcbnew.ToMM(u901.GetPosition().x), 43.25, places=3)
        self.assertAlmostEqual(pcbnew.ToMM(u901.GetPosition().y), 52.00, places=3)
        bt301 = board.FindFootprintByReference('BT301')
        self.assertAlmostEqual(pcbnew.ToMM(bt301.GetPosition().x), 62.50, places=3)
        c503 = board.FindFootprintByReference('C503')
        self.assertAlmostEqual(pcbnew.ToMM(c503.GetPosition().x), 56.28, places=3)
        self.assertAlmostEqual(pcbnew.ToMM(c503.GetPosition().y), 64.00, places=3)

        # Also test strict_uuid_check=True on the preserved R25 (v0.1.0) baseline board in repo
        r25_pcb = repo_root / spec['baseline_version_directory'] / 'Single.kicad_pcb'
        self.assertTrue(r25_pcb.is_file())
        self.assertEqual(verify_input_sha256(r25_pcb, delta), delta['baseline_r25_sha256'])
        r25_board = pcbnew.LoadBoard(str(r25_pcb))
        apply_single_r26_eco(r25_board, delta, strict_uuid_check=True)
        with tempfile.TemporaryDirectory() as d:
            out_r26 = Path(d) / 'ReplayedFromR25.kicad_pcb'
            pcbnew.SaveBoard(str(out_r26), r25_board)
            self.assertTrue(out_r26.is_file())

        with tempfile.TemporaryDirectory() as d:
            out_pcb = Path(d) / 'Replayed.kicad_pcb'
            pcbnew.SaveBoard(str(out_pcb), board)
            self.assertTrue(out_pcb.is_file())


if __name__ == '__main__':
    unittest.main()
