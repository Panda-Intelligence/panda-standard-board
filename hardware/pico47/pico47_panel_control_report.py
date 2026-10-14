"""Report exact native panel-control connections independently of airwires.

Connected names/net labels are not proof of joined copper. These checks describe
native pad groups only, never timing, power integrity or fabrication permission.
"""
LINKS = {
    'P47_CKV': (('R729', '2'), ('J601', '39')),
    'P47_SPV': (('R730', '2'), ('J601', '40')),
    'P47_XLE': (('R727', '2'), ('J601', '35')),
    'P47_XSTL': (('R728', '2'), ('J601', '37')),
}


def summarize_panel_controls(pads, groups):
    """Validate the complete eight-pad inventory and native connectivity partition."""
    expected = {identity: net for net, ends in LINKS.items() for identity in ends}
    if not isinstance(pads, list) or len(pads) != len(expected):
        raise ValueError('Panel controls require every exact native endpoint pad')
    inventory, identities = {}, {}
    for pad in pads:
        if not isinstance(pad, dict):
            raise ValueError('Invalid native pad record')
        if any(not isinstance(pad.get(key), str) or not pad[key]
               for key in ('uuid', 'ref', 'pin', 'net')):
            raise ValueError('Invalid native panel-control pad identity')
        identity = (pad['ref'], pad['pin'])
        if identity not in expected or pad['net'] != expected[identity]:
            raise ValueError('Panel-control physical pad or net mapping changed')
        if identity in identities or pad['uuid'] in inventory:
            raise ValueError('Duplicated or ambiguous panel-control pad')
        identities[identity] = pad['uuid']
        inventory[pad['uuid']] = pad
    if not isinstance(groups, list) or not groups:
        raise ValueError('Missing native connected-pad evidence')
    group_index = {}
    for index, group in enumerate(groups):
        if not isinstance(group, (list, tuple, set, frozenset)) or not group:
            raise ValueError('Invalid native panel-control pad group')
        if any(not isinstance(uid, str) or uid not in inventory for uid in group):
            raise ValueError('Unknown pad in native panel-control evidence')
        if len(set(group)) != len(group) or any(uid in group_index for uid in group):
            raise ValueError('Duplicated or overlapping native pad groups')
        if len({inventory[uid]['net'] for uid in group}) != 1:
            raise ValueError('Different control nets are physically shorted')
        group_index.update({uid: index for uid in group})
    if set(group_index) != set(inventory):
        raise ValueError('Incomplete native panel-control evidence')
    return {
        net: {
            'from_pad': '.'.join(source), 'to_pad': '.'.join(target),
            'connected': group_index[identities[source]] == group_index[identities[target]],
            'evidence': 'native_connected_pad_groups',
            'scope': 'connectivity_only_not_timing_or_fabrication',
        } for net, (source, target) in LINKS.items()
    }


def inspect_panel_control_links(board):
    """Read exact live KiCad pad groups without changing board geometry or rules."""
    board.BuildConnectivity()
    connectivity = board.GetConnectivity()
    records, native = [], {}
    for net, identities in LINKS.items():
        for ref, pin in identities:
            footprint = board.FindFootprintByReference(ref)
            if footprint is None:
                raise ValueError('Missing panel-control component ' + ref)
            pads = [pad for pad in footprint.Pads() if str(pad.GetNumber()) == pin]
            if len(pads) != 1:
                raise ValueError('Missing or ambiguous panel-control pad ' + ref + '.' + pin)
            pad = pads[0]
            uid = str(pad.m_Uuid.AsString())
            if uid in native or str(pad.GetNetname()) != net:
                raise ValueError('Panel-control native identity or net mismatch')
            native[uid] = pad
            records.append({'uuid': uid, 'ref': ref, 'pin': pin, 'net': net})
    groups, seen = [], set()
    for uid in sorted(native):
        if uid in seen:
            continue
        connected = {str(item.m_Uuid.AsString())
                     for item in connectivity.GetConnectedItems(native[uid])}
        group = (connected | {uid}) & set(native)
        groups.append(sorted(group))
        seen.update(group)
    return summarize_panel_controls(records, groups)
