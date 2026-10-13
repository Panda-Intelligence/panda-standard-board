"""Fresh native-report gate fixtures, not electrical or fabrication approval."""
import copy
import unittest
from pico47_complete_ground_gate import require_complete_ground_returns, TARGETS, REFERENCES
from pico47_ground_returns import summarize_ground_returns


def complete():
    reports = {}
    for board, targets in TARGETS.items():
        ref, pin = REFERENCES[board]
        pads = [{'uuid': board+'-ref', 'ref': ref, 'pin': pin, 'net':'GND', 'position_mm':[0,0]}]
        pads += [{'uuid':board+'-'+r+'.'+n,'ref':r,'pin':n,'net':'GND','position_mm':[i+1,1]}
                 for i,(r,n) in enumerate(sorted(targets))]
        reports[board] = summarize_ground_returns(pads, [[p['uuid'] for p in pads]], ref, pin,
                                                 sorted(targets))
    return reports


class CompleteGroundGate(unittest.TestCase):
    def test_complete_reports_pass_without_manufacturing_permission(self):
        result = require_complete_ground_returns(complete())
        self.assertTrue(result['complete'])
        self.assertFalse(result['manufacturing_release'])
        self.assertEqual(sum(b['named_ground_targets_connected'] for b in result['boards'].values()),8)

    def test_eighth_target_open_rejected_even_with_true_aggregate(self):
        data=complete()
        target=next(t for t in data['Display']['required_ground_targets'] if t['ref']=='U810' and t['pin']=='32')
        target['connected_to_reference']=False
        with self.assertRaisesRegex(ValueError,'U810.32'):require_complete_ground_returns(data)

    def test_disconnected_unnamed_ground_also_rejected(self):
        data=complete();data['Core']['ground_pad_count']+=1
        with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_all_targets_true_does_not_hide_another_island(self):
        data=complete();data['Display']['ground_group_count']=2
        with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_missing_board_rejected(self):
        data=complete();del data['Core']
        with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_extra_board_rejected(self):
        data=complete();data['Other']=copy.deepcopy(data['Core'])
        with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_missing_target_rejected(self):
        data=complete();data['Display']['required_ground_targets'].pop()
        with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_duplicate_named_target_rejected(self):
        data=complete();targets=data['Display']['required_ground_targets'];targets[0]=copy.deepcopy(targets[1])
        with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_unknown_target_rejected(self):
        data=complete();data['Core']['required_ground_targets'][0]['ref']='J999'
        with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_non_ground_target_rejected(self):
        data=complete();data['Core']['required_ground_targets'][0]['net']='P47_D0'
        with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_boolean_counts_are_not_numeric_evidence(self):
        for value in (True,'1',-1,None):
            data=complete();data['Core']['ground_group_count']=value
            with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_truthy_strings_not_connected(self):
        for key in ['all_ground_pads_connected_to_reference','all_required_ground_targets_connected']:
            data=complete();data['Core'][key]='true'
            with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_missing_evidence_rejected(self):
        for key in ['evidence','reference_pad','ground_pad_count','groups_not_connected_to_reference']:
            data=complete();del data['Core'][key]
            with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_wrong_reference_rejected(self):
        data=complete();data['Display']['reference_pad']['pin']='1'
        with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_contradictory_target_count_rejected(self):
        data=complete();data['Display']['connected_required_ground_target_count']=5
        with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_uuid_duplicates_rejected(self):
        data=complete();targets=data['Core']['required_ground_targets'];targets[0]['uuid']=targets[1]['uuid']
        with self.assertRaises(ValueError):require_complete_ground_returns(data)

    def test_no_input_mutation(self):
        data=complete();before=copy.deepcopy(data);require_complete_ground_returns(data)
        self.assertEqual(data,before)


if __name__=='__main__':unittest.main(verbosity=2)
