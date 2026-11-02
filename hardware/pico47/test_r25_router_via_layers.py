"""2026-10-31 Codex：通孔必须避开未参与信号布线的实际铜层。"""
import importlib.util
from pathlib import Path
import types
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name('r25_router')/'router2.py'
GEOMETRY_READY = all(importlib.util.find_spec(n) for n in ['numpy','scipy','shapely','PIL'])


@unittest.skipUnless(GEOMETRY_READY, 'Router geometry environment required')
class ViaLayerObstacleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy
        import scipy.ndimage
        import shapely.geometry
        from PIL import Image, ImageDraw
        spec = importlib.util.spec_from_file_location('pico47_raster_test', SOURCE)
        module = importlib.util.module_from_spec(spec)
        # 本组只测试真实几何栅格；未调用的原生搜索入口无需加载编译库。
        search = types.SimpleNamespace(astar=types.SimpleNamespace(),astar_w=types.SimpleNamespace())
        with mock.patch('ctypes.CDLL',return_value=search):
            spec.loader.exec_module(module)
        cls.R = module

    def setUp(self):
        from shapely.geometry import box
        r = self.R
        r.X0 = r.Y0 = 0
        r.X1 = r.Y1 = 2
        r.PITCH = .025
        r.NX = r.NY = 81
        r.LAYERS[:] = ['F.Cu','B.Cu']
        r.NL = 2
        r.NLAYER = r.NX*r.NY
        r.REGION = box(-1,-1,3,3)
        r.SPOKE_BOX = None
        r.irange.__defaults__ = (0,)

    def geometry(self):
        return dict(pads=[],tracks=[],vias=[],zones=[],outline=[[[0,0],[2,0],[2,2],[0,2]]])

    def test_excluded_layer_power_track_blocks_through_via(self):
        for layer in ['In1.Cu','In2.Cu']:
            with self.subTest(layer=layer):
                g = self.geometry()
                g['tracks'] = [dict(net='POWER',layer=layer,x1=.5,y1=1,x2=1.5,y2=1,w=.15)]
                tracks,vias = self.R.build_static(g,set(),set())
                self.assertFalse(tracks[:,40,40].any())
                self.assertTrue(vias[40,40])
                self.assertFalse(vias[20,40])

    def test_excluded_layer_pad_copper_blocks_through_via(self):
        g = self.geometry()
        g['pads'] = [dict(net='POWER',x=1,y=1,drill=None,
                          polys={'In2.Cu':[[[.9,.9],[1.1,.9],[1.1,1.1],[.9,1.1]]]})]
        tracks,vias = self.R.build_static(g,set(),set())
        self.assertFalse(tracks[:,40,40].any())
        self.assertTrue(vias[40,40])

    def test_fillable_ground_zone_can_create_via_antipad(self):
        g = self.geometry()
        g['zones'] = [dict(net='GND',rule=False,layers=['In1.Cu'],outline=g['outline'])]
        tracks,vias = self.R.build_static(g,set(),set())
        self.assertFalse(tracks[:,40,40].any())
        self.assertFalse(vias[40,40])

    def test_rule_area_hole_preserves_available_route_space(self):
        g = self.geometry()
        g['zones'] = [dict(net='',rule=True,layers=['B.Cu'],no_tracks=True,no_vias=False,
            outline=[[[.5,.5],[1.5,.5],[1.5,1.5],[.5,1.5]]],
            holes=[[[.8,.8],[1.2,.8],[1.2,1.2],[.8,1.2]]])]
        tracks,vias = self.R.build_static(g,set(),set())
        self.assertFalse(tracks[0,40,40])
        self.assertFalse(tracks[1,40,40])
        self.assertTrue(tracks[1,40,26])
        self.assertFalse(vias[40,40])

    def test_excluded_layer_track_is_not_a_search_terminal(self):
        r=self.R
        src=dict(net='POWER',layer='In2.Cu',x1=.5,y1=1,x2=1.5,y2=1,w=.15)
        item=r.Item('track',src,{'In2.Cu':r.seg_geom(.5,1,1.5,1,.075)})
        self.assertEqual(r.terminal_nodes([item]),{})

    def test_new_via_respects_actual_pad_edge_after_inside_export(self):
        r=self.R
        r.PITCH=.002
        r.NX=r.NY=1001
        r.NLAYER=r.NX*r.NY
        g=self.geometry()
        # 实际盘右边缘0.603；ERROR_INSIDE导出到0.601，两个孔位分别只有49/51um盘外间隙。
        g['pads']=[dict(ref='A',num='1',net='TEST',x=.5,y=1,drill=None,uuid='A',
            polys={'F.Cu':[[[.399,.899],[.601,.899],[.601,1.101],[.399,1.101]]]})]
        context=r.prepare(g,dict(nets={'TEST':[]},target_nets=[]))
        self.assertLess(.852-.2-.603,.05)
        self.assertGreater(.854-.2-.603,.05)
        self.assertIn(r.cell(.852,1),context.ownV['TEST'], '实际49um间隙的新孔必须阻挡')
        self.assertNotIn(r.cell(.854,1),context.ownV['TEST'], '实际51um间隙的新孔应保持可用')

    def test_new_via_respects_rounded_pad_corner_distance(self):
        from shapely.geometry import Point, Polygon
        r=self.R
        g=self.geometry()
        # 原生R727.1圆角轮廓平移至局部夹具；低分段buffer曾在此放过不足50um的孔。
        outline=[[1.03,.635],[1.0254,.669941],[1.005586,.712433],
                 [.972433,.745586],[.929941,.7654],[.895,.77],[.625,.77],
                 [.590059,.7654],[.547567,.745586],[.514414,.712433],
                 [.4946,.669941],[.49,.635],[.49,.265],[.4946,.230059],
                 [.514414,.187567],[.547567,.154414],[.590059,.1346],
                 [.625,.13],[.895,.13],[.929941,.1346],[.972433,.154414],
                 [1.005586,.187567],[1.0254,.230059],[1.03,.265]]
        g['pads']=[dict(ref='R',num='1',net='TEST',x=.76,y=.45,drill=None,
                        uuid='rounded-pad',polys={'F.Cu':[outline]})]
        context=r.prepare(g,dict(nets={'TEST':[]},target_nets=[]))
        distance=Polygon(outline).distance(Point(.5,1))
        self.assertLess(distance-r.VIA_D/2-r.PAD_EPS,.05)
        self.assertIn(r.cell(.5,1),context.ownV['TEST'],
                      '圆角近似不能缩小实际盘外孔间隙')
        self.assertGreater(Polygon(outline).distance(Point(.5,1.025))-r.VIA_D/2-r.PAD_EPS,.05)
        self.assertNotIn(r.cell(.5,1.025),context.ownV['TEST'])


if __name__=='__main__':
    unittest.main()
