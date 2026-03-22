"""Pydantic request / response models for the analysis endpoint."""

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    """Input parameters for a single-orbit solar environment analysis."""

    altitude_km: float = Field(
        default=500.0,
        gt=0,
        description="Orbital altitude above Earth's surface [km]",
    )
    beta_deg: float = Field(
        default=0.0,
        ge=-90.0,
        le=90.0,
        description="Beta angle — angle between the orbit plane and the Sun vector [deg]",
    )
    num_samples_per_orbit: int = Field(
        default=360,
        ge=10,
        le=3600,
        description="Number of evenly-spaced sample points over one orbit",
    )


class AnalysisResponse(BaseModel):
    """Full output of the solar environment analysis for one orbit."""

    # Scalar orbit parameters
    orbit_radius_km: float
    orbital_period_s: float
    orbital_period_min: float

    # Eclipse scalars
    eclipse_duration_s: float
    eclipse_duration_min: float
    eclipse_fraction: float
    sunlight_fraction: float
    critical_beta_deg_for_no_eclipse: float

    # Sampled arrays (one element per orbit-angle sample)
    orbit_angle_deg: list[float]
    sun_vvlh_x: list[float]
    sun_vvlh_y: list[float]
    sun_vvlh_z: list[float]
    sun_az_deg: list[float]
    sun_el_deg: list[float]
    in_eclipse: list[bool]
