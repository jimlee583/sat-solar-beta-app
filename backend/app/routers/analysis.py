"""Analysis router — POST /api/analyze/v1, /v2, and /v3."""

from dataclasses import dataclass

import numpy as np
from fastapi import APIRouter

from app.models import (
    AnalysisRequest,
    AnalysisRequestV2,
    AnalysisRequestV3,
    AnalysisResponse,
    AnalysisResponseV2,
    AnalysisResponseV3,
)
from app.services.constraints import AxisLimits
from app.services.eclipse import (
    critical_beta_deg,
    eclipse_duration_s,
    eclipse_fraction,
)
from app.services.orbit import orbit_radius_km, orbital_period_s
from app.services.power import compute_power_summary, compute_wing_power
from app.services.solar_array_geometry import (
    N0_LEFT,
    N0_RIGHT,
    compute_wing_arrays,
)
from app.services.sun_geometry import eclipse_mask, sun_angles_vvlh, sun_vector_vvlh
from app.services.tracking import compute_constrained_tracking

router = APIRouter(prefix="/api/analyze", tags=["analysis"])


# ---------------------------------------------------------------------------
# Shared V1 computation helper (P10)
# ---------------------------------------------------------------------------


@dataclass
class _V1Base:
    r_km: float
    T_s: float
    T_min: float
    beta_crit: float
    ef: float
    ed_s: float
    ed_min: float
    angles: np.ndarray
    sx: np.ndarray
    sy: np.ndarray
    sz: np.ndarray
    az: np.ndarray
    el: np.ndarray
    mask: np.ndarray


def _compute_v1_base(altitude_km: float, beta_deg: float, num_samples: int) -> _V1Base:
    """Compute orbit scalars, eclipse geometry, and sampled sun-vector arrays."""
    r_km = orbit_radius_km(altitude_km)
    T_s = orbital_period_s(altitude_km)
    T_min = T_s / 60.0

    beta_crit = critical_beta_deg(altitude_km)
    ef = eclipse_fraction(altitude_km, beta_deg)
    ed_s = eclipse_duration_s(altitude_km, beta_deg, T_s)
    ed_min = ed_s / 60.0

    angles = np.linspace(0.0, 360.0, num_samples, endpoint=False)
    sx, sy, sz = sun_vector_vvlh(angles, beta_deg)
    az, el = sun_angles_vvlh(sx, sy, sz)
    mask = eclipse_mask(angles, altitude_km, beta_deg)

    return _V1Base(
        r_km=r_km, T_s=T_s, T_min=T_min,
        beta_crit=beta_crit, ef=ef, ed_s=ed_s, ed_min=ed_min,
        angles=angles, sx=sx, sy=sy, sz=sz, az=az, el=el, mask=mask,
    )


def _v1_scalar_kwargs(b: _V1Base) -> dict:
    """Serialize V1 scalar fields for use in all three response constructors."""
    return dict(
        orbit_radius_km=round(b.r_km, 4),
        orbital_period_s=round(b.T_s, 4),
        orbital_period_min=round(b.T_min, 4),
        eclipse_duration_s=round(b.ed_s, 4),
        eclipse_duration_min=round(b.ed_min, 4),
        eclipse_fraction=round(b.ef, 6),
        sunlight_fraction=round(1.0 - b.ef, 6),
        critical_beta_deg_for_no_eclipse=round(b.beta_crit, 4),
    )


def _v1_array_kwargs(b: _V1Base) -> dict:
    """Serialize V1 array fields for use in all three response constructors."""
    return dict(
        orbit_angle_deg=b.angles.tolist(),
        sun_vvlh_x=b.sx.tolist(),
        sun_vvlh_y=b.sy.tolist(),
        sun_vvlh_z=b.sz.tolist(),
        sun_az_deg=b.az.tolist(),
        sun_el_deg=b.el.tolist(),
        in_eclipse=b.mask.tolist(),
    )


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.post("/v1", response_model=AnalysisResponse)
def analyze_v1(req: AnalysisRequest) -> AnalysisResponse:
    """Run the Version 1 single-orbit solar environment analysis."""
    b = _compute_v1_base(req.altitude_km, req.beta_deg, req.num_samples_per_orbit)
    return AnalysisResponse(**_v1_scalar_kwargs(b), **_v1_array_kwargs(b))


