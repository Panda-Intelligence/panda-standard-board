"""2026-11-03 Codex：中心采样间的小孔、同名孤岛与走线删减不能伪造参考改善。"""
import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class RearClockCorridorTests(unittest.TestCase):
    def fixture(self, hole=None, disconnected=False):
        import wx
        self.app = wx.GetApp() or wx.App(False)
        import pcbnew as P
        from r25_router.apply_single_r27_layout_eco import mm
        board=P.BOARD();board.SetCopperLayerCount(4)
        ground=P.NETINFO_ITEM(board,'GND',1);board.Add(ground)
        net=P.NETINFO_ITEM(board,'P47_CKV',2);board.Add(net)
        fp=P.FOOTPRINT(board);fp.SetReference('U501')
        pad=P.PAD(fp);pad.SetNumber('57');pad.SetNet(ground)
        pad.SetPosition(P.VECTOR2I(mm(10 if disconnected else 0),mm(0)))
        pad.SetSize(P.VECTOR2I(mm(.2),mm(.2)))
        layers=P.LSET();layers.AddLayer(P.In2_Cu);pad.SetLayerSet(layers);fp.Add(pad);board.Add(fp)
        shape=P.SHAPE_POLY_SET();shape.NewOutline()
        for x,y in [(-1,-1),(3,-1),(3,3),(-1,3)]:shape.Append(mm(x),mm(y))
        if hole:
            h=shape.NewHole(0)
            for x,y in hole:shape.Append(mm(x),mm(y),0,h)
        zone=P.ZONE(board);zone.SetNet(ground);zone.SetLayer(P.In2_Cu)
        zone.SetFilledPolysList(P.In2_Cu,shape);board.Add(zone)
        track=P.PCB_TRACK(board);track.SetNet(net);track.SetLayer(P.B_Cu);track.SetWidth(mm(.15))
        track.SetStart(P.VECTOR2I(mm(.2),mm(1)));track.SetEnd(P.VECTOR2I(mm(1.2),mm(1)));board.Add(track)
        contract=dict(signal_edge_margin_mm=.25,own_via_exclusion_radius_mm=.6,shape_error_um=.5,
                      net_limits={'P47_CKV':dict(track_count=1,required_area_mm2=None,maximum_uncovered_area_mm2=0.000001)})
        return board,contract,track

    def inspect(self, board, contract):
        from r25_router.apply_single_r27_layout_eco import inspect_rear_clock_corridors
        return inspect_rear_clock_corridors(board,contract)

    def test_complete_native_corridor_still_does_not_qualify_electrical_timing(self):
        board,contract,_=self.fixture();report=self.inspect(board,contract)
        self.assertTrue(report['layout_ground_coverage_complete'])
        self.assertFalse(report['electrical_timing_and_return_qualified'])
        self.assertGreater(report['nets'][0]['required_area_mm2'],.9)

    def test_small_hole_between_point_samples_is_rejected(self):
        board,contract,_=self.fixture(hole=[(.54,.97),(.56,.97),(.56,1.03),(.54,1.03)])
        with self.assertRaisesRegex(ValueError,'clock ground corridor'):
            self.inspect(board,contract)

    def test_lateral_gap_is_rejected_even_when_the_center_is_covered(self):
        board,contract,_=self.fixture(hole=[(.54,1.2),(.56,1.2),(.56,1.25),(.54,1.25)])
        with self.assertRaisesRegex(ValueError,'clock ground corridor'):
            self.inspect(board,contract)

    def test_disconnected_same_name_ground_is_rejected(self):
        board,contract,_=self.fixture(disconnected=True)
        with self.assertRaisesRegex(ValueError,'reference ground'):
            self.inspect(board,contract)

    def test_deleted_clock_track_or_changed_required_area_is_rejected(self):
        board,contract,track=self.fixture();row=self.inspect(board,contract)['nets'][0]
        contract['net_limits']['P47_CKV']['required_area_mm2']=row['required_area_mm2']
        track.SetEnd(type(track.GetEnd())(1100000,1000000))
        with self.assertRaisesRegex(ValueError,'required area'):
            self.inspect(board,contract)
        board,contract,track=self.fixture();board.Delete(track)
        with self.assertRaisesRegex(ValueError,'clock track inventory'):
            self.inspect(board,contract)

    def test_reduced_margin_or_enlarged_via_exclusion_is_rejected(self):
        for field,value in [('signal_edge_margin_mm',.1),('own_via_exclusion_radius_mm',.7),('shape_error_um',5)]:
            board,contract,_=self.fixture();contract[field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'clock corridor contract'):
                self.inspect(board,contract)

    def test_partial_coverage_report_remains_explicitly_incomplete(self):
        board,contract,_=self.fixture(hole=[(.54,.97),(.56,.97),(.56,1.03),(.54,1.03)])
        contract['net_limits']['P47_CKV']['maximum_uncovered_area_mm2']=.01
        report=self.inspect(board,contract)
        self.assertFalse(report['layout_ground_coverage_complete'])
        self.assertGreater(report['nets'][0]['uncovered_area_mm2'],.001)
        self.assertFalse(report['electrical_timing_and_return_qualified'])
