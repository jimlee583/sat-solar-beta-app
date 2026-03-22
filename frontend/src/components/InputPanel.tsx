import { useState } from "react";
import type { AnalysisRequest } from "../types/analysis";
import { DEFAULT_REQUEST } from "../types/analysis";

interface InputPanelProps {
  onAnalyze: (req: AnalysisRequest) => void;
  loading: boolean;
}

export default function InputPanel({ onAnalyze, loading }: InputPanelProps) {
  const [form, setForm] = useState<AnalysisRequest>({ ...DEFAULT_REQUEST });
  const [errors, setErrors] = useState<Record<string, string>>({});

  function validate(): boolean {
    const e: Record<string, string> = {};
    if (form.altitude_km <= 0) e.altitude_km = "Must be > 0";
    if (form.altitude_km > 40000) e.altitude_km = "Must be ≤ 40 000 km";
    if (form.beta_deg < -90 || form.beta_deg > 90)
      e.beta_deg = "Must be between -90° and +90°";
    if (
      form.num_samples_per_orbit < 10 ||
      form.num_samples_per_orbit > 3600 ||
      !Number.isInteger(form.num_samples_per_orbit)
    )
      e.num_samples_per_orbit = "Integer between 10 and 3600";
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
    const val = field === "num_samples_per_orbit" ? parseInt(raw) : parseFloat(raw);
    setForm((prev) => ({ ...prev, [field]: isNaN(val) ? 0 : val }));
  }

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <h2 style={styles.heading}>Orbit Parameters</h2>

      <label style={styles.label}>
        Altitude [km]
        <input
          type="number"
          step="any"
          value={form.altitude_km}
          onChange={(e) => update("altitude_km", e.target.value)}
          style={styles.input}
        />
        {errors.altitude_km && <span style={styles.err}>{errors.altitude_km}</span>}
      </label>

      <label style={styles.label}>
        Beta Angle [deg]
        <input
          type="number"
          step="any"
          min={-90}
          max={90}
          value={form.beta_deg}
          onChange={(e) => update("beta_deg", e.target.value)}
          style={styles.input}
        />
        {errors.beta_deg && <span style={styles.err}>{errors.beta_deg}</span>}
      </label>

      <label style={styles.label}>
        Samples / Orbit
        <input
          type="number"
          step="1"
          min={10}
          max={3600}
          value={form.num_samples_per_orbit}
          onChange={(e) => update("num_samples_per_orbit", e.target.value)}
          style={styles.input}
        />
        {errors.num_samples_per_orbit && (
          <span style={styles.err}>{errors.num_samples_per_orbit}</span>
        )}
      </label>

      <div style={styles.buttons}>
        <button type="submit" disabled={loading} style={styles.primary}>
          {loading ? "Analyzing…" : "Analyze"}
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
    gap: "1rem",
    padding: "1.5rem",
    background: "#f8f9fa",
    borderRadius: "8px",
    border: "1px solid #dee2e6",
    minWidth: "260px",
  },
  heading: {
    margin: 0,
    fontSize: "1.1rem",
    fontWeight: 600,
    color: "#212529",
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: "0.25rem",
    fontSize: "0.875rem",
    fontWeight: 500,
    color: "#495057",
  },
  input: {
    padding: "0.5rem",
    border: "1px solid #ced4da",
    borderRadius: "4px",
    fontSize: "0.95rem",
  },
  err: {
    color: "#dc3545",
    fontSize: "0.75rem",
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
