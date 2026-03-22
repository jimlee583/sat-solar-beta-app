export interface AnalysisRequest {
  altitude_km: number;
  beta_deg: number;
  num_samples_per_orbit: number;
  solar_array_area_m2_per_wing: number;
  solar_cell_efficiency: number;
  degradation_factor: number;
  required_bus_power_w: number;
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

  // V2: Right wing arrays
  right_outer_angle_deg: number[];
  right_inner_angle_deg: number[];
  right_normal_x: number[];
  right_normal_y: number[];
  right_normal_z: number[];
  right_incidence_deg: number[];
  right_cosine_efficiency: number[];
  right_power_w: number[];

  // V2: Left wing arrays
  left_outer_angle_deg: number[];
  left_inner_angle_deg: number[];
  left_normal_x: number[];
  left_normal_y: number[];
  left_normal_z: number[];
  left_incidence_deg: number[];
  left_cosine_efficiency: number[];
  left_power_w: number[];

  // V2: Total power
  total_power_w: number[];

  // V2: Summary
  average_total_power_w: number;
  average_left_power_w: number;
  average_right_power_w: number;
  peak_total_power_w: number;
  min_total_power_w: number;
  percent_of_required_bus_power_avg: number;
  max_left_incidence_deg: number;
  max_right_incidence_deg: number;
  min_left_incidence_deg: number;
  min_right_incidence_deg: number;
}

export const DEFAULT_REQUEST: AnalysisRequest = {
  altitude_km: 500,
  beta_deg: 0,
  num_samples_per_orbit: 360,
  solar_array_area_m2_per_wing: 5.0,
  solar_cell_efficiency: 0.30,
  degradation_factor: 0.85,
  required_bus_power_w: 3000,
};
