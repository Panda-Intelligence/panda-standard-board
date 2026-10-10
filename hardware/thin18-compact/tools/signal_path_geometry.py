#!/usr/bin/env python3
"""Read-only planar centreline path measurements from native-exported copper.

Unlike summing all net copper, this selects a connected endpoint-to-endpoint
path and reports branches separately. It is NOT a delay/impedance simulation,
CAM approval, or an alternative to native DRC. Arc/plane signal routes require
separate modelling. Shapely2 is required; use the project's geometry environment.
"""
from __future__ import annotations
from collections import defaultdict
import heapq
import math
from typing import Any
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points

EPS = 0.00001


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def point(value: list[float]) -> tuple[float, float]:
    require(len(value) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool)
            and math.isfinite(x) for x in value), 'Invalid coordinate')
    return float(value[0]), float(value[1])


class SignalPathGraph:
    def __init__(self, geometry: dict[str, Any], net: str):
        require(bool(net) and net != 'GND', 'Use the power/plane analyser for ground')
        self.net = net
        self.geometry = geometry
        self.rows = []
        self.graph: dict[tuple, list] = defaultdict(list)
        self.points: dict[int, dict[float, tuple[float, float]]] = defaultdict(dict)
        self.pads: dict[tuple[str, str], list[tuple]] = defaultdict(list)
        self.links = []
        self.centres = []
        for row in geometry['items']:
            if row['net'] != net:
                continue
            require(row['type'] != 'zone', 'A signal plane is not a centreline route')
            require(row['type'] in {'track', 'pad', 'via'}, 'Unsupported copper object')
            shapes = [Polygon(p['outer'], p.get('holes', [])) for p in row['polygons']]
            copper = shapely.union_all(shapes)
            require(not copper.is_empty and copper.is_valid, 'Invalid native copper polygon')
            r = dict(row, shape=copper)
            if r['type'] == 'track':
                require(not r.get('is_arc', False), 'Arc centrelines are not modelled')
                r['centre'] = LineString([point(r['start']), point(r['end'])])
                require(r['centre'].length > 0 and r['width'] > 0, 'Degenerate track')
            else:
                r['centre'] = Point(point(r['position']))
            self.rows.append(r)
        require(bool(self.rows), 'Net has no exported copper: ' + net)
        layers = defaultdict(list)
        barrels = defaultdict(list)
        for i, row in enumerate(self.rows):
            layers[row['layer']].append(i)
            if row['type'] == 'track':
                self.node(i, tuple(row['start']))
                self.node(i, tuple(row['end']))
            elif row['type'] == 'pad':
                surface = (row.get('surface_only_no_drill') is True
                           and row.get('drill_mm') == [0.0, 0.0]
                           and sum(r['type'] == 'pad' and r['uuid'] == row['uuid']
                                   for r in self.rows) == 1)
                require(row.get('smd') is True or surface,
                        'Non-SMD terminal needs an explicit barrel model')
                self.pads[(row['ref'], row['pad'])].append(self.node(i, row['position']))
            elif row['type'] == 'via':
                barrels[row['uuid']].append(i)
        for layer, ids in layers.items():
            shapes = [self.rows[i]['shape'] for i in ids]
            tree = shapely.STRtree(shapes)
            for local, i in enumerate(ids):
                for other in tree.query(shapes[local], predicate='dwithin', distance=EPS):
                    j = ids[int(other)]
                    if j <= i:
                        continue
                    a, b = self.rows[i], self.rows[j]
                    pa, pb = nearest_points(a['centre'], b['centre'])
                    na, nb = self.node(i, pa.coords[0]), self.node(j, pb.coords[0])
                    self.links.append((na, nb, pa.distance(pb), {'kind': 'copper_join', 'layer': layer}))
        for uid, ids in barrels.items():
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    require(math.dist(point(self.rows[a]['position']), point(self.rows[b]['position'])) < EPS,
                            'Via identity is used at two positions')
                    self.links.append((self.node(a, self.rows[a]['position']),
                                       self.node(b, self.rows[b]['position']), 0.,
                                       {'kind': 'via', 'uuid': uid, 'from': self.rows[a]['layer'],
                                        'to': self.rows[b]['layer'], 'xy': self.rows[a]['position']}))
        for i, samples in self.points.items():
            r = self.rows[i]
            order = sorted(samples)
            for a, b in zip(order, order[1:]):
                pa, pb = samples[a], samples[b]
                self.links.append(((i, a), (i, b), math.dist(pa, pb),
                                   {'kind': 'track', 'uuid': r['uuid'], 'layer': r['layer'],
                                    'width': r['width'], 'start': pa, 'end': pb}))
        for a, b, length, meta in self.links:
            require(math.isfinite(length) and length >= 0, 'Invalid graph length')
            self.graph[a].append((b, length, meta))
            self.graph[b].append((a, length, meta))

    def node(self, index: int, xy: tuple[float, float]) -> tuple:
        row = self.rows[index]
        if row['type'] != 'track':
            return index, 'terminal'
        along = round(row['centre'].project(Point(point(xy))), 9)
        q = row['centre'].interpolate(along)
        self.points[index][along] = q.coords[0]
        return index, along

    def path(self, start: tuple[str, str], end: tuple[str, str]) -> dict[str, Any]:
        require(len(self.pads[start]) == len(self.pads[end]) == 1,
                'Missing/ambiguous terminal: ' + str((self.net, start, end)))
        source, goal = self.pads[start][0], self.pads[end][0]
        best = {source: 0.}
        previous = {}
        serial = 0
        queue = [(0., serial, source)]
        while queue:
            distance, _, node = heapq.heappop(queue)
            if distance > best[node] + 1e-10:
                continue
            if node == goal:
                break
            for target, length, meta in self.graph[node]:
                value = distance + length
                if value + 1e-10 < best.get(target, math.inf):
                    best[target] = value
                    previous[target] = (node, meta, length)
                    serial += 1
                    heapq.heappush(queue, (value, serial, target))
        require(goal in best, 'Terminals are not connected: ' + str((self.net, start, end)))
        path = []
        cursor = goal
        visited_rows = {goal[0]}
        while cursor != source:
            cursor, meta, length = previous[cursor]
            visited_rows.add(cursor[0])
            path.append(dict(meta, planar_length_mm=length))
        tracks = [p for p in path if p['kind'] == 'track']
        via_ids = {p['uuid'] for p in path if p['kind'] == 'via'}
        layers = sorted({p['layer'] for p in path if 'layer' in p})
        return {'net': self.net, 'source': list(start), 'target': list(end),
                'planar_path_length_mm': round(best[goal], 6),
                'gross_net_track_length_mm': round(sum(r['centre'].length for r in self.rows if r['type'] == 'track'), 6),
                'signal_layers_used': layers, 'vias_on_path': len(via_ids),
                'path_via_uuids': sorted(via_ids),
                'trace_widths_on_path_mm': sorted({p['width'] for p in tracks}),
                'path_track_uuids': sorted({p['uuid'] for p in tracks}),
                # Zero-length joins can use an actual conductor without traversing
                # any of its centreline. Preserve it when extracting a physical route.
                'physical_path_copper_uuids': sorted({self.rows[i]['uuid'] for i in visited_rows}),
                'physical_path_track_uuids': sorted({self.rows[i]['uuid'] for i in visited_rows if self.rows[i]['type']=='track'}),
                'via_barrel_length_and_delay_modelled': False,
                'reference_or_impedance_qualified': False,
                'manufacturing_release': False,
                'path_edges': list(reversed(path))}
