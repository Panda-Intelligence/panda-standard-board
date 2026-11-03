"""2026-11-02 Codex：从不可变 R26 回放经原生验收的单板布局修订。"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

DELTA_PATH = Path(__file__).with_name('single_r27_layout_delta.json')


def mm(value):
    """JSON 浮点值四舍五入到 KiCad 纳米，避免 .3999999999 被截小。"""
    return int(round(float(value) * 1_000_000))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_delta(path=DELTA_PATH):
    return json.loads(Path(path).read_text())


def verify_input(path, delta):
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    require(digest == delta['baseline_sha256'], 'Layout ECO requires the bound immutable R26 PCB')


def apply_layout_eco(board, delta=None, candidate=None):
    """保留原板规则、网表、轮廓与未涉及铜；只执行精确、可审查的几何增量。"""
    import pcbnew as P
    if delta is None:
        delta = load_delta()
    require(board.GetCopperLayerCount() == 4, 'R27 requires four layers')
    if 'baseline_copper_fingerprint' in delta:
        require(copper_fingerprint(board, delta.get('complete_zone_fingerprint', False)) == delta['baseline_copper_fingerprint'],
                'Expected bound R26 baseline copper')
    layers = {name:board.GetLayerID(name) for name in ('F.Cu','In1.Cu','In2.Cu','B.Cu')}
    copper = list(board.GetTracks())
    by_id = {t.m_Uuid.AsString():t for t in copper}
    removed = set(delta['removed_uuids'])
    updated = {s['uuid']:s for s in delta['updated_copper']}
    require(removed.isdisjoint(updated), 'Copper cannot be removed and updated together')
    require(removed | set(updated) <= set(by_id), 'Required original copper UUID is missing')
    # 新增器件使用已绑定的本地封装，先完成身份/针序验证再修改原板。
    additions = []
    addition_poses = {}
    seen_refs = set()
    for spec in delta.get('added_footprints', []):
        require(candidate is not None, 'Added footprint requires the candidate library')
        ref = spec['ref']
        require(ref not in seen_refs and board.FindFootprintByReference(ref) is None,
                'Added footprint reference already exists: '+ref)
        seen_refs.add(ref)
        relative = Path(spec['library_path'])
        require(not relative.is_absolute() and '..' not in relative.parts,
                'Added footprint library must be relative')
        path = Path(candidate) / relative
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == spec['library_sha256'],
                'Added footprint library differs: '+ref)
        footprint = P.FootprintLoad(str(path.parent), path.stem, bool(spec.get('preserve_uuid',False)))
        require(footprint is not None and footprint.GetValue() == spec['value'],
                'Added footprint value differs: '+ref)
        require(spec['side'] in ('F.Cu','B.Cu') and footprint.GetLayer() == P.F_Cu,
                'Added footprint requires an outer face and a normalized front library')
        properties = {f.GetName():f.GetText() for f in footprint.GetFields()}
        require(all(properties.get(k) == v for k,v in spec['properties'].items()),
                'Added footprint identity differs: '+ref)
        pads = list(footprint.Pads())
        require(len(pads) == len(spec['pins']) and {p.GetNumber() for p in pads} == set(spec['pins']),
                'Added footprint pin inventory differs: '+ref)
        if spec.get('preserve_uuid'):
            require(footprint.m_Uuid.AsString() == spec['native_uuid']
                    and {p.GetNumber():p.m_Uuid.AsString() for p in pads} == spec['pad_uuids'],
                    'Added footprint native identity differs: '+ref)
        for pad in pads:
            net = board.FindNet(spec['pins'][pad.GetNumber()])
            require(net is not None and net.GetNetCode() > 0, 'Added footprint net is missing')
            pad.SetNet(net)
        footprint.SetFPID(P.LIB_ID(*spec['fpid'].split(':',1)))
        footprint.SetReference(ref)
        footprint.SetPosition(P.VECTOR2I(mm(spec['x']),mm(spec['y'])))
        footprint.SetOrientationDegrees(spec['rot'])
        footprint.SetPath(P.KIID_PATH(spec['schematic_path']))
        additions.append(footprint)
        addition_poses[ref] = spec
    # 先验证全部动作，缺少源器件/铜时拒绝执行部分 ECO。
    for ref, pose in delta['footprint_poses'].items():
        fp = board.FindFootprintByReference(ref)
        require(fp is not None, 'Missing moved footprint: '+ref)
        require([mm(P.ToMM(fp.GetPosition().x)),mm(P.ToMM(fp.GetPosition().y))] == pose['before_xy_nm'],
                'Unexpected original pose: '+ref)
    field_edits = []
    seen_fields = set()
    for edit in delta.get('footprint_field_edits', []):
        fp = board.FindFootprintByReference(edit['ref'])
        require(fp is not None and fp.m_Uuid.AsString()==edit['native_uuid'],
                'Footprint field predecessor identity differs: '+edit['ref'])
        fields = [f for f in fp.GetFields() if f.GetName()==edit['field']]
        identity = (edit['ref'],edit['field'])
        require(identity not in seen_fields and len(fields)==1
                and fields[0].GetText()==edit['before'] and bool(edit['after']),
                'Footprint field predecessor differs: '+edit['ref'])
        seen_fields.add(identity)
        field_edits.append((fields[0],edit['after']))
    for spec in delta['updated_copper']+delta['added_tracks']+delta['added_vias']:
        net = board.FindNet(spec['net'])
        require(net is not None and net.GetNetCode() > 0, 'Missing original net: '+spec['net'])
        require(spec.get('layer') != 'In1.Cu' or spec['net']=='GND', 'Signal routing on ground plane')
    for footprint in additions:
        footprint.thisown = False
        board.Add(footprint)
        pose = addition_poses[footprint.GetReference()]
        if pose['side'] == 'B.Cu':
            # 官方翻面接口需要有效父板；翻面后恢复源声明的角度及针序位置。
            footprint.Flip(footprint.GetPosition(), False)
            footprint.SetOrientationDegrees(pose['rot'])
    for ref, pose in delta['footprint_poses'].items():
        fp = board.FindFootprintByReference(ref)
        if board.GetLayerName(fp.GetLayer()) != pose['side']:
            fp.Flip(fp.GetPosition(), False)
        fp.SetPosition(P.VECTOR2I(mm(pose['x']), mm(pose['y'])))
        fp.SetOrientationDegrees(pose['rot'])
    for field, value in field_edits:
        field.SetText(value)
    for edit in delta.get('silk_graphic_offsets', []):
        fp = board.FindFootprintByReference(edit['ref'])
        matches = [s for s in fp.GraphicalItems() if s.m_Uuid.AsString() == edit['uuid']]
        require(len(matches) == 1 and matches[0].GetLayer() == P.F_SilkS,
                'Missing bound footprint marker: ' + edit['ref'])
        mark = matches[0]
        bbox = mark.GetBoundingBox()
        require([bbox.GetLeft(), bbox.GetTop(), bbox.GetRight(), bbox.GetBottom()]
                == edit['before_bbox_nm'], 'Footprint marker predecessor differs')
        mark.Move(P.VECTOR2I(mm(edit['dx_mm']), mm(edit['dy_mm'])))
    for item in copper:
        u = item.m_Uuid.AsString()
        if u in removed:
            board.Delete(item)
        elif u in updated:
            _set_copper(item, updated[u], board, layers, P)
    # 新铜由 KiCad 分配 UUID，重建以纳米坐标和区定义的指纹验收。
    for spec in delta['added_tracks']+delta['added_vias']:
        require(spec['uuid'] not in by_id, 'R27 already applied or duplicate copper UUID')
        item = P.PCB_TRACK(board) if 'x1' in spec else P.PCB_VIA(board)
        _set_copper(item, spec, board, layers, P)
        item.thisown = False
        board.Add(item)
    original_zones = list(board.Zones())
    for spec in delta['added_zones']:
        require(not any(z.GetZoneName()==spec['name'] for z in original_zones), 'R27 zone already exists')
        zone = P.ZONE(board)
        zone.SetZoneName(spec['name'])
        zone.SetLayer(layers[spec['layers'][0]])
        zone.SetAssignedPriority(int(spec.get('priority', 0)))
        zone.SetIsRuleArea(bool(spec['rule']))
        if spec['rule']:
            zone.SetDoNotAllowTracks(bool(spec['no_tracks']))
            zone.SetDoNotAllowVias(bool(spec.get('no_vias', False)))
            zone.SetDoNotAllowPads(bool(spec.get('no_pads', False)))
            zone.SetDoNotAllowFootprints(bool(spec.get('no_footprints', False)))
            zone.SetDoNotAllowZoneFills(bool(spec.get('no_zone_fills', False)))
        else:
            zone.SetNet(board.FindNet('GND'))
            zone.SetLocalClearance(mm(.2))
            zone.SetMinThickness(mm(.15))
            zone.SetPadConnection(P.ZONE_CONNECTION_FULL)
            zone.SetThermalReliefGap(mm(.2))
            zone.SetThermalReliefSpokeWidth(mm(.25))
        for ring in spec['outline']:
            zone.Outline().NewOutline()
            points = ring[:-1] if ring[0]==ring[-1] else ring
            for x,y in points:
                zone.Outline().Append(mm(x),mm(y))
        for ring in spec.get('holes', []):
            hole = zone.Outline().NewHole(0)
            points = ring[:-1] if ring[0] == ring[-1] else ring
            for x,y in points:
                zone.Outline().Append(mm(x), mm(y), 0, hole)
        zone.thisown = False
        board.Add(zone)
    return copper + additions


def apply_library_edits(candidate, delta):
    """回放绑定的局部库图元和项目名称元数据，保留全部规则与库原UUID。"""
    candidate = Path(candidate).resolve()
    for edit in delta.get('library_edits', []) + delta.get('project_metadata_edits', []):
        relative = Path(edit['path'])
        require(not relative.is_absolute() and '..' not in relative.parts,
                'Library edit path must remain inside candidate')
        path = candidate / relative
        require(hashlib.sha256(path.read_bytes()).hexdigest() == edit['before_sha256'],
                'Local footprint library predecessor differs')
        text = path.read_text()
        for replacement in edit['replacements']:
            require(text.count(replacement['before']) == 1, 'Local library edit is not unique')
            text = text.replace(replacement['before'], replacement['after'], 1)
        require(hashlib.sha256(text.encode()).hexdigest() == edit['after_sha256'],
                'Local library target differs')
        path.write_text(text)
    created = []
    seen = set()
    for spec in delta.get('created_files', []):
        relative = Path(spec['path'])
        require(not relative.is_absolute() and '..' not in relative.parts,
                'New CAD file must remain inside candidate')
        path = candidate / relative
        require(relative not in seen and not path.exists(), 'New CAD file already exists')
        seen.add(relative)
        content = spec['content'].encode()
        require(hashlib.sha256(content).hexdigest() == spec['sha256'], 'New CAD file content differs')
        created.append((path,content))
    for path,content in created:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(content)


def _set_copper(item, spec, board, layers, P):
    item.SetNet(board.FindNet(spec['net']))
    if 'x1' in spec:
        require(item.GetClass()=='PCB_TRACK', 'Copper type changed')
        item.SetStart(P.VECTOR2I(mm(spec['x1']),mm(spec['y1'])))
        item.SetEnd(P.VECTOR2I(mm(spec['x2']),mm(spec['y2'])))
        item.SetWidth(mm(spec['w']))
        item.SetLayer(layers[spec['layer']])
    else:
        require(item.GetClass()=='PCB_VIA', 'Copper type changed')
        item.SetViaType(P.VIATYPE_THROUGH)
        item.SetLayerPair(P.F_Cu,P.B_Cu)
        item.SetPosition(P.VECTOR2I(mm(spec['x']),mm(spec['y'])))
        item.SetWidth(mm(spec['d']))
        item.SetDrill(mm(spec['drill']))


def inspect_usb_reference(board):
    """直接采样原生已铺 In2 地铜；只扣除 USB 自身换层孔的反焊盘范围。"""
    import pcbnew as P
    zones=[z for z in board.Zones() if z.GetZoneName()=='USB_REFERENCE_GND']
    require(len(zones)==1 and zones[0].GetNetname()=='GND' and zones[0].GetLayer()==P.In2_Cu,
            'Missing native In2 USB ground reference')
    vias=[v.GetPosition() for v in board.GetTracks() if v.GetClass()=='PCB_VIA'
          and v.GetNetname() in ('USB_DP','USB_DM')]
    sampled=excluded=0
    missing=[]
    for track in board.GetTracks():
        if track.GetClass()!='PCB_TRACK' or track.GetLayer()!=P.B_Cu or track.GetNetname() not in ('USB_DP','USB_DM'):
            continue
        a,b=track.GetStart(),track.GetEnd()
        steps=max(1,math.ceil(math.hypot(b.x-a.x,b.y-a.y)/mm(.1)))
        for i in range(steps+1):
            x,y=a.x+(b.x-a.x)*i/steps,a.y+(b.y-a.y)*i/steps
            if any(math.hypot(x-v.x,y-v.y)<mm(.6) for v in vias):
                excluded+=1
                continue
            sampled+=1
            if not zones[0].HitTestFilledArea(P.In2_Cu,P.VECTOR2I(round(x),round(y))):
                missing.append([x/1e6,y/1e6])
    require(sampled>500, 'USB reference sample coverage is incomplete')
    require(not missing, f'USB reference plane has {len(missing)} uncovered samples: {missing[:5]}')
    return dict(step_mm=.1,sampled=sampled,excluded_self_via_samples=excluded,
                self_via_exclusion_radius_mm=.6,uncovered_samples=missing)


def reference_connected_ground_fills(board, reference_ref='U501', reference_pin='57'):
    """按原生铜形接触合并铺铜片、地轨/孔/焊盘，拒把孤立的同名GND片当参考。"""
    import pcbnew as P
    layers = [P.F_Cu, P.In1_Cu, P.In2_Cu, P.B_Cu]
    parents = []
    def node():
        parents.append(len(parents))
        return len(parents)-1
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    def union(i,j):
        parents[find(i)] = find(j)
    fills = []
    for zone in board.Zones():
        if zone.GetIsRuleArea() or zone.GetNetname() != 'GND':
            continue
        for layer in layers:
            if not zone.IsOnLayer(layer):
                continue
            native = zone.GetFilledPolysList(layer)
            for index in range(native.OutlineCount()):
                shape = P.SHAPE_POLY_SET()
                shape.AddOutline(native.Outline(index))
                for hole in range(native.HoleCount(index)):
                    shape.AddHole(native.Hole(index,hole))
                fills.append((node(),layer,shape,shape.BBox()))
    items = []
    reference = None
    for track in board.GetTracks():
        if track.GetNetname() != 'GND':
            continue
        index = node()
        active = layers if track.GetClass() == 'PCB_VIA' else [track.GetLayer()]
        for layer in active:
            shape = track.GetEffectiveShape(layer)
            items.append((index,layer,shape,shape.BBox()))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() != 'GND':
                continue
            index = node()
            if fp.GetReference() == reference_ref and pad.GetNumber() == reference_pin:
                require(reference is None, 'Ambiguous reference ground pad')
                reference = index
            for layer in layers:
                if pad.IsOnLayer(layer):
                    shape = pad.GetEffectiveShape(layer)
                    items.append((index,layer,shape,shape.BBox()))
    require(reference is not None and fills, 'Missing native reference ground or filled copper')
    for group in [fills,items]:
        for i,(a,la,sa,ba) in enumerate(group):
            for b,lb,sb,bb in group[i+1:]:
                if a != b and la == lb and ba.Intersects(bb) and sa.Collide(sb,0):
                    union(a,b)
    for a,la,sa,ba in items:
        for b,lb,sb,bb in fills:
            if la == lb and ba.Intersects(bb) and sb.Collide(sa,0):
                union(a,b)
    connected = [(layer,shape) for index,layer,shape,_ in fills if find(index) == find(reference)]
    require(connected, 'No filled copper reaches the reference ground pad')
    return connected


def inspect_signal_references(board, plan, ground_fills=None):
    """采样SD两侧0.25mm和USB中心的实际连通参考铜，仅排除信号组自身孔附近。"""
    import pcbnew as P
    fills = ground_fills if ground_fills is not None else reference_connected_ground_fills(board)
    sd = set()
    for channel in plan['mux']['channels']:
        if channel['select_0_net'].startswith('SDMMC_'):
            sd.update([channel['common_net'],channel['select_0_net'],channel['select_0_net']+'_CARD'])
    require(len(sd) == 18, 'Expected all eighteen physical SD nets')
    records = {}
    for name,nets,references,offsets in [
            ('SD',sd,{P.F_Cu:P.In1_Cu,P.B_Cu:P.In2_Cu},[0,-.25,.25]),
            ('USB',{'USB_DP','USB_DM'},{P.B_Cu:P.In2_Cu},[0])]:
        vias = [v.GetPosition() for v in board.GetTracks()
                if v.GetClass()=='PCB_VIA' and v.GetNetname() in nets]
        sampled = excluded = excluded_offset = 0
        missing = []
        for track in board.GetTracks():
            if (track.GetClass() != 'PCB_TRACK' or track.GetNetname() not in nets
                    or track.GetLayer() not in references):
                continue
            a,b = track.GetStart(),track.GetEnd()
            dx,dy = b.x-a.x,b.y-a.y
            length = math.hypot(dx,dy)
            if not length:
                continue
            steps = max(1,math.ceil(length/mm(.1)))
            for index in range(steps+1):
                x,y = a.x+dx*index/steps,a.y+dy*index/steps
                if any(math.hypot(x-v.x,y-v.y)<mm(.6) for v in vias):
                    excluded += 1
                    continue
                for offset in offsets:
                    xx,yy = x-dy/length*mm(offset),y+dx/length*mm(offset)
                    if offset and any(math.hypot(xx-v.x,yy-v.y)<mm(.6) for v in vias):
                        excluded_offset += 1
                        continue
                    sampled += 1
                    layer = references[track.GetLayer()]
                    at = P.VECTOR2I(round(xx),round(yy))
                    if not any(ly == layer and shape.Contains(at) for ly,shape in fills):
                        missing.append(dict(net=track.GetNetname(),xy_mm=[xx/1e6,yy/1e6],offset_mm=offset))
        require(sampled > (5000 if name=='SD' else 500), 'Incomplete '+name+' reference sampling')
        require(not missing, name+' reference has uncovered samples: '+str(missing[:5]))
        records[name] = dict(sampled=sampled,excluded_own_via_centers=excluded,
                             excluded_offset_via_samples=excluded_offset,uncovered_count=len(missing),
                             connected_to_reference='U501.57',step_mm=.1,
                             reference_half_width_mm=.25 if name=='SD' else 0)
    return records


def inspect_panel_clock_references(board, ground_fills=None):
    """检查时钟F/In2对In1的实际覆盖；B对In2结果单列，保留电气资格边界。"""
    import pcbnew as P
    fills = ground_fills if ground_fills is not None else reference_connected_ground_fills(board)
    nets = {net+suffix for net in ('P47_CKV','P47_XLE','P47_XCL','P47_XSTL')
            for suffix in ('','_SRC')}
    tracks = list(board.GetTracks())
    require(nets <= {t.GetNetname() for t in tracks if t.GetClass()=='PCB_TRACK'},
            'Missing panel clock copper')
    references = {P.F_Cu:P.In1_Cu,P.In2_Cu:P.In1_Cu,P.B_Cu:P.In2_Cu}
    rows = []
    hard_missing = []
    for net in sorted(nets):
        vias = [v.GetPosition() for v in tracks if v.GetClass()=='PCB_VIA' and v.GetNetname()==net]
        layers = {}
        for track in tracks:
            if track.GetClass()!='PCB_TRACK' or track.GetNetname()!=net:
                continue
            layer = track.GetLayer()
            require(layer in references, 'Panel signal entered the In1 ground plane')
            row = layers.setdefault(board.GetLayerName(layer),dict(sampled=0,uncovered_count=0,
                                   reference=board.GetLayerName(references[layer]),uncovered=[]))
            a,b = track.GetStart(),track.GetEnd()
            dx,dy = b.x-a.x,b.y-a.y
            length = math.hypot(dx,dy)
            if not length:
                continue
            steps = max(1,math.ceil(length/mm(.1)))
            for i in range(steps+1):
                x,y = a.x+dx*i/steps,a.y+dy*i/steps
                if any(math.hypot(x-v.x,y-v.y)<mm(.6) for v in vias):
                    continue
                row['sampled'] += 1
                point = P.VECTOR2I(round(x),round(y))
                if any(ly==references[layer] and shape.Contains(point) for ly,shape in fills):
                    continue
                row['uncovered_count'] += 1
                row['uncovered'].append([x/1e6,y/1e6])
                if layer in (P.F_Cu,P.In2_Cu):
                    hard_missing.append(dict(net=net,layer=board.GetLayerName(layer),xy_mm=[x/1e6,y/1e6]))
        rows.append(dict(net=net,layers=layers))
    require(not hard_missing, 'Panel F/In2 reference has uncovered samples: '+str(hard_missing[:5]))
    rear_missing = sum(row['layers'].get('B.Cu',{}).get('uncovered_count',0) for row in rows)
    return dict(step_mm=.1,own_signal_via_exclusion_radius_mm=.6,
                reference_connected_to='U501.57',F_and_In2_to_In1_all_covered=True,
                rear_adjacent_In2_uncovered_count=rear_missing,
                rear_adjacent_plane_complete=rear_missing==0,
                rear_results_observational_not_electrical_failure_or_qualification=True,
                electrical_timing_and_return_qualified=False,nets=rows)


def _clock_corridor_area(selected, vias, ground):
    """复用原生多边形检查固定铜边预算，先合并走线再扣除本网过孔圆区。"""
    import pcbnew as P
    corridor = P.SHAPE_POLY_SET()
    for track in selected:
        shape = P.SHAPE_POLY_SET()
        track.GetEffectiveShape(track.GetLayer()).TransformToPolygon(shape,500,P.ERROR_OUTSIDE)
        corridor.BooleanAdd(shape)
    corridor.Inflate(mm(.25),P.CORNER_STRATEGY_ROUND_ALL_CORNERS,500)
    for via in vias:
        shape = P.SHAPE_POLY_SET()
        P.SHAPE_CIRCLE(via.GetPosition(),mm(.6)).TransformToPolygon(shape,500,P.ERROR_INSIDE)
        corridor.BooleanSubtract(shape)
    area = corridor.Area()/1e12
    corridor.BooleanSubtract(ground)
    return area,corridor.Area()/1e12


def inspect_inner_clock_bridge(board, contract, ground_fills=None):
    """锁定XSTL两旧孔之间的指定In2桥，并要求完整铜边走廊由实际In1地覆盖。"""
    import pcbnew as P
    require(contract['net']=='P47_XSTL_SRC' and contract['signal_edge_margin_mm']==.25
            and contract['own_via_exclusion_radius_mm']==.6 and contract['shape_error_um']==.5,
            'Invalid inner clock bridge contract')
    tracks = [t for t in board.GetTracks() if t.GetNetname()==contract['net']]
    selected = [t for t in tracks if t.GetClass()=='PCB_TRACK' and t.GetLayer()==P.In2_Cu]
    def signature(t):
        a,b = t.GetStart(),t.GetEnd()
        return [a.x,a.y,b.x,b.y,t.GetWidth()]
    require(selected and sorted(signature(t) for t in selected)==sorted(contract['segments_nm']),
            'Inner clock bridge copper differs')
    vias = [t for t in tracks if t.GetClass()=='PCB_VIA']
    require(len(vias)==2 and sorted([v.GetPosition().x,v.GetPosition().y] for v in vias)
            ==sorted(contract['via_centers_nm']), 'Inner clock bridge via inventory differs')
    fills = ground_fills if ground_fills is not None else reference_connected_ground_fills(board)
    ground = P.SHAPE_POLY_SET()
    for layer,fill in fills:
        if layer==P.In1_Cu:
            ground.BooleanAdd(fill)
    require(not ground.IsEmpty(), 'Missing reference ground for inner clock bridge')
    area,missing = _clock_corridor_area(selected,vias,ground)
    require(area>.01 and missing<=.000001, 'Inner clock bridge ground corridor has a gap')
    result = dict(net=contract['net'],signal_layer='In2.Cu',reference_ground='U501.57 / native-connected In1.Cu fill',
                  track_count=len(selected),via_count=2,signal_edge_margin_mm=.25,own_via_exclusion_radius_mm=.6,
                  shape_error_um=.5,required_area_mm2=area,uncovered_area_mm2=missing,
                  bridge_ground_coverage_complete=True,electrical_timing_and_return_qualified=False)
    if 'additional_bridges' in contract:
        require(contract['additional_bridges'], 'Invalid inner clock bridge contract')
        extras = []
        for spec in contract['additional_bridges']:
            require(spec.get('net') in ('P47_XLE_SRC','P47_XCL_SRC','P47_XSTL','P47_CKV')
                    and spec.get('bridge_segments_nm') and spec.get('via_centers_nm'),
                    'Invalid inner clock bridge contract')
            net_items = [t for t in board.GetTracks() if t.GetNetname()==spec['net']]
            rear = [t for t in net_items if t.GetClass()=='PCB_TRACK' and t.GetLayer()==P.B_Cu]
            require(len(rear)==spec.get('rear_track_count',0), 'Inner clock bridge rear copper differs')
            in2 = [t for t in net_items if t.GetClass()=='PCB_TRACK' and t.GetLayer()==P.In2_Cu]
            require(len(in2)==spec.get('total_in2_track_count',len(in2)), 'Inner clock bridge copper differs')
            expected_segs = sorted(spec['bridge_segments_nm'])
            bridge = [t for t in in2 if signature(t) in spec['bridge_segments_nm']]
            require(len(bridge)==len(expected_segs) and sorted(signature(t) for t in bridge)==expected_segs,
                    'Inner clock bridge copper differs')
            net_vias = [t for t in net_items if t.GetClass()=='PCB_VIA']
            require(len(net_vias)==len(spec['via_centers_nm'])
                    and sorted([v.GetPosition().x,v.GetPosition().y] for v in net_vias)==sorted(spec['via_centers_nm']),
                    'Inner clock bridge via inventory differs')
            b_area,b_missing = _clock_corridor_area(bridge,net_vias,ground)
            require(b_area>.01 and b_missing<=.000001, 'Inner clock bridge ground corridor has a gap')
            extras.append(dict(net=spec['net'],signal_layer='In2.Cu',rear_track_count=len(rear),
                               bridge_track_count=len(bridge),total_in2_track_count=len(in2),
                               via_count=len(net_vias),required_area_mm2=b_area,uncovered_area_mm2=b_missing,
                               bridge_ground_coverage_complete=True,electrical_timing_and_return_qualified=False))
        result['additional_bridges'] = extras
    return result


def inspect_rear_clock_corridors(board, contract, ground_fills=None):
    """对全部背面时钟铜边外扩0.25mm作连续差集；保留未覆盖面积和实际资格边界。"""
    import pcbnew as P
    require(contract['signal_edge_margin_mm']==.25
            and contract['own_via_exclusion_radius_mm']==.6
            and contract['shape_error_um']==.5, 'Invalid clock corridor contract')
    fills = ground_fills if ground_fills is not None else reference_connected_ground_fills(board)
    ground = P.SHAPE_POLY_SET()
    for layer,fill in fills:
        if layer==P.In2_Cu:
            ground.BooleanAdd(fill)
    require(not ground.IsEmpty(), 'Missing reference ground for rear clock corridors')
    clocks = {name+suffix for name in ['P47_CKV','P47_XLE','P47_XCL','P47_XSTL']
              for suffix in ['','_SRC']}
    tracks = list(board.GetTracks())
    rear = [t for t in tracks if t.GetClass()=='PCB_TRACK'
            and t.GetLayer()==P.B_Cu and t.GetNetname() in clocks]
    limits = contract['net_limits']
    require(limits and set(limits)=={t.GetNetname() for t in rear}, 'Rear clock track inventory differs')
    rows = []
    for net,limit in sorted(limits.items()):
        selected = [t for t in rear if t.GetNetname()==net]
        require(len(selected)==limit['track_count'], 'Rear clock track inventory differs: '+net)
        area,missing = _clock_corridor_area(selected,[t for t in tracks if t.GetClass()=='PCB_VIA'
                                                    and t.GetNetname()==net],ground)
        expected = limit['required_area_mm2']
        require(expected is None or abs(area-expected)<=.000005,
                'Rear clock required area differs: '+net)
        require(0<=limit['maximum_uncovered_area_mm2']
                and missing<=limit['maximum_uncovered_area_mm2'],
                'Rear clock ground corridor exceeds reviewed uncovered area: '+net)
        rows.append(dict(net=net,track_count=len(selected),required_area_mm2=area,
                         uncovered_area_mm2=missing,covered_area_mm2=area-missing))
    return dict(reference_ground='U501.57 / native-connected In2.Cu fill',
                signal_edge_margin_mm=.25,own_via_exclusion_radius_mm=.6,shape_error_um=.5,
                required_area_mm2=sum(r['required_area_mm2'] for r in rows),
                uncovered_area_mm2=sum(r['uncovered_area_mm2'] for r in rows),
                layout_ground_coverage_complete=all(r['uncovered_area_mm2']<=.000001 for r in rows),
                electrical_timing_and_return_qualified=False,nets=rows)


def inspect_clock_ground_stitches(board, plan, ground_fills=None):
    """核对指定盘外地孔的真实In1/B地接触与换层目标，只报告几何改善。"""
    import pcbnew as P
    fills = ground_fills if ground_fills is not None else reference_connected_ground_fills(board)
    tracks = list(board.GetTracks())
    smd_pads = [pad for fp in board.GetFootprints() for pad in fp.Pads()
                if pad.GetAttribute() == P.PAD_ATTRIB_SMD]
    rows = []
    require(plan, 'Missing reviewed clock ground stitches')
    for spec in plan:
        at = P.VECTOR2I(mm(spec['xy_mm'][0]), mm(spec['xy_mm'][1]))
        matches = [v for v in tracks if v.GetClass() == 'PCB_VIA'
                   and v.GetNetname() == 'GND' and v.GetPosition() == at]
        require(len(matches) == 1, 'Missing or ambiguous clock ground stitch')
        via = matches[0]
        require(via.GetViaType() == P.VIATYPE_THROUGH
                and via.GetWidth(P.F_Cu) == mm(.4) and via.GetDrill() == mm(.2),
                'Clock ground stitch size or type differs')
        contacts = [board.GetLayerName(ly) for ly in (P.In1_Cu, P.B_Cu)
                    if any(layer == ly and shape.Collide(via.GetEffectiveShape(ly), 0)
                           for layer, shape in fills)]
        require(contacts == ['In1.Cu', 'B.Cu'], 'Clock ground stitch lacks reference-connected In1/B contact')
        for pad in smd_pads:
            for ly in (P.F_Cu, P.B_Cu):
                if pad.IsOnLayer(ly):
                    require(not pad.GetEffectiveShape(ly).Collide(via.GetEffectiveShape(ly), mm(.05)),
                            'Clock ground stitch violates 50um SMD pad-edge separation')
        observations = []
        require(spec['targets'], 'Clock ground stitch has no reviewed transition target')
        for target in spec['targets']:
            pt = P.VECTOR2I(mm(target['xy_mm'][0]), mm(target['xy_mm'][1]))
            signals = [v for v in tracks if v.GetClass() == 'PCB_VIA'
                       and v.GetNetname() == target['net'] and v.GetPosition() == pt]
            if target.get('eliminated_by_continuous_reference_routing'):
                c_layer = target.get('continuous_layer')
                c_seg = target.get('continuous_segment_mm')
                require(not signals and c_layer in ('F.Cu', 'In2.Cu')
                        and isinstance(c_seg, list) and len(c_seg) == 4,
                        'Clock ground stitch target differs')
                s_pt = P.VECTOR2I(mm(c_seg[0]), mm(c_seg[1]))
                e_pt = P.VECTOR2I(mm(c_seg[2]), mm(c_seg[3]))
                c_tracks = [t for t in tracks if t.GetClass() == 'PCB_TRACK'
                            and t.GetNetname() == target['net']
                            and board.GetLayerName(t.GetLayer()) == c_layer
                            and ((t.GetStart() == s_pt and t.GetEnd() == e_pt)
                                 or (t.GetStart() == e_pt and t.GetEnd() == s_pt))]
                rear_near = [t for t in tracks if t.GetClass() == 'PCB_TRACK'
                             and t.GetNetname() == target['net'] and t.GetLayer() == P.B_Cu
                             and t.GetEffectiveShape().Collide(P.SHAPE_CIRCLE(pt, mm(.2)), 0)]
                require(len(c_tracks) == 1 and not rear_near,
                        'Clock ground stitch eliminated transition replacement differs')
                distance = math.hypot(at.x-pt.x, at.y-pt.y)/1e6
                require(distance < target['before_mm'], 'Clock ground stitch did not reduce geometric distance')
                observations.append(dict(net=target['net'],xy_mm=target['xy_mm'],
                                         eliminated_by_continuous_reference_routing=True,
                                         continuous_layer=c_layer,continuous_segment_mm=c_seg,
                                         previous_nearest_In1_B_ground_via_mm=target['before_mm'],
                                         reviewed_ground_via_distance_mm=distance))
                continue
            require(len(signals) == 1, 'Clock ground stitch target differs')
            signal = signals[0]
            incident = sorted({board.GetLayerName(t.GetLayer()) for t in tracks
                               if t.GetClass() == 'PCB_TRACK' and t.GetNetCode() == signal.GetNetCode()
                               and t.GetEffectiveShape().Collide(signal.GetEffectiveShape(t.GetLayer()), 0)})
            require('B.Cu' in incident and any(ly in incident for ly in ('F.Cu','In2.Cu')),
                    'Clock ground stitch target has no B-layer transition')
            distance = math.hypot(at.x-pt.x, at.y-pt.y)/1e6
            require(distance < target['before_mm'], 'Clock ground stitch did not reduce geometric distance')
            observations.append(dict(net=target['net'],xy_mm=target['xy_mm'],incident_layers=incident,
                                     previous_nearest_In1_B_ground_via_mm=target['before_mm'],
                                     reviewed_ground_via_distance_mm=distance))
        rows.append(dict(xy_mm=spec['xy_mm'],reference_fill_contacts=contacts,targets=observations))
    return dict(reference_connected_to='U501.57',stitch_count=len(rows),
                all_reviewed_In1_B_contacts=True,all_reviewed_SMD_pad_edges_at_least_50um=True,
                electrical_timing_and_return_qualified=False,
                scope='Actual native ground contacts and distances only; no SI, EMI or timing threshold',
                stitches=rows)


def copper_fingerprint(board, full_zones=False):
    """按原生纳米坐标绑定铜与区定义；已有 placement fingerprint 不包含铜。"""
    import pcbnew as P
    rows=[]
    for item in board.GetTracks():
        if item.GetClass()=='PCB_TRACK':
            a,b=item.GetStart(),item.GetEnd()
            row=['track',str(item.GetNetname()),board.GetLayerName(item.GetLayer()),
                 a.x,a.y,b.x,b.y,item.GetWidth()]
        else:
            a=item.GetPosition()
            row=['via',str(item.GetNetname()),a.x,a.y,item.GetWidth(P.F_Cu),item.GetDrill()]
        rows.append(row)
    zones=[]
    for z in board.Zones():
        points=[[z.GetCornerPosition(i).x,z.GetCornerPosition(i).y] for i in range(z.GetNumCorners())]
        row = [z.GetZoneName(),str(z.GetNetname()),board.GetLayerName(z.GetLayer()),
                      z.GetIsRuleArea(),z.GetDoNotAllowTracks(),z.GetDoNotAllowVias(),
                      z.GetDoNotAllowPads(),z.GetDoNotAllowFootprints(),z.GetDoNotAllowZoneFills(),points]
        if full_zones:
            shape = z.Outline()
            holes = []
            for i in range(shape.OutlineCount()):
                for h in range(shape.HoleCount(i)):
                    ring = shape.Hole(i,h)
                    holes.append([i, [[ring.CPoint(j).x, ring.CPoint(j).y]
                                      for j in range(ring.PointCount())]])
            row.extend([int(z.GetAssignedPriority()), holes])
        zones.append(row)
    payload=dict(copper=sorted(rows),zones=sorted(zones))
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
