"""One exact, source-bound R801 assembly-side ECO; not a general layout waiver.

This preserves package/value/pin mapping and all other footprints. Native
capture must additionally prove the full generated-source geometry, unchanged
rules/libraries, all old electrical groups and complete reference grounds.
Assembly-height/DFM, analog performance and manufacturing approval are separate.
"""
import json

PREVIOUS_LAYOUT_SHA256 = 'c7c293dc2b73a52bed580fd2e33abec2dd0a7e9b99b1e271312050e9c4f3d058'
BEFORE = [28.0, 98.0, 0.0, 'F.Cu']
AFTER = [28.75, 97.75, 180.0, 'B.Cu']
PIN_NETS = {'1': 'P47_VGH', '2': 'P47_VGH_FB'}
EXPECTED_PAD_IDENTITIES = {
    'before': {
        '1': ['R801', '1', 27490000, 98000000, 'P47_VGH', ['F.Cu']],
        '2': ['R801', '2', 28510000, 98000000, 'P47_VGH_FB', ['F.Cu']],
    },
    'after': {
        '1': ['R801', '1', 29260000, 97750000, 'P47_VGH', ['B.Cu']],
        '2': ['R801', '2', 28240000, 97750000, 'P47_VGH_FB', ['B.Cu']],
    },
}


def validate_r801_eco(spec):
    """Only the exact reviewed change can use the exceptional continuity mapping."""
    if not isinstance(spec, dict):
        raise ValueError('Missing explicit R801 placement ECO')
    expected = {
        'schema': 'panda47-r801-backside-placement-eco-v1',
        'reference': 'R801',
        'previous_source_layout_sha256': PREVIOUS_LAYOUT_SHA256,
        'before': BEFORE,
        'after': AFTER,
        'pin_nets': PIN_NETS,
        'requires_two_sided_assembly': True,
        'assembly_height_and_process_qualified': False,
        'manufacturing_release': False,
    }
    if set(spec) != set(expected) or any(spec[key] != value for key, value in expected.items()):
        raise ValueError('Unreviewed R801 pose, source binding, pin mapping or release flag')
    for name in ('requires_two_sided_assembly', 'assembly_height_and_process_qualified',
                 'manufacturing_release'):
        if type(spec[name]) is not bool:
            raise ValueError('R801 process decisions must be actual booleans')
    for key in ('before', 'after'):
        if type(spec[key]) is not list or any(type(v) not in (int, float) for v in spec[key][:3]):
            raise ValueError('Malformed R801 physical pose')
    return True


def apply_r801_eco(board, spec):
    """Apply the reviewed physical change in a fresh board, never its routing."""
    import pcbnew as P
    validate_r801_eco(spec)
    fp = board.FindFootprintByReference('R801')
    if fp is None:
        raise ValueError('Missing R801')
    q = fp.GetPosition()
    pose = [P.ToMM(q.x), P.ToMM(q.y), fp.GetOrientationDegrees(), board.GetLayerName(fp.GetLayer())]
    if pose != BEFORE:
        raise ValueError('R801 ECO source pose differs from reviewed placement')
    pads = list(fp.Pads())
    if len(pads) != 2 or {str(p.GetNumber()): str(p.GetNetname()) for p in pads} != PIN_NETS:
        raise ValueError('R801 ECO physical pad identities changed')
    old_ids = {str(p.GetNumber()): str(p.m_Uuid.AsString()) for p in pads}
    old_value, old_fpid = fp.GetValue(), str(fp.GetFPID().GetLibItemName())
    fp.Flip(fp.GetPosition(), P.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetPosition(P.VECTOR2I(P.FromMM(AFTER[0]), P.FromMM(AFTER[1])))
    fp.SetOrientationDegrees(AFTER[2])
    if fp.GetLayer() != P.B_Cu or fp.GetValue() != old_value or str(fp.GetFPID().GetLibItemName()) != old_fpid:
        raise ValueError('R801 ECO changed package/value or failed to flip')
    for pad in fp.Pads():
        pin = str(pad.GetNumber()); q = pad.GetPosition()
        actual = ['R801', pin, int(q.x), int(q.y), str(pad.GetNetname()),
                  [board.GetLayerName(layer) for layer in (P.F_Cu, P.In1_Cu, P.In2_Cu, P.B_Cu)
                   if pad.IsOnLayer(layer)]]
        if actual != EXPECTED_PAD_IDENTITIES['after'][pin] or str(pad.m_Uuid.AsString()) != old_ids[pin]:
            raise ValueError('R801 native transformed pad geometry differs')
    return {'reference': 'R801', 'before': list(BEFORE), 'after': list(AFTER),
            'exact_package_value_and_pin_ids_preserved': True,
            'two_sided_assembly_required': True, 'manufacturing_release': False}


def normalize_r801_groups(groups, phase, spec):
    """Normalize ONLY the two strictly checked R801 identities across this ECO.

    All other reference/pad/position/net/copper-layer identities stay literal.
    Full baseline-to-candidate group-subset preservation remains mandatory.
    """
    validate_r801_eco(spec)
    if phase not in EXPECTED_PAD_IDENTITIES or not isinstance(groups, list) or not groups:
        raise ValueError('Missing ECO physical pad groups or phase')
    seen, r801_pins, normalized = set(), set(), []
    for group in groups:
        if not isinstance(group, (list, tuple, set, frozenset)) or not group:
            raise ValueError('Invalid native ECO group')
        mapped = set()
        for identity in group:
            if not isinstance(identity, str) or identity in seen:
                raise ValueError('Duplicate/malformed native physical pad identity')
            seen.add(identity)
            row = json.loads(identity)
            if not isinstance(row, list) or len(row) != 6:
                raise ValueError('Invalid native physical identity fields')
            if row[0] == 'R801':
                pin = row[1]
                if pin not in PIN_NETS or row != EXPECTED_PAD_IDENTITIES[phase][pin] or pin in r801_pins:
                    raise ValueError('Unreviewed or ambiguous R801 native pad identity')
                r801_pins.add(pin)
                mapped.add(json.dumps(['reviewed-R801-ECO', pin, PIN_NETS[pin]], separators=(',', ':')))
            else:
                mapped.add(identity)
        normalized.append(frozenset(mapped))
    if r801_pins != set(PIN_NETS):
        raise ValueError('Missing R801 pad evidence; cannot certify migration')
    return normalized
