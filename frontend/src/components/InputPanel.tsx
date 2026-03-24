import { useState } from "react";
import type { AnalysisRequest, KeepOutZone } from "../types/analysis";
import { DEFAULT_REQUEST } from "../types/analysis";

interface InputPanelProps {
  onAnalyze: (req: AnalysisRequest) => void;
  loading: boolean;
}

const EMPTY_ZONE: KeepOutZone = {
  wing: "right",
  outer_min_deg: -10,
  outer_max_deg: 10,
  inner_min_deg: -10,
  inner_max_deg: 10,
  label: "",
};

export default function InputPanel({ onAnalyze, loading }: InputPanelProps) {
  const [form, setForm] = useState<AnalysisRequest>({ ...DEFAULT_REQUEST });
  const [errors, setErrors] = useState<Record<string, string>>({});

  function validate(): boolean {
    const e: Record<string, string> = {};
    if (form.altitude_km <= 0) e.altitude_km = "Must be > 0";
    if (form.altitude_km > 40000) e.altitude_km = "Must be \u2264 40 000 km";
    if (form.beta_deg < -90 || form.beta_deg > 90)
      e.beta_deg = "Must be between -90\u00b0 and +90\u00b0";
    if (
      form.num_samples_per_orbit < 10 ||
      form.num_samples_per_orbit > 3600 ||
      !Number.isInteger(form.num_samples_per_orbit)
    )
      e.num_samples_per_orbit = "Integer between 10 and 3600";
    if (form.solar_array_area_m2_per_wing <= 0)
      e.solar_array_area_m2_per_wing = "Must be > 0";
    if (form.solar_cell_efficiency <= 0 || form.solar_cell_efficiency > 1)
      e.solar_cell_efficiency = "Must be between 0 and 1";
    if (form.degradation_factor <= 0 || form.degradation_factor > 1)
      e.degradation_factor = "Must be between 0 and 1";
    if (form.required_bus_power_w <= 0)
      e.required_bus_power_w = "Must be > 0";
    if (form.outer_rate_limit_deg_per_s < 0.05)
      e.outer_rate_limit = "Must be ≥ 0.05";
    if (form.inner_rate_limit_deg_per_s < 0.05)
      e.inner_rate_limit = "Must be ≥ 0.05";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (validate()) onAnalyze(form);
  }

  function handleReset() {
    setForm({ ...DEFAULT_REQUEST });
    setErrors({});
  }

  function update(field: keyof AnalysisRequest, raw: string) {
    const val =
      field === "num_samples_per_orbit" ? parseInt(raw) : parseFloat(raw);
    setForm((prev) => ({ ...prev, [field]: isNaN(val) ? 0 : val }));
  }

  function addKeepOutZone() {
    setForm((prev) => ({
      ...prev,
      keepout_zones: [...prev.keepout_zones, { ...EMPTY_ZONE }],
    }));
  }

  function removeKeepOutZone(idx: number) {
    setForm((prev) => ({
      ...prev,
      keepout_zones: prev.keepout_zones.filter((_, i) => i !== idx),
    }));
  }

  function updateZone(idx: number, field: keyof KeepOutZone, raw: string) {
    setForm((prev) => {
      const zones = [...prev.keepout_zones];
      if (field === "wing") {
        zones[idx] = { ...zones[idx], wing: raw as "left" | "right" };
      } else if (field === "label") {
        zones[idx] = { ...zones[idx], label: raw };
      } else {
        const val = parseFloat(raw);
        zones[idx] = { ...zones[idx], [field]: isNaN(val) ? 0 : val };
      }
      return { ...prev, keepout_zones: zones };
    });
  }

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <h2 style={styles.heading}>Orbit Parameters</h2>

      <label style={styles.label}>
        Altitude [km]
        <input type="number" step="any" value={form.altitude_km}
          onChange={(e) => update("altitude_km", e.target.value)} style={styles.input} />
        {errors.altitude_km && <span style={styles.err}>{errors.altitude_km}</span>}
      </label>

      <label style={styles.label}>
        Beta Angle [deg]
        <input type="number" step="any" min={-90} max={90} value={form.beta_deg}
          onChange={(e) => update("beta_deg", e.target.value)} style={styles.input} />
        {errors.beta_deg && <span style={styles.err}>{errors.beta_deg}</span>}
      </label>

      <label style={styles.label}>
        Samples / Orbit
        <input type="number" step="1" min={10} max={3600} value={form.num_samples_per_orbit}
          onChange={(e) => update("num_samples_per_orbit", e.target.value)} style={styles.input} />
        {errors.num_samples_per_orbit && <span style={styles.err}>{errors.num_samples_per_orbit}</span>}
      </label>

      <hr style={styles.divider} />
      <h2 style={styles.heading}>Solar Array</h2>

      <label style={styles.label}>
        Array Area / Wing [m²]
        <input type="number" step="any" value={form.solar_array_area_m2_per_wing}
          onChange={(e) => update("solar_array_area_m2_per_wing", e.target.value)} style={styles.input} />
        {errors.solar_array_area_m2_per_wing && <span style={styles.err}>{errors.solar_array_area_m2_per_wing}</span>}
      </label>

      <label style={styles.label}>
        Cell Efficiency
        <input type="number" step="0.01" min={0} max={1} value={form.solar_cell_efficiency}
          onChange={(e) => update("solar_cell_efficiency", e.target.value)} style={styles.input} />
        {errors.solar_cell_efficiency && <span style={styles.err}>{errors.solar_cell_efficiency}</span>}
      </label>

      <label style={styles.label}>
        Degradation Factor
        <input type="number" step="0.01" min={0} max={1} value={form.degradation_factor}
          onChange={(e) => update("degradation_factor", e.target.value)} style={styles.input} />
        {errors.degradation_factor && <span style={styles.err}>{errors.degradation_factor}</span>}
      </label>

      <label style={styles.label}>
        Required Bus Power [W]
        <input type="number" step="any" value={form.required_bus_power_w}
          onChange={(e) => update("required_bus_power_w", e.target.value)} style={styles.input} />
        {errors.required_bus_power_w && <span style={styles.err}>{errors.required_bus_power_w}</span>}
      </label>

      <hr style={styles.divider} />
      <h2 style={styles.heading}>Angle Limits [deg]</h2>

      <div style={styles.twoCol}>
        <div>
          <div style={styles.subheading}>Right Wing</div>
          <label style={styles.label}>Outer Min
            <input type="number" step="any" value={form.right_outer_min_deg}
              onChange={(e) => update("right_outer_min_deg", e.target.value)} style={styles.input} />
          </label>
          <label style={styles.label}>Outer Max
            <input type="number" step="any" value={form.right_outer_max_deg}
              onChange={(e) => update("right_outer_max_deg", e.target.value)} style={styles.input} />
          </label>
          <label style={styles.label}>Inner Min
            <input type="number" step="any" value={form.right_inner_min_deg}
              onChange={(e) => update("right_inner_min_deg", e.target.value)} style={styles.input} />
          </label>
          <label style={styles.label}>Inner Max
            <input type="number" step="any" value={form.right_inner_max_deg}
              onChange={(e) => update("right_inner_max_deg", e.target.value)} style={styles.input} />
          </label>
        </div>
        <div>
          <div style={styles.subheading}>Left Wing</div>
          <label style={styles.label}>Outer Min
            <input type="number" step="any" value={form.left_outer_min_deg}
              onChange={(e) => update("left_outer_min_deg", e.target.value)} style={styles.input} />
          </label>
          <label style={styles.label}>Outer Max
            <input type="number" step="any" value={form.left_outer_max_deg}
              onChange={(e) => update("left_outer_max_deg", e.target.value)} style={styles.input} />
          </label>
          <label style={styles.label}>Inner Min
            <input type="number" step="any" value={form.left_inner_min_deg}
              onChange={(e) => update("left_inner_min_deg", e.target.value)} style={styles.input} />
          </label>
          <label style={styles.label}>Inner Max
            <input type="number" step="any" value={form.left_inner_max_deg}
              onChange={(e) => update("left_inner_max_deg", e.target.value)} style={styles.input} />
          </label>
        </div>
      </div>

      <hr style={styles.divider} />
      <h2 style={styles.heading}>Rate Limits [deg/s]</h2>

      <label style={styles.label}>
        Outer Axis Rate Limit
        <input type="number" step="0.01" min={0.05} value={form.outer_rate_limit_deg_per_s}
          onChange={(e) => update("outer_rate_limit_deg_per_s", e.target.value)} style={styles.input} />
        {errors.outer_rate_limit && <span style={styles.err}>{errors.outer_rate_limit}</span>}
      </label>

      <label style={styles.label}>
        Inner Axis Rate Limit
        <input type="number" step="0.01" min={0.05} value={form.inner_rate_limit_deg_per_s}
          onChange={(e) => update("inner_rate_limit_deg_per_s", e.target.value)} style={styles.input} />
        {errors.inner_rate_limit && <span style={styles.err}>{errors.inner_rate_limit}</span>}
      </label>

      <hr style={styles.divider} />
      <h2 style={styles.heading}>Keep-Out Zones</h2>

      {form.keepout_zones.length === 0 && (
        <div style={styles.placeholder}>No keep-out zones defined.</div>
      )}

      {form.keepout_zones.map((zone, idx) => (
        <div key={idx} style={styles.zoneCard}>
          <div style={styles.zoneHeader}>
            <span style={styles.zoneTitle}>Zone {idx + 1}</span>
            <button type="button" onClick={() => removeKeepOutZone(idx)} style={styles.removeBtn}>
              Remove
            </button>
          </div>
          <label style={styles.label}>Wing
            <select value={zone.wing} onChange={(e) => updateZone(idx, "wing", e.target.value)} style={styles.input}>
              <option value="right">Right</option>
              <option value="left">Left</option>
            </select>
          </label>
          <label style={styles.label}>Label
            <input type="text" value={zone.label} onChange={(e) => updateZone(idx, "label", e.target.value)} style={styles.input} />
          </label>
          <div style={styles.twoCol}>
            <label style={styles.label}>Outer Min
              <input type="number" step="any" value={zone.outer_min_deg}
                onChange={(e) => updateZone(idx, "outer_min_deg", e.target.value)} style={styles.input} />
            </label>
            <label style={styles.label}>Outer Max
              <input type="number" step="any" value={zone.outer_max_deg}
                onChange={(e) => updateZone(idx, "outer_max_deg", e.target.value)} style={styles.input} />
            </label>
          </div>
          <div style={styles.twoCol}>
            <label style={styles.label}>Inner Min
              <input type="number" step="any" value={zone.inner_min_deg}
                onChange={(e) => updateZone(idx, "inner_min_deg", e.target.value)} style={styles.input} />
            </label>
            <label style={styles.label}>Inner Max
              <input type="number" step="any" value={zone.inner_max_deg}
                onChange={(e) => updateZone(idx, "inner_max_deg", e.target.value)} style={styles.input} />
            </label>
          </div>
        </div>
      ))}

      <button type="button" onClick={addKeepOutZone} style={styles.addBtn}>
        + Add Keep-Out Zone
      </button>

      <div style={styles.buttons}>
        <button type="submit" disabled={loading} style={styles.primary}>
          {loading ? "Analyzing\u2026" : "Analyze"}
        </button>
        <button type="button" onClick={handleReset} style={styles.secondary}>
          Reset Defaults
        </button>
      </div>
    </form>
  );
}

