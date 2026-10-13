"""The only electrical-rule delta allowed by quality revision C is stricter edge clearance."""
from copy import deepcopy

EXPECTED_RULE_CHANGES = {
    'board.design_settings.rules.min_copper_edge_clearance': {'old': 0.15, 'new': 0.2}
}


def validate_rule_change(before, after, declared):
    if declared != EXPECTED_RULE_CHANGES:
        raise ValueError('Unreviewed or missing fabrication-rule change')
    old = before['board']['design_settings']['rules']['min_copper_edge_clearance']
    new = after['board']['design_settings']['rules']['min_copper_edge_clearance']
    if old != 0.15 or new != 0.2:
        raise ValueError('Expected exact 0.15 to 0.20mm stricter routed-edge clearance')
    restored = deepcopy(after['board'])
    restored['design_settings']['rules']['min_copper_edge_clearance'] = old
    if restored != before['board']:
        raise ValueError('An additional PCB rule, exclusion or board setting changed')
    for key in ['erc', 'net_settings']:
        if before.get(key) != after.get(key):
            raise ValueError('Electrical rule or netclass changed: ' + key)
    return True
