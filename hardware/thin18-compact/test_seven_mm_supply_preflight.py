"""No fabricated registrations/receipts; synthetic tests never enter order data."""
import copy,json,unittest
from seven_mm_supply_preflight import CONTRACT,validate,required_quantities,warehouse_usable

class RequestTests(unittest.TestCase):
    def setUp(self):self.p=json.loads(CONTRACT.read_text())
    def changed(self,path,value):
        data=copy.deepcopy(self.p);node=data
        for key in path[:-1]:node=node[key]
        node[path[-1]]=value
        with self.assertRaises(ValueError):validate(data)
    def test_valid_technical_template(self):self.assertTrue(validate(self.p))
    def test_no_default_boards(self):
        self.assertTrue(all(r['requested_total'] is None and r['population_qty'] is None for r in required_quantities(self.p)))
    def test_missing_attrition_is_not_zero(self):
        rows=required_quantities(self.p,5,5)
        self.assertEqual([r['population_qty'] for r in rows],[20,5,5,5]);self.assertTrue(all(r['requested_total'] is None for r in rows))
    def test_explicit_attrition(self):
        rows=required_quantities(self.p,5,5,{r['mpn']:2 for r in self.p['request_lines']})
        self.assertEqual([r['requested_total'] for r in rows],[22,7,7,7])
    def test_bad_quantities(self):
        for q in [True,False,0,-1,1.5,'5',float('nan')]:
            with self.subTest(q=q), self.assertRaises(ValueError):required_quantities(self.p,q,5)
    def test_bad_attrition(self):
        for v in [True,-1,2.5,'3']:
            with self.subTest(v=v),self.assertRaises(ValueError):required_quantities(self.p,5,5,{'U22401-17':v})
    def test_unknown_attrition_part(self):
        with self.assertRaises(ValueError):required_quantities(self.p,5,5,{'U22401-23':2})
    def test_missing_smt_ref(self):self.changed(['request_lines',0,'refs'],['U402'])
    def test_qod_variant(self):self.changed(['request_lines',0,'mpn'],'SGM2578SYG/TR')
    def test_converter_variant(self):self.changed(['request_lines',1,'mpn'],'SGM62125BXG/TR')
    def test_led_package(self):self.changed(['request_lines',2,'package'],'TQFN-4x4-24L')
    def test_msl_wrong(self):self.changed(['request_lines',2,'moisture_sensitivity_level'],1)
    def test_boolean_msl(self):self.changed(['request_lines',0,'moisture_sensitivity_level'],True)
    def test_fabricated_code(self):self.changed(['request_lines',3,'catalog_code'],'C49325733')
    def test_fabricated_registration(self):self.changed(['request_lines',0,'registration_id'],'APPROVED')
    def test_fake_received(self):self.changed(['request_lines',0,'received'],True)
    def test_fake_acceptance(self):self.changed(['request_lines',0,'accepted'],True)
    def test_claimed_sent(self):self.changed(['supplier_inquiries_sent'],True)
    def test_claimed_order(self):self.changed(['orders_submitted'],True)
    def test_primary_reflow(self):self.changed(['rtc_assembly_request','reflow_allowed'],True)
    def test_bare_solder(self):self.changed(['rtc_assembly_request','bare_cell_direct_solder_allowed'],True)
    def test_invented_cell_sku(self):self.changed(['rtc_assembly_request','factory_assembly_part_number'],'CR1216-FAKE')
    def test_hidden_underbody_pad(self):self.changed(['rtc_assembly_request','existing_pads_lie_under_cell_body'],False)
    def test_polarity(self):self.changed(['rtc_assembly_request','positive_native_pad','net'],'GND')
    def test_cell_claimed_maximum(self):self.changed(['rtc_assembly_request','budget_is_not_supplier_maximum'],False)
    def test_cell_safety_claim(self):self.changed(['rtc_assembly_request','reverse_charge_and_retention_qualified'],True)
    def test_wrong_thickness(self):self.changed(['rejected_or_unapproved_catalog_candidates',0,'candidate_mid_mount_mm'],.8)
    def test_unreviewed_usb_approval(self):self.changed(['rejected_or_unapproved_catalog_candidates',0,'decision'],'APPROVED')
    def test_unknown_digest(self):self.changed(['catalog_recheck','evidence_sha256'],'g'*64)
    def test_no_positive_control(self):self.changed(['catalog_recheck','positive_control','matched_code'],'C999')

class WarehouseTests(unittest.TestCase):
    def test_intermediate_states_are_not_inventory(self):
        for state in ['Reviewing','Awaiting Confirmation','Awaiting Payment','Shipped','Received','Checked','Cancelled']:
            with self.subTest(state=state):self.assertFalse(warehouse_usable(state,100,5,exact_identity_reviewed=True,document_reviewed=True))
    def test_no_document_review(self):self.assertFalse(warehouse_usable('In Warehouse',100,5,exact_identity_reviewed=True))
    def test_no_identity_review(self):self.assertFalse(warehouse_usable('In Warehouse',100,5,document_reviewed=True))
    def test_insufficient(self):self.assertFalse(warehouse_usable('In Warehouse',4,5,exact_identity_reviewed=True,document_reviewed=True))
    def test_consistent_input_not_authentication(self):self.assertTrue(warehouse_usable('In Warehouse',5,5,exact_identity_reviewed=True,document_reviewed=True))
    def test_unknown_state(self):
        with self.assertRaises(ValueError):warehouse_usable('APPROVED',5,5)
    def test_bad_counts(self):
        for a,r in [(True,5),(-1,5),(1.5,1),(5,True),(5,0)]:
            with self.subTest(a=a,r=r),self.assertRaises(ValueError):warehouse_usable('In Warehouse',a,r)
    def test_string_review_not_truthy(self):
        with self.assertRaises(ValueError):warehouse_usable('In Warehouse',5,5,exact_identity_reviewed='false')

if __name__=='__main__':unittest.main(verbosity=2)
