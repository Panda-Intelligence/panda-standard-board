from copy import deepcopy
import unittest
from seven_mm_process_rules import validate_rule_change,EXPECTED_RULE_CHANGES
from verify_seven_mm_quality_catalog import validate_identity

class Rules(unittest.TestCase):
    def setUp(self):
        self.a={'board':{'design_settings':{'rules':{'min_copper_edge_clearance':.15,'min_track_width':.15,'min_hole_to_hole':.25},'rule_severities':{'clearance':'error'},'drc_exclusions':[]}},'erc':{'pin_conflict':'error'},'net_settings':{'classes':[{'clearance':.15}]}}
        self.b=deepcopy(self.a);self.b['board']['design_settings']['rules']['min_copper_edge_clearance']=.2
    def check(self):return validate_rule_change(self.a,self.b,EXPECTED_RULE_CHANGES)
    def test_exact_stricter_edge(self):self.assertTrue(self.check())
    def test_edge_relaxed(self):
        self.b['board']['design_settings']['rules']['min_copper_edge_clearance']=.1
        with self.assertRaises(ValueError):self.check()
    def test_edge_not_changed(self):
        with self.assertRaises(ValueError):validate_rule_change(self.a,self.a,EXPECTED_RULE_CHANGES)
    def test_narrower_track(self):
        self.b['board']['design_settings']['rules']['min_track_width']=.1
        with self.assertRaises(ValueError):self.check()
    def test_hole_relaxation(self):
        self.b['board']['design_settings']['rules']['min_hole_to_hole']=.1
        with self.assertRaises(ValueError):self.check()
    def test_added_exclusion(self):
        self.b['board']['design_settings']['drc_exclusions'].append('hidden')
        with self.assertRaises(ValueError):self.check()
    def test_silenced_severity(self):
        self.b['board']['design_settings']['rule_severities']['clearance']='ignore'
        with self.assertRaises(ValueError):self.check()
    def test_erc_relaxation(self):
        self.b['erc']['pin_conflict']='ignore'
        with self.assertRaises(ValueError):self.check()
    def test_netclass_relaxation(self):
        self.b['net_settings']['classes'][0]['clearance']=.1
        with self.assertRaises(ValueError):self.check()
    def test_missing_declared_change(self):
        with self.assertRaises(ValueError):validate_rule_change(self.a,self.b,{})
    def test_undeclared_source_minimum(self):
        self.a['board']['design_settings']['rules']['min_copper_edge_clearance']=.1
        with self.assertRaises(ValueError):self.check()

class Identities(unittest.TestCase):
    def setUp(self):self.expected={'manufacturer':'Espressif','mpn':'ESP32-S3R8','code':'C2913194'};self.fields={'Manufacturer':'Espressif','MPN':'ESP32-S3R8','LCSC':'C2913194'}
    def test_exact(self):self.assertTrue(validate_identity(self.fields,self.expected))
    def test_other_variant(self):
        self.fields['MPN']='ESP32-S3FN8'
        with self.assertRaises(ValueError):validate_identity(self.fields,self.expected)
    def test_other_catalog_code(self):
        self.fields['LCSC']='C2913202'
        with self.assertRaises(ValueError):validate_identity(self.fields,self.expected)
    def test_unspecified_manufacturer(self):
        self.fields['Manufacturer']='JLCPCB Assembly'
        with self.assertRaises(ValueError):validate_identity(self.fields,self.expected)
    def test_missing_code(self):
        del self.fields['LCSC']
        with self.assertRaises(ValueError):validate_identity(self.fields,self.expected)
if __name__=='__main__':unittest.main(verbosity=2)
