"""2026-11-02 Codex：单板几何回放、实际参考地与路径模型回归。"""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from r25_router.apply_single_r27_layout_eco import (
    mm, apply_layout_eco, apply_library_edits, copper_fingerprint,
    reference_connected_ground_fills,
    inspect_panel_clock_references,
    inspect_clock_ground_stitches,
)


class LayoutReplayTests(unittest.TestCase):
    def test_reviewed_pad_additions_cannot_hide_old_pad_loss_or_group_splits(self):
        from prune_pico47_stubs import preserves_groups,preserves_groups_with_additions
        before=[frozenset({'a','b'}),frozenset({'c'})]
        after=[frozenset({'a','b','d'}),frozenset({'c'})]
        self.assertFalse(preserves_groups(before,after),'原严格守卫仍拒绝库存改变')
        self.assertTrue(preserves_groups_with_additions(before,after,{'d'}))
        for wrong in [[frozenset({'a','d'}),frozenset({'c'})],
                      [frozenset({'a','b','d','e'}),frozenset({'c'})],
                      [frozenset({'a','d'}),frozenset({'b','c'})]]:
            self.assertFalse(preserves_groups_with_additions(before,wrong,{'d'}))
        self.assertFalse(preserves_groups_with_additions(before,after,{'b','d'}))

    def test_new_local_CAD_file_never_overwrites_an_existing_file(self):
        text='(footprint "newcap")\n'
        delta=dict(created_files=[dict(path='Panda47.pretty/newcap.kicad_mod',content=text,
                                      sha256=hashlib.sha256(text.encode()).hexdigest())])
        with tempfile.TemporaryDirectory() as folder:
            apply_library_edits(folder,delta)
            path=Path(folder)/'Panda47.pretty/newcap.kicad_mod'
            self.assertEqual(path.read_text(),text)
            with self.assertRaisesRegex(ValueError,'already exists'):
                apply_library_edits(folder,delta)
            self.assertEqual(path.read_text(),text)

    def test_new_local_CAD_file_requires_its_bound_content(self):
        delta=dict(created_files=[dict(path='new.kicad_mod',content='changed',sha256='0'*64)])
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'content differs'):
                apply_library_edits(folder,delta)
            self.assertFalse((Path(folder)/'new.kicad_mod').exists())

    @unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
    def test_missing_added_library_is_rejected_before_existing_parts_move(self):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD();board.SetCopperLayerCount(4)
        old=P.FOOTPRINT(board);old.SetReference('OLD');board.Add(old)
        delta=dict(removed_uuids=[],updated_copper=[],added_tracks=[],added_vias=[],added_zones=[],
                   footprint_poses={'OLD':dict(before_xy_nm=[0,0],x=1,y=2,rot=0,side='F.Cu')},
                   added_footprints=[dict(ref='NEW',library_path='absent.kicad_mod',library_sha256='0'*64)])
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'library differs'):
                apply_layout_eco(board,delta,folder)
        self.assertEqual(old.GetPosition(),P.VECTOR2I(0,0))
        self.assertEqual(len(list(board.GetFootprints())),1)

    def test_json_roundoff_cannot_shrink_minimum_via_or_drill(self):
        self.assertEqual(mm(.39999999999999997),400000)
        self.assertEqual(mm(.19999999999999998),200000)
        self.assertEqual(mm(17.399999999999999),17400000)

    def test_local_marker_replay_preserves_uuid_and_rejects_wrong_predecessor(self):
        before='(fp_poly (pts (xy 0 0) (xy 1 0) (xy 0 1)) (uuid "original"))\n'
        after=before.replace('(xy 0 1)', '(xy 0 1.2)')
        digest=lambda text:hashlib.sha256(text.encode()).hexdigest()
        delta=dict(library_edits=[dict(path='Panda47.pretty/test.kicad_mod',
            before_sha256=digest(before),after_sha256=digest(after),
            replacements=[dict(before='(xy 0 1)',after='(xy 0 1.2)')])])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'Panda47.pretty/test.kicad_mod'
            path.parent.mkdir();path.write_text(before)
            apply_library_edits(folder,delta)
            self.assertEqual(path.read_text(),after)
            self.assertIn('(uuid "original")',path.read_text())
            with self.assertRaisesRegex(ValueError,'predecessor'):
                apply_library_edits(folder,delta)
            self.assertEqual(path.read_text(),after)

    @unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
    def test_zone_hole_priority_and_via_keepout_survive_native_roundtrip(self):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD();board.SetCopperLayerCount(4)
        zone=dict(name='REFERENCE_CLEAR',net='',rule=True,layers=['In2.Cu'],
                  no_tracks=True,no_vias=True,priority=4,
                  outline=[[[0,0],[4,0],[4,4],[0,4]]],
                  holes=[[[1,1],[2,1],[2,2],[1,2]]])
        delta=dict(footprint_poses={},removed_uuids=[],updated_copper=[],
                   added_tracks=[],added_vias=[],added_zones=[zone])
        keep=apply_layout_eco(board,delta)
        native=next(iter(board.Zones()))
        self.assertTrue(native.GetDoNotAllowTracks())
        self.assertTrue(native.GetDoNotAllowVias())
        self.assertEqual(native.GetAssignedPriority(),4)
        self.assertEqual(native.Outline().HoleCount(0),1)
        fingerprint=copper_fingerprint(board,True)
        native.SetAssignedPriority(3)
        self.assertNotEqual(copper_fingerprint(board,True),fingerprint)
        native.SetAssignedPriority(4)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.kicad_pcb';P.SaveBoard(str(path),board)
            self.assertEqual(copper_fingerprint(P.LoadBoard(str(path)),True),fingerprint)

    @unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
    def test_reference_uses_touching_fills_and_rejects_same_net_islands_and_holes(self):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD();board.SetCopperLayerCount(4)
        net=P.NETINFO_ITEM(board,'GND',1);board.Add(net)
        fp=P.FOOTPRINT(board);fp.SetReference('U501')
        pad=P.PAD(fp);pad.SetNumber('57');pad.SetSize(P.VECTOR2I(mm(.3),mm(.3)))
        pad.SetPosition(P.VECTOR2I(mm(.5),mm(.5)));pad.SetNet(net)
        layers=P.LSET();layers.AddLayer(P.In2_Cu);pad.SetLayerSet(layers)
        fp.Add(pad);board.Add(fp)
        for index,(x0,x1) in enumerate([(0,2),(1.9,4),(6,8)]):
            native=P.SHAPE_POLY_SET();native.NewOutline()
            for x,y in [(x0,0),(x1,0),(x1,2),(x0,2)]:native.Append(mm(x),mm(y))
            if index==0:
                hole=native.NewHole(0)
                for x,y in [(1,1),(1.2,1),(1.2,1.2),(1,1.2)]:native.Append(mm(x),mm(y),0,hole)
            zone=P.ZONE(board);zone.SetNet(net);zone.SetLayer(P.In2_Cu)
            zone.SetFilledPolysList(P.In2_Cu,native);board.Add(zone)
        fills=reference_connected_ground_fills(board)
        inside=lambda x,y:any(layer==P.In2_Cu and shape.Contains(P.VECTOR2I(mm(x),mm(y)))
                              for layer,shape in fills)
        self.assertEqual(len(fills),2)
        self.assertTrue(inside(3,1),'相接的第二个地铜区必须计入参考')
        self.assertFalse(inside(7,1),'同网孤岛不得当参考')
        self.assertFalse(inside(1.1,1.1),'铜区孔洞不得当参考')
        pad.SetPosition(P.VECTOR2I(mm(20),mm(20)))
        with self.assertRaisesRegex(ValueError,'No filled copper'):
            reference_connected_ground_fills(board)

    @unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
    def test_retained_uuid_receives_geometry_update(self):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD()
        board.SetCopperLayerCount(4)
        net=P.NETINFO_ITEM(board,'TEST',1)
        board.Add(net)
        track=P.PCB_TRACK(board)
        track.SetStart(P.VECTOR2I(mm(1),mm(1)))
        track.SetEnd(P.VECTOR2I(mm(2),mm(1)))
        track.SetWidth(mm(.15))
        track.SetNet(net)
        board.Add(track)
        uid=track.m_Uuid.AsString()
        before=copper_fingerprint(board)
        delta=dict(footprint_poses={},removed_uuids=[],added_tracks=[],added_vias=[],added_zones=[],
                   updated_copper=[dict(uuid=uid,net='TEST',layer='B.Cu',x1=1,y1=1,x2=3,y2=2,w=.5)])
        keep=apply_layout_eco(board,delta)
        self.assertEqual(track.m_Uuid.AsString(),uid)
        self.assertEqual(track.GetEnd(),P.VECTOR2I(mm(3),mm(2)))
        self.assertEqual(track.GetWidth(),mm(.5))
        self.assertEqual(track.GetLayer(),P.B_Cu)
        self.assertEqual(len(keep),1)
        self.assertNotEqual(copper_fingerprint(board),before)

    @unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
    def test_missing_original_copper_is_rejected_before_mutation(self):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD()
        board.SetCopperLayerCount(4)
        delta=dict(footprint_poses={},removed_uuids=['absent'],updated_copper=[],added_tracks=[],added_vias=[],added_zones=[])
        with self.assertRaisesRegex(ValueError,'original copper UUID'):
            apply_layout_eco(board,delta)

    @unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
    def test_added_copper_replays_with_native_const_uuid_api(self):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD()
        board.SetCopperLayerCount(4)
        net=P.NETINFO_ITEM(board,'TEST',1)
        board.Add(net)
        delta=dict(footprint_poses={},removed_uuids=[],updated_copper=[],added_zones=[],
                   baseline_copper_fingerprint=copper_fingerprint(board),
                   added_tracks=[dict(uuid='3363152a-428a-468c-a847-1eb61b6a8387',net='TEST',
                                      layer='F.Cu',x1=1,y1=1,x2=2,y2=1,w=.15)],
                   added_vias=[dict(uuid='2d647504-8373-433b-86ca-bc486a921157',net='TEST',
                                   x=2,y=1,d=.39999999999999997,drill=.19999999999999998)])
        keep=apply_layout_eco(board,delta)
        self.assertEqual(len(list(board.GetTracks())),2)
        via=next(t for t in board.GetTracks() if t.GetClass()=='PCB_VIA')
        self.assertEqual(via.GetWidth(P.F_Cu),400000)
        self.assertEqual(via.GetDrill(),200000)
        with self.assertRaisesRegex(ValueError,'baseline copper'):
            apply_layout_eco(board,delta)


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class BacksideAdditionTests(unittest.TestCase):
    def library(self,folder,side):
        text='''(footprint "BACKCAP" (version 20260206) (generator "pcbnew") (layer "F.Cu")
          (uuid "11111111-1111-4111-8111-111111111111")
          (property "Reference" "NEW" (at 0 -1 0) (layer "F.Fab") (effects (font (size 1 1))))
          (property "Value" "1u" (at 0 1 0) (layer "F.Fab") (effects (font (size 1 1)))) (attr smd)
          (pad "1" smd rect (at -.5 0) (size .5 .5) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "22222222-2222-4222-8222-222222222222"))
          (pad "2" smd rect (at .5 0) (size .5 .5) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "33333333-3333-4333-8333-333333333333")))'''
        lib=Path(folder)/'Panda47.pretty';lib.mkdir();path=lib/'BACKCAP.kicad_mod';path.write_text(text)
        return dict(removed_uuids=[],updated_copper=[],added_tracks=[],added_vias=[],added_zones=[],footprint_poses={},
                    added_footprints=[dict(ref='NEW',library_path='Panda47.pretty/BACKCAP.kicad_mod',library_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),value='1u',side=side,properties={},pins={'1':'POWER','2':'GND'},fpid='Panda47:BACKCAP',x=2,y=3,rot=90,schematic_path='/44444444-4444-4444-8444-444444444444/55555555-5555-4555-8555-555555555555',preserve_uuid=True,native_uuid='11111111-1111-4111-8111-111111111111',pad_uuids={'1':'22222222-2222-4222-8222-222222222222','2':'33333333-3333-4333-8333-333333333333'})])

    def board(self):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD();board.SetCopperLayerCount(4)
        for i,name in enumerate(['POWER','GND'],1):board.Add(P.NETINFO_ITEM(board,name,i))
        return board

    def test_backside_addition_preserves_pin_nets_UUIDs_and_native_roundtrip(self):
        import pcbnew as P
        with tempfile.TemporaryDirectory() as folder:
            delta=self.library(folder,'B.Cu');board=self.board();keep=apply_layout_eco(board,delta,folder)
            path=Path(folder)/'back.kicad_pcb';P.SaveBoard(str(path),board);reloaded=P.LoadBoard(str(path))
            for native in [board,reloaded]:
                fp=native.FindFootprintByReference('NEW');self.assertEqual(fp.GetLayer(),P.B_Cu)
                self.assertEqual(fp.m_Uuid.AsString(),delta['added_footprints'][0]['native_uuid'])
                pads={p.GetNumber():p for p in fp.Pads()}
                self.assertEqual(pads['1'].GetPosition(),P.VECTOR2I(mm(2),mm(3.5)))
                self.assertEqual(pads['2'].GetPosition(),P.VECTOR2I(mm(2),mm(2.5)))
                self.assertEqual({n:p.GetNetname() for n,p in pads.items()},{'1':'POWER','2':'GND'})
                self.assertEqual({n:p.m_Uuid.AsString() for n,p in pads.items()},delta['added_footprints'][0]['pad_uuids'])
                self.assertTrue(all(p.IsOnLayer(P.B_Cu) and not p.IsOnLayer(P.F_Cu) for p in pads.values()))

    def test_internal_face_is_rejected_before_addition(self):
        with tempfile.TemporaryDirectory() as folder:
            delta=self.library(folder,'In1.Cu');board=self.board()
            with self.assertRaisesRegex(ValueError,'face|front'):
                apply_layout_eco(board,delta,folder)
            self.assertFalse(list(board.GetFootprints()))


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class OutputBypassTests(unittest.TestCase):
    def fixture(self,distance=1,ground_connected=True,cap_present=True):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD();board.SetCopperLayerCount(4)
        nets={}
        for i,name in enumerate(['OUT','GND','IN'],1):
            net=P.NETINFO_ITEM(board,name,i);board.Add(net);nets[name]=net
        def part(ref,rows):
            fp=P.FOOTPRINT(board);fp.SetReference(ref);fp.SetAttributes(P.FP_SMD);fp.SetValue('1u')
            for number,net,x,y in rows:
                p=P.PAD(fp);p.SetNumber(number);p.SetNet(nets[net]);p.SetAttribute(P.PAD_ATTRIB_SMD)
                p.SetSize(P.VECTOR2I(mm(.15),mm(.15)));p.SetPosition(P.VECTOR2I(mm(x),mm(y)))
                ls=P.LSET();ls.AddLayer(P.F_Cu);p.SetLayerSet(ls);fp.Add(p)
            board.Add(fp);return fp
        part('SW',[('A1','OUT',0,0),('B1','GND',.5,0)])
        if cap_present:
            part('COUT',[('1','OUT',0,distance),('2','GND',.5,distance)])
            for net,x in [('OUT',0),('GND',.5)]:
                if net=='GND' and not ground_connected:continue
                t=P.PCB_TRACK(board);t.SetNet(nets[net]);t.SetLayer(P.F_Cu);t.SetWidth(mm(.1))
                t.SetStart(P.VECTOR2I(mm(x),0));t.SetEnd(P.VECTOR2I(mm(x),mm(distance)));board.Add(t)
        contract=dict(switch='SW',cap='COUT',value='1u',output_pin='A1',ground_pin='B1',
                      output_net='OUT',maximum_pad_distance_mm=2.5)
        return board,contract

    def test_output_bypass_requires_actual_connections_and_keeps_dynamic_qualification_false(self):
        from build_pico47_single import inspect_output_bypass
        board,contract=self.fixture();report=inspect_output_bypass(board,contract)
        self.assertTrue(report['both_native_connections'])
        self.assertFalse(report['transient_and_DC_bias_qualified'])

    def test_missing_output_cap_is_rejected(self):
        from build_pico47_single import inspect_output_bypass
        board,contract=self.fixture(cap_present=False)
        with self.assertRaisesRegex(ValueError,'Missing load-switch output bypass'):
            inspect_output_bypass(board,contract)

    def test_same_net_label_without_a_ground_return_is_rejected(self):
        from build_pico47_single import inspect_output_bypass
        board,contract=self.fixture(ground_connected=False)
        with self.assertRaisesRegex(ValueError,'actual copper connection'):
            inspect_output_bypass(board,contract)

    def test_input_rail_cap_cannot_substitute_for_output_cap(self):
        from build_pico47_single import inspect_output_bypass
        board,contract=self.fixture()
        cap=board.FindFootprintByReference('COUT')
        next(p for p in cap.Pads() if p.GetNumber()=='1').SetNet(board.FindNet('IN'))
        with self.assertRaisesRegex(ValueError,'pin net differs'):
            inspect_output_bypass(board,contract)

    def test_remote_cap_does_not_meet_the_reviewed_local_placement(self):
        from build_pico47_single import inspect_output_bypass
        board,contract=self.fixture(distance=10)
        with self.assertRaisesRegex(ValueError,'local placement'):
            inspect_output_bypass(board,contract)

    def test_new_SMD_cap_cannot_cover_an_existing_same_net_via(self):
        import pcbnew as P
        from build_pico47_single import inspect_output_bypass
        board,contract=self.fixture();via=P.PCB_VIA(board);via.SetNet(board.FindNet('GND'))
        via.SetViaType(P.VIATYPE_THROUGH);via.SetLayerPair(P.F_Cu,P.B_Cu);via.SetWidth(mm(.4));via.SetDrill(mm(.2))
        via.SetPosition(P.VECTOR2I(mm(.5),mm(1)));board.Add(via)
        with self.assertRaisesRegex(ValueError,'pad-edge separation'):
            inspect_output_bypass(board,contract)


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class InputBypassTests(unittest.TestCase):
    def fixture(self,**kwargs):
        board,old = OutputBypassTests.fixture(self,**kwargs)
        switch = board.FindFootprintByReference('SW')
        pin = next(p for p in switch.Pads() if p.GetNumber()=='A1')
        pin.SetNumber('A2');pin.SetNet(board.FindNet('IN'))
        cap = board.FindFootprintByReference('COUT')
        if cap:
            cap.SetReference('CIN')
            next(p for p in cap.Pads() if p.GetNumber()=='1').SetNet(board.FindNet('IN'))
        for track in board.GetTracks():
            if track.GetNetname()=='OUT':track.SetNet(board.FindNet('IN'))
        contract=dict(switch='SW',cap='CIN',value='1u',input_pin='A2',ground_pin='B1',
                      input_net='IN',maximum_pad_distance_mm=2.5,new_component=True)
        return board,contract

    def test_input_bypass_checks_actual_connections_without_claiming_transients(self):
        from build_pico47_single import inspect_input_bypass
        board,contract=self.fixture();report=inspect_input_bypass(board,contract)
        self.assertEqual(report['input_net'],'IN')
        self.assertEqual(report['input_pad_distance_mm'],1)
        self.assertTrue(report['both_native_connections'])
        self.assertFalse(report['transient_and_DC_bias_qualified'])

    def test_output_rail_and_100n_cap_cannot_substitute_for_1u_input_cap(self):
        from build_pico47_single import inspect_input_bypass
        for wrong in ['rail','value']:
            with self.subTest(wrong=wrong):
                board,contract=self.fixture();cap=board.FindFootprintByReference('CIN')
                if wrong=='rail':
                    next(p for p in cap.Pads() if p.GetNumber()=='1').SetNet(board.FindNet('OUT'))
                else:cap.SetValue('100n')
                with self.assertRaisesRegex(ValueError,'pin net differs|value or assembly'):
                    inspect_input_bypass(board,contract)

    def test_input_bypass_rejects_missing_cap_or_missing_ground_copper(self):
        from build_pico47_single import inspect_input_bypass
        for args in [dict(cap_present=False),dict(ground_connected=False)]:
            with self.subTest(args=args):
                board,contract=self.fixture(**args)
                with self.assertRaisesRegex(ValueError,'Missing load-switch input|actual copper connection'):
                    inspect_input_bypass(board,contract)

    def test_remote_input_cap_does_not_meet_local_placement(self):
        from build_pico47_single import inspect_input_bypass
        board,contract=self.fixture(distance=29)
        with self.assertRaisesRegex(ValueError,'local placement'):
            inspect_input_bypass(board,contract)

    def test_new_input_cap_keeps_extra_via_margin_without_retroactively_moving_old_cap(self):
        import pcbnew as P
        from build_pico47_single import inspect_input_bypass
        board,contract=self.fixture();via=P.PCB_VIA(board);via.SetNet(board.FindNet('IN'))
        via.SetViaType(P.VIATYPE_THROUGH);via.SetLayerPair(P.F_Cu,P.B_Cu);via.SetWidth(mm(.4));via.SetDrill(mm(.2))
        via.SetPosition(P.VECTOR2I(mm(-.3),mm(1)));board.Add(via)
        with self.assertRaisesRegex(ValueError,'pad-edge separation'):
            inspect_input_bypass(board,contract)
        contract['new_component']=False
        self.assertTrue(inspect_input_bypass(board,contract)['both_native_connections'])
        del contract['new_component']
        with self.assertRaisesRegex(ValueError,'placement policy'):
            inspect_input_bypass(board,contract)


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class PowerBypassTests(unittest.TestCase):
    def fixture(self,side='F.Cu',**kwargs):
        board,old=OutputBypassTests.fixture(self,**kwargs)
        cap=board.FindFootprintByReference('COUT')
        if cap and side=='B.Cu':
            import pcbnew as P
            cap.Flip(cap.GetPosition(),False)
            for p in cap.Pads():
                xy=p.GetPosition();xy.x=mm(0 if p.GetNumber()=='1' else .5);p.SetPosition(xy)
            for track in board.GetTracks():track.SetLayer(P.B_Cu)
            # 两颗真实通孔把正面IC脚与背面局部旁路接通。
            for net,x in [('OUT',0),('GND',.5)]:
                via=P.PCB_VIA(board);via.SetNet(board.FindNet(net));via.SetViaType(P.VIATYPE_THROUGH)
                via.SetLayerPair(P.F_Cu,P.B_Cu);via.SetWidth(mm(.2));via.SetDrill(mm(.1))
                via.SetPosition(P.VECTOR2I(mm(x),0));board.Add(via)
        contract=dict(device='SW',cap='COUT',value='1u',power_pin='A1',ground_pin='B1',
                      power_net='OUT',maximum_pad_distance_mm=2.5,new_component=True,side=side)
        return board,contract

    def test_front_and_back_power_caps_have_real_connections_without_physical_claims(self):
        from build_pico47_single import inspect_power_bypass
        for side in ['F.Cu','B.Cu']:
            with self.subTest(side=side):
                board,contract=self.fixture(side);r=inspect_power_bypass(board,contract)
                self.assertEqual(r['device'],'SW');self.assertEqual(r['side'],side)
                self.assertTrue(r['both_native_connections'])
                self.assertFalse(r['transient_and_DC_bias_qualified'])
                self.assertFalse(r['backside_height_and_assembly_qualified'])

    def test_back_cap_cannot_pass_a_front_declaration_or_an_internal_face(self):
        from build_pico47_single import inspect_power_bypass
        board,contract=self.fixture('B.Cu')
        for face in ['F.Cu','In1.Cu']:
            contract['side']=face
            with self.assertRaisesRegex(ValueError,'assembly differs|outer assembly face'):
                inspect_power_bypass(board,contract)

    def test_wrong_rail_or_small_cap_cannot_replace_bulk_SPI_bypass(self):
        from build_pico47_single import inspect_power_bypass
        for wrong in ['rail','value']:
            board,contract=self.fixture();cap=board.FindFootprintByReference('COUT')
            if wrong=='rail':next(p for p in cap.Pads() if p.GetNumber()=='1').SetNet(board.FindNet('IN'))
            else:cap.SetValue('100n')
            with self.assertRaisesRegex(ValueError,'pin net differs|value or assembly'):
                inspect_power_bypass(board,contract)

    def test_missing_return_and_remote_cap_are_rejected(self):
        from build_pico47_single import inspect_power_bypass
        for args in [dict(ground_connected=False),dict(distance=12)]:
            board,contract=self.fixture(**args)
            with self.assertRaisesRegex(ValueError,'actual copper connection|local placement'):
                inspect_power_bypass(board,contract)

    def test_backside_cap_checks_same_net_via_margin_on_its_actual_face(self):
        import pcbnew as P
        from build_pico47_single import inspect_power_bypass
        board,contract=self.fixture('B.Cu');cap=board.FindFootprintByReference('COUT')
        via=P.PCB_VIA(board);via.SetNet(board.FindNet('OUT'));via.SetViaType(P.VIATYPE_THROUGH)
        via.SetLayerPair(P.F_Cu,P.B_Cu);via.SetWidth(mm(.4));via.SetDrill(mm(.2))
        via.SetPosition(next(p for p in cap.Pads() if p.GetNumber()=='1').GetPosition());board.Add(via)
        with self.assertRaisesRegex(ValueError,'pad-edge separation'):
            inspect_power_bypass(board,contract)


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class ReferenceFilterTests(unittest.TestCase):
    def fixture(self,**kwargs):
        board,contract=PowerBypassTests.fixture(self,**kwargs)
        contract.update(value='100n',maximum_nominal_capacitance_uf=.1)
        board.FindFootprintByReference('COUT').SetValue('100n')
        return board,contract

    def add_parallel(self,board,dnp=False):
        import pcbnew as P
        fp=P.FOOTPRINT(board);fp.SetReference('CEXTRA');fp.SetAttributes(P.FP_SMD)
        fp.SetValue('100n');fp.SetDNP(dnp)
        for number,net in [('1','OUT'),('2','GND')]:
            pad=P.PAD(fp);pad.SetNumber(number);pad.SetNet(board.FindNet(net));fp.Add(pad)
        board.Add(fp)

    def test_single_100n_reference_cap_retains_actual_connections_and_false_qualification(self):
        from build_pico47_single import inspect_reference_filter
        board,contract=self.fixture();r=inspect_reference_filter(board,contract)
        self.assertAlmostEqual(r['nominal_capacitance_uf'],.1)
        self.assertEqual(r['fitted_reference_caps'],['COUT'])
        self.assertTrue(r['both_native_connections'])
        self.assertFalse(r['supplier_current_revision_accepted'])
        self.assertFalse(r['transient_and_DC_bias_qualified'])

    def test_extra_fitted_reference_cap_is_rejected_even_with_the_same_value(self):
        from build_pico47_single import inspect_reference_filter
        board,contract=self.fixture();self.add_parallel(board)
        with self.assertRaisesRegex(ValueError,'parallel PMIC reference'):
            inspect_reference_filter(board,contract)

    def test_larger_cap_cannot_pass_by_changing_its_contract_value(self):
        from build_pico47_single import inspect_reference_filter
        board,contract=self.fixture();board.FindFootprintByReference('COUT').SetValue('1u')
        contract['value']='1u'
        with self.assertRaisesRegex(ValueError,'exceeds 0.1uF'):
            inspect_reference_filter(board,contract)
        contract['maximum_nominal_capacitance_uf']=1
        with self.assertRaisesRegex(ValueError,'limit differs'):
            inspect_reference_filter(board,contract)

    def test_unfitted_alternative_is_not_counted_as_a_parallel_cap(self):
        from build_pico47_single import inspect_reference_filter
        board,contract=self.fixture();self.add_parallel(board,dnp=True)
        self.assertEqual(inspect_reference_filter(board,contract)['fitted_reference_caps'],['COUT'])

    def test_reference_cap_still_requires_local_actual_return(self):
        from build_pico47_single import inspect_reference_filter
        for args in [dict(ground_connected=False),dict(distance=15)]:
            board,contract=self.fixture(**args)
            with self.assertRaisesRegex(ValueError,'actual copper connection|local placement'):
                inspect_reference_filter(board,contract)


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class ReferenceTreeBudgetTests(unittest.TestCase):
    def fixture(self,near_noise=False):
        import pcbnew as P
        board,contract=ReferenceFilterTests.fixture(self)
        board.Add(P.NETINFO_ITEM(board,'SWITCH',4))
        self.track(board,'SWITCH',(-.4,.3,-.4,1.3) if near_noise else (5,5,6,5))
        contract['routing_budget']=dict(maximum_total_track_length_mm=3,maximum_via_count=0,
            noise_projection_budget_mm=.5,noise_nets=['SWITCH'],inductor_refs=[],permitted_coupled_copper=[])
        return board,contract

    def track(self,board,net,xy,layer=None):
        import pcbnew as P
        t=P.PCB_TRACK(board);t.SetNet(board.FindNet(net));t.SetLayer(P.F_Cu if layer is None else layer)
        t.SetWidth(mm(.1));t.SetStart(P.VECTOR2I(mm(xy[0]),mm(xy[1])));t.SetEnd(P.VECTOR2I(mm(xy[2]),mm(xy[3])));board.Add(t)

    def test_native_tree_metrics_keep_noise_qualification_false(self):
        from build_pico47_single import inspect_reference_filter
        board,contract=self.fixture();m=inspect_reference_filter(board,contract)['reference_tree']
        self.assertAlmostEqual(m['total_track_length_mm'],1)
        self.assertEqual(m['via_count'],0);self.assertEqual(m['coupled_copper'],[])
        self.assertFalse(m['actual_noise_and_stability_qualified'])

    def test_a_near_cap_cannot_hide_a_long_connected_reference_loop(self):
        from build_pico47_single import inspect_reference_filter
        board,contract=self.fixture()
        for xy in [(0,0,-2,0),(-2,0,-2,2),(-2,2,0,2),(0,2,0,1)]:self.track(board,'OUT',xy)
        with self.assertRaisesRegex(ValueError,'total-copper budget'):
            inspect_reference_filter(board,contract)

    def test_extra_layer_changes_are_counted_even_with_a_near_filter(self):
        import pcbnew as P
        from build_pico47_single import inspect_reference_filter
        board,contract=self.fixture();contract['routing_budget']['maximum_total_track_length_mm']=10
        for xy in [(-1,0),(-1,1)]:
            via=P.PCB_VIA(board);via.SetNet(board.FindNet('OUT'));via.SetViaType(P.VIATYPE_THROUGH)
            via.SetLayerPair(P.F_Cu,P.B_Cu);via.SetWidth(mm(.2));via.SetDrill(mm(.1));via.SetPosition(P.VECTOR2I(mm(xy[0]),mm(xy[1])));board.Add(via)
        self.track(board,'OUT',(0,0,-1,0));self.track(board,'OUT',(-1,0,-1,1),P.B_Cu);self.track(board,'OUT',(-1,1,0,1))
        with self.assertRaisesRegex(ValueError,'via budget'):
            inspect_reference_filter(board,contract)

    def test_preserved_coupling_does_not_allow_new_reference_copper_near_a_switch(self):
        from build_pico47_single import inspect_reference_filter,reference_tree_metrics
        board,contract=self.fixture(near_noise=True)
        contract['routing_budget']['permitted_coupled_copper']=reference_tree_metrics(board,contract)['coupled_copper']
        m=inspect_reference_filter(board,contract)['reference_tree'];self.assertTrue(m['coupled_copper'])
        self.assertFalse(m['actual_noise_and_stability_qualified'])
        for xy in [(0,.3,-.1,.3),(-.1,.3,-.1,.7),(-.1,.7,0,.7)]:self.track(board,'OUT',xy)
        with self.assertRaisesRegex(ValueError,'Unreviewed reference copper'):
            inspect_reference_filter(board,contract)


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class PmicAnalogShieldTests(unittest.TestCase):
    def fixture(self):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD();board.SetCopperLayerCount(4)
        for index,name in enumerate(['GND','P47_VREF','P47_VEE_DRV'],1):
            board.Add(P.NETINFO_ITEM(board,name,index))
        fp=P.FOOTPRINT(board);fp.SetReference('U501')
        pad=P.PAD(fp);pad.SetNumber('57');pad.SetNet(board.FindNet('GND'))
        pad.SetSize(P.VECTOR2I(mm(.2),mm(.2)));pad.SetPosition(P.VECTOR2I(mm(-4),mm(-4)))
        layers=P.LSET();layers.AddLayer(P.In1_Cu);pad.SetLayerSet(layers);fp.Add(pad);board.Add(fp)
        shape=P.SHAPE_POLY_SET();shape.NewOutline()
        for x,y in [(-5,-5),(5,-5),(5,5),(-5,5)]:shape.Append(mm(x),mm(y))
        zone=P.ZONE(board);zone.SetNet(board.FindNet('GND'));zone.SetLayer(P.In1_Cu)
        zone.SetFilledPolysList(P.In1_Cu,shape);board.Add(zone)
        tracks=[]
        for net,layer,xy in [('P47_VEE_DRV',P.F_Cu,(-1,0,1,0)),
                             ('P47_VREF',P.In2_Cu,(0,-1,0,1))]:
            track=P.PCB_TRACK(board);track.SetNet(board.FindNet(net));track.SetLayer(layer)
            track.SetWidth(mm(.15));track.SetStart(P.VECTOR2I(mm(xy[0]),mm(xy[1])))
            track.SetEnd(P.VECTOR2I(mm(xy[2]),mm(xy[3])));board.Add(track);tracks.append(track)
        contract=dict(reference_net='P47_VREF',sensitive_nets=['P47_VREF'],
            noise_nets=['P47_VEE_DRV'],inductor_refs=[],clearance_mm=.5,
            ground_margin_mm=.2,shape_tolerance_um=2)
        return board,contract,zone,shape,tracks

    def test_reference_connected_plane_covers_both_sides_without_noise_qualification(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_analog_shield
        for layer in [P.In2_Cu,P.B_Cu]:
            board,c,_,_,tracks=self.fixture();tracks[1].SetLayer(layer)
            result=inspect_pmic_analog_shield(board,c)
            self.assertEqual(result['shielded_pair_count'],1)
            self.assertTrue(result['native_ground_geometry_passed'])
            self.assertFalse(result['actual_noise_and_stability_qualified'])

    def test_a_hole_between_the_traces_is_not_hidden_by_ground_under_each_trace(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_analog_shield
        board,c,zone,shape,_=self.fixture();hole=shape.NewHole(0)
        for x,y in [(.38,.38),(.42,.38),(.42,.42),(.38,.42)]:shape.Append(mm(x),mm(y),0,hole)
        zone.SetFilledPolysList(P.In1_Cu,shape)
        with self.assertRaisesRegex(ValueError,'ground corridor crosses a plane gap'):
            inspect_pmic_analog_shield(board,c)

    def test_same_named_but_reference_disconnected_plane_cannot_shield(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_analog_shield
        board,c,_,_,_=self.fixture()
        next(iter(board.FindFootprintByReference('U501').Pads())).SetPosition(P.VECTOR2I(mm(-6),mm(-6)))
        with self.assertRaisesRegex(ValueError,'reference ground|reference-connected|No filled copper'):
            inspect_pmic_analog_shield(board,c)

    def test_same_layer_sensitive_trace_never_uses_the_inner_plane_exception(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_analog_shield
        board,c,_,_,tracks=self.fixture();tracks[1].SetLayer(P.F_Cu)
        with self.assertRaisesRegex(ValueError,'Unshielded PMIC'):
            inspect_pmic_analog_shield(board,c)

    def test_noise_behind_the_ground_plane_is_not_treated_as_a_front_source(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_analog_shield
        board,c,_,_,tracks=self.fixture();tracks[0].SetLayer(P.In2_Cu)
        with self.assertRaisesRegex(ValueError,'Unshielded PMIC'):
            inspect_pmic_analog_shield(board,c)

    def test_sensitive_through_via_cannot_use_a_plane_it_crosses(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_analog_shield
        board,c,_,_,_=self.fixture();via=P.PCB_VIA(board);via.SetNet(board.FindNet('P47_VREF'))
        via.SetViaType(P.VIATYPE_THROUGH);via.SetLayerPair(P.F_Cu,P.B_Cu)
        via.SetWidth(mm(.4));via.SetDrill(mm(.2));via.SetPosition(P.VECTOR2I(0,0));board.Add(via)
        with self.assertRaisesRegex(ValueError,'Unshielded PMIC'):
            inspect_pmic_analog_shield(board,c)

    def test_native_inductor_courtyard_stays_forbidden_with_a_solid_plane(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_analog_shield
        board,c,_,_,_=self.fixture();lib=Path(__file__).parent/'v0.1.1/Panda47.pretty'
        fp=P.FootprintLoad(str(lib),'L802_Display');self.assertIsNotNone(fp)
        fp.SetReference('COIL');fp.SetPosition(P.VECTOR2I(0,0));fp.SetOrientationDegrees(0);board.Add(fp)
        c['inductor_refs']=['COIL']
        with self.assertRaisesRegex(ValueError,'Unshielded PMIC'):
            inspect_pmic_analog_shield(board,c)

    def test_contract_edits_cannot_reduce_the_reviewed_margin(self):
        from build_pico47_single import inspect_pmic_analog_shield
        for key,value in [('ground_margin_mm',.1),('clearance_mm',.15),('shape_tolerance_um',20)]:
            board,c,_,_,_=self.fixture();c[key]=value
            with self.assertRaisesRegex(ValueError,'budgets differ'):
                inspect_pmic_analog_shield(board,c)

    def test_fragmenting_the_same_copper_cannot_change_the_shield_result(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_analog_shield
        board,c,zone,shape,tracks=self.fixture()
        for original in tracks:
            net,layer=original.GetNet(),original.GetLayer()
            a=(original.GetStart().x,original.GetStart().y)
            b=(original.GetEnd().x,original.GetEnd().y);board.Delete(original)
            for index in range(20):
                segment=P.PCB_TRACK(board);segment.SetNet(net);segment.SetLayer(layer);segment.SetWidth(mm(.15))
                segment.SetStart(P.VECTOR2I(a[0]+(b[0]-a[0])*index//20,a[1]+(b[1]-a[1])*index//20))
                segment.SetEnd(P.VECTOR2I(a[0]+(b[0]-a[0])*(index+1)//20,a[1]+(b[1]-a[1])*(index+1)//20));board.Add(segment)
        self.assertEqual(inspect_pmic_analog_shield(board,c)['shielded_pair_count'],1)
        hole=shape.NewHole(0)
        for x,y in [(.38,.38),(.42,.38),(.42,.42),(.38,.42)]:shape.Append(mm(x),mm(y),0,hole)
        zone.SetFilledPolysList(P.In1_Cu,shape)
        with self.assertRaisesRegex(ValueError,'ground corridor crosses a plane gap'):
            inspect_pmic_analog_shield(board,c)


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class SolderJointViaTests(unittest.TestCase):
    def fixture(self,bare_only=False,also_bare=False,paste_only=False,annulus_only=False):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD();board.SetCopperLayerCount(4);net=P.NETINFO_ITEM(board,'GND',1);board.Add(net)
        def part(ref,bare):
            fp=P.FOOTPRINT(board);fp.SetReference(ref);fp.SetAttributes(P.FP_SMD|(P.FP_EXCLUDE_FROM_BOM if bare else 0))
            pad=P.PAD(fp);pad.SetNumber('1');pad.SetAttribute(P.PAD_ATTRIB_SMD);pad.SetNet(net);pad.SetSize(P.VECTOR2I(mm(.5),mm(.5)))
            ls=P.LSET();ls.AddLayer(P.F_Cu);ls.AddLayer(P.F_Mask)
            if not bare and not paste_only:ls.AddLayer(P.F_Paste)
            pad.SetLayerSet(ls);fp.Add(pad)
            if paste_only and not bare:
                stencil=P.PAD(fp);stencil.SetNumber('');stencil.SetAttribute(P.PAD_ATTRIB_SMD);stencil.SetSize(P.VECTOR2I(mm(.4),mm(.4)))
                layers=P.LSET();layers.AddLayer(P.F_Paste);stencil.SetLayerSet(layers);fp.Add(stencil)
            board.Add(fp)
        if not bare_only:part('U_TEST',False)
        if bare_only or also_bare:part('TP_TEST',True)
        via=P.PCB_VIA(board);via.SetNet(net);via.SetViaType(P.VIATYPE_THROUGH);via.SetLayerPair(P.F_Cu,P.B_Cu)
        via.SetWidth(mm(.4));via.SetDrill(mm(.2));via.SetPosition(P.VECTOR2I(mm(.4) if annulus_only else 0,0));board.Add(via)
        return board

    def test_stencil_only_pad_is_counted_for_a_thermal_joint(self):
        from verify_jlc_coupon_compliance import inspect_solder_joint_vias
        result=inspect_solder_joint_vias(self.fixture(paste_only=True),'FILLED_AND_CAPPED')
        self.assertEqual(result['filled_cap_via_count'],1)
        self.assertTrue(result['filled_and_capped_vias'][0]['paste_intersection'])
        self.assertFalse(result['supplier_process_accepted'])

    def test_testpoint_over_thermal_joint_does_not_double_count_the_via(self):
        from verify_jlc_coupon_compliance import inspect_solder_joint_vias
        result=inspect_solder_joint_vias(self.fixture(also_bare=True),'FILLED_AND_CAPPED')
        self.assertEqual(result['filled_cap_via_count'],1)
        self.assertEqual(len(result['all_drill_pad_contacts'][0]['contacts']),2)
        self.assertFalse(result['bare_test_only_vias'])

    def test_bare_test_landing_without_a_solder_joint_is_separate(self):
        from verify_jlc_coupon_compliance import inspect_solder_joint_vias
        result=inspect_solder_joint_vias(self.fixture(bare_only=True),'FILLED_AND_CAPPED')
        self.assertEqual(result['filled_cap_via_count'],0)
        self.assertEqual(len(result['bare_test_only_vias']),1)

    def test_annulus_contact_does_not_mean_the_drill_cuts_the_pad(self):
        from verify_jlc_coupon_compliance import inspect_solder_joint_vias
        result=inspect_solder_joint_vias(self.fixture(annulus_only=True),'FILLED_AND_CAPPED')
        self.assertEqual(result['filled_cap_via_count'],0)
        self.assertFalse(result['all_drill_pad_contacts'])

    def test_declared_native_footprint_IDs_survive_two_independent_replays(self):
        import pcbnew as P
        refid='11111111-1111-4111-8111-111111111111';one='22222222-2222-4222-8222-222222222222';two='33333333-3333-4333-8333-333333333333'
        text=f'''(footprint "CAPTEST" (version 20260206) (generator "pcbnew") (layer "F.Cu")
          (uuid "{refid}") (property "Reference" "NEW" (at 0 -1 0) (layer "F.Fab") (effects (font (size 1 1))))
          (property "Value" "1u" (at 0 1 0) (layer "F.Fab") (effects (font (size 1 1)))) (attr smd)
          (pad "1" smd rect (at -.5 0) (size .5 .5) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{one}"))
          (pad "2" smd rect (at .5 0) (size .5 .5) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{two}")))'''
        with tempfile.TemporaryDirectory() as folder:
            lib=Path(folder)/'Panda47.pretty';lib.mkdir();path=lib/'CAPTEST.kicad_mod';path.write_text(text)
            delta=dict(removed_uuids=[],updated_copper=[],added_tracks=[],added_vias=[],added_zones=[],footprint_poses={},
                       added_footprints=[dict(ref='NEW',library_path='Panda47.pretty/CAPTEST.kicad_mod',library_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),value='1u',side='F.Cu',properties={},pins={'1':'VOUT','2':'GND'},fpid='Panda47:CAPTEST',x=1,y=1,rot=0,schematic_path='/44444444-4444-4444-8444-444444444444/55555555-5555-4555-8555-555555555555',preserve_uuid=True,native_uuid=refid,pad_uuids={'1':one,'2':two})])
            for attempt in range(2):
                board=P.BOARD();board.SetCopperLayerCount(4)
                for i,name in enumerate(['VOUT','GND'],1):board.Add(P.NETINFO_ITEM(board,name,i))
                keep=apply_layout_eco(board,delta,folder);fp=board.FindFootprintByReference('NEW')
                self.assertEqual(fp.m_Uuid.AsString(),refid)
                self.assertEqual({p.GetNumber():p.m_Uuid.AsString() for p in fp.Pads()},{'1':one,'2':two})


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class PanelClockReferenceTests(unittest.TestCase):
    def fixture(self):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD();board.SetCopperLayerCount(4)
        ground=P.NETINFO_ITEM(board,'GND',1);board.Add(ground)
        fp=P.FOOTPRINT(board);fp.SetReference('U501')
        pad=P.PAD(fp);pad.SetNumber('57');pad.SetNet(ground)
        pad.SetSize(P.VECTOR2I(mm(.2),mm(.2)));pad.SetPosition(P.VECTOR2I(mm(.2),mm(1.75)))
        layers=P.LSET();layers.AddLayer(P.In1_Cu);pad.SetLayerSet(layers);fp.Add(pad);board.Add(fp)
        shape=P.SHAPE_POLY_SET();shape.NewOutline()
        for x,y in [(0,0),(2,0),(2,2),(0,2)]:shape.Append(mm(x),mm(y))
        hole=shape.NewHole(0)
        for x,y in [(1,1),(1.2,1),(1.2,1.2),(1,1.2)]:shape.Append(mm(x),mm(y),0,hole)
        zone=P.ZONE(board);zone.SetNet(ground);zone.SetLayer(P.In1_Cu)
        zone.SetFilledPolysList(P.In1_Cu,shape);board.Add(zone)
        tracks={}
        names=[name+suffix for name in ['P47_CKV','P47_XLE','P47_XCL','P47_XSTL'] for suffix in ['','_SRC']]
        for index,name in enumerate(names):
            net=P.NETINFO_ITEM(board,name,index+2);board.Add(net)
            track=P.PCB_TRACK(board);track.SetNet(net);track.SetLayer(P.F_Cu);track.SetWidth(mm(.15))
            track.SetStart(P.VECTOR2I(mm(.1),mm(.1+index*.1)));track.SetEnd(P.VECTOR2I(mm(.5),mm(.1+index*.1)));board.Add(track);tracks[name]=track
        return board,tracks

    def test_panel_reference_rejects_a_real_plane_hole_on_a_top_clock(self):
        import pcbnew as P
        board,tracks=self.fixture()
        self.assertTrue(inspect_panel_clock_references(board)['F_and_In2_to_In1_all_covered'])
        track=tracks['P47_XSTL'];track.SetStart(P.VECTOR2I(mm(.5),mm(1.1)));track.SetEnd(P.VECTOR2I(mm(1.7),mm(1.1)))
        with self.assertRaisesRegex(ValueError,'Panel F/In2 reference'):
            inspect_panel_clock_references(board)

    def test_rear_adjacent_plane_gap_remains_explicit_and_unqualified(self):
        import pcbnew as P
        board,tracks=self.fixture();tracks['P47_CKV'].SetLayer(P.B_Cu)
        report=inspect_panel_clock_references(board)
        self.assertGreater(report['rear_adjacent_In2_uncovered_count'],0)
        self.assertFalse(report['rear_adjacent_plane_complete'])
        self.assertFalse(report['electrical_timing_and_return_qualified'])


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class ClockGroundStitchTests(unittest.TestCase):
    def fixture(self):
        import pcbnew as P
        board,tracks=PanelClockReferenceTests().fixture()
        ground=board.FindNet('GND')
        via=P.PCB_VIA(board);via.SetViaType(P.VIATYPE_THROUGH);via.SetLayerPair(P.F_Cu,P.B_Cu)
        via.SetWidth(mm(.4));via.SetDrill(mm(.2));via.SetPosition(P.VECTOR2I(mm(.3),mm(1.5)))
        via.SetNet(ground);board.Add(via)
        shape=P.SHAPE_POLY_SET();shape.NewOutline()
        for x,y in [(0,0),(2,0),(2,2),(0,2)]:shape.Append(mm(x),mm(y))
        zone=P.ZONE(board);zone.SetNet(ground);zone.SetLayer(P.B_Cu)
        zone.SetFilledPolysList(P.B_Cu,shape);board.Add(zone)
        target=P.PCB_VIA(board);target.SetViaType(P.VIATYPE_THROUGH);target.SetLayerPair(P.F_Cu,P.B_Cu)
        target.SetWidth(mm(.4));target.SetDrill(mm(.2));target.SetPosition(P.VECTOR2I(mm(.9),mm(1.5)))
        target.SetNet(board.FindNet('P47_CKV'));board.Add(target)
        rear=P.PCB_TRACK(board);rear.SetNet(target.GetNet());rear.SetLayer(P.B_Cu);rear.SetWidth(mm(.15))
        rear.SetStart(target.GetPosition());rear.SetEnd(P.VECTOR2I(mm(1.1),mm(1.5)));board.Add(rear)
        tracks['P47_CKV'].SetStart(target.GetPosition());tracks['P47_CKV'].SetEnd(P.VECTOR2I(mm(1.1),mm(1.5)))
        plan=[dict(xy_mm=[.3,1.5],targets=[dict(net='P47_CKV',xy_mm=[.9,1.5],before_mm=2.0)])]
        return board,zone,shape,rear,plan

    def test_real_ground_bridge_reports_distance_without_electrical_qualification(self):
        board,_,_,_,plan=self.fixture()
        report=inspect_clock_ground_stitches(board,plan)
        self.assertTrue(report['all_reviewed_In1_B_contacts'])
        self.assertAlmostEqual(report['stitches'][0]['targets'][0]['reviewed_ground_via_distance_mm'],.6)
        self.assertFalse(report['electrical_timing_and_return_qualified'])

    def test_real_B_plane_hole_cannot_count_as_a_connected_ground_contact(self):
        import pcbnew as P
        board,zone,shape,_,plan=self.fixture()
        hole=shape.NewHole(0)
        for x,y in [(.05,1.25),(.55,1.25),(.55,1.75),(.05,1.75)]:shape.Append(mm(x),mm(y),0,hole)
        zone.SetFilledPolysList(P.B_Cu,shape)
        with self.assertRaisesRegex(ValueError,'reference-connected In1/B'):
            inspect_clock_ground_stitches(board,plan)

    def test_same_net_SMD_pad_still_requires_50um_pad_edge_separation(self):
        import pcbnew as P
        board,_,_,_,plan=self.fixture()
        fp=P.FOOTPRINT(board);fp.SetReference('C_TEST')
        pad=P.PAD(fp);pad.SetNumber('1');pad.SetNet(board.FindNet('GND'));pad.SetAttribute(P.PAD_ATTRIB_SMD)
        pad.SetSize(P.VECTOR2I(mm(.2),mm(.2)));pad.SetPosition(P.VECTOR2I(mm(.62),mm(1.5)))
        layers=P.LSET();layers.AddLayer(P.F_Cu);pad.SetLayerSet(layers);fp.Add(pad);board.Add(fp)
        with self.assertRaisesRegex(ValueError,'50um SMD'):
            inspect_clock_ground_stitches(board,plan)

    def test_same_reference_layer_change_is_not_reported_as_a_B_transition(self):
        import pcbnew as P
        board,_,_,rear,plan=self.fixture();rear.SetLayer(P.In2_Cu)
        with self.assertRaisesRegex(ValueError,'no B-layer transition'):
            inspect_clock_ground_stitches(board,plan)
        rear.SetLayer(P.B_Cu)
        for track in board.GetTracks():
            if track.GetClass()=='PCB_TRACK' and track.GetNetname()=='P47_CKV':
                track.SetLayer(P.B_Cu)
        with self.assertRaisesRegex(ValueError,'no B-layer transition'):
            inspect_clock_ground_stitches(board,plan)


@unittest.skipUnless(importlib.util.find_spec('shapely') and importlib.util.find_spec('numpy')
                     and importlib.util.find_spec('networkx'), 'Geometry analysis environment required')
class ActualPathTests(unittest.TestCase):
    def test_branch_is_excluded_from_endpoint_length(self):
        from layout_review_metrics import analyze
        def pad(ref,x,y):
            return dict(ref=ref,num='1',net='TEST',x=x,y=y,
                        polys={'F.Cu':[[[x-.1,y-.1],[x+.1,y-.1],[x+.1,y+.1],[x-.1,y+.1]]]})
        def line(a,b):
            return dict(net='TEST',x1=a[0],y1=a[1],x2=b[0],y2=b[1],w=.15,layer='F.Cu')
        data=dict(pads=[pad('A',0,0),pad('B',10,0),pad('PULL',5,20)],vias=[],
                  tracks=[line((0,0),(10,0)),line((5,0),(5,20))])
        result=analyze(data,'TEST',[('A.1','B.1')])
        self.assertAlmostEqual(result['whole_net_length_mm'],30)
        self.assertTrue(result['paths'][0]['connected_in_geometry_model'])
        self.assertLessEqual(result['paths'][0]['length_mm'],10)
        self.assertGreater(result['paths'][0]['length_mm'],9.7)


@unittest.skipUnless(importlib.util.find_spec('shapely') and importlib.util.find_spec('numpy')
                     and importlib.util.find_spec('networkx'), 'Geometry analysis environment required')
class LayerResolvedPathTests(unittest.TestCase):
    Z = {'F.Cu':0.0,'In1.Cu':.12625,'In2.Cu':.63875,'B.Cu':.765}

    def fixture(self, destination_layer):
        def pad(ref,x,layer):
            return dict(ref=ref,num='1',net='TEST',x=x,y=0,
                        polys={layer:[[[x-.05,-.05],[x+.05,-.05],[x+.05,.05],[x-.05,.05]]]})
        def track(x1,x2,layer):
            return dict(net='TEST',x1=x1,y1=0,x2=x2,y2=0,w=.15,layer=layer)
        return dict(pads=[pad('A',0,'F.Cu'),pad('B',2,destination_layer)],
                    tracks=[track(0,1,'F.Cu'),track(1,2,destination_layer)],
                    vias=[dict(net='TEST',x=1,y=0,d=.4,drill=.2)])

    def test_top_to_bottom_counts_one_actual_barrel_span(self):
        from layout_review_metrics import analyze
        result=analyze(self.fixture('B.Cu'),'TEST',[('A.1','B.1')],self.Z)['paths'][0]
        self.assertTrue(result['connected_in_geometry_model'])
        # 此夹具从源焊盘中心出发，至 x=1.95 处首先接触目标焊盘。
        self.assertAlmostEqual(result['length_mm'],1.95)
        self.assertAlmostEqual(result['vertical_length_mm'],.765)
        self.assertAlmostEqual(result['total_conductor_length_mm'],2.715)
        self.assertEqual(result['via_count'],1)
        self.assertEqual(len(result['via_transitions']),1)
        self.assertAlmostEqual(result['via_transitions'][0]['unused_barrel_length_mm'],0)

    def test_inner_exit_does_not_count_unused_bottom_stub(self):
        from layout_review_metrics import analyze
        result=analyze(self.fixture('In2.Cu'),'TEST',[('A.1','B.1')],self.Z)['paths'][0]
        self.assertAlmostEqual(result['vertical_length_mm'],.63875)
        self.assertAlmostEqual(result['via_transitions'][0]['unused_barrel_length_mm'],.12625)
        self.assertEqual(result['via_transitions'][0]['from_layer'],'F.Cu')
        self.assertEqual(result['via_transitions'][0]['to_layer'],'In2.Cu')

    def test_same_layer_via_contact_has_no_vertical_path(self):
        from layout_review_metrics import analyze
        data=self.fixture('F.Cu')
        planar=analyze(data,'TEST',[('A.1','B.1')])['paths'][0]
        result=analyze(data,'TEST',[('A.1','B.1')],self.Z)['paths'][0]
        self.assertAlmostEqual(result['length_mm'],planar['length_mm'])
        self.assertEqual(result['vertical_length_mm'],0)
        self.assertEqual(result['via_transitions'],[])

    def test_invalid_layer_coordinates_are_rejected(self):
        from layout_review_metrics import analyze
        invalid=[{'F.Cu':0,'B.Cu':.8},dict(self.Z,**{'In2.Cu':-.1}),
                 dict(self.Z,**{'B.Cu':float('nan')})]
        for z in invalid:
            with self.subTest(z=z),self.assertRaises(ValueError):
                analyze(self.fixture('B.Cu'),'TEST',[('A.1','B.1')],z)
        blind=self.fixture('In2.Cu')
        blind['vias'][0].update(via_type='other',copper_layer_span=['F.Cu','In2.Cu'])
        with self.assertRaisesRegex(ValueError,'through vias'):
            analyze(blind,'TEST',[('A.1','B.1')],self.Z)

    def test_native_job_centers_exclude_mask_and_include_half_copper(self):
        from layout_review_metrics import layer_centers_from_job
        rows=[dict(Type='SolderMask',Thickness=.01)]
        for name,thickness in [('F.Cu',.035),('d1',.1),('In1.Cu',.0175),('d2',.495),
                               ('In2.Cu',.0175),('d3',.1),('B.Cu',.035)]:
            rows.append(dict(Type='Copper' if name.endswith('.Cu') else 'Dielectric',
                             Name=name,Thickness=thickness))
        z=layer_centers_from_job(dict(MaterialStackup=rows))
        for layer,expected in self.Z.items():
            self.assertAlmostEqual(z[layer],expected)
        rows[2]['Thickness']=0
        with self.assertRaisesRegex(ValueError,'positive'):
            layer_centers_from_job(dict(MaterialStackup=rows))


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class SourcePoseEnvelopeTests(unittest.TestCase):
    def fixture(self):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD();board.SetCopperLayerCount(4)
        moved=[f'M{i}' for i in range(54)]
        added=[f'A{i}' for i in range(12)]
        for idx,ref in enumerate(moved+added+['NEIGHBOR']):
            fp=P.FOOTPRINT(board);fp.SetReference(ref);fp.SetAttributes(P.FP_SMD)
            x=(idx%10)*5;y=(idx//10)*5
            pad=P.PAD(fp);pad.SetNumber('1');pad.SetAttribute(P.PAD_ATTRIB_SMD)
            pad.SetSize(P.VECTOR2I(mm(.5),mm(.5)));pad.SetPosition(P.VECTOR2I(mm(x),mm(y)))
            ls=P.LSET();ls.AddLayer(P.F_Cu);pad.SetLayerSet(ls);fp.Add(pad)
            if ref!='NEIGHBOR':
                poly=P.PCB_SHAPE(fp,P.SHAPE_T_POLY);poly.SetLayer(P.F_CrtYd);poly.SetWidth(mm(.05))
                pts=poly.GetPolyShape();pts.NewOutline()
                for px,py in [(x-.4,y-.4),(x+.4,y-.4),(x+.4,y+.4),(x-.4,y+.4)]:
                    pts.Append(mm(px),mm(py))
                fp.Add(poly)
            fp.SetPosition(P.VECTOR2I(mm(x),mm(y)));board.Add(fp)
        contract=dict(fallback_margin_mm=.25,moved_refs=moved,added_refs=added)
        return board,contract

    def test_clean_66_pose_screen_passes_and_keeps_supplier_qualification_false(self):
        from build_pico47_single import inspect_source_pose_envelopes
        board,c=self.fixture();r=inspect_source_pose_envelopes(board,c)
        self.assertEqual(r['clashes'],[])
        self.assertEqual(r['checked_pose_count'],66)
        self.assertIn('NEIGHBOR:F.Cu',r['fallback_refs'])
        self.assertFalse(r['supplier_maximum_envelopes_and_tolerance_qualified'])

    def test_fallback_250um_margin_overlap_is_rejected(self):
        import pcbnew as P
        from build_pico47_single import inspect_source_pose_envelopes
        board,c=self.fixture()
        nb=board.FindFootprintByReference('NEIGHBOR')
        next(iter(nb.Pads())).SetPosition(P.VECTOR2I(mm(.8),0))
        with self.assertRaisesRegex(ValueError,'Source-pose envelope clashes'):
            inspect_source_pose_envelopes(board,c)

    def test_contract_cannot_weaken_fallback_margin_or_pose_count(self):
        from build_pico47_single import inspect_source_pose_envelopes
        board,c=self.fixture();c['fallback_margin_mm']=.1
        with self.assertRaisesRegex(ValueError,'fallback margin differs'):
            inspect_source_pose_envelopes(board,c)
        board,c=self.fixture();c['moved_refs']=c['moved_refs'][:-1]
        with self.assertRaisesRegex(ValueError,'inventory differs'):
            inspect_source_pose_envelopes(board,c)

    def test_opposite_face_part_at_same_xy_does_not_falsely_clash(self):
        import pcbnew as P
        from build_pico47_single import inspect_source_pose_envelopes
        board,c=self.fixture()
        nb=board.FindFootprintByReference('NEIGHBOR')
        p=next(iter(nb.Pads()));p.SetPosition(P.VECTOR2I(0,0))
        ls=P.LSET();ls.AddLayer(P.B_Cu);p.SetLayerSet(ls)
        self.assertEqual(inspect_source_pose_envelopes(board,c)['clashes'],[])


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class BacksideSmtClearanceTests(unittest.TestCase):
    def fixture(self):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD();board.SetCopperLayerCount(4)
        parts=[('C537',67.55,99.65,.55,False),('C538',67.1,100.65,.55,False),
               ('C543',68.345,94.963,.55,False),('C815',12.8,94.0,.55,False),
               ('R710',59.308,98.967,.4,False),('R731',64.7,89.1,.4,False),
               ('TP801',30.45,96.05,0,True),('TP803',13.65,91.85,0,True),('TP805',12.5,103.0,0,True)]
        for ref,x,y,_,bare in parts:
            fp=P.FOOTPRINT(board);fp.SetReference(ref);fp.SetLayer(P.B_Cu)
            fp.SetAttributes(P.FP_SMD|(P.FP_EXCLUDE_FROM_BOM if bare else 0))
            p=P.PAD(fp);p.SetNumber('1');p.SetAttribute(P.PAD_ATTRIB_SMD)
            p.SetSize(P.VECTOR2I(mm(.5),mm(.5)));p.SetPosition(P.VECTOR2I(mm(x),mm(y)))
            ls=P.LSET();ls.AddLayer(P.B_Cu);p.SetLayerSet(ls);fp.Add(p)
            fp.SetPosition(P.VECTOR2I(mm(x),mm(y)));board.Add(fp)
        contract=dict(expected_populated_refs=['C537','C538','C543','C815','R710','R731'],
                      expected_bare_testpoint_refs=['TP801','TP803','TP805'],
                      battery_bay_max_x_mm=37.5,battery_bay_max_y_mm=83.2,
                      min_battery_bay_clearance_mm=5.0,upper_right_bay_max_y_mm=31.2,
                      min_upper_right_bay_clearance_mm=50.0,maximum_component_thickness_mm=.6,
                      max_thickness_mm_by_ref={'C537':.55,'C538':.55,'C543':.55,'C815':.55,'R710':.4,'R731':.4})
        return board,contract

    def test_backside_smt_parts_clear_bays_and_keep_7mm_qualification_false(self):
        from build_pico47_single import inspect_backside_smt_clearances
        board,c=self.fixture();r=inspect_backside_smt_clearances(board,c)
        self.assertEqual(r['populated_count'],6)
        self.assertEqual(r['bare_testpoint_count'],3)
        self.assertAlmostEqual(r['max_reviewed_height_budget_mm'],.55)
        self.assertEqual(r['height_evidence_source'],'project_contract_only')
        self.assertFalse(r['supplier_maximum_height_verified'])
        self.assertTrue(all('reviewed_height_budget_mm' in row and
                            'max_datasheet_thickness_mm' not in row
                            for row in r['populated_parts']))
        self.assertGreaterEqual(r['min_battery_bay_clearance_mm'],5.0)
        self.assertTrue(r['rear_shell_local_relief_required'])
        self.assertFalse(r['backside_height_and_assembly_qualified'])
        self.assertFalse(r['actual_battery_full_panel_positive_tolerance_7mm_qualified'])

    def test_battery_or_upper_right_bay_encroachment_is_rejected(self):
        import pcbnew as P
        from build_pico47_single import inspect_backside_smt_clearances
        board,c=self.fixture()
        fp=board.FindFootprintByReference('C815')
        next(iter(fp.Pads())).SetPosition(P.VECTOR2I(mm(12.8),mm(86.0)))
        with self.assertRaisesRegex(ValueError,'battery bay clearance'):
            inspect_backside_smt_clearances(board,c)
        board,c=self.fixture()
        fp=board.FindFootprintByReference('R731')
        next(iter(fp.Pads())).SetPosition(P.VECTOR2I(mm(64.7),mm(75.0)))
        with self.assertRaisesRegex(ValueError,'upper-right support bay'):
            inspect_backside_smt_clearances(board,c)

    def test_excess_backside_thickness_or_unexpected_part_is_rejected(self):
        import pcbnew as P
        from build_pico47_single import inspect_backside_smt_clearances
        board,c=self.fixture();c['max_thickness_mm_by_ref']['C815']=.85
        with self.assertRaisesRegex(ValueError,'thickness budget'):
            inspect_backside_smt_clearances(board,c)
        board,c=self.fixture()
        extra=P.FOOTPRINT(board);extra.SetReference('C_EXTRA');extra.SetAttributes(P.FP_SMD)
        p=P.PAD(extra);p.SetNumber('1');p.SetAttribute(P.PAD_ATTRIB_SMD);p.SetSize(P.VECTOR2I(mm(.5),mm(.5)))
        p.SetPosition(P.VECTOR2I(mm(50),mm(100)));ls=P.LSET();ls.AddLayer(P.B_Cu);p.SetLayerSet(ls);extra.Add(p);board.Add(extra)
        with self.assertRaisesRegex(ValueError,'populated SMT inventory differs'):
            inspect_backside_smt_clearances(board,c)


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class PmicChargePumpStorageTests(unittest.TestCase):
    def fixture(self):
        import wx
        app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        board=P.BOARD();board.SetCopperLayerCount(4)
        for idx,name in enumerate(['GND','P47_VEE_BASE','P47_VEE_DRV','P47_VGL'],1):
            board.Add(P.NETINFO_ITEM(board,name,idx))
        def add_part(ref,val,pins):
            fp=P.FOOTPRINT(board);fp.SetReference(ref);fp.SetValue(val)
            fp.SetLayer(P.F_Cu);fp.SetAttributes(P.FP_SMD)
            for num,net,x,y in pins:
                p=P.PAD(fp);p.SetNumber(str(num));p.SetAttribute(P.PAD_ATTRIB_SMD)
                p.SetNet(board.FindNet(net));p.SetSize(P.VECTOR2I(mm(.4),mm(.4)))
                p.SetPosition(P.VECTOR2I(mm(x),mm(y)))
                ls=P.LSET();ls.AddLayer(P.F_Cu);p.SetLayerSet(ls);fp.Add(p)
            board.Add(fp)
        add_part('U810','SY7636A',[('30','P47_VEE_BASE',0,0),('32','GND',0,2),('28','P47_VEE_DRV',0,4)])
        add_part('C810','1u/50V/0805',[('1','P47_VEE_BASE',4,0),('2','GND',4,2)])
        add_part('D804','BAV99',[('1','P47_VGL',8,4),('2','P47_VEE_BASE',8,0)])
        add_part('C811','47n/50V/0805',[('2','P47_VEE_DRV',4,4)])
        add_part('R803','750k/0.1%',[('1','P47_VGL',4,6)])
        def trk(net,ly,x1,y1,x2,y2):
            t=P.PCB_TRACK(board);t.SetNet(board.FindNet(net));t.SetLayer(ly);t.SetWidth(mm(.15))
            t.SetStart(P.VECTOR2I(mm(x1),mm(y1)));t.SetEnd(P.VECTOR2I(mm(x2),mm(y2)));board.Add(t)
            return t
        def via(net,x,y):
            v=P.PCB_VIA(board);v.SetNet(board.FindNet(net));v.SetViaType(P.VIATYPE_THROUGH)
            v.SetLayerPair(P.F_Cu,P.B_Cu);v.SetWidth(mm(.4));v.SetDrill(mm(.2))
            v.SetPosition(P.VECTOR2I(mm(x),mm(y)));board.Add(v)
            return v
        trk('P47_VEE_BASE',P.F_Cu,0,0,1,0);via('P47_VEE_BASE',1,0)
        trk('P47_VEE_BASE',P.In2_Cu,1,0,3,0);via('P47_VEE_BASE',3,0)
        trk('P47_VEE_BASE',P.F_Cu,3,0,4,0);trk('P47_VEE_BASE',P.F_Cu,4,0,8,0)
        trk('GND',P.F_Cu,0,2,4,2)
        trk('P47_VEE_DRV',P.F_Cu,0,4,1,4);via('P47_VEE_DRV',1,4)
        trk('P47_VEE_DRV',P.B_Cu,1,4,3,4);via('P47_VEE_DRV',3,4)
        trk('P47_VEE_DRV',P.F_Cu,3,4,4,4)
        trk('P47_VGL',P.F_Cu,4,6,5,6);via('P47_VGL',5,6)
        trk('P47_VGL',P.In2_Cu,5,6,7,6);via('P47_VGL',7,6)
        trk('P47_VGL',P.B_Cu,7,6,8,6);via('P47_VGL',8,6)
        trk('P47_VGL',P.F_Cu,8,6,8,4)
        contract=dict(device='U810',power_pin='30',ground_pin='32',cap='C810',value='1u/50V/0805',
                      side='F.Cu',power_net='P47_VEE_BASE',diode='D804',diode_pin='2',
                      maximum_total_track_length_mm=10.0,maximum_via_count=2,allowed_layers=['F.Cu','In2.Cu'],
                      joint_driver_net='P47_VEE_DRV',driver_pin='28',driver_cap='C811',driver_cap_pin='2',
                      maximum_driver_track_length_mm=6.0,maximum_driver_via_count=2,
                      joint_vgl_net='P47_VGL',vgl_sense_ref='R803',vgl_sense_pin='1',
                      maximum_vgl_track_length_mm=10.0,maximum_vgl_via_count=4)
        return board,contract

    def test_short_inner_route_passes_and_keeps_transient_qualification_false(self):
        from build_pico47_single import inspect_pmic_charge_pump_storage
        board,c=self.fixture();r=inspect_pmic_charge_pump_storage(board,c)
        self.assertEqual(r['vee_base']['via_count'],2)
        self.assertEqual(r['vee_base']['track_layers'],['F.Cu','In2.Cu'])
        self.assertTrue(r['all_scoped_vias_clear_smd_50um'])
        self.assertFalse(r['charge_pump_transient_and_ripple_qualified'])
        self.assertFalse(r['actual_noise_and_stability_qualified'])

    def test_outer_bottom_loop_or_excess_length_or_extra_via_is_rejected(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_charge_pump_storage
        board,c=self.fixture()
        t=P.PCB_TRACK(board);t.SetNet(board.FindNet('P47_VEE_BASE'));t.SetLayer(P.B_Cu);t.SetWidth(mm(.15))
        t.SetStart(P.VECTOR2I(mm(1),0));t.SetEnd(P.VECTOR2I(mm(2),0));board.Add(t)
        with self.assertRaisesRegex(ValueError,'unreviewed copper layers'):
            inspect_pmic_charge_pump_storage(board,c)
        board,c=self.fixture();c['maximum_total_track_length_mm']=5.0
        with self.assertRaisesRegex(ValueError,'total track length budget'):
            inspect_pmic_charge_pump_storage(board,c)
        board,c=self.fixture();c['maximum_via_count']=1
        with self.assertRaisesRegex(ValueError,'via count budget'):
            inspect_pmic_charge_pump_storage(board,c)

    def test_joint_driver_or_vgl_budget_violation_is_rejected(self):
        from build_pico47_single import inspect_pmic_charge_pump_storage
        board,c=self.fixture();c['maximum_driver_via_count']=1
        with self.assertRaisesRegex(ValueError,'P47_VEE_DRV exceeds'):
            inspect_pmic_charge_pump_storage(board,c)
        board,c=self.fixture();c['maximum_vgl_track_length_mm']=2.0
        with self.assertRaisesRegex(ValueError,'P47_VGL exceeds'):
            inspect_pmic_charge_pump_storage(board,c)

    def test_via_within_50um_of_smd_pad_or_broken_link_is_rejected(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_charge_pump_storage
        board,c=self.fixture()
        v=P.PCB_VIA(board);v.SetNet(board.FindNet('P47_VEE_BASE'));v.SetViaType(P.VIATYPE_THROUGH)
        v.SetLayerPair(P.F_Cu,P.B_Cu);v.SetWidth(mm(.4));v.SetDrill(mm(.2))
        v.SetPosition(P.VECTOR2I(mm(.42),0));board.Add(v)
        with self.assertRaisesRegex(ValueError,'50um SMD pad-edge'):
            inspect_pmic_charge_pump_storage(board,c)
        board,c=self.fixture()
        for t in list(board.GetTracks()):
            if t.GetNetname()=='P47_VEE_DRV':
                board.RemoveNative(t)
        with self.assertRaisesRegex(ValueError,'no actual copper connection'):
            inspect_pmic_charge_pump_storage(board,c)

    def fixture_with_positive(self):
        import pcbnew as P
        board,c=self.fixture()
        for idx,name in enumerate(['P47_VGH_BASE','P47_VGH_DRV','P47_VGH'],5):
            board.Add(P.NETINFO_ITEM(board,name,idx))
        u810=board.FindFootprintByReference('U810')
        for num,net,x,y in [('34','P47_VGH_BASE',0,10),('36','P47_VGH_DRV',0,14)]:
            p=P.PAD(u810);p.SetNumber(num);p.SetAttribute(P.PAD_ATTRIB_SMD)
            p.SetNet(board.FindNet(net));p.SetSize(P.VECTOR2I(mm(.4),mm(.4)))
            p.SetPosition(P.VECTOR2I(mm(x),mm(y)))
            ls=P.LSET();ls.AddLayer(P.F_Cu);p.SetLayerSet(ls);u810.Add(p)
        def add_part(ref,val,pins):
            fp=P.FOOTPRINT(board);fp.SetReference(ref);fp.SetValue(val)
            fp.SetLayer(P.F_Cu);fp.SetAttributes(P.FP_SMD)
            for num,net,x,y in pins:
                p=P.PAD(fp);p.SetNumber(str(num));p.SetAttribute(P.PAD_ATTRIB_SMD)
                p.SetNet(board.FindNet(net));p.SetSize(P.VECTOR2I(mm(.4),mm(.4)))
                p.SetPosition(P.VECTOR2I(mm(x),mm(y)))
                ls=P.LSET();ls.AddLayer(P.F_Cu);p.SetLayerSet(ls);fp.Add(p)
            board.Add(fp)
        add_part('C807','1u/50V/0805',[('1','P47_VGH_BASE',4,10),('2','GND',4,2)])
        add_part('D803','BAV99',[('1','P47_VGH_BASE',8,10),('2','P47_VGH',8,16)])
        add_part('C808','47n/50V/0805',[('2','P47_VGH_DRV',4,14)])
        add_part('R801','1M/0.1%',[('1','P47_VGH',4,16)])
        def trk(net,ly,x1,y1,x2,y2):
            t=P.PCB_TRACK(board);t.SetNet(board.FindNet(net));t.SetLayer(ly);t.SetWidth(mm(.15))
            t.SetStart(P.VECTOR2I(mm(x1),mm(y1)));t.SetEnd(P.VECTOR2I(mm(x2),mm(y2)));board.Add(t)
        def via(net,x,y):
            v=P.PCB_VIA(board);v.SetNet(board.FindNet(net));v.SetViaType(P.VIATYPE_THROUGH)
            v.SetLayerPair(P.F_Cu,P.B_Cu);v.SetWidth(mm(.4));v.SetDrill(mm(.2))
            v.SetPosition(P.VECTOR2I(mm(x),mm(y)));board.Add(v)
        trk('P47_VGH_BASE',P.F_Cu,0,10,1,10);via('P47_VGH_BASE',1,10)
        trk('P47_VGH_BASE',P.In2_Cu,1,10,3,10);via('P47_VGH_BASE',3,10)
        trk('P47_VGH_BASE',P.F_Cu,3,10,4,10)
        trk('P47_VGH_BASE',P.In2_Cu,3,10,7,10);via('P47_VGH_BASE',7,10)
        trk('P47_VGH_BASE',P.F_Cu,7,10,8,10)
        trk('P47_VGH_DRV',P.F_Cu,0,14,1,14);via('P47_VGH_DRV',1,14)
        trk('P47_VGH_DRV',P.In2_Cu,1,14,3,14);via('P47_VGH_DRV',3,14)
        trk('P47_VGH_DRV',P.F_Cu,3,14,4,14)
        trk('P47_VGH',P.F_Cu,4,16,5,16);via('P47_VGH',5,16)
        trk('P47_VGH',P.B_Cu,5,16,7,16);via('P47_VGH',7,16)
        trk('P47_VGH',P.F_Cu,7,16,8,16)
        c['positive_storage']=dict(
            cap='C807',value='1u/50V/0805',side='F.Cu',power_pin='34',power_net='P47_VGH_BASE',
            diode='D803',diode_pin='1',maximum_total_track_length_mm=12.0,maximum_via_count=3,
            allowed_layers=['F.Cu','In2.Cu'],joint_driver_net='P47_VGH_DRV',driver_pin='36',
            driver_cap='C808',driver_cap_pin='2',maximum_driver_track_length_mm=6.0,
            maximum_driver_via_count=2,joint_vgh_net='P47_VGH',vgh_sense_ref='R801',
            vgh_sense_pin='1',maximum_vgh_track_length_mm=8.0,maximum_vgh_via_count=3)
        return board,c

    def test_positive_charge_pump_storage_passes_and_locks_c807_inner_route(self):
        from build_pico47_single import inspect_pmic_charge_pump_storage
        board,c=self.fixture_with_positive();r=inspect_pmic_charge_pump_storage(board,c)
        self.assertIn('positive_storage',r)
        self.assertEqual(r['positive_storage']['vgh_base']['via_count'],3)
        self.assertEqual(r['positive_storage']['vgh_base']['track_layers'],['F.Cu','In2.Cu'])
        self.assertFalse(r['charge_pump_transient_and_ripple_qualified'])

    def test_positive_storage_bottom_layer_or_excess_length_or_via_is_rejected(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_charge_pump_storage
        board,c=self.fixture_with_positive()
        t=P.PCB_TRACK(board);t.SetNet(board.FindNet('P47_VGH_BASE'));t.SetLayer(P.B_Cu);t.SetWidth(mm(.15))
        t.SetStart(P.VECTOR2I(mm(1),mm(10)));t.SetEnd(P.VECTOR2I(mm(2),mm(10)));board.Add(t)
        with self.assertRaisesRegex(ValueError,'P47_VGH_BASE uses unreviewed copper layers'):
            inspect_pmic_charge_pump_storage(board,c)
        board,c=self.fixture_with_positive();c['positive_storage']['maximum_total_track_length_mm']=5.0
        with self.assertRaisesRegex(ValueError,'P47_VGH_BASE exceeds reviewed total track length budget'):
            inspect_pmic_charge_pump_storage(board,c)
        board,c=self.fixture_with_positive();c['positive_storage']['maximum_via_count']=2
        with self.assertRaisesRegex(ValueError,'P47_VGH_BASE exceeds reviewed via count budget'):
            inspect_pmic_charge_pump_storage(board,c)

    def test_positive_storage_driver_vgh_budget_or_smd_via_clearance_is_rejected(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_charge_pump_storage
        board,c=self.fixture_with_positive();c['positive_storage']['maximum_driver_via_count']=1
        with self.assertRaisesRegex(ValueError,'P47_VGH_DRV exceeds'):
            inspect_pmic_charge_pump_storage(board,c)
        board,c=self.fixture_with_positive();c['positive_storage']['maximum_vgh_track_length_mm']=2.0
        with self.assertRaisesRegex(ValueError,'P47_VGH exceeds'):
            inspect_pmic_charge_pump_storage(board,c)
        board,c=self.fixture_with_positive()
        v=P.PCB_VIA(board);v.SetNet(board.FindNet('P47_VGH_BASE'));v.SetViaType(P.VIATYPE_THROUGH)
        v.SetLayerPair(P.F_Cu,P.B_Cu);v.SetWidth(mm(.4));v.SetDrill(mm(.2))
        v.SetPosition(P.VECTOR2I(mm(.42),mm(10)));board.Add(v)
        with self.assertRaisesRegex(ValueError,'50um SMD pad-edge'):
            inspect_pmic_charge_pump_storage(board,c)

    def fixture_with_output_caps(self):
        import pcbnew as P
        board,c=self.fixture_with_positive()
        def add_part(ref,val,pins):
            fp=P.FOOTPRINT(board);fp.SetReference(ref);fp.SetValue(val)
            fp.SetLayer(P.F_Cu);fp.SetAttributes(P.FP_SMD)
            for num,net,x,y in pins:
                p=P.PAD(fp);p.SetNumber(str(num));p.SetAttribute(P.PAD_ATTRIB_SMD)
                p.SetNet(board.FindNet(net));p.SetSize(P.VECTOR2I(mm(.4),mm(.4)))
                p.SetPosition(P.VECTOR2I(mm(x),mm(y)))
                ls=P.LSET();ls.AddLayer(P.F_Cu);p.SetLayerSet(ls);fp.Add(p)
            board.Add(fp)
        add_part('C812','1u/50V/0805',[('1','P47_VGL',8,5),('2','GND',4,2)])
        add_part('C809','1u/50V/0805',[('1','P47_VGH',7.5,16),('2','GND',4,2)])
        c['output_cap']='C812';c['output_cap_value']='1u/50V/0805'
        c['positive_storage']['output_cap']='C809'
        c['positive_storage']['output_cap_value']='1u/50V/0805'
        return board,c

    def test_output_storage_caps_direct_front_copper_passes(self):
        from build_pico47_single import inspect_pmic_charge_pump_storage
        board,c=self.fixture_with_output_caps();r=inspect_pmic_charge_pump_storage(board,c)
        self.assertEqual(r['output_cap']['cap'],'C812')
        self.assertTrue(r['output_cap']['rectifier_to_output_cap_front_only'])
        self.assertEqual(r['positive_storage']['output_cap']['cap'],'C809')
        self.assertTrue(r['positive_storage']['output_cap']['rectifier_to_output_cap_front_only'])

    def test_output_storage_cap_bottom_detour_or_bad_value_is_rejected(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_charge_pump_storage
        board,c=self.fixture_with_output_caps()
        for t in list(board.GetTracks()):
            if t.GetClass()=='PCB_TRACK' and t.GetNetname()=='P47_VGH' and t.GetLayer()==P.F_Cu and t.GetEnd().x==mm(8):
                t.SetEnd(P.VECTOR2I(mm(7.5),mm(16)))
        v1=P.PCB_VIA(board);v1.SetNet(board.FindNet('P47_VGH'));v1.SetViaType(P.VIATYPE_THROUGH)
        v1.SetLayerPair(P.F_Cu,P.B_Cu);v1.SetWidth(mm(.4));v1.SetDrill(mm(.2))
        v1.SetPosition(P.VECTOR2I(mm(9),mm(16)));board.Add(v1)
        t1=P.PCB_TRACK(board);t1.SetNet(board.FindNet('P47_VGH'));t1.SetLayer(P.F_Cu);t1.SetWidth(mm(.15))
        t1.SetStart(P.VECTOR2I(mm(8),mm(16)));t1.SetEnd(P.VECTOR2I(mm(9),mm(16)));board.Add(t1)
        t2=P.PCB_TRACK(board);t2.SetNet(board.FindNet('P47_VGH'));t2.SetLayer(P.B_Cu);t2.SetWidth(mm(.15))
        t2.SetStart(P.VECTOR2I(mm(7),mm(16)));t2.SetEnd(P.VECTOR2I(mm(9),mm(16)));board.Add(t2)
        c['positive_storage']['maximum_vgh_track_length_mm']=15.0
        c['positive_storage']['maximum_vgh_via_count']=5
        with self.assertRaisesRegex(ValueError,'C809 charge-pump output capacitor requires direct F.Cu connection'):
            inspect_pmic_charge_pump_storage(board,c)
        board,c=self.fixture_with_output_caps()
        board.FindFootprintByReference('C809').SetValue('100n/50V/0402')
        with self.assertRaisesRegex(ValueError,'C809 charge-pump output capacitor value or assembly differs'):
            inspect_pmic_charge_pump_storage(board,c)

    def fixture_with_flying_caps(self):
        import pcbnew as P
        board,c=self.fixture_with_output_caps()
        for idx,name in enumerate(['P47_PUMP_NEG','P47_PUMP_POS'],8):
            board.Add(P.NETINFO_ITEM(board,name,idx))
        def add_pad(ref,num,net,x,y):
            fp=board.FindFootprintByReference(ref)
            p=P.PAD(fp);p.SetNumber(str(num));p.SetAttribute(P.PAD_ATTRIB_SMD)
            p.SetNet(board.FindNet(net));p.SetSize(P.VECTOR2I(mm(.4),mm(.4)))
            p.SetPosition(P.VECTOR2I(mm(x),mm(y)))
            ls=P.LSET();ls.AddLayer(P.F_Cu);p.SetLayerSet(ls);fp.Add(p)
        add_pad('C811','1','P47_PUMP_NEG',4,3)
        add_pad('D804','3','P47_PUMP_NEG',8,3)
        add_pad('C808','1','P47_PUMP_POS',4,13)
        add_pad('D803','3','P47_PUMP_POS',8,13)
        def trk(net,ly,x1,y1,x2,y2):
            t=P.PCB_TRACK(board);t.SetNet(board.FindNet(net));t.SetLayer(ly);t.SetWidth(mm(.15))
            t.SetStart(P.VECTOR2I(mm(x1),mm(y1)));t.SetEnd(P.VECTOR2I(mm(x2),mm(y2)));board.Add(t)
        def via(net,x,y):
            v=P.PCB_VIA(board);v.SetNet(board.FindNet(net));v.SetViaType(P.VIATYPE_THROUGH)
            v.SetLayerPair(P.F_Cu,P.B_Cu);v.SetWidth(mm(.4));v.SetDrill(mm(.2))
            v.SetPosition(P.VECTOR2I(mm(x),mm(y)));board.Add(v)
        trk('P47_PUMP_NEG',P.F_Cu,4,3,5,3);via('P47_PUMP_NEG',5,3)
        trk('P47_PUMP_NEG',P.B_Cu,5,3,7,3);via('P47_PUMP_NEG',7,3)
        trk('P47_PUMP_NEG',P.F_Cu,7,3,8,3)
        trk('P47_PUMP_POS',P.F_Cu,4,13,8,13)
        c.update(driver_allowed_layers=['B.Cu','F.Cu'],flying_cap_value='47n/50V/0805',
                 pump_net='P47_PUMP_NEG',pump_diode_pin='3',
                 maximum_pump_track_length_mm=6.0,maximum_pump_via_count=2,
                 pump_allowed_layers=['B.Cu','F.Cu'])
        c['positive_storage'].update(
            driver_allowed_layers=['F.Cu','In2.Cu'],flying_cap_value='47n/50V/0805',
            pump_net='P47_PUMP_POS',pump_diode_pin='3',
            maximum_pump_track_length_mm=6.0,maximum_pump_via_count=0,
            pump_allowed_layers=['F.Cu'])
        return board,c

    def test_flying_caps_and_pump_nets_pass_and_lock_all_eight_charge_pump_nets(self):
        from build_pico47_single import inspect_pmic_charge_pump_storage
        board,c=self.fixture_with_flying_caps();r=inspect_pmic_charge_pump_storage(board,c)
        self.assertEqual(r['flying_cap']['cap'],'C811')
        self.assertEqual(r['flying_cap']['pump_net'],'P47_PUMP_NEG')
        self.assertEqual(r['flying_cap']['pump']['via_count'],2)
        self.assertEqual(r['flying_cap']['pump']['track_layers'],['B.Cu','F.Cu'])
        self.assertEqual(r['positive_storage']['flying_cap']['cap'],'C808')
        self.assertEqual(r['positive_storage']['flying_cap']['pump_net'],'P47_PUMP_POS')
        self.assertEqual(r['positive_storage']['flying_cap']['pump']['via_count'],0)
        self.assertEqual(r['positive_storage']['flying_cap']['pump']['track_layers'],['F.Cu'])

    def test_flying_cap_pump_layer_length_via_or_pad_clearance_is_rejected(self):
        import pcbnew as P
        from build_pico47_single import inspect_pmic_charge_pump_storage
        board,c=self.fixture_with_flying_caps()
        t=P.PCB_TRACK(board);t.SetNet(board.FindNet('P47_PUMP_POS'));t.SetLayer(P.B_Cu);t.SetWidth(mm(.15))
        t.SetStart(P.VECTOR2I(mm(5),mm(13)));t.SetEnd(P.VECTOR2I(mm(6),mm(13)));board.Add(t)
        with self.assertRaisesRegex(ValueError,'P47_PUMP_POS uses unreviewed copper layers'):
            inspect_pmic_charge_pump_storage(board,c)
        board,c=self.fixture_with_flying_caps();c['positive_storage']['maximum_pump_track_length_mm']=2.0
        with self.assertRaisesRegex(ValueError,'P47_PUMP_POS exceeds reviewed total track length budget'):
            inspect_pmic_charge_pump_storage(board,c)
        board,c=self.fixture_with_flying_caps();c['maximum_pump_via_count']=1
        with self.assertRaisesRegex(ValueError,'P47_PUMP_NEG exceeds reviewed via count budget'):
            inspect_pmic_charge_pump_storage(board,c)
        board,c=self.fixture_with_flying_caps()
        v=P.PCB_VIA(board);v.SetNet(board.FindNet('P47_PUMP_NEG'));v.SetViaType(P.VIATYPE_THROUGH)
        v.SetLayerPair(P.F_Cu,P.B_Cu);v.SetWidth(mm(.4));v.SetDrill(mm(.2))
        v.SetPosition(P.VECTOR2I(mm(4.42),mm(3)));board.Add(v)
        with self.assertRaisesRegex(ValueError,'50um SMD pad-edge'):
            inspect_pmic_charge_pump_storage(board,c)


if __name__=='__main__':
    unittest.main()
