#!/usr/bin/env python3
"""Negative controls for factory metadata, layer identity and drilling."""
import copy
import json
import unittest
from _split_c1_fabrication import (load_contract, normalize_job, validate_job,
    functions, geometry_payload, drill_summary, validate_gerber_contents)

SPEC=load_contract()['boards']['Core-C1']
HASH='a'*64


def fixture():
    return {'GeneralSpecs':{'LayerNumber':4,'BoardThickness':0.8,
            'Size':{'X':96.05,'Y':68.05},'Finish':'None','ImpedanceControlled':True,
            'ProjectId':{'Name':'old-source','GUID':'example','Revision':'old-unrouted'}},
            'MaterialStackup':[{'Type':'Copper','Thickness':0.035} for _ in range(4)]+
                [{'Type':'SolderMask','Color':'R255G0B128'} for _ in range(2)],
            'FilesAttributes':[{'Path':f'layer-{i}.gbr','FileFunction':fn}
                               for i,fn in enumerate(functions(4))]}


def drill(plated=True, empty=False):
    role='Plated' if plated else 'NonPlated';name='PTH' if plated else 'NPTH'
    prefix=f'M48\n; #@! TF.FileFunction,{role},1,4,{name}\nMETRIC\n'
    return prefix+('T1C1.400\n%\nT1\nX49.2Y-43.5G85X49.6Y-43.5\n' if not empty else '%\n')+'M30\n'


def contents():
    job=normalize_job(fixture(),SPEC,'Core-C1',HASH)
    data={'board.gbrjob':json.dumps(job).encode(),'board-PTH.drl':drill().encode(),
          'board-NPTH.drl':drill(False,True).encode(),'drill-report.txt':b'example'}
    for row in job['FilesAttributes']:
        fn=row['FileFunction'].replace('SolderMask','Soldermask')
        if fn=='Profile':fn+=',NP'
        data[row['Path']]=f'%MOMM*%\n%TF.FileFunction,{fn}*%\n%TF.ProjectId,board,guid,Core-C1-{HASH[:12]}*%\nM02*\n'.encode()
    return data


class FabricationMetadata(unittest.TestCase):
    def test_only_reviewed_fields_change(self):
        raw=fixture();original=copy.deepcopy(raw);job=normalize_job(raw,SPEC,'Core-C1',HASH)
        self.assertEqual(raw,original)
        self.assertEqual(job['GeneralSpecs']['Size'],{'X':96.0,'Y':68.0})
        self.assertNotIn('ImpedanceControlled',job['GeneralSpecs'])
        self.assertEqual(job['GeneralSpecs']['Finish'],'Nickel, Gold')
        self.assertTrue(validate_job(job,SPEC,'Core-C1',HASH))
    def test_default_half_ounce_is_rejected(self):
        raw=fixture();raw['MaterialStackup'][1]['Thickness']=0.0175
        with self.assertRaises(ValueError):normalize_job(raw,SPEC,'Core-C1',HASH)
    def test_wrong_board_layer_count(self):
        raw=fixture();raw['GeneralSpecs']['LayerNumber']=2
        with self.assertRaises(ValueError):normalize_job(raw,SPEC,'Core-C1',HASH)
    def test_wrong_board_dimensions(self):
        raw=fixture();raw['GeneralSpecs']['Size']['X']=45.0
        with self.assertRaises(ValueError):normalize_job(raw,SPEC,'Core-C1',HASH)
    def test_wrong_thickness(self):
        raw=fixture();raw['GeneralSpecs']['BoardThickness']=1.6
        with self.assertRaises(ValueError):normalize_job(raw,SPEC,'Core-C1',HASH)
    def test_wrong_finish_or_mask(self):
        for key in ['finish','mask']:
            job=normalize_job(fixture(),SPEC,'Core-C1',HASH)
            if key=='finish':job['GeneralSpecs']['Finish']='None'
            else:job['MaterialStackup'][-1]['Color']='Purple'
            with self.assertRaises(ValueError):validate_job(job,SPEC,'Core-C1',HASH)
    def test_stale_revision(self):
        job=normalize_job(fixture(),SPEC,'Core-C1',HASH)
        with self.assertRaises(ValueError):validate_job(job,SPEC,'Core-C1','b'*64)
    def test_unqualified_impedance_flag(self):
        job=normalize_job(fixture(),SPEC,'Core-C1',HASH);job['GeneralSpecs']['ImpedanceControlled']=True
        with self.assertRaises(ValueError):validate_job(job,SPEC,'Core-C1',HASH)
    def test_missing_duplicate_layer(self):
        job=normalize_job(fixture(),SPEC,'Core-C1',HASH);job['FilesAttributes'][-1]=job['FilesAttributes'][0]
        with self.assertRaises(ValueError):validate_job(job,SPEC,'Core-C1',HASH)
    def test_unsafe_path(self):
        job=normalize_job(fixture(),SPEC,'Core-C1',HASH);job['FilesAttributes'][0]['Path']='../other-board.gbr'
        with self.assertRaises(ValueError):validate_job(job,SPEC,'Core-C1',HASH)
    def test_geometry_payload_preserves_drawing(self):
        a='%TF.ProjectId,old,guid,old*%\n%TF.CreationDate,2020*%\n%ADD10C,0.4*%\nX100Y200D03*\n'
        b=a.replace('old*%','new*%').replace('2020','2026')
        self.assertEqual(geometry_payload(a),geometry_payload(b))
        self.assertNotEqual(geometry_payload(a),geometry_payload(b.replace('X100','X101')))


