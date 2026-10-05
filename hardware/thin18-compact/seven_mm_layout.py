#!/usr/bin/env python3
"""Hard user constraints and placement allocation, NOT native CAD qualification.

--plan checks the source allocation without writing any output. Native layout,
exact replacements, FPC and supplier maxima remain unimplemented/unverified.
The explicit product-export stop must not be removed based on this budget test.
"""
from pathlib import Path
import argparse
import copy
import json
import math
import unittest

CONTRACT = Path(__file__).with_suffix('.json')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def rectangle(value):
    require(len(value) == 4 and all(finite(v) for v in value), 'Invalid rectangle')
    require(value[0] < value[2] and value[1] < value[3], 'Empty rectangle')
    return value


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def validate_ports(plan):
    w, h = plan['case']['width_mm'], plan['case']['height_mm']
    require(set(plan['ports']) == {'J201', 'J501'}, 'Both physical interfaces are required')
    for ref, port in plan['ports'].items():
        x, y = port['opening_center_xy_mm']
        require(all(finite(v) for v in [x, y]), 'Nonfinite port center')
        edge = port['edge']
        require(edge in {'top','bottom','left','right'}, 'Unknown edge')
        normal = {'top':[0,-1], 'bottom':[0,1], 'left':[-1,0], 'right':[1,0]}[edge]
        require(port['outward_xy'] == normal, 'Port points into the case')
        require((edge == 'top' and y == 0) or (edge == 'bottom' and y == h)
                or (edge == 'left' and x == 0) or (edge == 'right' and x == w),
                'Opening center is not on the specified exterior edge')
        along, length = (x, w) if edge in {'top','bottom'} else (y, h)
        require(0 <= along <= length, 'Port outside enclosure')
        if port['placement_class'] == 'center':
            require(edge in {'top','bottom'}, 'Side middle is not authorized')
            require(abs(along-length/2) <= plan['port_center_tolerance_mm'], 'Port not centered')
        else:
            require(port['placement_class'] == 'near_corner' and edge in {'left','right'}, 'Unsupported port location')
            require(min(along, length-along) <= plan['port_corner_distance_maximum_mm'], 'Side port too far from corner')
        half = port['opening_width_budget_mm']/2
        require(finite(half) and half > 0, 'Invalid opening width')
        require(half + plan['port_end_corner_keepout_mm'] <= min(along, length-along), 'Opening enters a corner/support')
        require(finite(port['external_access_depth_budget_mm']) and port['external_access_depth_budget_mm'] > 0,
                'Plug/card service envelope missing')
    require(plan['ports']['J201']['opening_center_xy_mm'] == [37.5,112], 'Unreviewed USB datum')
    require(plan['ports']['J501']['opening_center_xy_mm'] == [75,96], 'Unreviewed microSD datum')