@router.post("/v2", response_model=AnalysisResponseV2)
def analyze_v2(req: AnalysisRequestV2) -> AnalysisResponseV2:
    """Run the Version 2 analysis: orbit + dual-wing solar array + power."""
    b = _compute_v1_base(req.altitude_km, req.beta_deg, req.num_samples_per_orbit)

    # Solar array tracking for each wing
    right_wing = compute_wing_arrays(b.sx, b.sy, b.sz, N0_RIGHT)
    left_wing = compute_wing_arrays(b.sx, b.sy, b.sz, N0_LEFT)

    # Power per wing
    right_power = compute_wing_power(
        right_wing["cosine_efficiency"], b.mask,
        req.solar_array_area_m2_per_wing, req.solar_cell_efficiency,
        req.degradation_factor,
    )
    left_power = compute_wing_power(
        left_wing["cosine_efficiency"], b.mask,
        req.solar_array_area_m2_per_wing, req.solar_cell_efficiency,
        req.degradation_factor,
    )
    total_power = left_power + right_power

    summary = compute_power_summary(
        left_power, right_power, req.required_bus_power_w,
        left_wing["incidence_deg"], right_wing["incidence_deg"],
    )

    return AnalysisResponseV2(
        **_v1_scalar_kwargs(b),
        **_v1_array_kwargs(b),
        # Right wing arrays
        right_outer_angle_deg=right_wing["outer_angle_deg"].tolist(),
        right_inner_angle_deg=right_wing["inner_angle_deg"].tolist(),
        right_normal_x=right_wing["normal_x"].tolist(),
        right_normal_y=right_wing["normal_y"].tolist(),
        right_normal_z=right_wing["normal_z"].tolist(),
        right_incidence_deg=right_wing["incidence_deg"].tolist(),
        right_cosine_efficiency=right_wing["cosine_efficiency"].tolist(),
        right_power_w=right_power.tolist(),
        # Left wing arrays
        left_outer_angle_deg=left_wing["outer_angle_deg"].tolist(),
        left_inner_angle_deg=left_wing["inner_angle_deg"].tolist(),
        left_normal_x=left_wing["normal_x"].tolist(),
        left_normal_y=left_wing["normal_y"].tolist(),
        left_normal_z=left_wing["normal_z"].tolist(),
        left_incidence_deg=left_wing["incidence_deg"].tolist(),
        left_cosine_efficiency=left_wing["cosine_efficiency"].tolist(),
        left_power_w=left_power.tolist(),
        # Total power
        total_power_w=total_power.tolist(),
        # Summary
        average_total_power_w=round(summary["average_total_power_w"], 2),
        average_left_power_w=round(summary["average_left_power_w"], 2),
        average_right_power_w=round(summary["average_right_power_w"], 2),
        peak_total_power_w=round(summary["peak_total_power_w"], 2),
        min_total_power_w=round(summary["min_total_power_w"], 2),
        percent_of_required_bus_power_avg=round(
            summary["percent_of_required_bus_power_avg"], 2
        ),
        max_left_incidence_deg=round(summary["max_left_incidence_deg"], 4),
        max_right_incidence_deg=round(summary["max_right_incidence_deg"], 4),
        min_left_incidence_deg=round(summary["min_left_incidence_deg"], 4),
        min_right_incidence_deg=round(summary["min_right_incidence_deg"], 4),
    )