class DrillAndLayerData(unittest.TestCase):
    def test_short_plated_slot_is_visible(self):
        d=drill_summary(drill(),True,4)
        self.assertEqual(d['hit_count'],1);self.assertEqual(d['slots'][0]['length_mm'],1.8)
        self.assertEqual(d['slots'][0]['width_mm'],1.4)
        self.assertTrue(d['slots'][0]['shorter_than_2_to_1'])
    def test_empty_npth_is_valid(self):
        self.assertEqual(drill_summary(drill(False,True),False,4)['hit_count'],0)
    def test_wrong_plating_or_units(self):
        for text in [drill().replace('METRIC','INCH'),drill().replace('Plated','NonPlated'),drill().replace('1,4,PTH','1,2,PTH')]:
            with self.assertRaises(ValueError):drill_summary(text,True,4)
    def test_undeclared_tool(self):
        with self.assertRaises(ValueError):drill_summary(drill().replace('\nT1\n','\nT2\n'),True,4)
    def test_valid_gerber_layers(self):
        self.assertEqual(validate_gerber_contents(contents(),SPEC,'Core-C1',HASH)['NPTH']['hit_count'],0)
    def test_swapped_inner_layers(self):
        d=contents();d['layer-1.gbr'],d['layer-2.gbr']=d['layer-2.gbr'],d['layer-1.gbr']
        with self.assertRaises(ValueError):validate_gerber_contents(d,SPEC,'Core-C1',HASH)
    def test_missing_npth(self):
        d=contents();del d['board-NPTH.drl']
        with self.assertRaises(ValueError):validate_gerber_contents(d,SPEC,'Core-C1',HASH)
    def test_extra_drill_file(self):
        d=contents();d['unknown.drl']=drill().encode()
        with self.assertRaises(ValueError):validate_gerber_contents(d,SPEC,'Core-C1',HASH)
    def test_truncated_copper(self):
        d=contents();d['layer-0.gbr']=d['layer-0.gbr'].replace(b'M02*',b'')
        with self.assertRaises(ValueError):validate_gerber_contents(d,SPEC,'Core-C1',HASH)
    def test_mixed_revision(self):
        d=contents();d['layer-0.gbr']=d['layer-0.gbr'].replace(HASH[:12].encode(),b'oldrevision0')
        with self.assertRaises(ValueError):validate_gerber_contents(d,SPEC,'Core-C1',HASH)


class CapRoundHoleRegression(unittest.TestCase):
    def test_exported_round_pair(self):
        from _split_c1_fabrication import verify_cap_drill_export
        d={'PTH':{'round_holes':[{'diameter_mm':1.9,'center_mm':[49.4,43.5]},{'diameter_mm':1.9,'center_mm':[69.4,43.5]}],'slots':[]}}
        self.assertTrue(verify_cap_drill_export(d))
    def test_wrong_round_size_and_missing_hole(self):
        from _split_c1_fabrication import verify_cap_drill_export
        for rows in [[],[{'diameter_mm':1.8,'center_mm':[49.4,43.5]},{'diameter_mm':1.9,'center_mm':[69.4,43.5]}]]:
            with self.assertRaises(ValueError):verify_cap_drill_export({'PTH':{'round_holes':rows,'slots':[]}})
    def test_part_envelope_and_ring(self):
        from verify_split_c1_cap_drill import fit_screen
        self.assertGreater(fit_screen()['calculated_radial_fit_margin_mm'],0)
        with self.assertRaises(ValueError):fit_screen(1.8,2.3)
        with self.assertRaises(ValueError):fit_screen(1.9,2.2)
    def test_second_native_eco_application_rejected(self):
        from _split_c1_cap_drill_eco import patch_lands
        old='(footprint "test" (pad "1" thru_hole oval (at -10 0) (size 2.4 2.0) (drill oval 1.8 1.4)) (pad "2" thru_hole oval (at 10 0) (size 2.4 2.0) (drill oval 1.8 1.4)))'
        new=patch_lands(old)
        self.assertEqual(new.count('(drill 1.9)'),2)
        with self.assertRaises(ValueError):patch_lands(new)


if __name__=='__main__':
    unittest.main(verbosity=2)
