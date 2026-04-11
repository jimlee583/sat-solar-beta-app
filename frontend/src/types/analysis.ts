export interface KeepOutZone {
  wing: "left" | "right";
  outer_min_deg: number;
  outer_max_deg: number;
  inner_min_deg: number;
  inner_max_deg: number;
  label: string;
}

export interface AnalysisRequest {
  altitude_km: number;
  beta_deg: number;
  num_samples_per_orbit: number;
  solar_array_area_m2_per_wing: number;
  solar_cell_efficiency: number;
  degradation_factor: number;
  required_bus_power_w: number;

  // V3: Angle limits
  right_outer_min_deg: number;
  right_outer_max_deg: number;
  right_inner_min_deg: number;
  right_inner_max_deg: number;
  left_outer_min_deg: number;
  left_outer_max_deg: number;
  left_inner_min_deg: number;
  left_inner_max_deg: number;

  // Wing mounting axis: "y" = ±Y cross-track (default), "x" = ±X velocity
  wing_mounting: "y" | "x";

  // V3: Rate limits
  outer_rate_limit_deg_per_s: number;
  inner_rate_limit_deg_per_s: number;

  // V3: Keep-out zones
  keepout_zones: KeepOutZone[];
}

export interface AnalysisResponse {
  // V1 scalars
  orbit_radius_km: number;
  orbital_period_s: number;
  orbital_period_min: number;
  eclipse_duration_s: number;
  eclipse_duration_min: number;
  eclipse_fraction: number;
  sunlight_fraction: number;
  critical_beta_deg_for_no_eclipse: number;

  // V1 arrays
  orbit_angle_deg: number[];
  sun_vvlh_x: number[];
  sun_vvlh_y: number[];
  sun_vvlh_z: number[];
  sun_az_deg: number[];
  sun_el_deg: number[];
  in_eclipse: boolean[];

  // V3: Right wing ideal vs achieved
  right_ideal_outer_angle_deg: number[];
  right_ideal_inner_angle_deg: number[];
  right_achieved_outer_angle_deg: number[];
  right_achieved_inner_angle_deg: number[];
  right_ideal_incidence_deg: number[];
  right_achieved_incidence_deg: number[];
  right_ideal_power_w: number[];
  right_achieved_power_w: number[];
  right_outer_angle_limited: boolean[];
  right_inner_angle_limited: boolean[];
  right_outer_rate_limited: boolean[];
  right_inner_rate_limited: boolean[];
  right_in_keepout: boolean[];
  right_keepout_label: string[];

  // V3: Left wing ideal vs achieved
  left_ideal_outer_angle_deg: number[];
  left_ideal_inner_angle_deg: number[];
  left_achieved_outer_angle_deg: number[];
  left_achieved_inner_angle_deg: number[];
  left_ideal_incidence_deg: number[];
  left_achieved_incidence_deg: number[];
  left_ideal_power_w: number[];
  left_achieved_power_w: number[];
  left_outer_angle_limited: boolean[];
  left_inner_angle_limited: boolean[];
  left_outer_rate_limited: boolean[];
  left_inner_rate_limited: boolean[];
  left_in_keepout: boolean[];
  left_keepout_label: string[];

  // V3: Total power arrays
  ideal_total_power_w: number[];
  achieved_total_power_w: number[];

  // V3: Summary metrics
  average_ideal_total_power_w: number;
  average_achieved_total_power_w: number;
  average_ideal_left_power_w: number;
  average_ideal_right_power_w: number;
  peak_ideal_total_power_w: number;
  min_ideal_total_power_w: number;
  percent_of_required_bus_power_ideal_avg: number;
  percent_of_required_bus_power_achieved_avg: number;
  ideal_tracking_loss_percent: number;
  constrained_tracking_loss_percent: number;
  achieved_vs_ideal_energy_ratio: number;
  max_left_incidence_deg: number;
  max_right_incidence_deg: number;
  min_left_incidence_deg: number;
  min_right_incidence_deg: number;

  right_fraction_outer_angle_limited: number;
  right_fraction_inner_angle_limited: number;
  left_fraction_outer_angle_limited: number;
  left_fraction_inner_angle_limited: number;
  right_fraction_outer_rate_limited: number;
  right_fraction_inner_rate_limited: number;
  left_fraction_outer_rate_limited: number;
  left_fraction_inner_rate_limited: number;
  right_fraction_in_keepout: number;
  left_fraction_in_keepout: number;
}

export const DEFAULT_REQUEST: AnalysisRequest = {
  altitude_km: 500,
  beta_deg: 0,
  num_samples_per_orbit: 360,
  solar_array_area_m2_per_wing: 5.0,
  solar_cell_efficiency: 0.30,
  degradation_factor: 0.85,
  required_bus_power_w: 3000,

  right_outer_min_deg: -180,
  right_outer_max_deg: 180,
  right_inner_min_deg: -60,
  right_inner_max_deg: 60,
  left_outer_min_deg: -180,
  left_outer_max_deg: 180,
  left_inner_min_deg: -60,
  left_inner_max_deg: 60,

  wing_mounting: "y",

  outer_rate_limit_deg_per_s: 1.0,
  inner_rate_limit_deg_per_s: 1.0,

  keepout_zones: [],
};
