"""Report actual ground connectivity separately from a pad's zone-connection mode.

A solid/thermal pad setting does not prove a connection to the reference plane.
This report describes native connected-pad groups only, not power integrity,
current capacity, physical qualification, or permission to fabricate/power a PCB.
"""
import math


def summarize_ground_returns(pads, groups, reference_ref, reference_pin, required_targets=None):
    """Summarize complete native ground-pad evidence relative to one known pad.

    Preserve UUID-level identity: two connector mounting lands can have the same
    reference and pad number but still be physically disconnected. Missing,
    duplicated, overlapping or ambiguous evidence raises instead of reporting
    success. A valid partial board returns its disconnected groups explicitly.
    """
    if not isinstance(pads, list) or not pads:
        raise ValueError('Missing ground-pad inventory')
    if not isinstance(groups, list) or not groups:
        raise ValueError('Missing native ground-pad groups')
    if not all(isinstance(v, str) and v for v in (reference_ref, reference_pin)):
        raise ValueError('Invalid reference ground-pad identity')
    inventory = {}
    for pad in pads:
        if not isinstance(pad, dict):
            raise ValueError('Ground-pad record must be a mapping')
        if any(not isinstance(pad.get(key), str) or not pad[key]
               for key in ('uuid', 'ref', 'pin')):
            raise ValueError('Invalid ground-pad identity')
        if pad.get('net') != 'GND':
            raise ValueError('Ground inventory contains a non-ground pad')
        xy = pad.get('position_mm')
        if not isinstance(xy, (tuple, list)) or len(xy) != 2:
            raise ValueError('Missing physical ground-pad coordinates')
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) for v in xy):
            raise ValueError('Invalid physical ground-pad coordinates')
        if pad['uuid'] in inventory:
            raise ValueError('Duplicated native ground-pad UUID')
        inventory[pad['uuid']] = {
            'uuid': pad['uuid'], 'ref': pad['ref'], 'pin': pad['pin'],
            'net': 'GND', 'position_mm': list(xy)}
    seen = set()
    partition = []
    for group in groups:
        if not isinstance(group, (list, tuple, set, frozenset)) or not group:
            raise ValueError('Empty or malformed native ground-pad group')
        if any(not isinstance(uid, str) or not uid for uid in group):
            raise ValueError('Invalid native ground-pad UUID in group')
        current = set(group)
        if len(current) != len(group) or current & seen:
            raise ValueError('Duplicated or overlapping native ground-pad groups')
        if not current <= set(inventory):
            raise ValueError('Unknown ground-pad UUID in native evidence')
        seen.update(current)
        partition.append(current)
    if seen != set(inventory):
        raise ValueError('Incomplete native ground-pad evidence')
    reference = [pad for pad in inventory.values()
                 if pad['ref'] == reference_ref and pad['pin'] == reference_pin]
    if len(reference) != 1:
        raise ValueError('Reference ground pad is missing or physically ambiguous')
    reference = reference[0]
    connected = next(group for group in partition if reference['uuid'] in group)
    def key(pad):
        return (pad['ref'], pad['pin'], *pad['position_mm'], pad['uuid'])
    isolated = [sorted((inventory[uid] for uid in group), key=key)
                for group in partition if group is not connected]
    isolated.sort(key=lambda group: key(group[0]))
    result = {
        'evidence': 'native_connected_pad_groups',
        'reference_pad': reference,
        'ground_pad_count': len(inventory),
        'ground_group_count': len(partition),
        'reference_group_pad_count': len(connected),
        'all_ground_pads_connected_to_reference': len(partition) == 1,
        'unconnected_ground_pad_count': len(inventory) - len(connected),
        'groups_not_connected_to_reference': isolated,
        'scope': 'connectivity_only_not_physical_qualification',
    }


    if required_targets is not None:
        if not isinstance(required_targets, (list, tuple)) or not required_targets:
            raise ValueError('Required ground targets must be a nonempty sequence')
        checked = set()
        targets = []
        for target in required_targets:
            if not isinstance(target, (list, tuple)) or len(target) != 2:
                raise ValueError('A required target needs reference and pad number')
            if any(not isinstance(value, str) or not value for value in target):
                raise ValueError('Invalid required ground target identity')
            identity = tuple(target)
            if identity in checked:
                raise ValueError('Duplicate required ground target')
            checked.add(identity)
            matching = [pad for pad in inventory.values()
                        if (pad['ref'], pad['pin']) == identity]
            if len(matching) != 1:
                raise ValueError('Required ground target missing or physically ambiguous')
            pad = matching[0]
            targets.append({**pad, 'connected_to_reference': pad['uuid'] in connected})
        targets.sort(key=key)
        result['required_ground_targets'] = targets
        result['required_ground_target_count'] = len(targets)
        result['connected_required_ground_target_count'] = sum(
            target['connected_to_reference'] for target in targets)
        result['all_required_ground_targets_connected'] = all(
            target['connected_to_reference'] for target in targets)
    return result


def inspect_ground_returns(board, reference_ref, reference_pin, required_targets=None):
    """Read actual KiCad connectivity without changing copper or zone settings."""
    import pcbnew as P
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    native = {}
    inventory = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if not pad.GetNumber() or str(pad.GetNetname()) != 'GND':
                continue
            uid = str(pad.m_Uuid.AsString())
            if uid in native:
                raise ValueError('Duplicated native ground-pad identity')
            native[uid] = pad
            position = pad.GetPosition()
            inventory.append({
                'uuid': uid, 'ref': footprint.GetReference(),
                'pin': pad.GetNumber(), 'net': 'GND',
                'position_mm': [round(P.ToMM(position.x), 6),
                                round(P.ToMM(position.y), 6)]})
    groups, done = [], set()
    ground_ids = set(native)
    for uid in sorted(native):
        if uid in done:
            continue
        linked = {str(item.m_Uuid.AsString())
                  for item in connection.GetConnectedItems(native[uid])}
        group = (linked | {uid}) & ground_ids
        if group & done:
            raise ValueError('Inconsistent overlapping native ground connectivity')
        groups.append(sorted(group))
        done.update(group)
    return summarize_ground_returns(inventory, groups, reference_ref, reference_pin, required_targets)