@router.post("/v3", response_model=AnalysisResponseV3)
def analyze_v3(req: AnalysisRequestV3) -> AnalysisResponseV3:
    """Run the Version 3 analysis: constrained articulation tracking."""
    b = _compute_v1_base(req.altitude_km, req.beta_deg, req.num_samples_per_orbit)

    # Ideal solar array tracking for each wing
    right_wing = compute_wing_arrays(b.sx, b.sy, b.sz, N0_RIGHT)
    left_wing = compute_wing_arrays(b.sx, b.sy, b.sz, N0_LEFT)

    # Ideal power per wing
    right_power_ideal = compute_wing_power(
        right_wing["cosine_efficiency"], b.mask,
        req.solar_array_area_m2_per_wing, req.solar_cell_efficiency,
        req.degradation_factor,
    )
    left_power_ideal = compute_wing_power(
        left_wing["cosine_efficiency"], b.mask,
        req.solar_array_area_m2_per_wing, req.solar_cell_efficiency,
        req.degradation_factor,
    )
    total_power_ideal = left_power_ideal + right_power_ideal

    # Ideal summary (unique metrics not in V3-specific summary below)
    summary_ideal = compute_power_summary(
        left_power_ideal, right_power_ideal, req.required_bus_power_w,
        left_wing["incidence_deg"], right_wing["incidence_deg"],
    )

    # Time step and axis limits
    dt_s = b.T_s / req.num_samples_per_orbit
    right_limits = AxisLimits(
        outer_min=req.right_outer_min_deg, outer_max=req.right_outer_max_deg,
        inner_min=req.right_inner_min_deg, inner_max=req.right_inner_max_deg,
    )
    left_limits = AxisLimits(
        outer_min=req.left_outer_min_deg, outer_max=req.left_outer_max_deg,
        inner_min=req.left_inner_min_deg, inner_max=req.left_inner_max_deg,
    )

    # Constrained tracking
    right_ct = compute_constrained_tracking(
        right_wing["outer_angle_deg"], right_wing["inner_angle_deg"],
        b.sx, b.sy, b.sz, b.mask, N0_RIGHT, "right",
        right_limits, req.outer_rate_limit_deg_per_s,
        req.inner_rate_limit_deg_per_s, dt_s, req.keepout_zones,
    )
    left_ct = compute_constrained_tracking(
        left_wing["outer_angle_deg"], left_wing["inner_angle_deg"],
        b.sx, b.sy, b.sz, b.mask, N0_LEFT, "left",
        left_limits, req.outer_rate_limit_deg_per_s,
        req.inner_rate_limit_deg_per_s, dt_s, req.keepout_zones,
    )

    # Achieved power
    right_power_achieved = compute_wing_power(
        right_ct["achieved_cos_eff"], b.mask,
        req.solar_array_area_m2_per_wing, req.solar_cell_efficiency,
        req.degradation_factor,
    )
    left_power_achieved = compute_wing_power(
        left_ct["achieved_cos_eff"], b.mask,
        req.solar_array_area_m2_per_wing, req.solar_cell_efficiency,
        req.degradation_factor,
    )
    total_power_achieved = left_power_achieved + right_power_achieved

    # Summary metrics
    avg_ideal = float(np.mean(total_power_ideal))
    avg_achieved = float(np.mean(total_power_achieved))
    max_possible = (
        1361.0 * req.solar_array_area_m2_per_wing * 2.0
        * req.solar_cell_efficiency * req.degradation_factor
    )

    # Pointing-loss metrics use sunlit-only samples so eclipse unavailability
    # does not inflate the reported percentage (eclipse_fraction covers that).
    sunlit = ~b.mask
    n_sunlit = int(np.sum(sunlit))
    if n_sunlit > 0 and max_possible > 0:
        avg_ideal_sunlit = float(np.sum(total_power_ideal[sunlit])) / n_sunlit
        avg_achieved_sunlit = float(np.sum(total_power_achieved[sunlit])) / n_sunlit
        ideal_loss = (1.0 - avg_ideal_sunlit / max_possible) * 100.0
        constrained_loss = (1.0 - avg_achieved_sunlit / max_possible) * 100.0
    else:
        ideal_loss = 0.0
        constrained_loss = 0.0

    energy_ratio = avg_achieved / avg_ideal if avg_ideal > 0 else 0.0
    pct_ideal = (avg_ideal / req.required_bus_power_w * 100.0) if req.required_bus_power_w > 0 else 0.0
    pct_achieved = (avg_achieved / req.required_bus_power_w * 100.0) if req.required_bus_power_w > 0 else 0.0
    n_samples = float(req.num_samples_per_orbit)

    return AnalysisResponseV3(
        **_v1_scalar_kwargs(b),
        **_v1_array_kwargs(b),
        # Right wing ideal vs achieved
        right_ideal_outer_angle_deg=right_wing["outer_angle_deg"].tolist(),
        right_ideal_inner_angle_deg=right_wing["inner_angle_deg"].tolist(),
        right_achieved_outer_angle_deg=right_ct["achieved_outer_deg"].tolist(),
        right_achieved_inner_angle_deg=right_ct["achieved_inner_deg"].tolist(),
        right_ideal_incidence_deg=right_wing["incidence_deg"].tolist(),
        right_achieved_incidence_deg=right_ct["achieved_incidence_deg"].tolist(),
        right_ideal_power_w=right_power_ideal.tolist(),
        right_achieved_power_w=right_power_achieved.tolist(),
        right_outer_angle_limited=right_ct["outer_angle_limited"].tolist(),
        right_inner_angle_limited=right_ct["inner_angle_limited"].tolist(),
        right_outer_rate_limited=right_ct["outer_rate_limited"].tolist(),
        right_inner_rate_limited=right_ct["inner_rate_limited"].tolist(),
        right_in_keepout=right_ct["in_keepout"].tolist(),
        right_keepout_label=right_ct["keepout_label"],
        # Left wing ideal vs achieved
        left_ideal_outer_angle_deg=left_wing["outer_angle_deg"].tolist(),
        left_ideal_inner_angle_deg=left_wing["inner_angle_deg"].tolist(),
        left_achieved_outer_angle_deg=left_ct["achieved_outer_deg"].tolist(),
        left_achieved_inner_angle_deg=left_ct["achieved_inner_deg"].tolist(),
        left_ideal_incidence_deg=left_wing["incidence_deg"].tolist(),
        left_achieved_incidence_deg=left_ct["achieved_incidence_deg"].tolist(),
        left_ideal_power_w=left_power_ideal.tolist(),
        left_achieved_power_w=left_power_achieved.tolist(),
        left_outer_angle_limited=left_ct["outer_angle_limited"].tolist(),
        left_inner_angle_limited=left_ct["inner_angle_limited"].tolist(),
        left_outer_rate_limited=left_ct["outer_rate_limited"].tolist(),
        left_inner_rate_limited=left_ct["inner_rate_limited"].tolist(),
        left_in_keepout=left_ct["in_keepout"].tolist(),
        left_keepout_label=left_ct["keepout_label"],
        # Total power arrays
        ideal_total_power_w=total_power_ideal.tolist(),
        achieved_total_power_w=total_power_achieved.tolist(),
        # Summary metrics
        average_ideal_total_power_w=round(avg_ideal, 2),
        average_achieved_total_power_w=round(avg_achieved, 2),
        average_ideal_left_power_w=round(summary_ideal["average_left_power_w"], 2),
        average_ideal_right_power_w=round(summary_ideal["average_right_power_w"], 2),
        peak_ideal_total_power_w=round(summary_ideal["peak_total_power_w"], 2),
        min_ideal_total_power_w=round(summary_ideal["min_total_power_w"], 2),
        percent_of_required_bus_power_ideal_avg=round(pct_ideal, 2),
        percent_of_required_bus_power_achieved_avg=round(pct_achieved, 2),
        ideal_tracking_loss_percent=round(ideal_loss, 4),
        constrained_tracking_loss_percent=round(constrained_loss, 4),
        achieved_vs_ideal_energy_ratio=round(energy_ratio, 6),
        max_left_incidence_deg=round(summary_ideal["max_left_incidence_deg"], 4),
        max_right_incidence_deg=round(summary_ideal["max_right_incidence_deg"], 4),
        min_left_incidence_deg=round(summary_ideal["min_left_incidence_deg"], 4),
        min_right_incidence_deg=round(summary_ideal["min_right_incidence_deg"], 4),
        right_fraction_outer_angle_limited=round(float(np.sum(right_ct["outer_angle_limited"])) / n_samples, 6),
        right_fraction_inner_angle_limited=round(float(np.sum(right_ct["inner_angle_limited"])) / n_samples, 6),
        left_fraction_outer_angle_limited=round(float(np.sum(left_ct["outer_angle_limited"])) / n_samples, 6),
        left_fraction_inner_angle_limited=round(float(np.sum(left_ct["inner_angle_limited"])) / n_samples, 6),
        right_fraction_outer_rate_limited=round(float(np.sum(right_ct["outer_rate_limited"])) / n_samples, 6),
        right_fraction_inner_rate_limited=round(float(np.sum(right_ct["inner_rate_limited"])) / n_samples, 6),
        left_fraction_outer_rate_limited=round(float(np.sum(left_ct["outer_rate_limited"])) / n_samples, 6),
        left_fraction_inner_rate_limited=round(float(np.sum(left_ct["inner_rate_limited"])) / n_samples, 6),
        right_fraction_in_keepout=round(float(np.sum(right_ct["in_keepout"])) / n_samples, 6),
        left_fraction_in_keepout=round(float(np.sum(left_ct["in_keepout"])) / n_samples, 6),
    )
