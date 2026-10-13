"""Keep board-specific native margins and source bindings explicit."""
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from pico47_native_routing_limits import FIELDS, parse_bound_routing_limits, read_bound_routing_limits


def project(edge=.2):
    rules={name:.25 for name in FIELDS}
    rules.update(min_copper_edge_clearance=edge,min_track_width=.15,
                 min_via_diameter=.4,min_through_hole_diameter=.2,min_via_annular_width=.1)
    return {'board':{'design_settings':{'rules':rules}}}


def bound(data):
    raw=json.dumps(data).encode()
    return raw,hashlib.sha256(raw).hexdigest()


class NativeRoutingLimits(unittest.TestCase):
    def test_board_specific_edge_margins_not_replaced_by_shared_default(self):
        core=parse_bound_routing_limits(*bound(project(.2)))
        display=parse_bound_routing_limits(*bound(project(.5)))
        self.assertEqual(core['global_minima_mm']['min_copper_edge_clearance'],.2)
        self.assertEqual(display['global_minima_mm']['min_copper_edge_clearance'],.5)

    def test_all_requested_native_minima_are_reported(self):
        self.assertEqual(set(parse_bound_routing_limits(*bound(project()))['global_minima_mm']),set(FIELDS))

    def test_mutated_project_rejected_with_old_hash(self):
        raw,sha=bound(project(.5))
        changed,_=bound(project(.2))
        with self.assertRaisesRegex(ValueError,'source binding'):parse_bound_routing_limits(changed,sha)

    def test_missing_rule_not_a_default_zero(self):
        for key in FIELDS:
            data=project();del data['board']['design_settings']['rules'][key]
            with self.assertRaises(ValueError):parse_bound_routing_limits(*bound(data))

    def test_invalid_numeric_rules_rejected(self):
        for value in (True,'0.2',None,0,-.1,math.inf,math.nan):
            data=project();data['board']['design_settings']['rules']['min_copper_edge_clearance']=value
            with self.assertRaises(ValueError):parse_bound_routing_limits(*bound(data))

    def test_missing_native_structure_rejected(self):
        for data in ({}, {'board':None}, {'board':{'design_settings':{'rules':[]}}}):
            with self.assertRaises(ValueError):parse_bound_routing_limits(*bound(data))

    def test_malformed_exact_json_rejected(self):
        raw=b'{malformed'
        with self.assertRaises(ValueError):parse_bound_routing_limits(raw,hashlib.sha256(raw).hexdigest())

    def test_unbound_or_invalid_digest_rejected(self):
        raw,_=bound(project())
        for digest in (None,'',True,'f'*63,'G'*64):
            with self.assertRaises(ValueError):parse_bound_routing_limits(raw,digest)

    def test_text_not_substituted_for_exact_bytes(self):
        raw,sha=bound(project())
        with self.assertRaises(ValueError):parse_bound_routing_limits(raw.decode(),sha)

    def test_read_does_not_modify_native_project(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'Core.kicad_pro';raw,sha=bound(project());p.write_bytes(raw)
            result=read_bound_routing_limits(p,sha)
            self.assertEqual(p.read_bytes(),raw)
            self.assertEqual(result['native_project_sha256'],sha)

    def test_global_rules_do_not_claim_effective_rules_or_qualification(self):
        result=parse_bound_routing_limits(*bound(project()))
        self.assertTrue(result['native_drc_and_complete_ground_validation_required'])
        self.assertIn('global_minima_only',result['scope'])
        self.assertNotIn('manufacturing_release',result)

    def test_unrelated_project_settings_still_part_of_hash_binding(self):
        data=project();raw,sha=bound(data);data['unrelated_setting']='changed'
        changed,_=bound(data)
        with self.assertRaises(ValueError):parse_bound_routing_limits(changed,sha)

if __name__=='__main__':unittest.main(verbosity=2)
