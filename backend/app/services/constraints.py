"""
Articulation constraint logic for Version 3.

Provides helpers for:
- Angle-limit clipping
- Gimbal rate-limit enforcement
- Keep-out zone detection and resolution

Keep-Out Resolution Strategy (Version 3 approximation)
-------------------------------------------------------
When the ideal angle pair (outer, inner) falls inside a rectangular keep-out
zone in angle space, the pair is projected to the nearest boundary point of
that rectangle using Euclidean distance in angle space.

If the projected point still violates angle limits, it is clipped to the angle
limits.  When multiple keep-out zones overlap, the nearest allowed point among
all candidate boundary projections is chosen.

This is a first-order approximation suitable for engineering trade studies.
It does not guarantee globally optimal pointing recovery.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.models import KeepOutZone


# ---------------------------------------------------------------------------
# Angle-limit clipping
# ---------------------------------------------------------------------------


def apply_angle_limits(angle_deg: float, min_deg: float, max_deg: float) -> tuple[float, bool]:
    """
    Clip *angle_deg* to [min_deg, max_deg].

    Returns (clipped_angle, was_clipped).
    """
    if angle_deg < min_deg:
        return min_deg, True
    if angle_deg > max_deg:
        return max_deg, True
    return angle_deg, False


# ---------------------------------------------------------------------------
# Rate-limit enforcement
# ---------------------------------------------------------------------------


def apply_rate_limit(
    prev_deg: float,
    cmd_deg: float,
    rate_limit_deg_per_s: float,
    dt_s: float,
) -> tuple[float, bool]:
    """
    Move from *prev_deg* toward *cmd_deg*, limited by max angular rate.

    max_delta = rate_limit_deg_per_s * dt_s

    Returns (achieved_deg, was_rate_limited).
    """
    max_delta = rate_limit_deg_per_s * dt_s
    delta = cmd_deg - prev_deg

    if abs(delta) <= max_delta:
        return cmd_deg, False

    sign = 1.0 if delta > 0 else -1.0
    return prev_deg + sign * max_delta, True


# ---------------------------------------------------------------------------
# Keep-out zone detection
# ---------------------------------------------------------------------------


def is_in_keepout_zone(
    outer_deg: float,
    inner_deg: float,
    zone: KeepOutZone,
) -> bool:
    """True if (outer_deg, inner_deg) lies inside or on the boundary of the rectangular zone."""
    return (
        zone.outer_min_deg <= outer_deg <= zone.outer_max_deg
        and zone.inner_min_deg <= inner_deg <= zone.inner_max_deg
    )


def find_keepout_violation(
    wing_name: str,
    outer_deg: float,
    inner_deg: float,
    keepout_zones: list[KeepOutZone],
) -> tuple[bool, str]:
    """
    Check whether (outer, inner) falls inside any keep-out zone for *wing_name*.

    Returns (is_violated, zone_label).  zone_label is empty when no violation.
    """
    for zone in keepout_zones:
        if zone.wing != wing_name:
            continue
        if is_in_keepout_zone(outer_deg, inner_deg, zone):
            return True, zone.label
    return False, ""


# ---------------------------------------------------------------------------
# Keep-out resolution
# ---------------------------------------------------------------------------


@dataclass
class AxisLimits:
    outer_min: float
    outer_max: float
    inner_min: float
    inner_max: float


_BOUNDARY_NUDGE_DEG = 1e-6


def _project_to_rect_boundary(
    outer: float,
    inner: float,
    zone: KeepOutZone,
) -> list[tuple[float, float, float]]:
    """
    Project a point inside a rectangular zone to each of its four boundary
    edges and return candidate (outer, inner, distance) tuples.

    A small nudge is applied so the candidate lies strictly outside the zone
    boundary (the zone is defined with inclusive inequalities).
    """
    candidates: list[tuple[float, float, float]] = []

    clamp_outer = max(zone.outer_min_deg, min(zone.outer_max_deg, outer))
    clamp_inner = max(zone.inner_min_deg, min(zone.inner_max_deg, inner))

    edges: list[tuple[float, float]] = [
        (zone.outer_min_deg - _BOUNDARY_NUDGE_DEG, clamp_inner),
        (zone.outer_max_deg + _BOUNDARY_NUDGE_DEG, clamp_inner),
        (clamp_outer, zone.inner_min_deg - _BOUNDARY_NUDGE_DEG),
        (clamp_outer, zone.inner_max_deg + _BOUNDARY_NUDGE_DEG),
    ]

    for eo, ei in edges:
        d = math.hypot(eo - outer, ei - inner)
        candidates.append((eo, ei, d))

    return candidates


def resolve_keepout_violation(
    wing_name: str,
    ideal_outer_deg: float,
    ideal_inner_deg: float,
    keepout_zones: list[KeepOutZone],
    axis_limits: AxisLimits,
) -> tuple[float, float, bool, str]:
    """
    If the ideal angle pair is inside a keep-out zone, project to the nearest
    allowed boundary point.

    Returns (resolved_outer, resolved_inner, was_adjusted, zone_label).
    """
    violated, label = find_keepout_violation(
        wing_name, ideal_outer_deg, ideal_inner_deg, keepout_zones,
    )
    if not violated:
        return ideal_outer_deg, ideal_inner_deg, False, ""

    best_outer = ideal_outer_deg
    best_inner = ideal_inner_deg
    best_dist = math.inf
    best_label = label

    for zone in keepout_zones:
        if zone.wing != wing_name:
            continue
        if not is_in_keepout_zone(ideal_outer_deg, ideal_inner_deg, zone):
            continue

        for co, ci, d in _project_to_rect_boundary(
            ideal_outer_deg, ideal_inner_deg, zone,
        ):
            co_clipped = max(axis_limits.outer_min, min(axis_limits.outer_max, co))
            ci_clipped = max(axis_limits.inner_min, min(axis_limits.inner_max, ci))

            still_violated, _ = find_keepout_violation(
                wing_name, co_clipped, ci_clipped, keepout_zones,
            )
            if still_violated:
                continue

            dist = math.hypot(co_clipped - ideal_outer_deg, ci_clipped - ideal_inner_deg)
            if dist < best_dist:
                best_dist = dist
                best_outer = co_clipped
                best_inner = ci_clipped
                best_label = zone.label

    if math.isinf(best_dist):
        # No boundary candidate survived — overlapping zones fill the allowed
        # space.  Clip to axis limits as a last resort and validate.
        best_outer = max(axis_limits.outer_min, min(axis_limits.outer_max, ideal_outer_deg))
        best_inner = max(axis_limits.inner_min, min(axis_limits.inner_max, ideal_inner_deg))
        still_violated, still_label = find_keepout_violation(
            wing_name, best_outer, best_inner, keepout_zones,
        )
        if still_violated:
            # Keep-out zones cover the entire allowed angle space; no valid
            # position exists.  The caller (tracking loop) will detect this
            # via its post-rate-limit keep-out check on the achieved angle.
            best_label = f"UNRESOLVED:{still_label}"

    return best_outer, best_inner, True, best_label
