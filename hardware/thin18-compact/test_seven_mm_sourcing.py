"""Reject wrong exact parts and false supply closure; exercise safe metadata edits."""
import copy, json, unittest
from seven_mm_sourcing import CONTRACT, validate, indexed, properties, set_properties, strip_metadata, patch_blocks, desired

class ContractTests(unittest.TestCase):
    def setUp(self):self.plan=json.loads(CONTRACT.read_text())
    def change_ref(self,ref,key,value):
        p=copy.deepcopy(self.plan);indexed(p)[ref][key]=value
        with self.assertRaises((ValueError,KeyError,TypeError)):validate(p)
    def test_complete_scope(self):self.assertEqual(len(validate(self.plan)),20)
    def test_accounting(self):
        rows=validate(self.plan)
        self.assertEqual(sum(bool(r['lcsc']) for r in rows.values()),12)
        self.assertEqual(sum(r['assembly_stage']=='SMT' and not r['lcsc'] for r in rows.values()),7)
    def test_resistor_22ohm_code_rejected(self):self.change_ref('R540','lcsc','C140177')
    def test_old_unverified_resistor_string_rejected(self):self.change_ref('R540','mpn','RC-02K0000FT')
    def test_mpn_replacement_must_be_explicit(self):self.change_ref('R540','change_kind','EXACT_CODE')
    def test_wrong_crystal_15pf_code(self):self.change_ref('Y501','lcsc','C9010')
    def test_wrong_crystal_15pf_mpn(self):self.change_ref('Y501','mpn','XL2EL89CPI-111YLC-40M')
    def test_wrong_crystal_load(self):
        spec=dict(indexed(self.plan)['Y501']['electrical_spec']);spec['load_capacitance_pf']=15
        self.change_ref('Y501','electrical_spec',spec)
    def test_wrong_crystal_land(self):
        spec=copy.deepcopy(indexed(self.plan)['Y501']['electrical_spec']);spec['land_size_mm']=[1.3,1.0]
        self.change_ref('Y501','electrical_spec',spec)
    def test_wrong_crystal_ground_pins(self):
        spec=copy.deepcopy(indexed(self.plan)['Y501']['electrical_spec']);spec['ground_pins']=['1','3']
        self.change_ref('Y501','electrical_spec',spec)
    def test_unreviewed_crystal_drawing(self):self.change_ref('Y501','drawing_reviewed',False)
    def test_supplier_page_missing(self):self.change_ref('Y501','source_page_sha256','')
    def test_foreign_brand(self):self.change_ref('C530','manufacturer','Samsung')
    def test_rf_capacitance(self):
        spec=dict(indexed(self.plan)['C530']['electrical_spec']);spec['capacitance_pf']=8
        self.change_ref('C530','electrical_spec',spec)
    def test_wrong_inductor_size(self):self.change_ref('L507','package','0402')
    def test_wrong_inductor_code(self):self.change_ref('L507','lcsc','C43365')
    def test_load_switch_without_qod(self):self.change_ref('U402','mpn','SGM2578SYG/TR')
    def test_wrong_default_output_variant(self):self.change_ref('U902','mpn','SGM62125BXG/TR')
    def test_twentyfour_pin_frontlight(self):self.change_ref('U905','mpn','SGM37601YTWY24G/TR')
    def test_usb_suffix_substitution(self):self.change_ref('J201','mpn','U22401-05')
    def test_fake_new_jlc_code(self):self.change_ref('U902','lcsc','C999999999')
    def test_registration_is_not_acceptance(self):self.change_ref('U905','order_supply_accepted',True)
    def test_quote_not_received(self):self.change_ref('J201','quote_received',True)
    def test_cell_cannot_reflow(self):self.change_ref('BT301','reflow_allowed',True)
    def test_cell_not_smt(self):self.change_ref('BT301','assembly_stage','SMT')
    def test_cell_not_omitted(self):self.change_ref('BT301','required_in_system_bom',False)
    def test_bare_cell_code_not_assembly(self):self.change_ref('BT301','lcsc','C123')
    def test_manual_tab_drawing_not_accepted(self):self.change_ref('BT301','assembly_drawing_accepted',True)
    def test_fake_stock(self):self.change_ref('C530','stock_reserved',True)
    def test_missing_reference(self):
        self.plan['catalog'][0]['refs']=[]
        with self.assertRaises(ValueError):validate(self.plan)
    def test_duplicate_reference(self):
        self.plan['catalog'][0]['refs'].append('Y501')
        with self.assertRaises(ValueError):validate(self.plan)
    def test_counts_not_hiding_pending(self):
        self.plan['summary']['pending_jlc_registration_references']=0
        with self.assertRaises(ValueError):validate(self.plan)
    def test_release_cannot_be_set(self):
        self.plan['manufacturing_release']=True
        with self.assertRaises(ValueError):validate(self.plan)
    def test_wrong_product_source(self):
        self.plan['product_source_sha256']='0'*64
        with self.assertRaises(ValueError):validate(self.plan)

