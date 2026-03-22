"""Analysis router — POST /api/analyze/v1."""

import numpy as np
from fastapi import APIRouter

from app.models import AnalysisRequest, AnalysisResponse
from app.services.eclipse import (
    critical_beta_deg,
    eclipse_duration_s,
    eclipse_fraction,
)
from app.services.orbit import orbit_radius_km, orbital_period_s
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
