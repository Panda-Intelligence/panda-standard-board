"""Read global routing minima from a hash-bound native KiCad project.

A planner must not silently share one board's edge margin with a different board.
These are global minima only: per-net/custom rules, physical process acceptance,
current capacity and native DRC/ground checks still apply independently.
"""
from pathlib import Path
import hashlib
import json
import math
import re

FIELDS = (
    'min_copper_edge_clearance', 'min_track_width', 'min_via_diameter',
    'min_through_hole_diameter', 'min_via_annular_width',
    'min_hole_clearance', 'min_hole_to_hole',
)


def parse_bound_routing_limits(project_bytes, expected_sha256):
    """Return a fresh dictionary only for exactly the reviewed project bytes."""
    if not isinstance(project_bytes, bytes):
        raise ValueError('Native project must be supplied as exact bytes')
    if not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise ValueError('A reviewed native project SHA-256 is required')
    actual = hashlib.sha256(project_bytes).hexdigest()
    if actual != expected_sha256:
        raise ValueError('Native project differs from its reviewed source binding')
    try:
        data = json.loads(project_bytes)
        rules = data['board']['design_settings']['rules']
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError('Missing or invalid native global routing rules') from error
    if not isinstance(rules, dict):
        raise ValueError('Native routing rules must be a mapping')
    limits = {}
    for name in FIELDS:
        value = rules.get(name)
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise ValueError('Missing or nonnumeric native routing rule: ' + name)
        if not math.isfinite(value) or value <= 0:
            raise ValueError('Native routing rule must be positive and finite: ' + name)
        limits[name] = float(value)
    return {'native_project_sha256': actual, 'global_minima_mm': limits,
            'scope': 'global_minima_only_not_effective_net_rules_or_release',
            'native_drc_and_complete_ground_validation_required': True}


def read_bound_routing_limits(project_path, expected_sha256):
    """Read without modifying the project; its reviewed hash is mandatory."""
    return parse_bound_routing_limits(Path(project_path).read_bytes(), expected_sha256)
