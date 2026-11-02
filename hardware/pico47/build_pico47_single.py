#!/usr/bin/env python3
"""2026-10-30 Codex：从绑定的原生源重建 Single 并重新生成验收和制造资料。

显式输入为 single_board.json 指定的外部原生文件及完整本地库，输入可迁移但
内容必须匹配。每次在新目录重铺铜和检查，不使用输入包中的旧验收报告。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SPEC = HERE / 'single_board.json'
sys.path.insert(0, str(HERE.parent / 'thin18-compact'))
from _split_c1_common import kicad_cli
from seven_mm_routing import native_semantic_fingerprint
from capture_pico47_checkpoint import counts_from_reports
from pico47_contract import CONTRACT, validate, GPIO_PACKAGE, PANEL_PINS
from pico47_ground_returns import inspect_ground_returns
from prune_pico47_stubs import pad_components, preserves_groups, preserves_groups_with_additions
from verify_mainland_bom_compliance import verify_board_mainland_compliance
from verify_jlc_coupon_compliance import export_jlc_orderpack, inspect_board_native, inspect_solder_joint_vias


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify_inputs(source, spec):
    """逐个核对必需原生文件和完整库清单，临时报告不作为源。"""
    bindings = spec['input_sha256']
    required = {'Single' + s for s in ('.kicad_pcb', '.kicad_sch', '.kicad_pro', '.kicad_dru')}
    required.update(('Panda7.kicad_sym', 'fp-lib-table', 'sym-lib-table'))
    require(required <= set(bindings), 'Incomplete Single source bindings')
    libraries = {str(p.relative_to(source)) for p in (source / 'Panda47.pretty').glob('*.kicad_mod')}
    require(libraries and libraries == {p for p in bindings if p.startswith('Panda47.pretty/')},
            'Footprint library inventory differs')
    for relative, digest in bindings.items():
        require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,
                'Source binding must be relative')
        path = source / relative
        require(path.is_file() and sha(path) == digest, 'Source differs: ' + relative)


def run_cli(arguments, log):
    with log.open('w') as stream:
        subprocess.run([kicad_cli(), *map(str, arguments)], check=True,
                       stdout=stream, stderr=subprocess.STDOUT, timeout=180)


def _inspect_switch_bypass(board, contract, groups, terminal, check_via_pad_edge, side='F.Cu'):
    """输入与输出共用真实接点检查；新增电容另查50µm盘外孔预算。"""
    import pcbnew as P
    require(side in ('F.Cu','B.Cu'), 'Power bypass requires an outer assembly face')
    face = P.F_Cu if side=='F.Cu' else P.B_Cu
    title = terminal.capitalize() + ' bypass'
    switch = board.FindFootprintByReference(contract['switch'])
    cap = board.FindFootprintByReference(contract['cap'])
    require(switch is not None and cap is not None, 'Missing load-switch ' + terminal + ' bypass')
    require(cap.GetValue() == contract['value'] and not cap.IsDNP()
            and cap.GetLayer() == face and cap.GetAttributes() & P.FP_SMD,
            title + ' value or assembly differs')
    def pin(fp, number):
        found = [p for p in fp.Pads() if p.GetNumber() == number]
        require(len(found) == 1, title + ' pin inventory differs')
        return found[0]
    power,ground = pin(switch,contract[terminal+'_pin']),pin(switch,contract['ground_pin'])
    a,b = pin(cap,'1'),pin(cap,'2')
    require(a.GetNetname() == power.GetNetname() == contract[terminal+'_net']
            and b.GetNetname() == ground.GetNetname() == 'GND', title + ' pin net differs')
    if check_via_pad_edge:
        for via in board.GetTracks():
            if via.GetClass() == 'PCB_VIA':
                require(not any(p.GetEffectiveShape(face).Collide(via.GetEffectiveShape(face),50000)
                                for p in (a,b)), title + ' violates ordinary-via pad-edge separation')
    group_for = {u:g for g in (groups if groups is not None else pad_components(board)) for u in g}
    for x,y in [(a,power),(b,ground)]:
        require(y.m_Uuid.AsString() in group_for[x.m_Uuid.AsString()],
                title + ' has no actual copper connection')
    distance = ((a.GetPosition().x-power.GetPosition().x)**2
                +(a.GetPosition().y-power.GetPosition().y)**2)**.5/1e6
    require(distance <= contract['maximum_pad_distance_mm'], title + ' is outside the reviewed local placement')
    return {'switch':contract['switch'],'cap':contract['cap'],'value':contract['value'],
            terminal+'_net':contract[terminal+'_net'],terminal+'_pad_distance_mm':distance,
            'both_native_connections':True,'transient_and_DC_bias_qualified':False}


def inspect_output_bypass(board, contract, groups=None):
    """保持既有输出去耦的真实接点、摆位及盘外孔约束。"""
    return _inspect_switch_bypass(board,contract,groups,'output',True)


def inspect_input_bypass(board, contract, groups=None):
    """已有CIN保持原生规则和工艺清单；明确新增CIN沿用50µm盘外孔预算。"""
    require(isinstance(contract.get('new_component'),bool), 'Input bypass placement policy is missing')
    return _inspect_switch_bypass(board,contract,groups,'input',contract['new_component'])


def inspect_power_bypass(board, contract, groups=None):
    """核对数字IC局部电源旁路及声明装配面；原输入/输出接口仍固定正面。"""
    require(isinstance(contract.get('new_component'),bool), 'Power bypass placement policy is missing')
    normalized = {**contract,'switch':contract['device']}
    result = _inspect_switch_bypass(board,normalized,groups,'power',contract['new_component'],contract['side'])
    result['device'] = result.pop('switch')
    result.update(side=contract['side'],backside_height_and_assembly_qualified=False)
    return result


def reference_tree_metrics(board, contract):
    """量测原生参考树及噪声投影内原语；铜几何不等同实际噪声或稳定性。"""
    import pcbnew as P
    budget = contract['routing_budget']
    items = [t for t in board.GetTracks() if t.GetNetname()==contract['power_net']]
    require(all(t.GetClass() in ('PCB_TRACK','PCB_VIA') for t in items),
            'Unsupported reference-tree copper')
    noise = []
    for item in board.GetTracks():
        if item.GetNetname() in budget['noise_nets']:
            noise.append((item.GetEffectiveShape(P.F_Cu) if item.GetClass()=='PCB_VIA'
                          else item.GetEffectiveShape(),0))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() in budget['noise_nets']:
                noise.append((pad.GetEffectiveShape(pad.GetLayer()),0))
    for ref in budget['inductor_refs']:
        fp = board.FindFootprintByReference(ref)
        require(fp is not None, 'Missing reference-tree noise envelope: '+ref)
        fp.BuildCourtyardCaches()
        shape = fp.GetCourtyard(P.F_Cu)
        require(not shape.IsEmpty(), 'Missing native inductor courtyard: '+ref)
        half = max((g.GetWidth()//2 for g in fp.GraphicalItems() if g.GetLayer()==P.F_CrtYd),default=0)
        noise.append((shape,half))
    require(noise, 'Reference-tree noise projection is empty')
    clearance = round(budget['noise_projection_budget_mm']*1e6)
    coupled = []
    tracks = [t for t in items if t.GetClass()=='PCB_TRACK']
    vias = [t for t in items if t.GetClass()=='PCB_VIA']
    for item in items:
        is_via = item.GetClass()=='PCB_VIA'
        shape = item.GetEffectiveShape(P.F_Cu) if is_via else item.GetEffectiveShape()
        if any(shape.Collide(other,clearance+half) for other,half in noise):
            if is_via:
                at = item.GetPosition()
                row = ['via',item.GetNetname(),at.x,at.y,item.GetWidth(P.F_Cu),item.GetDrill()]
            else:
                a,b = item.GetStart(),item.GetEnd()
                row = ['track',item.GetNetname(),board.GetLayerName(item.GetLayer()),a.x,a.y,b.x,b.y,item.GetWidth()]
            coupled.append(row)
    return dict(total_track_length_mm=sum(t.GetLength() for t in tracks)/1e6,
                via_count=len(vias),track_layers=sorted({board.GetLayerName(t.GetLayer()) for t in tracks}),
                coupled_copper=sorted(coupled),noise_projection_budget_mm=budget['noise_projection_budget_mm'],
                actual_noise_and_stability_qualified=False)


def inspect_reference_filter(board, contract, groups=None):
    """SY7636A参考脚只保留已审单颗100n滤波，拒绝大容量或额外并联。"""
    require(contract['maximum_nominal_capacitance_uf'] == .1,
            'PMIC reference capacitance limit differs')
    cap = board.FindFootprintByReference(contract['cap'])
    require(cap is not None, 'Missing PMIC reference filter')
    value = re.match(r'^\s*([\d.]+)\s*([pnuµm])(?:f)?(?:[/\s]|$)',cap.GetValue(),re.I)
    require(value is not None, 'Unknown PMIC reference capacitance')
    nominal = float(value[1])*{'p':1e-6,'n':.001,'u':1,'µ':1,'m':1000}[value[2].lower()]
    require(0 < nominal <= contract['maximum_nominal_capacitance_uf']+1e-12,
            'PMIC reference filter exceeds 0.1uF')
    fitted = []
    for fp in board.GetFootprints():
        if not fp.GetReference().startswith('C') or fp.IsDNP():
            continue
        nets = {p.GetNetname() for p in fp.Pads() if p.GetNumber()}
        if nets == {contract['power_net'],'GND'}:
            fitted.append(fp.GetReference())
    require(fitted == [contract['cap']], 'Unexpected parallel PMIC reference filter')
    result = inspect_power_bypass(board,contract,groups)
    result.update(nominal_capacitance_uf=nominal,fitted_reference_caps=fitted,
                  supplier_current_revision_accepted=False)
    if 'routing_budget' in contract:
        budget = contract['routing_budget']
        metrics = reference_tree_metrics(board,contract)
        require(metrics['total_track_length_mm']<=budget['maximum_total_track_length_mm']+1e-6,
                'Reference tree exceeds the reviewed total-copper budget')
        require(metrics['via_count']<=budget['maximum_via_count'],
                'Reference tree exceeds the reviewed via budget')
        permitted = {tuple(row) for row in budget['permitted_coupled_copper']}
        require(all(tuple(row) in permitted for row in metrics['coupled_copper']),
                'Unreviewed reference copper enters the noise projection')
        result['reference_tree'] = metrics
    return result


def inspect_pmic_analog_shield(board, contract):
    """只允许完整参考地夹在F噪声铜和内层VREF之间；孔、线圈与同层不豁免。"""
    import pcbnew as P
    from r25_router.apply_single_r27_layout_eco import reference_connected_ground_fills
    require(contract['clearance_mm']==.5 and contract['ground_margin_mm']==.2
            and contract['shape_tolerance_um']==2, 'PMIC analog geometry budgets differ')
    require(board.GetCopperLayerCount()==4, 'PMIC shield requires the reviewed four layers')
    noise, sensitive = [], []
    def add(kind, net, layer, shape, identity):
        row = (kind,net,layer,shape,identity)
        if net in contract['noise_nets']:
            noise.append(row)
        if net in contract['sensitive_nets']:
            sensitive.append(row)
    for item in board.GetTracks():
        via = item.GetClass()=='PCB_VIA'
        if via:
            at = item.GetPosition()
            identity = [at.x,at.y,item.GetWidth(P.F_Cu),item.GetDrill()]
        else:
            a,b = item.GetStart(),item.GetEnd()
            identity = [a.x,a.y,b.x,b.y,item.GetWidth()]
        add('via' if via else 'track',item.GetNetname(),None if via else item.GetLayer(),
            item.GetEffectiveShape(P.F_Cu) if via else item.GetEffectiveShape(),identity)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            for layer in [P.F_Cu,P.In1_Cu,P.In2_Cu,P.B_Cu]:
                if pad.IsOnLayer(layer) and pad.FlashLayer(layer):
                    add('pad',pad.GetNetname(),layer,pad.GetEffectiveShape(layer),
                        [fp.GetReference(),pad.GetNumber()])
    for ref in contract['inductor_refs']:
        fp = board.FindFootprintByReference(ref)
        require(fp is not None, 'Missing PMIC inductor envelope: '+ref)
        fp.BuildCourtyardCaches()
        shape = P.SHAPE_POLY_SET(fp.GetCourtyard(P.F_Cu))
        require(not shape.IsEmpty(), 'Missing native PMIC inductor courtyard: '+ref)
        half = max((g.GetWidth()//2 for g in fp.GraphicalItems()
                    if g.GetLayer()==P.F_CrtYd),default=0)
        shape.Inflate(half,P.CORNER_STRATEGY_ROUND_ALL_CORNERS,500)
        noise.append(('inductor','',None,shape,[ref]))
    require(noise and sensitive, 'Missing PMIC noise or sensitive copper')
    def polygon(shape):
        result = P.SHAPE_POLY_SET()
        shape.TransformToPolygon(result,500,P.ERROR_OUTSIDE)
        return result
    def inflate(shape, amount):
        result = P.SHAPE_POLY_SET(shape)
        result.Inflate(amount,P.CORNER_STRATEGY_ROUND_ALL_CORNERS,500)
        return result
    def hull(first, second):
        # 整数坐标单调链；偏移、裁切及差集均复用KiCad原生多边形接口。
        points = sorted({(s.Outline(i).CPoint(j).x,s.Outline(i).CPoint(j).y)
                         for s in [first,second] for i in range(s.OutlineCount())
                         for j in range(s.Outline(i).PointCount())})
        def cross(a,b,c):
            return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        chains = []
        for sequence in [points,list(reversed(points))]:
            chain = []
            for at in sequence:
                while len(chain)>1 and cross(chain[-2],chain[-1],at)<=0:
                    chain.pop()
                chain.append(at)
            chains.append(chain[:-1])
        result = P.SHAPE_POLY_SET()
        result.NewOutline()
        for x,y in chains[0]+chains[1]:
            result.Append(x,y)
        return result
    def continuous_tracks(items):
        # 同网同层连续铜先合并，分割同一走线不能缩小必须覆盖的地铜走廊。
        joined, result = {}, [row for row in items if row[0]!='track']
        for kind,net,layer,shape,identity in items:
            if kind=='track':
                joined.setdefault((net,layer),P.SHAPE_POLY_SET()).BooleanAdd(polygon(shape))
        for (net,layer),whole in sorted(joined.items()):
            for index in range(whole.OutlineCount()):
                patch=P.SHAPE_POLY_SET();patch.AddOutline(whole.Outline(index))
                for hole in range(whole.HoleCount(index)):
                    patch.AddHole(whole.Hole(index,hole))
                result.append(('track',net,layer,patch,['continuous_track_patch',index]))
        return result
    noise, sensitive = continuous_tracks(noise), continuous_tracks(sensitive)
    ground, rows = None, []
    for kind,net,layer,shape,identity in sensitive:
        for other,other_net,other_layer,other_shape,other_identity in noise:
            if not shape.Collide(other_shape,500000):
                continue
            require(kind=='track' and net==contract['reference_net']
                    and layer in [P.In2_Cu,P.B_Cu] and other in ['track','pad']
                    and other_layer==P.F_Cu,
                    'Unshielded PMIC sensitive copper enters the noise projection')
            receiver, source = polygon(shape), polygon(other_shape)
            rpart, spart = P.SHAPE_POLY_SET(receiver), P.SHAPE_POLY_SET(source)
            rpart.BooleanIntersection(inflate(source,500000))
            spart.BooleanIntersection(inflate(receiver,500000))
            if rpart.Area()==0 or spart.Area()==0:
                continue
            if ground is None:
                ground = P.SHAPE_POLY_SET()
                for ly,fill in reference_connected_ground_fills(board):
                    if ly==P.In1_Cu:
                        ground.BooleanAdd(fill)
                require(not ground.IsEmpty(), 'Missing reference-connected In1 PMIC shield')
                ground = inflate(ground,2000)
            corridor = inflate(hull(rpart,spart),200000)
            area = corridor.Area()
            corridor.BooleanSubtract(ground)
            require(corridor.Area()<=100000,
                    'PMIC source/receiver ground corridor crosses a plane gap')
            rows.append(dict(receiver=[kind,net,board.GetLayerName(layer),identity],
                             noise_source=[other,other_net,'F.Cu',other_identity],
                             required_ground_area_mm2=area/1e12))
    return dict(coupled_pairs=rows,shielded_pair_count=len(rows),
                reference_ground='U501.57 / native-connected In1.Cu fill',
                clearance_mm=.5,ground_margin_mm=.2,shape_tolerance_um=2,
                interposed_ground_checked=ground is not None,
                native_ground_geometry_passed=True,actual_noise_and_stability_qualified=False)


def inspect_source_pose_envelopes(board, contract):
    """核对全部源迁位/新增器件与全板同面器件的原生庭院及250um回退包络零重叠；不声称供应商极值公差资格。"""
    import pcbnew as P
    require(contract['fallback_margin_mm'] == .25, 'Source pose fallback margin differs')
    moved = list(contract['moved_refs'])
    added = list(contract['added_refs'])
    checked = sorted(set(moved) | set(added))
    require(len(moved) == 54 and len(added) == 12 and len(checked) == 66,
            'Reviewed source pose inventory differs')
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    require(set(checked) <= set(fps), 'Missing reviewed source-pose footprint')
    margin_nm = round(contract['fallback_margin_mm'] * 1e6)
    fallback_refs = []
    envs = {}
    for ref, fp in sorted(fps.items()):
        fp.BuildCourtyardCaches()
        for side, ctyd_layer, fab_layer, name in [
            (P.F_Cu, P.F_CrtYd, P.F_Fab, 'F.Cu'),
            (P.B_Cu, P.B_CrtYd, P.B_Fab, 'B.Cu'),
        ]:
            pads = [p for p in fp.Pads() if p.IsOnLayer(side)]
            if not pads:
                continue
            poly = P.SHAPE_POLY_SET(fp.GetCourtyard(side))
            if not poly.IsEmpty():
                half = max((g.GetWidth() // 2 for g in fp.GraphicalItems()
                            if g.GetLayer() == ctyd_layer), default=0)
                if half:
                    poly.Inflate(half, P.CORNER_STRATEGY_ROUND_ALL_CORNERS, 500)
                envs[(ref, name)] = (poly, poly.BBox())
            else:
                fallback_refs.append(f'{ref}:{name}')
                boxes = [p.GetEffectiveShape(side).BBox() for p in pads]
                boxes += [g.GetBoundingBox() for g in fp.GraphicalItems() if g.GetLayer() == fab_layer]
                x1 = min(b.GetLeft() for b in boxes) - margin_nm
                y1 = min(b.GetTop() for b in boxes) - margin_nm
                x2 = max(b.GetRight() for b in boxes) + margin_nm
                y2 = max(b.GetBottom() for b in boxes) + margin_nm
                poly = P.SHAPE_POLY_SET()
                poly.NewOutline()
                for x, y in [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]:
                    poly.Append(x, y)
                envs[(ref, name)] = (poly, poly.BBox())
    clashes = []
    bbox_false_positives = []
    checked_set = set(checked)
    items = sorted(envs.items())
    for idx, ((r1, s1), (p1, b1)) in enumerate(items):
        for (r2, s2), (p2, b2) in items[idx + 1:]:
            if s1 != s2 or (r1 not in checked_set and r2 not in checked_set):
                continue
            if b1.Intersects(b2):
                if p1.Collide(p2, 0):
                    clashes.append([r1, r2])
                else:
                    bbox_false_positives.append([r1, r2])
    require(not clashes, f'Source-pose envelope clashes remain: {clashes}')
    return dict(clashes=clashes, bounding_box_false_positives=bbox_false_positives,
                fallback_refs=fallback_refs, fallback_margin_mm=contract['fallback_margin_mm'],
                moved_count=len(moved), added_count=len(added), checked_pose_count=len(checked),
                supplier_maximum_envelopes_and_tolerance_qualified=False)


def inspect_backside_smt_clearances(board, contract):
    """核对背面6颗贴片器件与25个裸测点/调试焊盘的禁布净空与高度上限；实物背壳避空及<=7mm正公差仍待资格化。"""
    import pcbnew as P
    expected = sorted(contract['expected_populated_refs'])
    expected_tp = sorted(contract['expected_bare_testpoint_refs'])
    thickness_map = contract['max_thickness_mm_by_ref']
    require(sorted(thickness_map) == expected, 'Backside thickness inventory differs')
    populated, testpoints = [], []
    rows = []
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        ref = fp.GetReference()
        pads_b = [p for p in fp.Pads() if p.IsOnLayer(P.B_Cu) and not p.IsOnLayer(P.F_Cu)]
        if not pads_b:
            continue
        is_bare = bool(fp.GetAttributes() & P.FP_EXCLUDE_FROM_BOM)
        if is_bare:
            testpoints.append(ref)
            continue
        if fp.IsDNP() or not (fp.GetAttributes() & P.FP_SMD):
            continue
        populated.append(ref)
        require(ref in thickness_map, f'Backside populated SMT inventory differs: {ref}')
        boxes = [p.GetEffectiveShape(P.B_Cu).BBox() for p in pads_b]
        boxes += [g.GetBoundingBox() for g in fp.GraphicalItems() if g.GetLayer() == P.B_Fab]
        x1, y1 = min(b.GetLeft() for b in boxes) / 1e6, min(b.GetTop() for b in boxes) / 1e6
        x2, y2 = max(b.GetRight() for b in boxes) / 1e6, max(b.GetBottom() for b in boxes) / 1e6
        bat_dx = max(0.0, x1 - contract['battery_bay_max_x_mm'])
        bat_dy = max(0.0, y1 - contract['battery_bay_max_y_mm'])
        bat_dist = (bat_dx ** 2 + bat_dy ** 2) ** 0.5
        ur_dy = max(0.0, y1 - contract['upper_right_bay_max_y_mm'])
        max_z = float(thickness_map[ref])
        require(bat_dist >= contract['min_battery_bay_clearance_mm'],
                f'Backside SMT {ref} encroaches on battery bay clearance')
        require(ur_dy >= contract['min_upper_right_bay_clearance_mm'],
                f'Backside SMT {ref} encroaches on upper-right support bay clearance')
        require(0 < max_z <= contract['maximum_component_thickness_mm'],
                f'Backside SMT {ref} exceeds reviewed backside component thickness budget')
        rows.append(dict(ref=ref, value=fp.GetValue(),
                         x_mm=round(P.ToMM(fp.GetPosition().x), 4),
                         y_mm=round(P.ToMM(fp.GetPosition().y), 4),
                         rot_deg=round(fp.GetOrientationDegrees(), 2),
                         bbox_mm=[round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)],
                         battery_bay_clearance_mm=round(bat_dist, 4),
                         upper_right_bay_clearance_mm=round(ur_dy, 4),
                         max_datasheet_thickness_mm=max_z))
    require(sorted(populated) == expected, f'Backside populated SMT inventory differs: {populated}')
    require(sorted(testpoints) == expected_tp, f'Backside bare testpoint inventory differs: {testpoints}')
    return dict(populated_count=len(rows), bare_testpoint_count=len(testpoints),
                populated_parts=rows, bare_testpoint_refs=sorted(testpoints),
                max_populated_thickness_mm=max(r['max_datasheet_thickness_mm'] for r in rows),
                min_battery_bay_clearance_mm=min(r['battery_bay_clearance_mm'] for r in rows),
                rear_shell_local_relief_required=True,
                backside_height_and_assembly_qualified=False,
                actual_battery_full_panel_positive_tolerance_7mm_qualified=False)


def inspect_single(candidate, spec):
    """以源针序、独立原理图网表和原生物理连接组检查 Single。"""
    import pcbnew as P
    spec = {**spec, **spec.get('layout_ecos',{}).get(spec['revision'],{}).get('inspection_overrides',{})}
    plan = json.loads(CONTRACT.read_text())
    validate(plan)
    board = P.LoadBoard(str(candidate / 'Single.kicad_pcb'))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    require(not set(spec['removed_connectors']) & set(fps), 'Old interboard connectors remain')
    require(board.GetCopperLayerCount() == 4, 'Expected four copper layers')
    require(not any(t.GetClass() == 'PCB_TRACK' and t.GetLayer() == P.In1_Cu
                    and t.GetNetname() != 'GND' for t in board.GetTracks()), 'Signal on In1.Cu')
    xml = candidate / 'Single-independent-netlist.xml'
    run_cli(['sch', 'export', 'netlist', '--format', 'kicadxml', '--output', xml,
             candidate / 'Single.kicad_sch'], candidate / 'Single-independent-netlist.log')
    root = ET.parse(xml).getroot()
    actual = {(n.get('ref'), n.get('pin')): net.get('name')
              for net in root.findall('nets/net') for n in net.findall('node')}
    def normal(net):
        return '' if not net or net.startswith('unconnected-') else net
    def pads(ref, pin):
        require(ref in fps, 'Missing part: ' + ref)
        found = [p for p in fps[ref].Pads() if p.GetNumber() == str(pin)]
        require(found, 'Missing pad: ' + ref + '.' + str(pin))
        return found
    def expect(ref, pin, net):
        require(all(normal(p.GetNetname()) == net for p in pads(ref, pin)),
                'PCB pin mismatch: ' + ref + '.' + str(pin))
        require(normal(actual.get((ref, str(pin)))) == net,
                'Schematic pin mismatch: ' + ref + '.' + str(pin))
    for gpio, pin in GPIO_PACKAGE.items():
        expect('U501', pin, plan['gpio'][str(gpio)]['net'])
    for pin in (28, 38, 39, 40, 41, 42):
        expect('U501', pin, '')
    for pin, net in enumerate(PANEL_PINS, 1):
        expect('J820', pin, net)
    for index, ref in enumerate(('U710', 'U711')):
        require(fps[ref].GetValue() == 'SGM330A-YTS/TR', 'Wrong mux identity')
        for channel, triple in zip(plan['mux']['channels'][index * 4:index * 4 + 4],
                                   ((2, 3, 4), (5, 6, 7), (11, 10, 9), (14, 13, 12))):
            for pin, key in zip(triple, ('select_0_net', 'select_1_net', 'common_net')):
                expect(ref, pin, channel[key])
        for pin, net in {1:'P47_BUS_SELECT', 8:'GND', 15:'P47_BUS_OE_N', 16:'3V3_AON'}.items():
            expect(ref, pin, net)
    require(fps['U501'].GetValue() == 'ESP32-S3R8', 'Wrong MCU memory variant')
    require(fps['U506'].GetValue() == 'GD25Q128ESIG', 'Wrong 16MB flash')
    expect('U810', 49, '')
    expect('U810', 21, 'P47_HV_EN')
    for pin in (8, 32, 41, 48):
        expect('U810', pin, 'GND')
    expect('U811', 4, 'P47_HV_EN')
    groups = pad_components(board)
    bypasses = [inspect_output_bypass(board,c,groups) for c in spec.get('output_bypasses',[])]
    input_bypasses = [inspect_input_bypass(board,c,groups) for c in spec.get('input_bypasses',[])]
    power_bypasses = [inspect_power_bypass(board,c,groups) for c in spec.get('power_bypasses',[])]
    reference_filters = [inspect_reference_filter(board,c,groups) for c in spec.get('reference_filters',[])]
    group_for = {u:g for g in groups for u in g}
    links = []
    for ref, pin, other_ref, other_pin in spec['critical_links'] + spec.get('layout_critical_links', []):
        a, b = pads(ref, pin), pads(other_ref, other_pin)
        linked = all(str(y.m_Uuid.AsString()) in group_for[str(x.m_Uuid.AsString())]
                     for x in a for y in b)
        require(linked, f'Open critical path: {ref}.{pin} -> {other_ref}.{other_pin}')
        links.append({'from':ref+'.'+pin, 'to':other_ref+'.'+other_pin, 'connected':linked})
    ground = inspect_ground_returns(board, 'U501', '57',
                                   [('C804','2'), ('J820','9'), ('J820','22'), ('R809','2'),
                                    ('R810','2'), ('U810','32'), ('U810','41')])
    require(ground['all_ground_pads_connected_to_reference']
            and ground['ground_pad_count'] == spec['required_ground_pad_count'], 'Incomplete ground')
    bom = verify_board_mainland_compliance(candidate, 'Single')
    require(bom['all_passed'], 'BOM identity audit failed')
    geometry = inspect_board_native(candidate, 'Single')
    vip = []
    for target in spec['via_in_pad']['targets']:
        pad = pads(target['ref'], target['pin'])[0]
        found = [v for v in board.GetTracks() if v.GetClass() == 'PCB_VIA'
                 and pad.HitTest(v.GetPosition()) and v.GetNetname() == pad.GetNetname()]
        require(len(found) == target['count'], 'Prescribed via-in-pad inventory differs')
        for via in found:
            require(abs(P.ToMM(via.GetDrill())-target['drill_mm']) < 1e-6
                    and abs(P.ToMM(via.GetWidth(P.F_Cu))-target['diameter_mm']) < 1e-6,
                    'Prescribed via-in-pad geometry differs')
            vip.append({'uuid':via.m_Uuid.AsString(), 'ref':target['ref'], 'pin':target['pin'],
                        'x_mm':P.ToMM(via.GetPosition().x), 'y_mm':P.ToMM(via.GetPosition().y),
                        'diameter_mm':target['diameter_mm'], 'drill_mm':target['drill_mm'],
                        'process':spec['via_in_pad']['process']})
    dogbone = []
    for target in spec['via_in_pad'].get('external_dogbone_vias', []):
        pad = pads(target['ref'], target['pin'])[0]
        in_pad = [v for v in board.GetTracks() if v.GetClass() == 'PCB_VIA' and pad.HitTest(v.GetPosition())]
        require(not in_pad, f"Via-in-pad must be eliminated on {target['ref']}.{target['pin']}")
        found = [v for v in board.GetTracks() if v.GetClass() == 'PCB_VIA'
                 and abs(P.ToMM(v.GetPosition().x) - target['x_mm']) < 1e-3
                 and abs(P.ToMM(v.GetPosition().y) - target['y_mm']) < 1e-3
                 and v.GetNetname() == pad.GetNetname()]
        require(len(found) == 1, f"Missing external dog-bone via for {target['ref']}.{target['pin']}")
        via = found[0]
        require(abs(P.ToMM(via.GetDrill())-target['drill_mm']) < 1e-6
                and abs(P.ToMM(via.GetWidth(P.F_Cu))-target['diameter_mm']) < 1e-6,
                'Dog-bone via geometry differs')
        dogbone.append({'uuid':via.m_Uuid.AsString(), 'ref':target['ref'], 'pin':target['pin'],
                        'x_mm':P.ToMM(via.GetPosition().x), 'y_mm':P.ToMM(via.GetPosition().y),
                        'diameter_mm':target['diameter_mm'], 'drill_mm':target['drill_mm']})
    bay = spec.get('battery_bay_clearance')
    if bay:
        require(bay.get('study_only_not_supplier_qualified') is True,
                'Battery study envelope must not claim supplier qualification without exact battery pack drawing')
        edge_pts = []
        for d in board.GetDrawings():
            if d.GetLayer() == P.Edge_Cuts:
                edge_pts.append((round(P.ToMM(d.GetStart().x), 3), round(P.ToMM(d.GetStart().y), 3)))
                edge_pts.append((round(P.ToMM(d.GetEnd().x), 3), round(P.ToMM(d.GetEnd().y), 3)))
        require(edge_pts and all(x >= bay['upper_left_pcb_step_min_x_mm'] - 1e-3
                                 or y >= bay['upper_left_pcb_step_max_y_mm'] - 1e-3
                                 for x, y in edge_pts),
                'PCB outline encroaches on 323576 battery bay')
        envs = bay.get('battery_assembly_envelopes_mm', {})
        pack = envs.get('BATTERY_PACK')
        pcm = envs.get('BATTERY_PCM')
        require(pack and abs((pack[2] - pack[0]) - 35.0) < 1e-3 and abs((pack[3] - pack[1]) - 76.0) < 1e-3,
                'BATTERY_PACK must preserve full 35.0 x 76.0 mm 323576 body dimensions')
        require(pcm and abs((pcm[2] - pcm[0]) - 30.0) < 1e-3 and abs((pcm[3] - pcm[1]) - 3.8) < 1e-3,
                'BATTERY_PCM must preserve full 30.0 x 3.8 mm protection board dimensions')
        for part_name, (bx1, by1, bx2, by2) in envs.items():
            require(bx1 >= 1.1 and by1 >= 1.1,
                    f'Battery assembly sub-part {part_name} encroaches on housing perimeter wall')
            require(bx2 <= bay['upper_left_pcb_step_min_x_mm'] + 1e-3
                    and by2 <= bay['upper_left_pcb_step_max_y_mm'] + 1e-3,
                    f'Battery assembly sub-part {part_name} overlaps PCB step')
    ur_bay = spec.get('upper_right_support_bay')
    if ur_bay:
        require(ur_bay.get('study_only_not_supplier_qualified') is True,
                'Upper-right support bay must be marked study_only_not_supplier_qualified')
        ur_xy = ur_bay.get('envelopes_xy_mm', {})
        ur_z = ur_bay.get('envelopes_z_mm', {})
        for part_name in ('UPPER_RIGHT_RIB_GRID', 'UPPER_RIGHT_PORON_PAD', 'SPEAKER_BOX_1511', 'FPC_ANTENNA_2G4'):
            require(part_name in ur_xy and part_name in ur_z,
                    f'Missing Option 1 upper-right support component {part_name}')
            ux1, uy1, ux2, uy2 = ur_xy[part_name]
            uz1, uz2 = ur_z[part_name]
            require(ux1 >= ur_bay['battery_right_edge_max_x_mm'] + 1e-3,
                    f'{part_name} overlaps 323576 battery assembly')
            require(uy2 <= ur_bay['pcb_top_edge_min_y_mm'] - 1e-3,
                    f'{part_name} overlaps Single.kicad_pcb top edge')
            require(ux2 <= 73.9 - 1e-3 and uy1 >= 1.1 + 1e-3,
                    f'{part_name} encroaches on rear shell perimeter wall')
            require(uz1 >= 0.55 - 1e-3 and uz2 <= ur_bay['coplanar_support_top_z_mm'] + 1e-3,
                    f'{part_name} exceeds Z support envelope')
        require(abs(ur_z['UPPER_RIGHT_PORON_PAD'][1] - ur_bay['coplanar_support_top_z_mm']) < 1e-3,
                'UPPER_RIGHT_PORON_PAD top must be coplanar with 3.95mm battery top surface')
    process_inventory = None
    if 'complete_via_in_pad_inventory' in spec:
        process_inventory = inspect_solder_joint_vias(board,spec['via_in_pad']['process'])
        def signature(row):
            return [row['net'],round(row['x_mm'],6),round(row['y_mm'],6),
                    round(row['diameter_mm'],6),round(row['drill_mm'],6),row['soldered_contacts']]
        actual_inventory = sorted([signature(row) for row in process_inventory['filled_and_capped_vias']])
        require(actual_inventory == spec['complete_via_in_pad_inventory']['soldered_vias'],
                'Complete solder-joint via inventory differs')
        require(process_inventory['filled_cap_via_count'] == len(actual_inventory),
                'Duplicate solder-joint via inventory')
        vip = process_inventory['filled_and_capped_vias']
    supplies, manual = [], []
    for ref, fp in sorted(fps.items()):
        if fp.IsDNP() or fp.GetAttributes() & P.FP_EXCLUDE_FROM_BOM:
            continue
        fields = {f.GetName():f.GetText() for f in fp.GetFields()}
        row = {'ref':ref, 'manufacturer':fields.get('Manufacturer',''), 'mpn':fields.get('MPN',''),
               'value':fp.GetValue(), 'footprint':fp.GetFPIDAsString(), 'lcsc':fields.get('LCSC',''),
               'supply_status':fields.get('PandaSupplyStatus','')}
        if ref in spec['manual_assembly_refs']:
            manual.append(row)
        elif not row['lcsc']:
            supplies.append(row)
    analog_shield = (inspect_pmic_analog_shield(board,spec['pmic_analog_shield'])
                     if 'pmic_analog_shield' in spec else None)
    pose_envelopes = (inspect_source_pose_envelopes(board,spec['source_pose_envelope_screen'])
                      if 'source_pose_envelope_screen' in spec else None)
    backside_clearance = (inspect_backside_smt_clearances(board,spec['backside_smt_clearance'])
                          if 'backside_smt_clearance' in spec else None)
    return board, groups, {'ground':ground, 'critical_links':links, 'bom':bom,
                           'geometry':geometry, 'via_in_pad':vip, 'pending_supply':supplies,
                           'required_post_smt':manual,
                           **({'output_bypasses':bypasses} if bypasses else {}),
                           **({'input_bypasses':input_bypasses} if input_bypasses else {}),
                           **({'power_bypasses':power_bypasses} if power_bypasses else {}),
                           **({'reference_filters':reference_filters} if reference_filters else {}),
                           **({'solder_joint_via_process':process_inventory} if process_inventory else {}),
                           **({'pmic_analog_shield':analog_shield} if analog_shield else {}),
                           **({'source_pose_envelopes':pose_envelopes} if pose_envelopes else {}),
                           **({'backside_smt_clearance':backside_clearance} if backside_clearance else {})}


def write_csv(path, rows):
    require(rows, 'Missing required manufacturing rows')
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(source, output, spec_path=SPEC, revision=None):
    import wx
    app = wx.GetApp() or wx.App(False)
    import pcbnew as P
    source, output = Path(source).resolve(), Path(output).resolve()
    spec = json.loads(Path(spec_path).read_text())
    revision = revision or spec['revision']
    require(revision in ('R26','R27','R28','R29','R30','R31','R32','R33','R34','R35','R36','R37','R38','R39'), 'Unknown Single layout revision')
    verify_inputs(source, spec)
    require(not output.exists() and not output.is_relative_to(source)
            and not source.is_relative_to(output), 'Choose a new independent output directory')
    require(not output.is_relative_to(REPO) or output.is_relative_to(REPO / '.work'),
            'Generated candidates belong in .work or external delivery')
    output.mkdir(parents=True)
    for relative in spec['input_sha256']:
        dest = output / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, dest)
    pcb = output / 'Single.kicad_pcb'
    before = P.LoadBoard(str(pcb))
    old_groups = pad_components(before)
    eco_binding = None
    if revision in ('R27','R28','R29','R30','R31','R32','R33','R34','R35','R36','R37','R38','R39'):
        from r25_router.apply_single_r27_layout_eco import apply_layout_eco, apply_library_edits, verify_input, copper_fingerprint
        eco_binding = spec.get('layout_ecos', {}).get(revision, spec['layout_eco'])
        delta_path = HERE / eco_binding['source']
        require(sha(delta_path) == eco_binding['sha256'], revision + ' layout source differs')
        delta = json.loads(delta_path.read_text())
        verify_input(pcb, delta)
        apply_library_edits(output, delta)
        eco_keepalive = apply_layout_eco(before, delta, output)
        P.SaveBoard(str(pcb), before)
        require(native_semantic_fingerprint(pcb) == delta['target_semantic_fingerprint'],
                revision + ' replay geometry differs from the accepted native checkpoint')
        require(copper_fingerprint(before, delta.get('complete_zone_fingerprint', False)) == delta['target_copper_fingerprint'],
                revision + ' replay copper or reference zones differ')
    fingerprint = native_semantic_fingerprint(pcb)
    run_cli(['pcb','drc','--refill-zones','--save-board','--severity-all','--all-track-errors',
             '--schematic-parity','--exit-code-violations','--format','json','--output',
             output / 'Single-drc.json', pcb], output / 'Single-drc.log')
    run_cli(['sch','erc','--severity-all','--exit-code-violations','--format','json','--output',
             output / 'Single-erc.json', output / 'Single.kicad_sch'], output / 'Single-erc.log')
    counts = counts_from_reports(json.loads((output/'Single-drc.json').read_text()),
                                 json.loads((output/'Single-erc.json').read_text()))
    require(not any(counts.values()), 'Single native checks are not all zero')
    require(native_semantic_fingerprint(pcb) == fingerprint, 'Native roundtrip changed intent')
    board, groups, inspection = inspect_single(output, {**spec,'revision':revision})
    additions = delta.get('added_footprints',[]) if eco_binding else []
    added_pads = [p.m_Uuid.AsString() for s in additions
                  for p in board.FindFootprintByReference(s['ref']).Pads() if p.GetNumber()]
    require(len(set(added_pads)) == len(added_pads), 'Duplicate added pad identity')
    require(preserves_groups_with_additions(old_groups,groups,added_pads),
            'Original native pad inventory or groups differ')
    if revision in ('R27','R28','R29','R30','R31','R32','R33','R34','R35','R36','R37','R38','R39'):
        from r25_router.apply_single_r27_layout_eco import inspect_usb_reference
        require(copper_fingerprint(board, delta.get('complete_zone_fingerprint', False)) == delta['target_copper_fingerprint'],
                revision + ' native roundtrip changed copper or reference zones')
        if revision in ('R30','R31','R32','R33','R34','R35','R36','R37','R38','R39'):
            from r25_router.apply_single_r27_layout_eco import (
                reference_connected_ground_fills, inspect_signal_references,
                inspect_panel_clock_references,
            )
            ground_fills = reference_connected_ground_fills(board)
            inspection['signal_references'] = inspect_signal_references(
                board, json.loads(CONTRACT.read_text()), ground_fills)
            inspection['panel_clock_references'] = inspect_panel_clock_references(board, ground_fills)
            if revision in ('R31','R32','R33','R34','R35','R36','R37','R38','R39'):
                from r25_router.apply_single_r27_layout_eco import inspect_clock_ground_stitches
                inspection['clock_ground_stitches'] = inspect_clock_ground_stitches(
                    board, delta['clock_ground_stitches'], ground_fills)
        elif revision in ('R28','R29'):
            from r25_router.apply_single_r27_layout_eco import inspect_signal_references
            inspection['signal_references'] = inspect_signal_references(board, json.loads(CONTRACT.read_text()))
        else:
            inspection['usb_reference'] = inspect_usb_reference(board)
    orderpack = output / 'orderpack'
    export_jlc_orderpack(output, orderpack, revision=revision)
    smt_count = sum(bool(f.GetAttributes() & P.FP_SMD) and not f.IsDNP()
                    and not f.GetAttributes() & (P.FP_EXCLUDE_FROM_BOM | P.FP_EXCLUDE_FROM_POS_FILES)
                    and f.GetReference() not in spec['manual_assembly_refs'] for f in board.GetFootprints())
    bypass_notes = ''.join(f'{b["cap"]} 是 {b["switch"]} 的局部输出去耦，位置与两端真实连接已核对；'
                          '其直流偏压、供料及实物瞬态仍待资格化。\n'
                          for b in inspection.get('output_bypasses',[]))
    bypass_notes += ''.join(f'{b["cap"]} 是 {b["switch"]} 的局部输入去耦，位置与两端真实连接已核对；'
                           '其直流偏压、供料及实物瞬态仍待资格化。\n'
                           for b in inspection.get('input_bypasses',[]))
    bypass_notes += ''.join(f'{b["cap"]} 是 {b["device"]} 的局部电源旁路（{b["side"]}），'
                           '位置与真实接点已核对；有效电容、瞬态及背面装配/高度仍待资格化。\n'
                           for b in inspection.get('power_bypasses',[]))
    bypass_notes += ''.join(f'{b["cap"]} 保持单颗100nF参考滤波并移至{b["side"]}；'
                           '不得另并联或增大容量，当前厂商版本与实物稳定性仍待资格化。\n'
                           for b in inspection.get('reference_filters',[]))
    write_csv(orderpack/'REQUIRED-VIA-IN-PAD.csv', inspection['via_in_pad'])
    write_csv(orderpack/'PENDING-SUPPLY.csv', inspection['pending_supply'])
    write_csv(orderpack/'REQUIRED-POST-SMT.csv', inspection['required_post_smt'])
    (orderpack/'MANUFACTURING-REQUIREMENTS.md').write_text(
        f'# Single 制造工艺要求\n\n{spec["date"]}，{revision}，Codex。\n\n'
        '四层、0.8 mm 标称、绿油、ENIG；详细层叠以 Single-job.gbrjob 为准。\n'
        '左上板阶为 X = 38.0..73.0 mm (Y = 32.0..83.5 mm)。323576 (35x76x3.2 mm) 仅为历史研究包络；其二维不重叠不代表实际可更换2050mAh电池的厂商、MPN、最大包络、引线/保护板/连接器或整机含正公差≤7mm资格。实际电池与完整屏幕规格仍待确认。\n'
        'C804.2 接地回流过孔保持盘外狗骨位置 (17.40, 104.80) (0.45/0.20 mm)。U501.57 原9颗0.50/0.25mm散热孔保持。\n'
        f'REQUIRED-VIA-IN-PAD.csv 本修订列出 {len(inspection["via_in_pad"])} 颗须处理的焊接盘过孔，需树脂塞孔+电镀盖帽 (FILLED_AND_COPPER_CAPPED_OR_SUPPLIER_APPROVED_EQUIVALENT) 或板厂CAM确认的等效工艺。填孔盖帽在四层板上需明确选择并核价，不能以普通塞油/盖油替代；确认前 supplier_process_accepted = false。\n'
        f'{smt_count} 个 SMT 器件见 BOM/CPL；PENDING-SUPPLY.csv 保留 {len(inspection["pending_supply"])} 个需客供/建档的物料，不能空贴。\n'
        f'{bypass_notes}'
        'BT301 必须使用工厂绝缘引脚/焊片组件，SMT 后安装（见 REQUIRED-POST-SMT.csv）；不得回流或直接焊裸电池。\n'
        'J201 为 MUP U22401-17 沉板式 USB-C 母座；上述工艺、供料及实际电池包/完整屏幕模组规格确认前，manufacturing_release 保持为 false。\n')
    manifest = {'schema':'panda47-single-rebuild-v1', 'revision':revision,
                'layout_eco':eco_binding,
                'source_spec_sha256':sha(spec_path), 'source_design_sha256':sha(CONTRACT),
                'input_sha256':spec['input_sha256'], 'counts':counts,
                'all_original_pad_groups_preserved':True, 'geometry_sha256':fingerprint,
                'inspection':inspection, 'manufacturing_release':False,
                'files_sha256':{str(f.relative_to(output)):sha(f) for f in sorted(output.rglob('*'))
                                if f.is_file()}}
    (output/'SINGLE-CHECKPOINT.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    verify_inputs(source, spec)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revision', choices=('R26','R27','R28','R29','R30','R31','R32','R33','R34','R35','R36','R37','R38','R39'), help='显式重建所选单板布局修订')
    args = parser.parse_args()
    spec_data = json.loads(SPEC.read_text())
    default = Path(spec_data['input_checkpoint'])
    if not default.exists() and 'version_directory' in spec_data:
        default = REPO / spec_data['version_directory']
    result = build(args.source or default, args.output, revision=args.revision)
    print(json.dumps({'counts':result['counts'], 'ground_pads':result['inspection']['ground']['ground_pad_count'],
                      'pending_supply':len(result['inspection']['pending_supply']),
                      'manufacturing_release':False}, indent=2))
