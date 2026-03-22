"""
Solar power generation model for a dual-wing solar array system.

Power per wing
--------------
    P_wing = SOLAR_CONSTANT * area_per_wing * cell_efficiency
             * degradation_factor * cosine_efficiency

    cosine_efficiency = max(0, dot(wing_normal, sun_direction))

During eclipse: P_wing = 0

Total power: P_total = P_left + P_right

Assumptions (Version 2)
-----------------------
- Panel front side only generates power; back side contributes zero.
- Sun must be on the positive side of the panel normal to generate power.
- Ideal articulation — no gimbal limits, rate limits, or cable-wrap.
- No structural blockage or body shadowing.
- No keep-out zones.
"""

import numpy as np

from app.services.constants import SOLAR_CONSTANT_W_M2


def compute_wing_power(
    cosine_efficiency: np.ndarray,
    in_eclipse: np.ndarray,
    area_m2: float,
    cell_efficiency: float,
    degradation_factor: float,
) -> np.ndarray:
    """
    Compute instantaneous power [W] for one wing at each orbit sample.

    Parameters
    ----------
    cosine_efficiency : (N,) array
        max(0, dot(n_hat, s_hat)) at each sample.
    in_eclipse : (N,) bool array
        True where satellite is in Earth's shadow.
    area_m2 : float
        Solar array area per wing [m²].
    cell_efficiency : float
        Solar cell BOL efficiency [0–1].
    degradation_factor : float
        End-of-life degradation factor [0–1].

    Returns
    -------
    power_w : (N,) array
        Instantaneous electrical power [W] at each sample.
    """
    sunlit = ~np.asarray(in_eclipse, dtype=bool)
    power = (
        SOLAR_CONSTANT_W_M2
        * area_m2
        * cell_efficiency
        * degradation_factor
        * np.asarray(cosine_efficiency, dtype=float)
        * sunlit.astype(float)
    )
    return np.maximum(power, 0.0)


def compute_power_summary(
    left_power: np.ndarray,
    right_power: np.ndarray,
    required_bus_power_w: float,
    left_incidence: np.ndarray,
    right_incidence: np.ndarray,
) -> dict[str, float]:
    """
    Compute aggregate power and incidence statistics over the orbit.

    Returns
    -------
    dict with keys:
        average_total_power_w, average_left_power_w, average_right_power_w,
        peak_total_power_w, min_total_power_w,
        percent_of_required_bus_power_avg,
        max_left_incidence_deg, max_right_incidence_deg,
        min_left_incidence_deg, min_right_incidence_deg
    """
    total = left_power + right_power
    avg_total = float(np.mean(total))
    pct = (avg_total / required_bus_power_w * 100.0) if required_bus_power_w > 0 else 0.0

    return {
        "average_total_power_w": avg_total,
        "average_left_power_w": float(np.mean(left_power)),
        "average_right_power_w": float(np.mean(right_power)),
        "peak_total_power_w": float(np.max(total)),
        "min_total_power_w": float(np.min(total)),
        "percent_of_required_bus_power_avg": pct,
        "max_left_incidence_deg": float(np.max(left_incidence)),
        "max_right_incidence_deg": float(np.max(right_incidence)),
        "min_left_incidence_deg": float(np.min(left_incidence)),
        "min_right_incidence_deg": float(np.min(right_incidence)),
    }
