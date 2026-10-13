"""Opt-in engineering gate for all native ground pads and the eight repair targets.

This does not qualify electrical performance, fabrication, charging or panel
power. It consumes the fresh native inspector's output and refuses incomplete
or contradictory evidence instead of promoting a seven-of-eight checkpoint.
"""

TARGETS = {
    'Core': {('J601', '36'), ('J601', '38')},
    'Display': {('J820', '9'), ('J820', '22'), ('R809', '2'), ('R810', '2'),
                ('U810', '32'), ('U810', '41')},
}
REFERENCES = {'Core': ('U501', '57'), 'Display': ('C804', '2')}


def require_complete_ground_returns(reports):
    """Require complete, internally consistent fresh ground reports for both boards."""
    def require(condition, message):
        if not condition:
            raise ValueError('Complete-ground gate: ' + message)

    require(isinstance(reports, dict) and set(reports) == set(TARGETS),
            'both Core and Display reports are required')
    summary = {}
    for board, expected in TARGETS.items():
        data = reports[board]
        require(isinstance(data, dict), board + ' report is malformed')
        require(data.get('evidence') == 'native_connected_pad_groups',
                board + ' lacks native pad-group evidence')
        require(data.get('scope') == 'connectivity_only_not_physical_qualification',
                board + ' evidence scope differs')
        reference = data.get('reference_pad')
        require(isinstance(reference, dict)
                and (reference.get('ref'), reference.get('pin')) == REFERENCES[board]
                and reference.get('net') == 'GND', board + ' reference differs')
        for field in ('ground_pad_count', 'ground_group_count', 'reference_group_pad_count',
                      'unconnected_ground_pad_count', 'required_ground_target_count',
                      'connected_required_ground_target_count'):
            require(type(data.get(field)) is int and data[field] >= 0,
                    board + ' invalid or missing ' + field)
        count = data['ground_pad_count']
        require(count > len(expected) and data['ground_group_count'] == 1
                and data['reference_group_pad_count'] == count
                and data['unconnected_ground_pad_count'] == 0,
                board + ' still contains disconnected ground pads')
        require(data.get('all_ground_pads_connected_to_reference') is True,
                board + ' ground membership is not complete')
        require(type(data.get('groups_not_connected_to_reference')) is list
                and data['groups_not_connected_to_reference'] == [],
                board + ' contains unreported or contradictory ground groups')
        targets = data.get('required_ground_targets')
        require(type(targets) is list and len(targets) == len(expected),
                board + ' required-target inventory differs')
        seen, uuids = set(), set()
        for target in targets:
            require(isinstance(target, dict), board + ' target is malformed')
            identity = (target.get('ref'), target.get('pin'))
            require(all(isinstance(value, str) for value in identity),
                    board + ' target identity is malformed')
            require(identity in expected and identity not in seen,
                    board + ' missing, unexpected or duplicate target')
            uid = target.get('uuid')
            require(isinstance(uid, str) and uid and uid not in uuids,
                    board + ' duplicated or missing native target UUID')
            require(target.get('net') == 'GND' and target.get('connected_to_reference') is True,
                    board + '/' + '.'.join(identity) + ' is not connected to reference')
            seen.add(identity)
            uuids.add(uid)
        require(data['required_ground_target_count'] == len(expected)
                and data['connected_required_ground_target_count'] == len(expected)
                and data.get('all_required_ground_targets_connected') is True,
                board + ' target counts contradict native target states')
        summary[board] = {'ground_pads_connected': count,
                          'named_ground_targets_connected': len(expected)}
    return {'required': True, 'complete': True, 'boards': summary,
            'scope': 'native_ground_connectivity_only', 'manufacturing_release': False}
