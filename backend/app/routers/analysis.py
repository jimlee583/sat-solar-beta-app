"""Analysis router — POST /api/analyze/v1 and POST /api/analyze/v2."""

import numpy as np
from fastapi import APIRouter

from app.models import (
    AnalysisRequest,
    AnalysisRequestV2,
    AnalysisResponse,
    AnalysisResponseV2,
)
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
