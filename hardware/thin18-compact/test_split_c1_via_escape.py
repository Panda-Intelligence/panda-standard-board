#!/usr/bin/env python3
import copy,json,unittest
from _core_c1_pcb_patch import digest
from _split_c1_via_escape_eco import transform

OLD='(via (at 1 1) (size 0.45) (drill 0.25) (layers "F.Cu" "B.Cu") (net "CONTROL") (uuid "v1"))'
NEW=OLD.replace('(at 1 1)','(at 2 1)')
SEG='(segment (start 1 1) (end 2 1) (width 0.2) (layer "F.Cu") (net "CONTROL") (uuid "s1"))'
TEXT='(kicad_pcb (footprint "untouched" (at 20 30)) '+OLD+')'
TARGET=TEXT.replace(OLD,NEW)[:-1]+SEG+')'
PLAN={'source_copper_sha256':digest(TEXT),'routed_copper_sha256':digest(TARGET),'modified':{'v1':{'before':OLD,'after':NEW}},'removed':{},'added':{'s1':SEG}}

class EscapeTests(unittest.TestCase):
 def test_replay(self):self.assertEqual(digest(transform(TEXT,PLAN)),digest(TARGET))
 def test_footprint_untouched(self):self.assertIn('(footprint "untouched" (at 20 30))',transform(TEXT,PLAN))
 def test_second_application_rejected(self):
  with self.assertRaises(ValueError):transform(transform(TEXT,PLAN),PLAN)
 def test_foreign_source_rejected(self):
  with self.assertRaises(ValueError):transform(TEXT.replace('(size 0.45)','(size 0.5)'),PLAN)
 def test_moved_predecessor_rejected(self):
  p=copy.deepcopy(PLAN);p['modified']['v1']['before']=NEW
  with self.assertRaises(ValueError):transform(TEXT,p)
 def test_drill_change_rejected(self):
  p=copy.deepcopy(PLAN);p['modified']['v1']['after']=NEW.replace('(drill 0.25)','(drill 0.2)')
  with self.assertRaises(ValueError):transform(TEXT,p)
 def test_land_change_rejected(self):
  p=copy.deepcopy(PLAN);p['modified']['v1']['after']=NEW.replace('(size 0.45)','(size 0.4)')
  with self.assertRaises(ValueError):transform(TEXT,p)
 def test_layer_change_rejected(self):
  p=copy.deepcopy(PLAN);p['modified']['v1']['after']=NEW.replace('B.Cu','In2.Cu')
  with self.assertRaises(ValueError):transform(TEXT,p)
 def test_net_change_rejected(self):
  p=copy.deepcopy(PLAN);p['modified']['v1']['after']=NEW.replace('CONTROL','GND')
  with self.assertRaises(ValueError):transform(TEXT,p)
 def test_uuid_collision_rejected(self):
  p=copy.deepcopy(PLAN);p['added']['v1']=SEG
  with self.assertRaises(ValueError):transform(TEXT,p)
 def test_result_digest_rejected(self):
  p=copy.deepcopy(PLAN);p['routed_copper_sha256']='bad'
  with self.assertRaises(ValueError):transform(TEXT,p)
 def test_removal_predecessor_rejected(self):
  p=copy.deepcopy(PLAN);p['removed']['v2']=OLD
  with self.assertRaises(ValueError):transform(TEXT,p)

if __name__=='__main__':unittest.main(verbosity=2)
