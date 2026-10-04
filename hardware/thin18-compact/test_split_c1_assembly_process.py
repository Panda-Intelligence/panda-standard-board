#!/usr/bin/env python3
"""Synthetic geometry/report guards; no supplier or physical test data is written."""
import copy
import math
import unittest
from unittest.mock import patch
import audit_split_c1_assembly_process as audit

SQUARE = [[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]]


class GeometryTests(unittest.TestCase):
    def test_polygon_identity_ignores_vertex_start_and_winding(self):
        expected=audit.polygon_identity([SQUARE])
        self.assertEqual(expected,audit.polygon_identity([SQUARE[2:]+SQUARE[:2]]))
        self.assertEqual(expected,audit.polygon_identity([list(reversed(SQUARE))]))
    def test_polygon_identity_tracks_shape_not_runtime_uuid(self):
        shifted=[[x+5,y] for x,y in SQUARE]
        self.assertNotEqual(audit.polygon_identity([SQUARE]),audit.polygon_identity([shifted]))
        self.assertEqual(audit.polygon_identity([SQUARE,shifted]),audit.polygon_identity([shifted,SQUARE]))
    def test_inside_and_boundary(self):
        for point in [[0,0],[1,0],[-1,-1]]:
            self.assertEqual(audit.point_to_polygon(point,SQUARE),0)
    def test_orientation_does_not_change_shape(self):
        self.assertEqual(audit.point_to_polygon([2,0],SQUARE),1)
        self.assertEqual(audit.point_to_polygon([2,0],list(reversed(SQUARE))),1)
    def test_diagonal_distance(self):
        self.assertAlmostEqual(audit.point_to_polygon([2,2],SQUARE),math.sqrt(2))
    def test_bbox_false_positive_is_rejected(self):
        triangle = [[0,0],[2,0],[0,2]]
        self.assertIsNone(audit.hole_overlap([1.8,1.8],.2,[triangle]))
    def test_concave_notch_is_not_copper(self):
        polygon = [[0,0],[3,0],[3,3],[2,3],[2,1],[1,1],[1,3],[0,3]]
        self.assertIsNone(audit.hole_overlap([1.5,2],.2,[polygon]))
    def test_center_in_land(self):
        self.assertEqual(audit.hole_overlap([0,0],.2,[SQUARE])['classification'],'center_in_land')
    def test_hole_edge_overlap(self):
        self.assertEqual(audit.hole_overlap([1.05,0],.2,[SQUARE])['classification'],'hole_crosses_land_edge')
    def test_render_tolerance_flag_is_explicit(self):
        self.assertEqual(audit.hole_overlap([1.1005,0],.2,[SQUARE])['classification'],'within_polygon_render_tolerance')
        self.assertIsNone(audit.hole_overlap([1.102,0],.2,[SQUARE]))
    def test_annulus_only_is_not_drill_overlap(self):
        self.assertIsNone(audit.hole_overlap([1.2,0],.2,[SQUARE]))
    def test_disconnected_pad_polygons(self):
        shifted = [[x+5,y] for x,y in SQUARE]
        self.assertEqual(audit.hole_overlap([5,0],.2,[SQUARE,shifted])['classification'],'center_in_land')
    def test_nonfinite_and_bad_sizes_rejected(self):
        for size in [0,-1,math.inf,math.nan]:
            with self.subTest(size=size),self.assertRaises(ValueError):audit.hole_overlap([0,0],size,[SQUARE])
        for point in [[math.nan,0],[math.inf,0]]:
            with self.subTest(point=point),self.assertRaises(ValueError):audit.point_to_polygon(point,SQUARE)
    def test_no_polygon_rejected(self):
        with self.assertRaises(ValueError):audit.hole_overlap([0,0],.2,[])
        with self.assertRaises(ValueError):audit.point_to_polygon([0,0],[[0,0],[1,0]])
    def test_collinear_polygon_rejected(self):
        with self.assertRaises(ValueError):audit.point_to_polygon([0,0],[[0,0],[1,0],[2,0]])


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.report = {'schema':'panda-split-c1-assembly-process-v1','inputs':{},'policy':{'core_via_treatment':'Epoxy Filled & Capped','cam_accepted':False,'stencil_accepted':False,'physical_qualification_passed':False},'boards':{},
                       'native_cad_modified':False,'physical_qualification_passed':False,'manufacturing_release':False}
        for board in ['Core-C1','Display-C1']:
            entry={'path':board+'.kicad_pcb','sha256':'fixture'}
            self.report['inputs'][board+'/pcb']=entry
            self.report['boards'][board]={'pcb':entry,'via_inventory':[],'via_count':0,'land_overlap_hole_count':0,
                'land_overlap_contacts':[],'required_via_treatment':'NO_IN_PAD_FILL_REQUIRED_BY_THIS_SCREEN',
                'cam_accepted':False,'stencil_accepted':False,'assembly_process_qualified':False}
        self.via={'uuid':'v1','center_mm':[1.,2.],'net':'GND','drill_mm':.2}
        self.hit={'via_uuid':'v1','pad_shape_sha256':'p1','side':'F.Cu','center_mm':[1.,2.],'net':'GND','drill_mm':.2,
                  'ref':'U1','pad':'1','via_copper_diameter_mm':.4,'classification':'center_in_land'}
        self.core=self.report['boards']['Core-C1'];self.core.update(via_inventory=[self.via],via_count=1,
            land_overlap_contacts=[self.hit],land_overlap_hole_count=1,required_via_treatment='EPOXY_FILLED_AND_CAPPED')
        self.hash_patch=patch.object(audit,'sha',return_value='fixture');self.hash_patch.start();self.addCleanup(self.hash_patch.stop)
        self.contract_patch=patch.object(audit,'load_contract',return_value={'assembly_process':{'core_via_treatment':'Epoxy Filled & Capped','cam_accepted':False,'stencil_accepted':False,'physical_qualification_passed':False}});self.contract_patch.start();self.addCleanup(self.contract_patch.stop)
    def test_valid_synthetic_record(self):audit.verify_fresh(self.report)
    def test_release_claims_rejected(self):
        for flag in ['native_cad_modified','physical_qualification_passed','manufacturing_release']:
            bad=copy.deepcopy(self.report);bad[flag]=True
            with self.subTest(flag=flag),self.assertRaises(ValueError):audit.verify_fresh(bad)
        for flag in ['cam_accepted','stencil_accepted','assembly_process_qualified']:
            bad=copy.deepcopy(self.report);bad['boards']['Core-C1'][flag]=True
            with self.subTest(flag=flag),self.assertRaises(ValueError):audit.verify_fresh(bad)
    def test_process_substitution_rejected(self):
        self.core['required_via_treatment']='TENTING'
        with self.assertRaises(ValueError):audit.verify_fresh(self.report)
    def test_wrong_policy_rejected(self):
        self.report['policy']={}
        with self.assertRaises(ValueError):audit.verify_fresh(self.report)
    def test_policy_cannot_approve_itself(self):
        self.report['policy']['cam_accepted']=True
        with patch.object(audit,'load_contract',return_value={'assembly_process':self.report['policy']}),self.assertRaises(ValueError):audit.verify_fresh(self.report)
    def test_matching_wrong_treatment_rejected(self):
        self.report['policy']['core_via_treatment']='Soldermask plugging'
        with patch.object(audit,'load_contract',return_value={'assembly_process':self.report['policy']}),self.assertRaises(ValueError):audit.verify_fresh(self.report)
    def test_missing_board_rejected(self):
        del self.report['boards']['Display-C1']
        with self.assertRaises(ValueError):audit.verify_fresh(self.report)
    def test_stale_source_rejected(self):
        with patch.object(audit,'sha',return_value='changed'),self.assertRaises(ValueError):audit.verify_fresh(self.report)
    def test_duplicate_inventory_rejected(self):
        self.core['via_inventory'].append(self.via.copy())
        with self.assertRaises(ValueError):audit.verify_fresh(self.report)
    def test_duplicate_contact_rejected(self):
        self.core['land_overlap_contacts'].append(self.hit.copy())
        with self.assertRaises(ValueError):audit.verify_fresh(self.report)
    def test_wrong_hole_rejected(self):
        self.hit['drill_mm']=.25
        with self.assertRaises(ValueError):audit.verify_fresh(self.report)
    def test_wrong_coordinate_rejected(self):
        self.hit['center_mm']=[2.,1.]
        with self.assertRaises(ValueError):audit.verify_fresh(self.report)
    def test_wrong_count_rejected(self):
        self.core['land_overlap_hole_count']=0
        with self.assertRaises(ValueError):audit.verify_fresh(self.report)
    def test_actual_drill_coverage(self):
        drills={'PTH':{'round_holes':[{'center_mm':[1.,2.],'diameter_mm':.2}]}}
        self.assertTrue(audit.drill_coverage(self.core,drills))
        drills['PTH']['round_holes'][0]['center_mm'][1]=-2
        with self.assertRaises(ValueError):audit.drill_coverage(self.core,drills)
    def test_missing_and_duplicate_drills(self):
        for holes in [[],[{'center_mm':[1.,2.],'diameter_mm':.2}]*2]:
            with self.subTest(holes=holes),self.assertRaises(ValueError):audit.drill_coverage(self.core,{'PTH':{'round_holes':holes}})
    def test_csv_includes_uuid_and_side(self):
        text=audit.contact_csv(self.core)
        self.assertIn('Via_UUID',text);self.assertIn('U1,1,F.Cu,1.0,2.0,0.2,0.4,GND,v1',text)


if __name__ == '__main__':unittest.main(verbosity=2)