def validate_plan(plan):
    require(plan['schema'] == 'panda-seven-mm-layout-v1', 'Wrong layout schema')
    c = plan['case']
    require([c['width_mm'], c['height_mm']] == [75,112], 'Unreviewed portrait envelope')
    dims = [c['nominal_thickness_mm'], c['positive_tolerance_budget_mm'], c['maximum_finished_thickness_mm']]
    require(all(finite(v) and v > 0 for v in dims), 'Invalid case thickness/tolerance')
    require(c['maximum_finished_thickness_mm'] <= 7, 'Finished thickness exceeds user maximum')
    require(c['nominal_thickness_mm'] + c['positive_tolerance_budget_mm'] <= 7+1e-9, 'No space for positive tolerance')
    require(set(plan['boards']) == {'Core','Display'}, 'Exactly two boards required')
    outlines = {'Core': [[55,2],[73,2],[73,110],[2,110],[2,101],[40,101],[40,66],[55,66]],
                'Display': [[2,66],[38,66],[38,99],[2,99]]}
    occupied = []
    for name, board in plan['boards'].items():
        require(board['outline_xy_mm'] == outlines[name], 'Unreviewed outline differs from allocation')
        require(board['layers'] == (4 if name == 'Core' else 2), 'Wrong layer count')
        require(board['rear_z_mm'] == .75 and board['component_side'] == 'front', 'Stacked/back-loaded board violates allocation')
        require(board['thickness_nominal_mm'] == .8 and board['thickness_maximum_budget_mm'] == .88, 'PCB budget changed')
        require(0 < board['maximum_mounted_component_height_mm'] <= 2.4, 'Component height exceeds allocation')
        for value in board['regions_xyxy_mm']:
            r = rectangle(value)
            require(1 <= r[0] < r[2] <= 74 and 1 <= r[1] < r[3] <= 111, 'PCB region enters case wall')
            require(not any(overlaps(r, prior) for _, prior in occupied), 'Overlapping PCB allocation')
            occupied.append((name, r))
    b = plan['battery'];br = rectangle(b['body_xyxy_mm'])
    require(not any(overlaps(br, r) for _, r in occupied), 'Battery must be beside, not under a PCB')
    require([br[2]-br[0],br[3]-br[1]] == [51,62], 'Battery XY silently changed')
    require(b['capacity_target_mah'] == 1100 and b['minimum_capacity_target_mah'] == 900, 'Do not trade away capacity without approval')
    require(b['maximum_complete_pack_thickness_budget_mm'] == 2.8 and b['swelling_allowance_mm'] == .5, 'Unreviewed battery thickness/swelling')
    require(plan['interconnect']['contacts'] == 60, 'Interface contacts removed')
    require(plan['panel']['mpn'] == 'GDEQ0426T82-FT01C', 'Panel changed')
    panel = rectangle(plan['panel']['body_xyxy_mm'])
    require(abs(panel[2]-panel[0]-62.37) < 1e-8 and abs(panel[3]-panel[1]-105.33) < 1e-8, 'Panel was scaled')
    require(plan['panel']['thickness_budget_mm'] == 2.2, 'Unreviewed panel budget')
    section_totals = {}
    for name, section in plan['z_sections_maximum_budgets_mm'].items():
        require(all(finite(v) and v > 0 for v in section.values()), 'Invalid or deleted Z allowance')
        total = sum(section.values())
        require(total <= c['maximum_finished_thickness_mm']+1e-9, 'Worst-case section exceeds 7mm: '+name)
        section_totals[name] = round(total, 6)
    require(set(section_totals) == {'electronics','battery'}, 'Missing thickness section')
    es = plan['z_sections_maximum_budgets_mm']['electronics'];bs = plan['z_sections_maximum_budgets_mm']['battery']
    require(es['mounted_component'] == 2.4 and es['pcb'] == .88 and bs['complete_pack'] == 2.8 and bs['swelling'] == .5,
            'Section/component budgets diverged')
    require(all(s['panel'] == 2.2 and s['assembly_reserve'] >= .1 for s in [es,bs]), 'Panel or tolerance reserve omitted')
    require(plan['status'] == 'RELAYOUT_REQUIRED_NOT_ROUTED', 'Allocation must not claim native completion')
    require(set(plan['evidence']) == {'native_relayout_implemented','native_drc_erc_parity_passed','supplier_maximum_envelopes_verified','fpc_harness_and_port_access_verified','mechanical_tolerance_stack_verified','cam_and_smt_accepted','manufacturing_release'}, 'Missing evidence scope')
    require(all(value is False for value in plan['evidence'].values()), 'Do not turn planned dimensions into qualification')
    require(plan['preserve'] == {'two_pcbs':True,'mainland_bom':True,'flash_mb':16,'psram_mb':8,'rtc_isolated_retention_hours':24,'frontlight_touch_audio_imu_microsd':True,'default_off_charge_and_direct_inhibit':True}, 'Function or protection contract removed')
    validate_ports(plan)
    return {'allocation_checks_passed':True, 'maximum_section_budgets_mm':section_totals,
            'native_relayout_complete':False, 'supplier_envelopes_verified':False, 'manufacturing_release':False}


def block_obsolete_product_export():
    """Fail closed until a reviewed, native 7mm relayout replaces the old target.

    A JSON flag, successful budget sum, clean OLD DRC or changing the rendered
    outer thickness is insufficient. Removing this stop needs an independently
    reviewed native/electrical/mating/tolerance validation implementation.
    """
    validate_plan(json.loads(CONTRACT.read_text()))
    raise ValueError('7mm product relayout is not implemented/qualified. The old Split-C1 stacked PCB and 22mm enclosure are not the requested product. Product render, RFQ and fabrication export are blocked. Native design checks may still be run separately; no output or paid order is authorized.')


