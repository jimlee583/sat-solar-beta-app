"""Pydantic request / response models for the analysis endpoints (V1, V2, V3)."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


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

    # Wing mounting axis: "y" = ±Y cross-track (default), "x" = ±X velocity
    wing_mounting: Literal["y", "x"] = Field(default="y")


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


# ---------------------------------------------------------------------------
# Version 3 models — constrained articulation
# ---------------------------------------------------------------------------


class KeepOutZone(BaseModel):
    """Rectangular forbidden region in (outer_deg, inner_deg) angle space."""

    wing: Literal["left", "right"] = Field(
        description="Which wing this keep-out zone applies to",
    )
    outer_min_deg: float = Field(description="Minimum outer angle of forbidden region [deg]")
    outer_max_deg: float = Field(description="Maximum outer angle of forbidden region [deg]")
    inner_min_deg: float = Field(description="Minimum inner angle of forbidden region [deg]")
    inner_max_deg: float = Field(description="Maximum inner angle of forbidden region [deg]")
    label: str = Field(default="", description="Optional label for this zone")

    @model_validator(mode="after")
    def check_zone_bounds(self) -> "KeepOutZone":
        if self.outer_min_deg >= self.outer_max_deg:
            raise ValueError(
                f"outer_min_deg ({self.outer_min_deg}) must be less than "
                f"outer_max_deg ({self.outer_max_deg})"
            )
        if self.inner_min_deg >= self.inner_max_deg:
            raise ValueError(
                f"inner_min_deg ({self.inner_min_deg}) must be less than "
                f"inner_max_deg ({self.inner_max_deg})"
            )
        return self


class AnalysisRequestV3(BaseModel):
    """Input parameters for Version 3 analysis (constrained articulation)."""

    # Orbit parameters (same as V1/V2)
    altitude_km: float = Field(default=500.0, gt=0)
    beta_deg: float = Field(default=0.0, ge=-90.0, le=90.0)
    num_samples_per_orbit: int = Field(default=360, ge=10, le=3600)

    # Solar array parameters (same as V2)
    solar_array_area_m2_per_wing: float = Field(default=5.0, gt=0)
    solar_cell_efficiency: float = Field(default=0.30, gt=0, le=1.0)
    degradation_factor: float = Field(default=0.85, gt=0, le=1.0)
    required_bus_power_w: float = Field(default=3000.0, gt=0)

    # Wing mounting axis: "y" = ±Y cross-track (default), "x" = ±X velocity
    wing_mounting: Literal["y", "x"] = Field(default="y")

    # V3: Per-axis angle limits [deg]
    right_outer_min_deg: float = Field(default=-180.0)
    right_outer_max_deg: float = Field(default=180.0)
    right_inner_min_deg: float = Field(default=-60.0)
    right_inner_max_deg: float = Field(default=60.0)
    left_outer_min_deg: float = Field(default=-180.0)
    left_outer_max_deg: float = Field(default=180.0)
    left_inner_min_deg: float = Field(default=-60.0)
    left_inner_max_deg: float = Field(default=60.0)

    # V3: Rate limits [deg/s]
    outer_rate_limit_deg_per_s: float = Field(default=1.0, ge=0.05)
    inner_rate_limit_deg_per_s: float = Field(default=1.0, ge=0.05)

    # V3: Keep-out zones
    keepout_zones: list[KeepOutZone] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_angle_limit_bounds(self) -> "AnalysisRequestV3":
        pairs = [
            ("right_outer_min_deg", "right_outer_max_deg",
             self.right_outer_min_deg, self.right_outer_max_deg),
            ("right_inner_min_deg", "right_inner_max_deg",
             self.right_inner_min_deg, self.right_inner_max_deg),
            ("left_outer_min_deg", "left_outer_max_deg",
             self.left_outer_min_deg, self.left_outer_max_deg),
            ("left_inner_min_deg", "left_inner_max_deg",
             self.left_inner_min_deg, self.left_inner_max_deg),
        ]
        for min_name, max_name, min_val, max_val in pairs:
            if min_val >= max_val:
                raise ValueError(
                    f"{min_name} ({min_val}) must be less than {max_name} ({max_val})"
                )
        return self


class AnalysisResponseV3(BaseModel):
    """Full output of the Version 3 analysis (constrained articulation)."""

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

    # --- V3: Right wing ideal vs achieved ---
    right_ideal_outer_angle_deg: list[float]
    right_ideal_inner_angle_deg: list[float]
    right_achieved_outer_angle_deg: list[float]
    right_achieved_inner_angle_deg: list[float]
    right_ideal_incidence_deg: list[float]
    right_achieved_incidence_deg: list[float]
    right_ideal_power_w: list[float]
    right_achieved_power_w: list[float]
    right_outer_angle_limited: list[bool]
    right_inner_angle_limited: list[bool]
    right_outer_rate_limited: list[bool]
    right_inner_rate_limited: list[bool]
    right_in_keepout: list[bool]
    right_keepout_label: list[str]

    # --- V3: Left wing ideal vs achieved ---
    left_ideal_outer_angle_deg: list[float]
    left_ideal_inner_angle_deg: list[float]
    left_achieved_outer_angle_deg: list[float]
    left_achieved_inner_angle_deg: list[float]
    left_ideal_incidence_deg: list[float]
    left_achieved_incidence_deg: list[float]
    left_ideal_power_w: list[float]
    left_achieved_power_w: list[float]
    left_outer_angle_limited: list[bool]
    left_inner_angle_limited: list[bool]
    left_outer_rate_limited: list[bool]
    left_inner_rate_limited: list[bool]
    left_in_keepout: list[bool]
    left_keepout_label: list[str]

    # --- V3: Total power arrays ---
    ideal_total_power_w: list[float]
    achieved_total_power_w: list[float]

    # --- V3: Summary metrics ---
    average_ideal_total_power_w: float
    average_achieved_total_power_w: float
    average_ideal_left_power_w: float
    average_ideal_right_power_w: float
    peak_ideal_total_power_w: float
    min_ideal_total_power_w: float
    percent_of_required_bus_power_ideal_avg: float
    percent_of_required_bus_power_achieved_avg: float
    ideal_tracking_loss_percent: float
    constrained_tracking_loss_percent: float
    achieved_vs_ideal_energy_ratio: float
    max_left_incidence_deg: float
    max_right_incidence_deg: float
    min_left_incidence_deg: float
    min_right_incidence_deg: float

    right_fraction_outer_angle_limited: float
    right_fraction_inner_angle_limited: float
    left_fraction_outer_angle_limited: float
    left_fraction_inner_angle_limited: float
    right_fraction_outer_rate_limited: float
    right_fraction_inner_rate_limited: float
    left_fraction_outer_rate_limited: float
    left_fraction_inner_rate_limited: float
    right_fraction_in_keepout: float
    left_fraction_in_keepout: float
