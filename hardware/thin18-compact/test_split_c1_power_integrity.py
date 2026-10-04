#!/usr/bin/env python3
"""In-memory positive/negative circuit and release-target regression fixtures."""
import contextlib
import copy
import io
import subprocess
import unittest
from unittest.mock import patch
import release_split_c1 as release
from verify_split_c1_power_integrity import EXACT_PARTS, EXPECTED_PINS, verify_contract


def fixture():
    fields={ref:dict(zip(['Manufacturer','MPN','Footprint','LCSC'],values)) for ref,values in EXACT_PARTS.items()}
    pins={(r,p):n for r,values in EXPECTED_PINS.items() for p,n in values.items()}
    pins.update({('U901','2'):'SGM41513_PSEL',('U901','22'):'SGM41513_REGN',
                 ('U601','17'):'PG_3V3_MAIN',('TP16','1'):'PG_3V3_MAIN'})
    return fields,pins


def nets_for(pins):
    nets={}
    for key,net in pins.items():nets.setdefault(net,set()).add(key)
    return nets


class CircuitContracts(unittest.TestCase):
    def check_fixture(self,fields,pins):return verify_contract(fields,pins,nets_for(pins))
    def test_reviewed_topology(self):self.assertTrue(self.check_fixture(*fixture()))
    def reject_pin(self,ref,pin,net):
        fields,pins=fixture();pins[ref,pin]=net
        with self.assertRaises(ValueError):self.check_fixture(fields,pins)
    def test_reject_downstream_aon_psel(self):self.reject_pin('U901','2','3V3_AON')
    def test_reject_psel_tied_to_usb(self):self.reject_pin('U901','2','VBUS_USB')
    def test_reject_psel_without_regn(self):self.reject_pin('R204','2','3V3_AON')
    def test_reject_divider_lower_leg_open(self):self.reject_pin('R201','2','unconnected-R201')
    def test_reject_supervisor_reversed_output(self):self.reject_pin('U906','2','GND')
    def test_reject_supervisor_wrong_supply(self):self.reject_pin('U906','3','VSYS_RAW')
    def test_reject_missing_bypass_ground(self):self.reject_pin('C204','2','SGM41513_PSEL')
    def test_reject_unreviewed_pg_load(self):self.reject_pin('U501','3','PG_3V3_MAIN')
    def test_reject_legacy_ilim_net(self):self.reject_pin('R999','1','BQ_ILIM_RC')
    def test_reject_missing_pg_source(self):
        fields,pins=fixture();del pins['U906','2']
        with self.assertRaises(ValueError):self.check_fixture(fields,pins)
    def test_reject_wrong_threshold_or_output_variant(self):
        for mpn in ['SGM803B-TXN3LG/TR','SGM810B-TXN3LG/TR','SGM809B-TXN3TG/TR']:
            with self.subTest(mpn=mpn):
                fields,pins=fixture();fields['U906']['MPN']=mpn
                with self.assertRaises(ValueError):self.check_fixture(fields,pins)
    def test_reject_wrong_charger_variant(self):
        fields,pins=fixture();fields['U901']['MPN']='SGM41513DYTQF24G/TR'
        with self.assertRaises(ValueError):self.check_fixture(fields,pins)
    def test_reject_wrong_divider_part(self):
        fields,pins=fixture();fields['R204']['MPN']='RS-03K5601FT'
        with self.assertRaises(ValueError):self.check_fixture(fields,pins)
    def test_reject_invented_supplier_code(self):
        fields,pins=fixture();fields['U906']['LCSC']='C12345'
        with self.assertRaises(ValueError):self.check_fixture(fields,pins)


class TargetIsolation(unittest.TestCase):
    def test_explicit_target_required(self):
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as error:release.main([])
        self.assertEqual(error.exception.code,2)
    def test_split_does_not_require_thin7(self):
        self.assertFalse(any(s.startswith('thin7/') for s,a,n in release.release_steps('split-c1')))
    def test_thin7_has_no_split_export(self):
        self.assertEqual([s for s,a,n in release.release_steps('thin7')],['thin7/audit_thin7.py'])
    def test_thin7_cannot_export_even_after_audit_passes(self):
        called=[]
        with self.assertRaises(RuntimeError):release.execute('thin7',lambda s,a,n:called.append(s))
        self.assertEqual(called,['thin7/audit_thin7.py'])
    def test_native_failure_stops_pipeline(self):
        called=[]
        def fail(s,a,n):called.append(s);raise subprocess.CalledProcessError(1,s)
        with self.assertRaises(subprocess.CalledProcessError):release.execute('split-c1',fail)
        self.assertEqual(called,['validate_split_c1.py'])
    def test_both_dimensions_enforced(self):
        steps=[a for s,a,n in release.release_steps('split-c1') if s=='export_production.py']
        self.assertEqual(len(steps),2)
        self.assertEqual([a[a.index('--nominal-size')+1:a.index('--nominal-size')+3] for a in steps],[[96,68],[45,36]])
    def test_domestic_complete_required(self):
        self.assertIn(('audit_split_c1_domestic.py',['--require-complete'],False),release.release_steps('split-c1'))


if __name__=='__main__':unittest.main(verbosity=2)
