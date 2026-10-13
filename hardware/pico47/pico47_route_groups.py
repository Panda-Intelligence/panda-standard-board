"""Select repair targets without accidentally routing pre-existing open pins.

These set operations support routing proposals; only a fresh native KiCad
connectivity snapshot can prove a physical connection. They do not approve CAD.
"""
from collections.abc import Sequence, Set


def _partition(groups: Sequence[Set[str]], name: str) -> list[frozenset[str]]:
    if not isinstance(groups, (list, tuple)) or not groups:
        raise ValueError(name + ': missing connected-pad groups')
    result: list[frozenset[str]] = []
    seen: set[str] = set()
    for group in groups:
        if not isinstance(group, (set, frozenset)) or not group:
            raise ValueError(name + ': every group must be a nonempty pad set')
        if any(not isinstance(pad, str) or not pad for pad in group):
            raise ValueError(name + ': invalid pad identity')
        if seen.intersection(group):
            raise ValueError(name + ': a pad appears in multiple groups')
        seen.update(group)
        result.append(frozenset(group))
    return result


def repair_pairs(original_groups: Sequence[Set[str]],
                 live_pad_sets: Sequence[Set[str]]) -> list[tuple[int, int]]:
    """Return live-group pairs needed to restore original connections.

    Example: original [{a,b},{c}], live [{a},{b},{c}] yields only the a/b
    pair. Pin c was already open and must not become an incidental repair target.
    New desired connections must be handled separately by the routing caller.
    Pad inventories must match; absent pads must never be interpreted as success.
    """
    original = _partition(original_groups, 'original')
    live = _partition(live_pad_sets, 'live')
    if set().union(*original) != set().union(*live):
        raise ValueError('Original and live physical pad inventories differ')
    label = {pad: index for index, group in enumerate(original) for pad in group}
    labels = [{label[pad] for pad in group} for group in live]
    return [(i, j) for i in range(len(live)) for j in range(i)
            if labels[i].intersection(labels[j])]
