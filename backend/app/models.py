"""Pydantic request / response models for the analysis endpoints (V1 and V2)."""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Version 1 models (preserved for backward compatibility)
# ---------------------------------------------------------------------------


class AnalysisRequest(BaseModel):
    """Input parameters for a single-orbit solar environment analysis (V1)."""

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
    """Full output of the solar environment analysis for one orbit (V1)."""

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


# ---------------------------------------------------------------------------
# Version 2 models — orbit + dual-wing solar array + power
# ---------------------------------------------------------------------------


class AnalysisRequestV2(BaseModel):
    """Input parameters for Version 2 analysis (orbit + solar array + power)."""

    # Orbit parameters (same as V1)
    altitude_km: float = Field(
        default=500.0,
        gt=0,
        description="Orbital altitude above Earth's surface [km]",
    )
    beta_deg: float = Field(
        default=0.0,
        ge=-90.0,
        le=90.0,
        description="Beta angle [deg]",
    )
    num_samples_per_orbit: int = Field(
        default=360,
        ge=10,
        le=3600,
        description="Number of evenly-spaced sample points over one orbit",
    )

    # Solar array parameters (V2)
    solar_array_area_m2_per_wing: float = Field(
        default=5.0,
        gt=0,
        description="Solar array area per wing [m²]",
    )
    solar_cell_efficiency: float = Field(
        default=0.30,
        gt=0,
        le=1.0,
        description="Solar cell BOL efficiency [0–1]",
    )
    degradation_factor: float = Field(
        default=0.85,
        gt=0,
        le=1.0,
        description="End-of-life degradation factor [0–1]",
    )
    required_bus_power_w: float = Field(
        default=3000.0,
        gt=0,
        description="Required spacecraft bus power [W]",
    )


class AnalysisResponseV2(BaseModel):
    """Full output of the Version 2 analysis (orbit + solar array + power)."""

    # --- V1 scalar fields (unchanged) ---
    orbit_radius_km: float
    orbital_period_s: float
    orbital_period_min: float
    eclipse_duration_s: float
    eclipse_duration_min: float
    eclipse_fraction: float
    sunlight_fraction: float
    critical_beta_deg_for_no_eclipse: float

    # --- V1 sampled arrays (unchanged) ---
    orbit_angle_deg: list[float]
    sun_vvlh_x: list[float]
    sun_vvlh_y: list[float]
    sun_vvlh_z: list[float]
    sun_az_deg: list[float]
    sun_el_deg: list[float]
    in_eclipse: list[bool]

    # --- V2: Right wing sampled arrays ---
    right_outer_angle_deg: list[float]
    right_inner_angle_deg: list[float]
    right_normal_x: list[float]
    right_normal_y: list[float]
    right_normal_z: list[float]
    right_incidence_deg: list[float]
    right_cosine_efficiency: list[float]
    right_power_w: list[float]

    # --- V2: Left wing sampled arrays ---
    left_outer_angle_deg: list[float]
    left_inner_angle_deg: list[float]
    left_normal_x: list[float]
    left_normal_y: list[float]
    left_normal_z: list[float]
    left_incidence_deg: list[float]
    left_cosine_efficiency: list[float]
    left_power_w: list[float]

    # --- V2: Total power array ---
    total_power_w: list[float]

    # --- V2: Summary scalars ---
    average_total_power_w: float
    average_left_power_w: float
    average_right_power_w: float
    peak_total_power_w: float
    min_total_power_w: float
    percent_of_required_bus_power_avg: float
    max_left_incidence_deg: float
    max_right_incidence_deg: float
    min_left_incidence_deg: float
    min_right_incidence_deg: float
