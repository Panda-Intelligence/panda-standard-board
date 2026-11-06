"""2026-11-03 Codex：CAD全绿不能代替CAM、来料、整机及EVT实测签核。"""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from build_pico47_single import build_qualification_report, write_csv


class QualificationEvidenceTests(unittest.TestCase):
    def fixture(self, root):
        (root/'orderpack').mkdir()
        (root/'Single.kicad_pcb').write_text('fixture only, not a fabricated native result')
        vias=[dict(uuid='via-a',net='GND',x_mm=1.0,y_mm=2.0,diameter_mm=.4,drill_mm=.2,
                   soldered_contacts='U1.1:F.Cu',process='FILLED_AND_COPPER_CAPPED_OR_SUPPLIER_APPROVED_EQUIVALENT')]
        pending=[dict(ref='C1',manufacturer='FH',mpn='exact-part',value='1uF',footprint='lib:cap',
                      lcsc='',supply_status='EXACT_SUPPLY_NOT_VERIFIED')]
        manual=[dict(ref='BT301',manufacturer='Power Glory',mpn='CR1216',value='RTC PRIMARY',
                     footprint='lib:cell',lcsc='',supply_status='FACTORY_ASSEMBLY_DRAWING_AND_RECEIPT_PENDING')]
        inspection=dict(via_in_pad=vias,pending_supply=pending,required_post_smt=manual,
                        solder_joint_via_process=dict(filled_and_capped_vias=copy.deepcopy(vias),
                            filled_cap_via_count=1,supplier_process_accepted=False),
                        pmic_analog_shield=dict(native_ground_geometry_passed=True,
                            actual_noise_and_stability_qualified=False),
                        pmic_charge_pump_storage=dict(actual_noise_and_stability_qualified=False,
                            charge_pump_transient_and_ripple_qualified=False),
                        native_counts=dict(drc_errors=0,drc_warnings=0,open=0,parity=0,erc=0))
        spec=dict(revision='FIXTURE',date='2026-11-03',manufacturing_release=False,
                  via_in_pad=dict(supplier_process_accepted=False),
                  complete_via_in_pad_inventory=dict(soldered_vias=[['GND',1.0,2.0,.4,.2,'U1.1:F.Cu']]))
        for name,key in [('REQUIRED-VIA-IN-PAD.csv','via_in_pad'),('PENDING-SUPPLY.csv','pending_supply'),
                         ('REQUIRED-POST-SMT.csv','required_post_smt')]:
            write_csv(root/'orderpack'/name,inspection[key])
        source=root/'spec.json';source.write_text(json.dumps(spec))
        return spec,inspection,source

    def test_green_native_checks_leave_all_four_physical_qualifications_false(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);spec,inspection,source=self.fixture(root)
            report=build_qualification_report(root,spec,inspection,source)
            self.assertEqual(len(report['status_flags']),4)
            self.assertTrue(all(v is False for v in report['status_flags'].values()))
            self.assertEqual(report['binding']['pcb_sha256'],hashlib.sha256((root/'Single.kicad_pcb').read_bytes()).hexdigest())
            self.assertEqual(report['binding']['source_spec_sha256'],hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(report['inventories']['post_smt'][0]['ref'],'BT301')
            self.assertEqual(len(report['required_evidence']),6)
            self.assertTrue(all(r['status']=='pending_external_evidence' and r['accepted_evidence']==[]
                                for r in report['required_evidence']))
            for requirement in report['required_evidence']:
                if requirement['id'].startswith('evt_'):
                    self.assertIsNone(requirement['numerical_acceptance_limits'])

    def test_changed_supplier_or_nested_electrical_qualification_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);spec,inspection,source=self.fixture(root)
            changes=[('spec','manufacturing_release'),('spec_process','supplier_process_accepted'),
                     ('shield','actual_noise_and_stability_qualified'),
                     ('pump','charge_pump_transient_and_ripple_qualified')]
            for target,key in changes:
                for value in [True,'false',0]:
                    s,i=copy.deepcopy(spec),copy.deepcopy(inspection)
                    section={'spec':s,'spec_process':s['via_in_pad'],
                             'shield':i['pmic_analog_shield'],'pump':i['pmic_charge_pump_storage']}[target]
                    section[key]=value
                    with self.subTest(key=key,value=value),self.assertRaisesRegex(ValueError,'physical qualification'):
                        build_qualification_report(root,s,i,source)

    def test_wrong_receipt_identity_or_incomplete_CAM_csv_cannot_be_bound(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);spec,inspection,source=self.fixture(root)
            for name,key in [('REQUIRED-VIA-IN-PAD.csv','via_in_pad'),('PENDING-SUPPLY.csv','pending_supply'),
                             ('REQUIRED-POST-SMT.csv','required_post_smt')]:
                path=root/'orderpack'/name;before=path.read_bytes()
                changed=copy.deepcopy(inspection[key]);changed[0][next(iter(changed[0]))]='different'
                write_csv(path,changed)
                with self.subTest(name=name),self.assertRaisesRegex(ValueError,'inventory CSV differs'):
                    build_qualification_report(root,spec,inspection,source)
                path.write_bytes(before)
            path=root/'orderpack/REQUIRED-VIA-IN-PAD.csv';path.unlink()
            with self.assertRaisesRegex(ValueError,'Missing qualification inventory'):
                build_qualification_report(root,spec,inspection,source)

    def test_missing_BT301_or_inconsistent_full_process_inventory_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);spec,inspection,source=self.fixture(root)
            for change in ['missing_post_smt','short_process','wrong_source_count']:
                s,i=copy.deepcopy(spec),copy.deepcopy(inspection)
                if change=='missing_post_smt':i['required_post_smt']=[]
                elif change=='short_process':i['solder_joint_via_process']['filled_and_capped_vias']=[]
                else:s['complete_via_in_pad_inventory']['soldered_vias']*=2
                with self.subTest(change=change),self.assertRaisesRegex(ValueError,'qualification inventory'):
                    build_qualification_report(root,s,i,source)

    def test_same_count_wrong_CAM_signature_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);spec,inspection,source=self.fixture(root)
            changed=copy.deepcopy(inspection)
            changed['via_in_pad'][0]['x_mm']=9.0
            changed['solder_joint_via_process']['filled_and_capped_vias']=copy.deepcopy(changed['via_in_pad'])
            write_csv(root/'orderpack/REQUIRED-VIA-IN-PAD.csv',changed['via_in_pad'])
            with self.assertRaisesRegex(ValueError,'Source qualification inventory differs'):
                build_qualification_report(root,spec,changed,source)

    def test_catalogue_thermistor_identity_adds_pending_physical_temperature_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);spec,inspection,source=self.fixture(root)
            inspection['temperature_sense']=dict(mpn='CMKD103F3380HANT',temperature_accuracy_qualified=False)
            report=build_qualification_report(root,spec,inspection,source)
            item=next(r for r in report['required_evidence'] if r['id']=='evt_temperature_sense')
            self.assertEqual(item['accepted_evidence'],[])
            self.assertEqual(item['status'],'pending_external_evidence')
            self.assertIsNone(item['numerical_acceptance_limits'])
            self.assertTrue(all(v is False for v in report['status_flags'].values()))


if __name__=='__main__':
    unittest.main()
