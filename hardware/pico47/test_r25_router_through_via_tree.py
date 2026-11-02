"""2026-11-01 Codex：三层真实A*夹具验证新增通孔可被后续支路复用。"""
import ctypes
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SOURCE = HERE/'r25_router'/'router2.py'
READY = shutil.which('cc') and all(importlib.util.find_spec(name)
                                  for name in ['numpy', 'scipy', 'shapely', 'PIL'])


@unittest.skipUnless(READY, 'Geometry environment and C compiler required')
class ThroughViaTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        library = Path(cls.temporary.name)/'astar-test.dylib'
        flags = ['-dynamiclib'] if sys.platform == 'darwin' else ['-shared', '-fPIC']
        subprocess.run(['cc', '-O2', '-std=gnu11', *flags,
                        str(SOURCE.with_name('astar.c')), '-o', str(library), '-lm'],
                       check=True, capture_output=True)
        native = ctypes.CDLL(str(library))
        spec = importlib.util.spec_from_file_location('pico47_via_tree_test', SOURCE)
        cls.R = importlib.util.module_from_spec(spec)
        with mock.patch('ctypes.CDLL', return_value=native):
            spec.loader.exec_module(cls.R)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        from shapely.geometry import box
        r = self.R
        r.X0 = r.Y0 = 0
        r.X1 = r.Y1 = 4
        r.PITCH = .025
        r.NX = r.NY = 161
        r.LAYERS[:] = ['F.Cu', 'In2.Cu', 'B.Cu']
        r.LCOST[:] = [1000, 1000, 1000]
        r.NL = 3
        r.NLAYER = r.NX*r.NY
        r.W = .15
        r.VIA_D = .4
        r.VIA_DR = .2
        r.SPOKE_BOX = None
        r.REGION = box(-1, -1, 5, 5)
        r.irange.__defaults__ = (0,)

    def geometry(self):
        def pad(ref, x, layer):
            return dict(ref=ref, num='1', net='TEST', x=x, y=2, drill=None,
                        uuid=ref, polys={layer:[[[x-.15, 1.85], [x+.15, 1.85],
                                                [x+.15, 2.15], [x-.15, 2.15]]]})
        def keepout(name, layers, ring, tracks=True, vias=False, holes=None):
            return dict(name=name, net='', rule=True, layers=layers, outline=[ring],
                        holes=holes or [], no_tracks=tracks, no_vias=vias)
        # 第一支路由F到B；随后必须从同一通孔接入In2上的保留铜段。
        return dict(outline=[[[0, 0], [4, 0], [4, 4], [0, 4]]],
                    pads=[pad('A', 1, 'F.Cu'), pad('B', 3, 'B.Cu')], vias=[],
                    tracks=[dict(net='TEST', layer='In2.Cu', w=.15, uuid='retained-tail',
                                 x1=2, y1=3.2, x2=2.075, y2=3.2)],
                    zones=[
                        keepout('surface-upper', ['F.Cu', 'B.Cu'],
                                [[0, 0], [4, 0], [4, 1.8], [0, 1.8]]),
                        keepout('surface-lower', ['F.Cu', 'B.Cu'],
                                [[0, 2.2], [4, 2.2], [4, 4], [0, 4]]),
                        keepout('inner-left', ['In2.Cu'],
                                [[0, 0], [1.8, 0], [1.8, 4], [0, 4]]),
                        keepout('inner-right', ['In2.Cu'],
                                [[2.2, 0], [4, 0], [4, 4], [2.2, 4]]),
                        keepout('one-drill-port', ['F.Cu', 'In2.Cu', 'B.Cu'],
                                [[0, 0], [4, 0], [4, 4], [0, 4]], tracks=False, vias=True,
                                holes=[[[1.79, 1.79], [2.21, 1.79],
                                        [2.21, 2.21], [1.79, 2.21]]])])

    def route(self, geometry):
        import numpy as np
        r = self.R
        context = r.prepare(geometry, dict(nets={'TEST':[]}, target_nets=[]))
        result = r.route_net(context, 'TEST', np.zeros(r.NL*r.NLAYER, np.int32),
                             np.zeros(r.NLAYER, np.int32))
        self.assertIsNotNone(result, '三层支路应当能够通过唯一盘外通孔连通')
        return result

    def test_new_through_via_serves_all_three_signal_layers(self):
        tracks, vias, _ = self.route(self.geometry())
        self.assertEqual(vias, [(2.0, 2.0)], '通孔应当复用，不能在同坐标再钻一孔')
        self.assertEqual({track[0] for track in tracks}, {'F.Cu', 'In2.Cu', 'B.Cu'})

    def test_existing_through_via_is_a_zero_new_drill_calibration(self):
        geometry = self.geometry()
        geometry['vias'] = [dict(net='TEST', x=2, y=2, d=.4, drill=.2, uuid='fixed-via')]
        geometry['tracks'] += [dict(net='TEST', layer=layer, w=.15, uuid=layer,
                                   x1=a, y1=2, x2=b, y2=2)
                               for layer, a, b in [('F.Cu', 1, 2), ('B.Cu', 2, 3)]]
        _, vias, _ = self.route(geometry)
        self.assertEqual(vias, [])


if __name__ == '__main__':
    unittest.main()
