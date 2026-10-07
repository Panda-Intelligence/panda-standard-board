"""Fail-closed tests for routing evidence and exact S-expression handling."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from seven_mm_native_evidence import checked_counts,sha
from seven_mm_routing import sexpr_blocks,balanced,freeze,apply

class Counts(unittest.TestCase):
    def setUp(self):
        self.d={'violations':[],'unconnected_items':[],'schematic_parity':[]}
        self.e={'sheets':[{'violations':[]}]}
    def test_clean(self):self.assertEqual(checked_counts(self.d,self.e),{'drc':0,'open':0,'parity':0,'erc':0})
    def test_open_rejected(self):
        self.d['unconnected_items']=[{}]
        with self.assertRaises(ValueError):checked_counts(self.d,self.e)
    def test_violation_rejected(self):
        self.d['violations']=[{}]
        with self.assertRaises(ValueError):checked_counts(self.d,self.e)
    def test_parity_rejected(self):
        self.d['schematic_parity']=[{}]
        with self.assertRaises(ValueError):checked_counts(self.d,self.e)
    def test_erc_rejected(self):
        self.e['sheets'][0]['violations']=[{}]
        with self.assertRaises(ValueError):checked_counts(self.d,self.e)
    def test_missing_parity_rejected(self):
        del self.d['schematic_parity']
        with self.assertRaises(ValueError):checked_counts(self.d,self.e)
    def test_no_sheets_rejected(self):
        with self.assertRaises(ValueError):checked_counts(self.d,{'sheets':[]})
    def test_incomplete_erc_rejected(self):
        with self.assertRaises(ValueError):checked_counts(self.d,{'sheets':[{}]})

class Parsing(unittest.TestCase):
    def test_exact_atoms(self):
        s='(kicad_pcb (via_size 1) (vias not_allowed) (via (at 1 2)))'
        self.assertEqual(sexpr_blocks(s,'(via'),['(via (at 1 2))'])
    def test_quoted_example(self):
        s='(kicad_pcb (descr "example (via (at 1 2))") (via (at 3 4)))'
        self.assertEqual(sexpr_blocks(s,'(via'),['(via (at 3 4))'])
    def test_escaped_quote(self):
        s=json.dumps('example " (segment (start 1 2))')+' (segment (start 3 4))'
        self.assertEqual(sexpr_blocks(s,'(segment'),['(segment (start 3 4))'])
    def test_unclosed_expression(self):
        with self.assertRaises(ValueError):sexpr_blocks('(via (at 1 2)','(via')

class Plans(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.pcb=Path(self.tmp.name)/'Board.kicad_pcb';self.pcb.write_text('(kicad_pcb)')
        self.pcb.with_suffix('.kicad_pro').write_text('{}')
        self.pcb.with_suffix('.kicad_sch').write_text('(schematic)')
        self.item='(segment (start 1 2) (end 2 2) (width 0.15) (layer "F.Cu") (net "TEST") (uuid "unique"))'
        self.plan={'schema':'panda-seven-mm-routing-v1','board':'Core','source_semantic_sha256':'same','segment_count':1,'via_count':0,'copper_items':[self.item],
                   'native_checks':{'drc':0,'open':0,'parity':0,'erc':0},'copper_sha256':hashlib.sha256(self.item.encode()).hexdigest(),
                   'native_evidence':{'counts':{'drc':0,'open':0,'parity':0,'erc':0},'refill_before_drc':True,'severity_all':True,'schematic_parity_requested':True,'project_sha256':sha(self.pcb.with_suffix('.kicad_pro')),'design_rules_sha256':None,'schematic_sha256':sha(self.pcb.with_suffix('.kicad_sch'))}}
        self.path=Path(self.tmp.name)/'plan.json'
    def execute(self):
        self.path.write_text(json.dumps(self.plan))
        with patch('seven_mm_routing.native_semantic_fingerprint',return_value='same'):
            return apply(self.pcb,self.path,'Core')
    def test_valid_plan(self):
        self.assertEqual(self.execute()['segments'],1)
        self.assertIn(self.item,self.pcb.read_text())
    def test_copper_mutation(self):
        self.plan['copper_items'][0]=self.item.replace('(end 2 2)','(end 22 2)')
        with self.assertRaises(ValueError):self.execute()
        self.assertEqual(self.pcb.read_text(),'(kicad_pcb)')
    def test_no_evidence(self):
        del self.plan['native_evidence']
        with self.assertRaises(ValueError):self.execute()
    def test_unrefilled(self):
        self.plan['native_evidence']['refill_before_drc']=False
        with self.assertRaises(ValueError):self.execute()
    def test_changed_rules(self):
        self.pcb.with_suffix('.kicad_pro').write_text('{"different":true}')
        with self.assertRaises(ValueError):self.execute()
    def test_duplicate_ids(self):
        self.plan['copper_items']=[self.item,self.item];self.plan['segment_count']=2
        self.plan['copper_sha256']=hashlib.sha256((self.item+'\n'+self.item).encode()).hexdigest()
        with self.assertRaises(ValueError):self.execute()
    def test_second_application_rejected(self):
        self.execute()
        with self.assertRaises(ValueError):self.execute()
    def test_native_count_mismatch(self):
        self.plan['native_evidence']['counts']['open']=1
        with self.assertRaises(ValueError):self.execute()
    def test_freeze_runs_native_gate(self):
        output=Path(self.tmp.name)/'unwritten.json'
        with patch('seven_mm_routing.native_semantic_fingerprint',return_value='same'),patch('seven_mm_routing.copper_blocks',side_effect=[[],[self.item]]),patch('seven_mm_routing.verify_native_clean',side_effect=ValueError('native failed')) as check:
            with self.assertRaises(ValueError):freeze(self.pcb,self.pcb,output,'Core')
            check.assert_called_once()
        self.assertFalse(output.exists())

if __name__=='__main__':unittest.main(verbosity=2)
