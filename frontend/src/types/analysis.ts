export interface AnalysisRequest {
  altitude_km: number;
  beta_deg: number;
  num_samples_per_orbit: number;
}

export interface AnalysisResponse {
  orbit_radius_km: number;
  orbital_period_s: number;
  orbital_period_min: number;
  eclipse_duration_s: number;
  eclipse_duration_min: number;
  eclipse_fraction: number;
  sunlight_fraction: number;
  critical_beta_deg_for_no_eclipse: number;
  orbit_angle_deg: number[];
  sun_vvlh_x: number[];
  sun_vvlh_y: number[];
  sun_vvlh_z: number[];
  sun_az_deg: number[];
  sun_el_deg: number[];
  in_eclipse: boolean[];
}

export const DEFAULT_REQUEST: AnalysisRequest = {
  altitude_km: 500,
  beta_deg: 0,
  num_samples_per_orbit: 360,
};
