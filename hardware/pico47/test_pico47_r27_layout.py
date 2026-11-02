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


if __name__=='__main__':
    unittest.main()
