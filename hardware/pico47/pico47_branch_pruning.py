"""Conservative graph proposals for peeling complete dangling copper branches.

Coordinates/nets/layers belong in caller-provided node IDs. Nodes touching pads,
vias, filled copper or non-endpoint junctions must be anchored by the caller.
This function only proposes UUIDs: native DRC, pad-group continuity, exact source
bindings and unchanged geometry/rules remain mandatory before CAD adoption.
"""
from collections import defaultdict, deque
from collections.abc import Iterable, Mapping


def dangling_branch_ids(edges: Mapping[str, tuple[str, str]],
                        anchors: Iterable[str], seeds: Iterable[str]) -> list[str]:
    """Peel seed-marked degree-one branches until an anchor/junction is reached.

    Other branches, cycles, parallel edges and self-loops are retained. An
    anchor is never crossed, but a dead branch terminating at it may be removed.
    Inputs are not modified. The sorted result is independent of input order.
    """
    if not isinstance(edges, Mapping):
        raise ValueError('Edges must map unique copper IDs to endpoint pairs')
    adjacency: dict[str, set[str]] = defaultdict(set)
    for uid, ends in edges.items():
        if not isinstance(uid, str) or not uid:
            raise ValueError('Invalid copper identity')
        if not isinstance(ends, tuple) or len(ends) != 2:
            raise ValueError('Each edge needs exactly two endpoint IDs')
        if any(not isinstance(node, str) or not node for node in ends):
            raise ValueError('Invalid endpoint identity')
        for node in ends:
            adjacency[node].add(uid)
    if isinstance(anchors, (str, bytes)) or isinstance(seeds, (str, bytes)):
        raise ValueError('Anchors and seeds must be collections of identities')
    protected, selected = set(anchors), set(seeds)
    if any(not isinstance(node, str) or not node for node in protected):
        raise ValueError('Invalid anchor identity')
    if not selected.issubset(edges):
        raise ValueError('DRC seed does not resolve to a known copper edge')
    if not protected.issubset(adjacency):
        raise ValueError('Anchor not present in the native endpoint graph')
    queue = deque(sorted({node for uid in selected for node in edges[uid]
                          if node not in protected and len(adjacency[node]) == 1}))
    removed: set[str] = set()
    while queue:
        node = queue.popleft()
        if node in protected or len(adjacency[node]) != 1:
            continue
        uid = next(iter(adjacency[node]))
        a, b = edges[uid]
        if a == b:
            continue  # A self-loop is not a removable leaf.
        removed.add(uid)
        other = b if a == node else a
        adjacency[node].remove(uid)
        adjacency[other].remove(uid)
        if other not in protected and len(adjacency[other]) == 1:
            queue.append(other)
    return sorted(removed)
