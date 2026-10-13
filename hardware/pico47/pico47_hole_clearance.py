"""Geometry helpers for conservative NPTH routing obstacles.

These calculations do not override KiCad rules or qualify a fabrication process.
A non-plated hole's edge clearance is measured to the new via's copper annulus,
not merely to its drill. Plated-hole drill spacing is a separate constraint.
"""
import math


def _positive(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + ' must be a finite number')
    if not math.isfinite(value) or value <= 0:
        raise ValueError(label + ' must be positive and finite')
    return float(value)


def npth_annulus_allowance(copper_diameter_mm: float, drill_diameter_mm: float) -> float:
    """Extra obstacle inflation for a planner already using the drill radius.

    For a 0.45/0.25mm via, a drill-based obstacle needs another 0.10mm to account
    for the annulus. The caller must still add the native hole clearance and
    its numerical margin, and independently enforce all other native rules.
    """
    copper = _positive(copper_diameter_mm, 'Copper diameter')
    drill = _positive(drill_diameter_mm, 'Drill diameter')
    if copper <= drill:
        raise ValueError('A via must have a positive copper annulus')
    return (copper - drill) / 2.0


def round_npth_copper_clearance(center_distance_mm: float,
                                npth_diameter_mm: float,
                                via_copper_diameter_mm: float) -> float:
    """Edge-to-edge gap for a round NPTH and a circular copper annulus.

    A negative result indicates overlap. This formula is not a substitute for
    polygon-distance checks on slots, oblong holes or other noncircular shapes.
    """
    if isinstance(center_distance_mm, bool) or not isinstance(center_distance_mm, (int, float)):
        raise ValueError('Center distance must be a finite nonnegative number')
    if not math.isfinite(center_distance_mm) or center_distance_mm < 0:
        raise ValueError('Center distance must be finite and nonnegative')
    hole = _positive(npth_diameter_mm, 'NPTH diameter')
    copper = _positive(via_copper_diameter_mm, 'Copper diameter')
    return float(center_distance_mm) - (hole + copper) / 2.0
