"""Analysis router — POST /api/analyze/v1, /v2, and /v3."""

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


@router.post("/v1", response_model=AnalysisResponse)
def analyze_v1(req: AnalysisRequest) -> AnalysisResponse:
    """Run the Version 1 single-orbit solar environment analysis."""

    # --- Orbit scalars ---
    r_km = orbit_radius_km(req.altitude_km)
    T_s = orbital_period_s(req.altitude_km)
    T_min = T_s / 60.0

    # --- Eclipse scalars ---
    beta_crit = critical_beta_deg(req.altitude_km)
    ef = eclipse_fraction(req.altitude_km, req.beta_deg)
    ed_s = eclipse_duration_s(req.altitude_km, req.beta_deg, T_s)
    ed_min = ed_s / 60.0

    # --- Sampled arrays over one orbit ---
    angles = np.linspace(0.0, 360.0, req.num_samples_per_orbit, endpoint=False)
    sx, sy, sz = sun_vector_vvlh(angles, req.beta_deg)
    az, el = sun_angles_vvlh(sx, sy, sz)
    mask = eclipse_mask(angles, req.altitude_km, req.beta_deg)

    return AnalysisResponse(
        orbit_radius_km=round(r_km, 4),
        orbital_period_s=round(T_s, 4),
        orbital_period_min=round(T_min, 4),
        eclipse_duration_s=round(ed_s, 4),
        eclipse_duration_min=round(ed_min, 4),
        eclipse_fraction=round(ef, 6),
        sunlight_fraction=round(1.0 - ef, 6),
        critical_beta_deg_for_no_eclipse=round(beta_crit, 4),
        orbit_angle_deg=angles.tolist(),
        sun_vvlh_x=sx.tolist(),
        sun_vvlh_y=sy.tolist(),
        sun_vvlh_z=sz.tolist(),
        sun_az_deg=az.tolist(),
        sun_el_deg=el.tolist(),
        in_eclipse=mask.tolist(),
    )


