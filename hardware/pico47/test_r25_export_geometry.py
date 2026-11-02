"""2026-11-01 Codex：用原生 KiCad 区域验证导出不会填平开口或丢弃优先级。"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

KICAD_READY = all(importlib.util.find_spec(name) for name in ['pcbnew', 'wx'])
EXPORT = Path(__file__).with_name('r25_router')/'export_geom.py'


@unittest.skipUnless(KICAD_READY, 'KiCad Python required')
class NativeZoneExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import wx
        import pcbnew
        cls.app = wx.GetApp() or wx.App(False)
        cls.P = pcbnew

    def add_ring(self, shape, points, hole=None):
        for x, y in points:
            if hole is None:
                shape.Append(self.P.FromMM(x), self.P.FromMM(y))
            else:
                shape.Append(self.P.FromMM(x), self.P.FromMM(y), 0, hole)

    def export(self, board, directory):
        native = directory/'input.kicad_pcb'
        result = directory/'geometry.json'
        self.P.SaveBoard(str(native), board)
        process = subprocess.run([sys.executable, str(EXPORT), str(native), str(result)],
                                 capture_output=True, text=True, timeout=30)
        return process, result

    def test_native_rule_area_holes_and_priority_survive_export(self):
        p = self.P
        board = p.BOARD()
        zone = p.ZONE(board)
        zone.SetZoneName('SD_REFERENCE_FIXTURE')
        zone.SetIsRuleArea(True)
        zone.SetLayer(p.B_Cu)
        zone.SetDoNotAllowTracks(True)
        zone.SetDoNotAllowVias(True)
        zone.SetAssignedPriority(7)
        shape = zone.Outline()
        shape.NewOutline()
        self.add_ring(shape, [(1, 1), (9, 1), (9, 9), (1, 9)])
        expected = [[(2, 2), (3, 2), (3, 3), (2, 3)],
                    [(6, 6), (8, 6), (8, 8), (6, 8)]]
        for ring in expected:
            self.add_ring(shape, ring, shape.NewHole(0))
        zone.thisown = False
        board.Add(zone)
        with tempfile.TemporaryDirectory() as temporary:
            process, output = self.export(board, Path(temporary))
            self.assertEqual(process.returncode, 0, process.stderr)
            exported = json.loads(output.read_text())['zones'][0]
        self.assertEqual(len(exported['holes']), 2)
        self.assertEqual(exported['priority'], 7)
        self.assertTrue(exported['no_tracks'])
        self.assertTrue(exported['no_vias'])
        for actual, ring in zip(exported['holes'], expected):
            self.assertEqual({tuple(round(value, 6) for value in point) for point in actual},
                             set(ring))

    def test_native_copper_zone_priority_survives_export_without_holes(self):
        p = self.P
        board = p.BOARD()
        zone = p.ZONE(board)
        zone.SetZoneName('USB_REFERENCE_FIXTURE')
        zone.SetLayer(p.F_Cu)
        zone.SetAssignedPriority(3)
        shape = zone.Outline()
        shape.NewOutline()
        self.add_ring(shape, [(1, 1), (2, 1), (2, 2), (1, 2)])
        zone.thisown = False
        board.Add(zone)
        with tempfile.TemporaryDirectory() as temporary:
            process, output = self.export(board, Path(temporary))
            self.assertEqual(process.returncode, 0, process.stderr)
            exported = json.loads(output.read_text())['zones'][0]
        self.assertEqual(exported['priority'], 3)
        self.assertEqual(exported['holes'], [])
        self.assertFalse(exported['rule'])


if __name__ == '__main__':
    unittest.main()