class Tests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(CONTRACT.read_text())
    def bad(self, path, value):
        p = copy.deepcopy(self.plan);node = p
        for key in path[:-1]:node = node[key]
        node[path[-1]] = value
        with self.assertRaises((ValueError,KeyError)):validate_plan(p)
    def test_allocation(self):self.assertTrue(validate_plan(self.plan)['allocation_checks_passed'])
    def test_no_release_from_budget(self):self.assertFalse(validate_plan(self.plan)['manufacturing_release'])
    def test_old_export_blocked(self):
        with self.assertRaises(ValueError):block_obsolete_product_export()
    def test_22mm(self):self.bad(['case','nominal_thickness_mm'],22)
    def test_7mm_plus_tolerance(self):self.bad(['case','nominal_thickness_mm'],7)
    def test_relaxed_maximum(self):self.bad(['case','maximum_finished_thickness_mm'],22)
    def test_nan(self):self.bad(['case','nominal_thickness_mm'],float('nan'))
    def test_bool_dimension(self):self.bad(['case','nominal_thickness_mm'],True)
    def test_stacked_boards(self):self.bad(['boards','Display','rear_z_mm'],-1.5)
    def test_back_components(self):self.bad(['boards','Core','component_side'],'back')
    def test_module_height(self):self.bad(['boards','Core','maximum_mounted_component_height_mm'],3.2)
    def test_capacitor_height(self):self.bad(['z_sections_maximum_budgets_mm','electronics','mounted_component'],6.5)
    def test_battery_over_board(self):self.bad(['battery','body_xyxy_mm'],[22,2,73,64])
    def test_battery_capacity(self):self.bad(['battery','minimum_capacity_target_mah'],500)
    def test_battery_thickness(self):self.bad(['battery','maximum_complete_pack_thickness_budget_mm'],5.5)
    def test_no_swelling(self):self.bad(['z_sections_maximum_budgets_mm','battery','swelling'],0)
    def test_no_assembly_tolerance(self):self.bad(['z_sections_maximum_budgets_mm','electronics','assembly_reserve'],0)
    def test_panel_scaled(self):self.bad(['panel','body_xyxy_mm'],[6,2,60,100])
    def test_board_overlap(self):self.bad(['boards','Display','regions_xyxy_mm'],[[40,66,73,99]])
    def test_board_wall(self):self.bad(['boards','Core','regions_xyxy_mm'],[[0,2,73,66]])
    def test_usb_not_centered(self):self.bad(['ports','J201','opening_center_xy_mm'],[39,112])
    def test_card_middle(self):self.bad(['ports','J501','opening_center_xy_mm'],[75,56])
    def test_inward_port(self):self.bad(['ports','J501','outward_xy'],[-1,0])
    def test_missing_service(self):self.bad(['ports','J201','external_access_depth_budget_mm'],0)
    def test_corner_collision(self):self.bad(['ports','J501','opening_width_budget_mm'],30)
    def test_pin_count(self):self.bad(['interconnect','contacts'],30)
    def test_false_native_pass(self):self.bad(['evidence','native_relayout_implemented'],True)
    def test_false_completion(self):self.bad(['status'],'READY')
    def test_empty_evidence(self):self.bad(['evidence'],{})
    def test_rtc_removed(self):self.bad(['preserve','rtc_isolated_retention_hours'],0)
    def test_outline_scaled(self):self.bad(['boards','Display','outline_xy_mm'],[[2,66],[47,66],[47,102],[2,102]])
    def test_omitted_board(self):self.bad(['boards'],{'Core':self.plan['boards']['Core']})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',action='store_true')
    parser.add_argument('--test',action='store_true')
    args=parser.parse_args()
    if args.test:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        return 0 if result.wasSuccessful() else 1
    if args.plan:
        plan=json.loads(CONTRACT.read_text());print(json.dumps({'requirements':plan,'screen':validate_plan(plan)},indent=2));return 0
    try:block_obsolete_product_export()
    except ValueError as error:print(str(error));return 2
    return 2


if __name__ == '__main__':raise SystemExit(main())
