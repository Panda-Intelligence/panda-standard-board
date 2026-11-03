"""2026-11-03 Codex：0603/3950错件不能借0402焊盘或相同10k标称值通过。"""
import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('pcbnew'),'KiCad Python required')
class TemperatureSenseTests(unittest.TestCase):
    def fixture(self):
        import wx
        self.app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        b=P.BOARD();b.SetCopperLayerCount(4);nets={}
        for index,name in enumerate(['P47_TS','P47_VREF','GND'],1):
            n=P.NETINFO_ITEM(b,name,index);b.Add(n);nets[name]=n
        def part(ref,value,x,y,pins,mpn=''):
            f=P.FOOTPRINT(b);f.SetReference(ref);f.SetValue(value);f.SetAttributes(P.FP_SMD);f.SetPosition(P.VECTOR2I(round(x*1e6),round(y*1e6)))
            for name,text in [('Manufacturer','FH (Fenghua Advanced)'),('MPN',mpn)]:
                field=P.PCB_FIELD(f,P.FIELD_T_USER);field.SetName(name);field.SetText(text);f.Add(field)
            for num,net,dx in pins:
                p=P.PAD(f);p.SetNumber(num);p.SetNet(nets[net]);p.SetAttribute(P.PAD_ATTRIB_SMD);p.SetSize(P.VECTOR2I(540000,640000));p.SetPosition(P.VECTOR2I(round((x+dx)*1e6),round(y*1e6)));layers=P.LSET();layers.AddLayer(P.F_Cu);p.SetLayerSet(layers);f.Add(p)
            b.Add(f);return f
        device=part('U810','SY7636ARMC',0,0,[('1','P47_VREF',0),('47','P47_TS',1),('48','GND',2)])
        ntc=part('TH801','10k NTC / CURVE TO QUALIFY',4,3,[('1','P47_TS',-.51),('2','GND',.51)],'CMKD103F3380HANT')
        up=part('R805','7.5k/1%',2,1,[('1','P47_VREF',-.51),('2','P47_TS',.51)],'RC-02K7501FT')
        parallel=part('R806','36k/1%',2,4,[('1','P47_TS',-.51),('2','GND',.51)],'RC-02K3602FT')
        groups=[frozenset(p.m_Uuid.AsString() for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()==name) for name in nets]
        c=dict(device='U810',thermistor='TH801',manufacturer='FH (Fenghua Advanced)',mpn='CMKD103F3380HANT',
               package='0402',value='10k NTC / CURVE TO QUALIFY',nominal_r25_ohm=10000,nominal_beta_25_50_k=3380,
               r25_tolerance_percent=1,beta_tolerance_percent=3,
               pad_geometry_nm=[['1',-510000,0,540000,640000],['2',510000,0,540000,640000]],
               pullup=dict(ref='R805',value='7.5k/1%',mpn='RC-02K7501FT'),
               parallel=dict(ref='R806',value='36k/1%',mpn='RC-02K3602FT'))
        return b,c,groups,ntc,up,parallel

    def test_correct_catalog_identity_still_leaves_full_curve_and_accuracy_unqualified(self):
        from build_pico47_single import inspect_temperature_sense
        b,c,g,_,_,_=self.fixture();r=inspect_temperature_sense(b,c,g)
        self.assertEqual(r['nominal_beta_25_50_k'],3380)
        self.assertEqual(r['catalogue_package'],'0402')
        self.assertFalse(r['exact_rt_curve_qualified'])
        self.assertFalse(r['temperature_accuracy_qualified'])
        self.assertFalse(r['supplier_receipt_accepted'])

    def test_same_10k_but_0603_3950_MPN_is_rejected(self):
        from build_pico47_single import inspect_temperature_sense
        b,c,g,f,_,_=self.fixture();next(x for x in f.GetFields() if x.GetName()=='MPN').SetText('CMFA103F3950HANT')
        with self.assertRaisesRegex(ValueError,'thermistor identity'):
            inspect_temperature_sense(b,c,g)

    def test_wrong_land_or_linearization_value_is_rejected(self):
        from build_pico47_single import inspect_temperature_sense
        b,c,g,f,_,parallel=self.fixture();p=next(iter(f.Pads()));p.SetSize(type(p.GetSize())(800000,950000))
        with self.assertRaisesRegex(ValueError,'0402 land'):
            inspect_temperature_sense(b,c,g)
        b,c,g,_,_,parallel=self.fixture();parallel.SetValue('10k/1%')
        with self.assertRaisesRegex(ValueError,'linearization identity'):
            inspect_temperature_sense(b,c,g)

    def test_same_GND_label_without_reference_connection_is_rejected(self):
        from build_pico47_single import inspect_temperature_sense
        b,c,g,f,_,_=self.fixture();pad=next(p for p in f.Pads() if p.GetNumber()=='2');uid=pad.m_Uuid.AsString();g=[frozenset(u for u in row if u!=uid) for row in g]+[frozenset({uid})]
        with self.assertRaisesRegex(ValueError,'temperature connection'):
            inspect_temperature_sense(b,c,g)

    def test_relabeling_the_contract_cannot_approve_the_old_0603_3950_part(self):
        from build_pico47_single import inspect_temperature_sense
        b,c,g,_,_,_=self.fixture();c['mpn']='CMFA103F3950HANT';c['nominal_beta_25_50_k']=3950
        with self.assertRaisesRegex(ValueError,'temperature part contract'):
            inspect_temperature_sense(b,c,g)


@unittest.skipUnless(importlib.util.find_spec('pcbnew'),'KiCad Python required')
class FootprintFieldReplayTests(unittest.TestCase):
    def fixture(self):
        import wx
        self.app=wx.GetApp() or wx.App(False)
        import pcbnew as P
        b=P.BOARD();b.SetCopperLayerCount(4);f=P.FOOTPRINT(b);f.SetReference('TH801')
        field=P.PCB_FIELD(f,P.FIELD_T_USER);field.SetName('MPN');field.SetText('old-part');f.Add(field);b.Add(f)
        delta=dict(footprint_poses={},removed_uuids=[],updated_copper=[],added_tracks=[],added_vias=[],added_zones=[],
                   footprint_field_edits=[dict(ref='TH801',native_uuid=f.m_Uuid.AsString(),field='MPN',before='old-part',after='new-part')])
        return b,f,field,delta

    def test_one_field_replay_preserves_native_footprint_identity(self):
        from r25_router.apply_single_r27_layout_eco import apply_layout_eco
        b,f,field,d=self.fixture();uid=f.m_Uuid.AsString();apply_layout_eco(b,d)
        self.assertEqual(field.GetText(),'new-part');self.assertEqual(f.m_Uuid.AsString(),uid)

    def test_wrong_field_predecessor_or_uuid_rejects_before_any_field_is_changed(self):
        from r25_router.apply_single_r27_layout_eco import apply_layout_eco
        for key,value in [('before','different'),('native_uuid','wrong')]:
            b,_,field,d=self.fixture();d['footprint_field_edits'][0][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'field predecessor'):
                apply_layout_eco(b,d)
            self.assertEqual(field.GetText(),'old-part')

    def test_invalid_later_edit_cannot_partially_apply_the_first_edit(self):
        from r25_router.apply_single_r27_layout_eco import apply_layout_eco
        b,_,field,d=self.fixture();second=dict(d['footprint_field_edits'][0]);second['ref']='ABSENT';d['footprint_field_edits'].append(second)
        with self.assertRaisesRegex(ValueError,'field predecessor'):
            apply_layout_eco(b,d)
        self.assertEqual(field.GetText(),'old-part')


if __name__=='__main__':
    unittest.main()