class MetadataTests(unittest.TestCase):
    def test_compact_properties(self):
        s='(symbol(property "MPN" "OLD")(pin passive line(at 0 0 0)))'
        p=set_properties(s,{'MPN':'NEW','LCSC':'C1'})
        self.assertEqual(properties(p),{'MPN':'NEW','LCSC':'C1'})
        self.assertEqual(strip_metadata(s),strip_metadata(p))
    def test_quoted_escape(self):
        p=set_properties('(symbol(property "MPN" "OLD"))',{'MPN':'a"b\\c'})
        self.assertEqual(properties(p)['MPN'],'a"b\\c')
    def test_pad_function_preserved(self):
        s='(footprint "F" (property "Reference" "U1")(pad "57" smd rect(property pad_prop_heatsink)(net "GND")))'
        p=set_properties(s,{'LCSC':'C1'})
        self.assertIn('(property pad_prop_heatsink)',p)
        self.assertEqual(strip_metadata(s),strip_metadata(p))
    def test_bga_flag_not_metadata(self):
        s='(footprint "F"(pad "1" smd circle(property pad_prop_bga)))'
        self.assertEqual(properties(s),{})
        self.assertNotEqual(strip_metadata(s),strip_metadata(s.replace('pad_prop_bga','pad_prop_heatsink')))
    def test_reference_cannot_change(self):
        with self.assertRaises(ValueError):set_properties('(symbol)',{'Reference':'U2'})
    def test_value_cannot_change(self):
        with self.assertRaises(ValueError):set_properties('(symbol)',{'Value':'22R'})
    def test_net_edit_detected(self):
        s='(pad "1" smd rect(net "A")(property pad_prop_bga))'
        self.assertNotEqual(strip_metadata(s),strip_metadata(s.replace('"A"','"B"')))
    def test_dnp_edit_detected(self):
        s='(symbol(dnp no)(property "MPN" "A"))'
        self.assertNotEqual(strip_metadata(s),strip_metadata(s.replace('dnp no','dnp yes')))
    def test_geometry_edit_detected(self):
        self.assertNotEqual(strip_metadata('(pad(size 1 1))'),strip_metadata('(pad(size 1 2))'))
    def test_string_spaces_preserved(self):
        self.assertNotEqual(strip_metadata('(value "A B")'),strip_metadata('(value "A  B")'))
    def test_duplicate_field_rejected(self):
        with self.assertRaises(ValueError):properties('(f(property "LCSC" "C1")(property "LCSC" "C2"))')
    def test_pending_code_stays_blank(self):
        p=json.loads(CONTRACT.read_text());r=indexed(p)['U902'];self.assertEqual(desired(r)['LCSC'],'')
        self.assertEqual(desired(r)['PandaSupplyStatus'],'JLC_REGISTRATION_AND_RECEIPT_PENDING')
    def test_old_instance_mpn_required(self):
        p=json.loads(CONTRACT.read_text());r=indexed(p)['Y501'];s='(footprint "F"(property "Reference" "Y501")(property "MPN" "BAD"))'
        with self.assertRaises(ValueError):patch_blocks(s,'(footprint',{'Y501':r})

if __name__=='__main__':unittest.main(verbosity=2)