const styles: Record<string, React.CSSProperties> = {
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "0.75rem",
    padding: "1.5rem",
    background: "#f8f9fa",
    borderRadius: "8px",
    border: "1px solid #dee2e6",
    minWidth: "260px",
    maxHeight: "90vh",
    overflowY: "auto",
  },
  heading: {
    margin: 0,
    fontSize: "1.1rem",
    fontWeight: 600,
    color: "#212529",
  },
  subheading: {
    fontSize: "0.85rem",
    fontWeight: 600,
    color: "#495057",
    marginBottom: "0.25rem",
  },
  divider: {
    border: "none",
    borderTop: "1px solid #dee2e6",
    margin: "0.25rem 0",
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: "0.25rem",
    fontSize: "0.8rem",
    fontWeight: 500,
    color: "#495057",
    minWidth: 0,
  },
  input: {
    padding: "0.4rem",
    border: "1px solid #ced4da",
    borderRadius: "4px",
    fontSize: "0.85rem",
    width: "100%",
    boxSizing: "border-box" as const,
  },
  err: {
    color: "#dc3545",
    fontSize: "0.75rem",
  },
  twoCol: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "0.5rem",
    minWidth: 0,
  },
  placeholder: {
    fontSize: "0.8rem",
    color: "#6c757d",
    fontStyle: "italic",
  },
  zoneCard: {
    display: "flex",
    flexDirection: "column",
    gap: "0.4rem",
    padding: "0.75rem",
    background: "#fff",
    border: "1px solid #dee2e6",
    borderRadius: "6px",
  },
  zoneHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  zoneTitle: {
    fontWeight: 600,
    fontSize: "0.85rem",
    color: "#212529",
  },
  removeBtn: {
    padding: "0.2rem 0.5rem",
    background: "#dc3545",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    fontSize: "0.75rem",
    cursor: "pointer",
  },
  addBtn: {
    padding: "0.5rem",
    background: "#198754",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: "0.85rem",
  },
  buttons: {
    display: "flex",
    gap: "0.5rem",
    marginTop: "0.5rem",
  },
  primary: {
    flex: 1,
    padding: "0.6rem",
    background: "#0d6efd",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: "0.9rem",
  },
  secondary: {
    flex: 1,
    padding: "0.6rem",
    background: "#6c757d",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: "0.9rem",
  },
};
