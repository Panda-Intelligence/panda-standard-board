"""Exact two-testpoint source ECO onto already connected same-net copper.

No new track, via, electrical net or component is substituted. Backside probe
access remains a separate assembly/mechanical review, not implicit approval.
"""
import json

PREVIOUS_LAYOUT_SHA256 = 'e83121eb331615a332e310205760cf759e829a318d46ef3762caa3a41a02de4e'
BEFORE = {'TP801': [27.25, 110.25, 0.0, 'F.Cu'], 'TP803': [27.25, 108.0, 0.0, 'F.Cu']}
AFTER = {'TP801': [29.45, 96.05, 180.0, 'B.Cu'], 'TP803': [13.65, 91.85, 180.0, 'B.Cu']}
NETS = {'TP801': 'P47_VGH', 'TP803': 'P47_VPOS'}
EXPECTED_IDENTITIES = {
    phase: {ref: [ref, '1', int(round(pose[0] * 1_000_000)), int(round(pose[1] * 1_000_000)),
                  NETS[ref], [pose[3]]] for ref, pose in poses.items()}
    for phase, poses in [('before', BEFORE), ('after', AFTER)]
}


def expected_spec():
    return {
        'schema': 'panda47-native-copper-testpoint-eco-v1',
        'previous_source_layout_sha256': PREVIOUS_LAYOUT_SHA256,
        'before': {ref: list(pose) for ref, pose in BEFORE.items()},
        'after': {ref: list(pose) for ref, pose in AFTER.items()},
        'pin_nets': {ref: {'1': net} for ref, net in NETS.items()},
        'new_copper_or_vias_required': False,
        'requires_backside_probe_access_review': True,
        'physical_probe_access_qualified': False,
        'manufacturing_release': False,
    }


def validate_testpoint_eco(spec):
    if not isinstance(spec, dict) or set(spec) != set(expected_spec()) or spec != expected_spec():
        raise ValueError('Unreviewed testpoint pose, source binding or net mapping')
    for name in ('new_copper_or_vias_required', 'requires_backside_probe_access_review',
                 'physical_probe_access_qualified', 'manufacturing_release'):
        if type(spec[name]) is not bool:
            raise ValueError('Testpoint review states must be actual booleans')
    for mapping in ('before', 'after'):
        for pose in spec[mapping].values():
            if type(pose) is not list or len(pose) != 4:
                raise ValueError('Malformed testpoint physical pose')
            if any(type(value) not in (float, int) for value in pose[:3]):
                raise ValueError('Testpoint pose values must be real coordinates')
    return True


def apply_testpoint_eco(board, spec):
    import pcbnew as P
    validate_testpoint_eco(spec)
    result = []
    for ref in sorted(BEFORE):
        footprint = board.FindFootprintByReference(ref)
        if footprint is None:
            raise ValueError('Missing native testpoint ' + ref)
        q = footprint.GetPosition()
        actual = [P.ToMM(q.x), P.ToMM(q.y), footprint.GetOrientationDegrees(),
                  board.GetLayerName(footprint.GetLayer())]
        if actual != BEFORE[ref]:
            raise ValueError('Testpoint source pose differs: ' + ref)
        pads = list(footprint.Pads())
        if len(pads) != 1 or str(pads[0].GetNumber()) != '1' or str(pads[0].GetNetname()) != NETS[ref]:
            raise ValueError('Testpoint package, pin or net changed: ' + ref)
        pad = pads[0]
        def immutable_identity():
            return (str(pad.m_Uuid.AsString()), pad.GetSize().x, pad.GetSize().y,
                    pad.GetDrillSize().x, pad.GetDrillSize().y, int(pad.GetShape()),
                    footprint.GetValue(), str(footprint.GetFPID().GetLibNickname()),
                    str(footprint.GetFPID().GetLibItemName()))
        original = immutable_identity()
        footprint.Flip(footprint.GetPosition(), P.FLIP_DIRECTION_LEFT_RIGHT)
        x, y, angle, _ = AFTER[ref]
        footprint.SetPosition(P.VECTOR2I(P.FromMM(x), P.FromMM(y)))
        footprint.SetOrientationDegrees(angle)
        q = pad.GetPosition()
        current = [ref, '1', int(q.x), int(q.y), str(pad.GetNetname()),
                   [board.GetLayerName(layer) for layer in (P.F_Cu, P.In1_Cu, P.In2_Cu, P.B_Cu)
                    if pad.IsOnLayer(layer)]]
        if current != EXPECTED_IDENTITIES['after'][ref] or immutable_identity() != original:
            raise ValueError('Testpoint transform changed package, geometry or net: ' + ref)
        result.append({'ref': ref, 'before': list(BEFORE[ref]), 'after': list(AFTER[ref]),
                       'net': NETS[ref], 'no_new_copper_required': True,
                       'manufacturing_release': False})
    return result


def normalize_testpoint_groups(groups, phase, spec):
    """Normalize only the two exactly reviewed pad identities during migration."""
    validate_testpoint_eco(spec)
    if phase not in EXPECTED_IDENTITIES or not isinstance(groups, list) or not groups:
        raise ValueError('Missing exact testpoint native-group evidence')
    seen, changed, result = set(), set(), []
    for group in groups:
        if not isinstance(group, (list, tuple, set, frozenset)) or not group:
            raise ValueError('Malformed native connected-pad group')
        mapped = set()
        for identity in group:
            if not isinstance(identity, str) or identity in seen:
                raise ValueError('Duplicate or malformed native physical identity')
            seen.add(identity)
            row = json.loads(identity)
            if not isinstance(row, list) or len(row) != 6:
                raise ValueError('Invalid native physical identity fields')
            if row[0] in NETS:
                ref = row[0]
                if row != EXPECTED_IDENTITIES[phase][ref] or ref in changed:
                    raise ValueError('Unreviewed or ambiguous testpoint physical identity')
                changed.add(ref)
                mapped.add(json.dumps(['reviewed-testpoint-copper-ECO', ref, '1', NETS[ref]],
                                      separators=(',', ':')))
            else:
                mapped.add(identity)
        result.append(frozenset(mapped))
    if changed != set(NETS):
        raise ValueError('Missing one or more exact testpoint identities')
    return result