@router.post("/v2", response_model=AnalysisResponseV2)
def analyze_v2(req: AnalysisRequestV2) -> AnalysisResponseV2:
    """Run the Version 2 analysis: orbit + dual-wing solar array + power."""

    # --- V1: Orbit scalars ---
    r_km = orbit_radius_km(req.altitude_km)
    T_s = orbital_period_s(req.altitude_km)
    T_min = T_s / 60.0

    # --- V1: Eclipse scalars ---
    beta_crit = critical_beta_deg(req.altitude_km)
    ef = eclipse_fraction(req.altitude_km, req.beta_deg)
    ed_s = eclipse_duration_s(req.altitude_km, req.beta_deg, T_s)
    ed_min = ed_s / 60.0

    # --- V1: Sampled arrays over one orbit ---
    angles = np.linspace(0.0, 360.0, req.num_samples_per_orbit, endpoint=False)
    sx, sy, sz = sun_vector_vvlh(angles, req.beta_deg)
    az, el = sun_angles_vvlh(sx, sy, sz)
    mask = eclipse_mask(angles, req.altitude_km, req.beta_deg)

    # --- V2: Solar array tracking for each wing ---
    right_wing = compute_wing_arrays(sx, sy, sz, N0_RIGHT)
    left_wing = compute_wing_arrays(sx, sy, sz, N0_LEFT)

    # --- V2: Power per wing ---
    right_power = compute_wing_power(
        right_wing["cosine_efficiency"],
        mask,
        req.solar_array_area_m2_per_wing,
        req.solar_cell_efficiency,
        req.degradation_factor,
    )
    left_power = compute_wing_power(
        left_wing["cosine_efficiency"],
        mask,
        req.solar_array_area_m2_per_wing,
        req.solar_cell_efficiency,
        req.degradation_factor,
    )
    total_power = left_power + right_power

    # --- V2: Summary statistics ---
    summary = compute_power_summary(
        left_power,
        right_power,
        req.required_bus_power_w,
        left_wing["incidence_deg"],
        right_wing["incidence_deg"],
    )

    return AnalysisResponseV2(
        # V1 scalars
        orbit_radius_km=round(r_km, 4),
        orbital_period_s=round(T_s, 4),
        orbital_period_min=round(T_min, 4),
        eclipse_duration_s=round(ed_s, 4),
        eclipse_duration_min=round(ed_min, 4),
        eclipse_fraction=round(ef, 6),
        sunlight_fraction=round(1.0 - ef, 6),
        critical_beta_deg_for_no_eclipse=round(beta_crit, 4),
        # V1 arrays
        orbit_angle_deg=angles.tolist(),
        sun_vvlh_x=sx.tolist(),
        sun_vvlh_y=sy.tolist(),
        sun_vvlh_z=sz.tolist(),
        sun_az_deg=az.tolist(),
        sun_el_deg=el.tolist(),
        in_eclipse=mask.tolist(),
        # V2: Right wing arrays
        right_outer_angle_deg=right_wing["outer_angle_deg"].tolist(),
        right_inner_angle_deg=right_wing["inner_angle_deg"].tolist(),
        right_normal_x=right_wing["normal_x"].tolist(),
        right_normal_y=right_wing["normal_y"].tolist(),
        right_normal_z=right_wing["normal_z"].tolist(),
        right_incidence_deg=right_wing["incidence_deg"].tolist(),
        right_cosine_efficiency=right_wing["cosine_efficiency"].tolist(),
        right_power_w=right_power.tolist(),
        # V2: Left wing arrays
        left_outer_angle_deg=left_wing["outer_angle_deg"].tolist(),
        left_inner_angle_deg=left_wing["inner_angle_deg"].tolist(),
        left_normal_x=left_wing["normal_x"].tolist(),
        left_normal_y=left_wing["normal_y"].tolist(),
        left_normal_z=left_wing["normal_z"].tolist(),
        left_incidence_deg=left_wing["incidence_deg"].tolist(),
        left_cosine_efficiency=left_wing["cosine_efficiency"].tolist(),
        left_power_w=left_power.tolist(),
        # V2: Total power
        total_power_w=total_power.tolist(),
        # V2: Summary
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

    # --- V1: Orbit scalars ---
    r_km = orbit_radius_km(req.altitude_km)
    T_s = orbital_period_s(req.altitude_km)
    T_min = T_s / 60.0

    # --- V1: Eclipse scalars ---
    beta_crit = critical_beta_deg(req.altitude_km)
    ef = eclipse_fraction(req.altitude_km, req.beta_deg)
    ed_s = eclipse_duration_s(req.altitude_km, req.beta_deg, T_s)
    ed_min = ed_s / 60.0

    # --- V1: Sampled arrays over one orbit ---
    angles = np.linspace(0.0, 360.0, req.num_samples_per_orbit, endpoint=False)
    sx, sy, sz = sun_vector_vvlh(angles, req.beta_deg)
    az, el = sun_angles_vvlh(sx, sy, sz)
    mask = eclipse_mask(angles, req.altitude_km, req.beta_deg)

    # --- V2: Ideal solar array tracking for each wing ---
    right_wing = compute_wing_arrays(sx, sy, sz, N0_RIGHT)
    left_wing = compute_wing_arrays(sx, sy, sz, N0_LEFT)

    # --- V2: Ideal power per wing ---
    right_power_ideal = compute_wing_power(
        right_wing["cosine_efficiency"], mask,
        req.solar_array_area_m2_per_wing, req.solar_cell_efficiency,
        req.degradation_factor,
    )
    left_power_ideal = compute_wing_power(
        left_wing["cosine_efficiency"], mask,
        req.solar_array_area_m2_per_wing, req.solar_cell_efficiency,
        req.degradation_factor,
    )
    total_power_ideal = left_power_ideal + right_power_ideal

    # --- V2: Ideal summary ---
    summary_ideal = compute_power_summary(
        left_power_ideal, right_power_ideal, req.required_bus_power_w,
        left_wing["incidence_deg"], right_wing["incidence_deg"],
    )

    # --- V3: Time step ---
    dt_s = T_s / req.num_samples_per_orbit

    # --- V3: Axis limits ---
    right_limits = AxisLimits(
        outer_min=req.right_outer_min_deg, outer_max=req.right_outer_max_deg,
        inner_min=req.right_inner_min_deg, inner_max=req.right_inner_max_deg,
    )
    left_limits = AxisLimits(
        outer_min=req.left_outer_min_deg, outer_max=req.left_outer_max_deg,
        inner_min=req.left_inner_min_deg, inner_max=req.left_inner_max_deg,
    )

    # --- V3: Constrained tracking ---
    right_ct = compute_constrained_tracking(
        right_wing["outer_angle_deg"], right_wing["inner_angle_deg"],
        sx, sy, sz, mask, N0_RIGHT, "right",
        right_limits, req.outer_rate_limit_deg_per_s,
        req.inner_rate_limit_deg_per_s, dt_s, req.keepout_zones,
    )
    left_ct = compute_constrained_tracking(
        left_wing["outer_angle_deg"], left_wing["inner_angle_deg"],
        sx, sy, sz, mask, N0_LEFT, "left",
        left_limits, req.outer_rate_limit_deg_per_s,
        req.inner_rate_limit_deg_per_s, dt_s, req.keepout_zones,
    )

    # --- V3: Achieved power ---
    right_power_achieved = compute_wing_power(
        right_ct["achieved_cos_eff"], mask,
        req.solar_array_area_m2_per_wing, req.solar_cell_efficiency,
        req.degradation_factor,
    )
    left_power_achieved = compute_wing_power(
        left_ct["achieved_cos_eff"], mask,
        req.solar_array_area_m2_per_wing, req.solar_cell_efficiency,
        req.degradation_factor,
    )
    total_power_achieved = left_power_achieved + right_power_achieved

    # --- V3: Summary metrics ---
    avg_ideal = float(np.mean(total_power_ideal))
    avg_achieved = float(np.mean(total_power_achieved))
    max_possible = (
        1361.0 * req.solar_array_area_m2_per_wing * 2.0
        * req.solar_cell_efficiency * req.degradation_factor
    )

    # Pointing-loss metrics are computed over *sunlit samples only* so that
    # eclipse unavailability does not inflate the reported loss percentage.
    # (Eclipse loss is already captured by eclipse_fraction in the response.)
    sunlit = ~mask
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
        # V1 scalars
        orbit_radius_km=round(r_km, 4),
        orbital_period_s=round(T_s, 4),
        orbital_period_min=round(T_min, 4),
        eclipse_duration_s=round(ed_s, 4),
        eclipse_duration_min=round(ed_min, 4),
        eclipse_fraction=round(ef, 6),
        sunlight_fraction=round(1.0 - ef, 6),
        critical_beta_deg_for_no_eclipse=round(beta_crit, 4),
        # V1 arrays
        orbit_angle_deg=angles.tolist(),
        sun_vvlh_x=sx.tolist(),
        sun_vvlh_y=sy.tolist(),
        sun_vvlh_z=sz.tolist(),
        sun_az_deg=az.tolist(),
        sun_el_deg=el.tolist(),
        in_eclipse=mask.tolist(),
        # V2: Right wing ideal (preserved)
        right_outer_angle_deg=right_wing["outer_angle_deg"].tolist(),
        right_inner_angle_deg=right_wing["inner_angle_deg"].tolist(),
        right_normal_x=right_wing["normal_x"].tolist(),
        right_normal_y=right_wing["normal_y"].tolist(),
        right_normal_z=right_wing["normal_z"].tolist(),
        right_incidence_deg=right_wing["incidence_deg"].tolist(),
        right_cosine_efficiency=right_wing["cosine_efficiency"].tolist(),
        right_power_w=right_power_ideal.tolist(),
        # V2: Left wing ideal (preserved)
        left_outer_angle_deg=left_wing["outer_angle_deg"].tolist(),
        left_inner_angle_deg=left_wing["inner_angle_deg"].tolist(),
        left_normal_x=left_wing["normal_x"].tolist(),
        left_normal_y=left_wing["normal_y"].tolist(),
        left_normal_z=left_wing["normal_z"].tolist(),
        left_incidence_deg=left_wing["incidence_deg"].tolist(),
        left_cosine_efficiency=left_wing["cosine_efficiency"].tolist(),
        left_power_w=left_power_ideal.tolist(),
        # V2: Total ideal power (preserved)
        total_power_w=total_power_ideal.tolist(),
        # V2: Ideal summary (preserved)
        average_total_power_w=round(summary_ideal["average_total_power_w"], 2),
        average_left_power_w=round(summary_ideal["average_left_power_w"], 2),
        average_right_power_w=round(summary_ideal["average_right_power_w"], 2),
        peak_total_power_w=round(summary_ideal["peak_total_power_w"], 2),
        min_total_power_w=round(summary_ideal["min_total_power_w"], 2),
        percent_of_required_bus_power_avg=round(
            summary_ideal["percent_of_required_bus_power_avg"], 2,
        ),
        max_left_incidence_deg=round(summary_ideal["max_left_incidence_deg"], 4),
        max_right_incidence_deg=round(summary_ideal["max_right_incidence_deg"], 4),
        min_left_incidence_deg=round(summary_ideal["min_left_incidence_deg"], 4),
        min_right_incidence_deg=round(summary_ideal["min_right_incidence_deg"], 4),
        # V3: Right wing ideal vs achieved
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
        # V3: Left wing ideal vs achieved
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
        # V3: Total power arrays
        ideal_total_power_w=total_power_ideal.tolist(),
        achieved_total_power_w=total_power_achieved.tolist(),
        # V3: Summary metrics
        average_ideal_total_power_w=round(avg_ideal, 2),
        average_achieved_total_power_w=round(avg_achieved, 2),
        percent_of_required_bus_power_ideal_avg=round(pct_ideal, 2),
        percent_of_required_bus_power_achieved_avg=round(pct_achieved, 2),
        ideal_tracking_loss_percent=round(ideal_loss, 4),
        constrained_tracking_loss_percent=round(constrained_loss, 4),
        achieved_vs_ideal_energy_ratio=round(energy_ratio, 6),
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
