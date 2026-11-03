"""2026-11-03 Codex：新In2桥须有连续相邻地覆盖，不能借铜环搭接或同名岛通过。"""
import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('pcbnew'),'KiCad Python required')
class InnerClockBridgeTests(unittest.TestCase):
    def fixture(self,hole=None,disconnected=False):
        import wx
        self.app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        from r25_router.apply_single_r27_layout_eco import mm
        board=P.BOARD();board.SetCopperLayerCount(4)
        ground=P.NETINFO_ITEM(board,'GND',1);net=P.NETINFO_ITEM(board,'P47_XSTL_SRC',2)
        board.Add(ground);board.Add(net)
        fp=P.FOOTPRINT(board);fp.SetReference('U501');pad=P.PAD(fp);pad.SetNumber('57');pad.SetNet(ground)
        pad.SetPosition(P.VECTOR2I(mm(10 if disconnected else 1.5),mm(1)))
        pad.SetSize(P.VECTOR2I(mm(.2),mm(.2)));layers=P.LSET();layers.AddLayer(P.In1_Cu);pad.SetLayerSet(layers);fp.Add(pad);board.Add(fp)
        shape=P.SHAPE_POLY_SET();shape.NewOutline()
        for x,y in [(-1,-1),(4,-1),(4,2),(-1,2)]:shape.Append(mm(x),mm(y))
        if hole:
            h=shape.NewHole(0)
            for x,y in hole:shape.Append(mm(x),mm(y),0,h)
        zone=P.ZONE(board);zone.SetNet(ground);zone.SetLayer(P.In1_Cu);zone.SetFilledPolysList(P.In1_Cu,shape);board.Add(zone)
        segments=[];tracks=[]
        for i in range(6):
            a,b=mm(i*.5),mm((i+1)*.5);t=P.PCB_TRACK(board);t.SetNet(net);t.SetLayer(P.In2_Cu);t.SetWidth(mm(.15))
            t.SetStart(P.VECTOR2I(a,0));t.SetEnd(P.VECTOR2I(b,0));board.Add(t);tracks.append(t);segments.append([a,0,b,0,mm(.15)])
        for x in [0,3]:
            v=P.PCB_VIA(board);v.SetNet(net);v.SetViaType(P.VIATYPE_THROUGH);v.SetLayerPair(P.F_Cu,P.B_Cu)
            v.SetPosition(P.VECTOR2I(mm(x),0));v.SetWidth(mm(.4));v.SetDrill(mm(.2));board.Add(v)
        c=dict(net='P47_XSTL_SRC',signal_edge_margin_mm=.25,own_via_exclusion_radius_mm=.6,shape_error_um=.5,
               via_centers_nm=[[0,0],[mm(3),0]],segments_nm=segments)
        return board,c,tracks

    def inspect(self,board,contract):
        from r25_router.apply_single_r27_layout_eco import inspect_inner_clock_bridge
        return inspect_inner_clock_bridge(board,contract)

    def test_full_continuous_bridge_is_still_not_electrically_qualified(self):
        b,c,_=self.fixture();r=self.inspect(b,c)
        self.assertTrue(r['bridge_ground_coverage_complete'])
        self.assertFalse(r['electrical_timing_and_return_qualified'])
        self.assertGreater(r['required_area_mm2'],.5)

    def test_small_hole_between_center_samples_fails(self):
        b,c,_=self.fixture(hole=[(1.24,-.01),(1.26,-.01),(1.26,.01),(1.24,.01)])
        with self.assertRaisesRegex(ValueError,'ground corridor has a gap'):self.inspect(b,c)

    def test_lateral_plane_gap_fails(self):
        b,c,_=self.fixture(hole=[(1.24,.2),(1.26,.2),(1.26,.25),(1.24,.25)])
        with self.assertRaisesRegex(ValueError,'ground corridor has a gap'):self.inspect(b,c)

    def test_same_name_disconnected_ground_fails(self):
        b,c,_=self.fixture(disconnected=True)
        with self.assertRaisesRegex(ValueError,'reference ground'):self.inspect(b,c)

    def test_shifted_endpoint_cannot_pass_by_overlapping_copper_caps(self):
        import pcbnew as P
        b,c,t=self.fixture();t[0].SetEnd(P.VECTOR2I(500001,0))
        with self.assertRaisesRegex(ValueError,'bridge copper differs'):self.inspect(b,c)

    def test_extra_signal_via_cannot_expand_the_exclusion_mask(self):
        import pcbnew as P
        b,c,_=self.fixture();v=P.PCB_VIA(b);v.SetNet(b.FindNet('P47_XSTL_SRC'));v.SetPosition(P.VECTOR2I(1500000,0));b.Add(v)
        with self.assertRaisesRegex(ValueError,'via inventory differs'):self.inspect(b,c)

    def test_margin_and_via_exclusion_are_fixed(self):
        for key,value in [('signal_edge_margin_mm',.1),('own_via_exclusion_radius_mm',.7)]:
            b,c,_=self.fixture();c[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'bridge contract'):self.inspect(b,c)

    def fixture_with_xle_bridge(self, xle_hole=None):
        import pcbnew as P
        from r25_router.apply_single_r27_layout_eco import mm
        b,c,_=self.fixture(hole=xle_hole)
        xle=P.NETINFO_ITEM(b,'P47_XLE_SRC',3);b.Add(xle)
        xle_segs=[];xle_tracks=[]
        for i in range(3):
            x1,x2=mm(i*.8),mm((i+1)*.8);y=mm(.8)
            t=P.PCB_TRACK(b);t.SetNet(xle);t.SetLayer(P.In2_Cu);t.SetWidth(mm(.15))
            t.SetStart(P.VECTOR2I(x1,y));t.SetEnd(P.VECTOR2I(x2,y));b.Add(t)
            xle_tracks.append(t);xle_segs.append([x1,y,x2,y,mm(.15)])
        for x in [0,2.4]:
            v=P.PCB_VIA(b);v.SetNet(xle);v.SetViaType(P.VIATYPE_THROUGH);v.SetLayerPair(P.F_Cu,P.B_Cu)
            v.SetPosition(P.VECTOR2I(mm(x),mm(.8)));v.SetWidth(mm(.4));v.SetDrill(mm(.2));b.Add(v)
        c['additional_bridges']=[dict(net='P47_XLE_SRC',rear_track_count=0,total_in2_track_count=3,
                                      via_centers_nm=[[0,mm(.8)],[mm(2.4),mm(.8)]],
                                      bridge_segments_nm=xle_segs)]
        return b,c,xle_tracks

    def test_additional_xle_inner_bridge_requires_complete_in1_corridor_and_zero_rear_copper(self):
        b,c,_=self.fixture_with_xle_bridge();r=self.inspect(b,c)
        self.assertEqual(len(r['additional_bridges']),1)
        extra=r['additional_bridges'][0]
        self.assertEqual(extra['net'],'P47_XLE_SRC')
        self.assertEqual(extra['rear_track_count'],0)
        self.assertEqual(extra['via_count'],2)
        self.assertTrue(extra['bridge_ground_coverage_complete'])
        self.assertFalse(extra['electrical_timing_and_return_qualified'])

    def test_additional_bridge_rejects_leftover_rear_copper_or_corridor_gap_or_obsolete_via(self):
        import pcbnew as P
        from r25_router.apply_single_r27_layout_eco import mm
        b,c,xle_tracks=self.fixture_with_xle_bridge()
        rear=P.PCB_TRACK(b);rear.SetNet(b.FindNet('P47_XLE_SRC'));rear.SetLayer(P.B_Cu);rear.SetWidth(mm(.15))
        rear.SetStart(P.VECTOR2I(0,mm(.8)));rear.SetEnd(P.VECTOR2I(mm(.5),mm(.8)));b.Add(rear)
        with self.assertRaisesRegex(ValueError,'rear copper differs'):self.inspect(b,c)
        b,c,xle_tracks=self.fixture_with_xle_bridge()
        xle_tracks[0].SetEnd(P.VECTOR2I(mm(.8)+1,mm(.8)))
        with self.assertRaisesRegex(ValueError,'bridge copper differs'):self.inspect(b,c)
        b,c,_=self.fixture_with_xle_bridge()
        extra_via=P.PCB_VIA(b);extra_via.SetNet(b.FindNet('P47_XLE_SRC'));extra_via.SetPosition(P.VECTOR2I(mm(1.2),mm(.8)));b.Add(extra_via)
        with self.assertRaisesRegex(ValueError,'via inventory differs'):self.inspect(b,c)
        b,c,_=self.fixture_with_xle_bridge(xle_hole=[(1.18,.78),(1.22,.78),(1.22,.82),(1.18,.82)])
        with self.assertRaisesRegex(ValueError,'ground corridor has a gap'):self.inspect(b,c)

    def test_additional_xstl_and_ckv_inner_bridges_lock_rear_and_in2_inventories(self):
        import pcbnew as P
        from r25_router.apply_single_r27_layout_eco import mm
        b,c,_=self.fixture_with_xle_bridge()
        xstl=P.NETINFO_ITEM(b,'P47_XSTL',4);ckv=P.NETINFO_ITEM(b,'P47_CKV',5)
        b.Add(xstl);b.Add(ckv)
        xstl_segs=[]
        for i in range(2):
            x1,x2=mm(i*.8),mm((i+1)*.8);y=mm(1.2)
            t=P.PCB_TRACK(b);t.SetNet(xstl);t.SetLayer(P.In2_Cu);t.SetWidth(mm(.15))
            t.SetStart(P.VECTOR2I(x1,y));t.SetEnd(P.VECTOR2I(x2,y));b.Add(t)
            xstl_segs.append([x1,y,x2,y,mm(.15)])
        for x in [0,1.6]:
            v=P.PCB_VIA(b);v.SetNet(xstl);v.SetViaType(P.VIATYPE_THROUGH);v.SetLayerPair(P.F_Cu,P.B_Cu)
            v.SetPosition(P.VECTOR2I(mm(x),mm(1.2)));v.SetWidth(mm(.4));v.SetDrill(mm(.2));b.Add(v)
        ckv_segs=[]
        for i in range(2):
            x1,x2=mm(i*.8),mm((i+1)*.8);y=mm(-.4)
            t=P.PCB_TRACK(b);t.SetNet(ckv);t.SetLayer(P.In2_Cu);t.SetWidth(mm(.15))
            t.SetStart(P.VECTOR2I(x1,y));t.SetEnd(P.VECTOR2I(x2,y));b.Add(t)
            ckv_segs.append([x1,y,x2,y,mm(.15)])
        rear=P.PCB_TRACK(b);rear.SetNet(ckv);rear.SetLayer(P.B_Cu);rear.SetWidth(mm(.15))
        rear.SetStart(P.VECTOR2I(mm(1.6),mm(-.4)));rear.SetEnd(P.VECTOR2I(mm(2.4),mm(-.4)));b.Add(rear)
        for x in [0,1.6]:
            v=P.PCB_VIA(b);v.SetNet(ckv);v.SetViaType(P.VIATYPE_THROUGH);v.SetLayerPair(P.F_Cu,P.B_Cu)
            v.SetPosition(P.VECTOR2I(mm(x),mm(-.4)));v.SetWidth(mm(.4));v.SetDrill(mm(.2));b.Add(v)
        c['additional_bridges'].extend([
            dict(net='P47_XSTL',rear_track_count=0,total_in2_track_count=2,
                 via_centers_nm=[[0,mm(1.2)],[mm(1.6),mm(1.2)]],bridge_segments_nm=xstl_segs),
            dict(net='P47_CKV',rear_track_count=1,total_in2_track_count=2,
                 via_centers_nm=[[0,mm(-.4)],[mm(1.6),mm(-.4)]],bridge_segments_nm=ckv_segs),
        ])
        r=self.inspect(b,c)
        self.assertEqual([e['net'] for e in r['additional_bridges']],['P47_XLE_SRC','P47_XSTL','P47_CKV'])
        self.assertEqual([e['rear_track_count'] for e in r['additional_bridges']],[0,0,1])
        self.assertTrue(all(e['bridge_ground_coverage_complete'] for e in r['additional_bridges']))
        self.assertTrue(all(not e['electrical_timing_and_return_qualified'] for e in r['additional_bridges']))

    def test_additional_bridge_rejects_unknown_net_name(self):
        b,c,_=self.fixture_with_xle_bridge()
        c['additional_bridges'][0]['net']='P47_D0'
        with self.assertRaisesRegex(ValueError,'bridge contract'):self.inspect(b,c)
