"""
Constrained tracking logic for Version 3.

Propagates achieved gimbal angles over one orbit, applying:
1. Keep-out zone resolution
2. Angle-limit clipping
3. Rate-limit enforcement

At each time step the pipeline is:
    ideal angles  →  keep-out resolution  →  angle limits  →  rate limits  →  achieved angles

Initial condition: the achieved angles at the first sample are set to the
first resolved (keep-out + angle-limited) commanded angles.  This is a
simplification — the real system would have a pre-existing achieved state.
"""

from __future__ import annotations

import numpy as np

from app.models import KeepOutZone
from app.services.constraints import (
    AxisLimits,
    apply_angle_limits,
    apply_rate_limit,
    find_keepout_violation,
    resolve_keepout_violation,
)
from app.services.solar_array_geometry import compute_wing_normal


def compute_constrained_tracking(
    ideal_outer_deg: np.ndarray,
    ideal_inner_deg: np.ndarray,
    sun_x: np.ndarray,
    sun_y: np.ndarray,
    sun_z: np.ndarray,
    in_eclipse: np.ndarray,
    n0: np.ndarray,
    wing_name: str,
    axis_limits: AxisLimits,
    outer_rate_limit_deg_per_s: float,
    inner_rate_limit_deg_per_s: float,
    dt_s: float,
    keepout_zones: list[KeepOutZone],
) -> dict[str, np.ndarray]:
    """
    Compute achieved tracking angles for one wing over the orbit.

    Returns a dict with arrays (length N) for achieved angles, incidence,
    cosine efficiency, and constraint-status flags.
    """
    n = len(ideal_outer_deg)

    achieved_outer = np.empty(n)
    achieved_inner = np.empty(n)
    achieved_incidence = np.empty(n)
    achieved_cos_eff = np.empty(n)

    outer_angle_limited = np.zeros(n, dtype=bool)
    inner_angle_limited = np.zeros(n, dtype=bool)
    outer_rate_limited = np.zeros(n, dtype=bool)
    inner_rate_limited = np.zeros(n, dtype=bool)
    in_keepout = np.zeros(n, dtype=bool)
    keepout_labels: list[str] = [""] * n

    for i in range(n):
        # 1. Start from ideal angles
        cmd_outer = float(ideal_outer_deg[i])
        cmd_inner = float(ideal_inner_deg[i])

        # 2. Resolve keep-out zones
        cmd_outer, cmd_inner, was_kz, kz_label = resolve_keepout_violation(
            wing_name, cmd_outer, cmd_inner, keepout_zones, axis_limits,
        )
        # NOTE: in_keepout flag is set after step 4 (rate limiting) so it
        # reflects the *achieved* angle, not the ideal/resolved command.

        # 3. Apply angle limits
        cmd_outer, was_outer_lim = apply_angle_limits(
            cmd_outer, axis_limits.outer_min, axis_limits.outer_max,
        )
        cmd_inner, was_inner_lim = apply_angle_limits(
            cmd_inner, axis_limits.inner_min, axis_limits.inner_max,
        )
        outer_angle_limited[i] = was_outer_lim
        inner_angle_limited[i] = was_inner_lim

        # 4. Apply rate limits from previous achieved state
        if i == 0:
            ach_outer = cmd_outer
            ach_inner = cmd_inner
            outer_rate_limited[i] = False
            inner_rate_limited[i] = False
        else:
            ach_outer, was_outer_rl = apply_rate_limit(
                achieved_outer[i - 1], cmd_outer, outer_rate_limit_deg_per_s, dt_s,
            )
            ach_inner, was_inner_rl = apply_rate_limit(
                achieved_inner[i - 1], cmd_inner, inner_rate_limit_deg_per_s, dt_s,
            )
            outer_rate_limited[i] = was_outer_rl
            inner_rate_limited[i] = was_inner_rl

        achieved_outer[i] = ach_outer
        achieved_inner[i] = ach_inner

        # Post-rate-limit keep-out validation (C1+C2 fix):
        # Rate limiting may prevent the achieved angle from reaching the
        # resolved boundary, leaving it inside a keep-out zone.  Report
        # in_keepout based on where the *achieved* angle actually lands.
        ach_kz_violated, ach_kz_label = find_keepout_violation(
            wing_name, ach_outer, ach_inner, keepout_zones,
        )
        in_keepout[i] = ach_kz_violated
        keepout_labels[i] = ach_kz_label if ach_kz_violated else kz_label

        # 5. Compute achieved wing normal and incidence
        o_rad = np.radians(ach_outer)
        i_rad = np.radians(ach_inner)
        n_vec = compute_wing_normal(o_rad, i_rad, n0)
        n_len = np.linalg.norm(n_vec)
        if n_len > 0:
            n_vec = n_vec / n_len

        s = np.array([sun_x[i], sun_y[i], sun_z[i]])
        s_norm = np.linalg.norm(s)

        if s_norm < 1e-15 or bool(in_eclipse[i]):
            achieved_incidence[i] = 90.0
            achieved_cos_eff[i] = 0.0
        else:
            s_hat = s / s_norm
            dot = float(np.dot(n_vec, s_hat))
            dot_clipped = np.clip(dot, -1.0, 1.0)
            achieved_incidence[i] = float(np.degrees(np.arccos(dot_clipped)))
            achieved_cos_eff[i] = max(0.0, dot_clipped)

    return {
        "achieved_outer_deg": achieved_outer,
        "achieved_inner_deg": achieved_inner,
        "achieved_incidence_deg": achieved_incidence,
        "achieved_cos_eff": achieved_cos_eff,
        "outer_angle_limited": outer_angle_limited,
        "inner_angle_limited": inner_angle_limited,
        "outer_rate_limited": outer_rate_limited,
        "inner_rate_limited": inner_rate_limited,
        "in_keepout": in_keepout,
        "keepout_label": keepout_labels,
    }
