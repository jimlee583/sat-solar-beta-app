import type { AnalysisResponse } from "../types/analysis";

interface SummaryCardsProps {
  data: AnalysisResponse;
}

interface Metric {
  label: string;
  value: string;
  unit: string;
  color?: string;
}

export default function SummaryCards({ data }: SummaryCardsProps) {
  const orbitMetrics: Metric[] = [
    { label: "Orbit Radius", value: data.orbit_radius_km.toFixed(1), unit: "km" },
    { label: "Orbital Period", value: data.orbital_period_min.toFixed(2), unit: "min" },
    { label: "Critical \u03b2*", value: data.critical_beta_deg_for_no_eclipse.toFixed(2), unit: "deg" },
    { label: "Eclipse Duration", value: data.eclipse_duration_min.toFixed(2), unit: "min" },
    { label: "Eclipse Fraction", value: (data.eclipse_fraction * 100).toFixed(2), unit: "%" },
    { label: "Sunlight Fraction", value: (data.sunlight_fraction * 100).toFixed(2), unit: "%" },
  ];

  const idealPowerMetrics: Metric[] = [
    {
      label: "Avg Ideal Power",
      value: data.average_ideal_total_power_w.toFixed(1),
      unit: "W",
      color: "#0d6efd",
    },
    {
      label: "% Bus (Ideal)",
      value: data.percent_of_required_bus_power_ideal_avg.toFixed(1),
      unit: "%",
      color: data.percent_of_required_bus_power_ideal_avg >= 100 ? "#198754" : "#dc3545",
    },
    {
      label: "Ideal Loss",
      value: data.ideal_tracking_loss_percent.toFixed(2),
      unit: "%",
    },
  ];

  const achievedPowerMetrics: Metric[] = [
    {
      label: "Avg Achieved Power",
      value: data.average_achieved_total_power_w.toFixed(1),
      unit: "W",
      color: "#6610f2",
    },
    {
      label: "% Bus (Achieved)",
      value: data.percent_of_required_bus_power_achieved_avg.toFixed(1),
      unit: "%",
      color: data.percent_of_required_bus_power_achieved_avg >= 100 ? "#198754" : "#dc3545",
    },
    {
      label: "Constrained Loss",
      value: data.constrained_tracking_loss_percent.toFixed(2),
      unit: "%",
    },
    {
      label: "Achieved / Ideal",
      value: (data.achieved_vs_ideal_energy_ratio * 100).toFixed(2),
      unit: "%",
      color: data.achieved_vs_ideal_energy_ratio >= 0.95 ? "#198754" : "#fd7e14",
    },
  ];

  const constraintMetrics: Metric[] = [
    {
      label: "R Outer Ang Lim",
      value: (data.right_fraction_outer_angle_limited * 100).toFixed(1),
      unit: "%",
    },
    {
      label: "R Inner Ang Lim",
      value: (data.right_fraction_inner_angle_limited * 100).toFixed(1),
      unit: "%",
    },
    {
      label: "L Outer Ang Lim",
      value: (data.left_fraction_outer_angle_limited * 100).toFixed(1),
      unit: "%",
    },
    {
      label: "L Inner Ang Lim",
      value: (data.left_fraction_inner_angle_limited * 100).toFixed(1),
      unit: "%",
    },
    {
      label: "R Outer Rate Lim",
      value: (data.right_fraction_outer_rate_limited * 100).toFixed(1),
      unit: "%",
    },
    {
      label: "R Inner Rate Lim",
      value: (data.right_fraction_inner_rate_limited * 100).toFixed(1),
      unit: "%",
    },
    {
      label: "L Outer Rate Lim",
      value: (data.left_fraction_outer_rate_limited * 100).toFixed(1),
      unit: "%",
    },
    {
      label: "L Inner Rate Lim",
      value: (data.left_fraction_inner_rate_limited * 100).toFixed(1),
      unit: "%",
    },
    {
      label: "R In Keep-Out",
      value: (data.right_fraction_in_keepout * 100).toFixed(1),
      unit: "%",
    },
    {
      label: "L In Keep-Out",
      value: (data.left_fraction_in_keepout * 100).toFixed(1),
      unit: "%",
    },
  ];

  return (
    <div style={styles.wrapper}>
      <h3 style={styles.sectionLabel}>Orbit & Eclipse</h3>
      <div style={styles.grid}>
        {orbitMetrics.map((m) => (
          <div key={m.label} style={styles.card}>
            <div style={styles.cardLabel}>{m.label}</div>
            <div style={{ ...styles.cardValue, color: m.color || "#212529" }}>
              {m.value}<span style={styles.cardUnit}> {m.unit}</span>
            </div>
          </div>
        ))}
      </div>

      <h3 style={styles.sectionLabel}>Ideal Power</h3>
      <div style={styles.grid}>
        {idealPowerMetrics.map((m) => (
          <div key={m.label} style={styles.card}>
            <div style={styles.cardLabel}>{m.label}</div>
            <div style={{ ...styles.cardValue, color: m.color || "#212529" }}>
              {m.value}<span style={styles.cardUnit}> {m.unit}</span>
            </div>
          </div>
        ))}
      </div>

      <h3 style={styles.sectionLabel}>Achieved Power (Constrained)</h3>
      <div style={styles.grid}>
        {achievedPowerMetrics.map((m) => (
          <div key={m.label} style={styles.card}>
            <div style={styles.cardLabel}>{m.label}</div>
            <div style={{ ...styles.cardValue, color: m.color || "#212529" }}>
              {m.value}<span style={styles.cardUnit}> {m.unit}</span>
            </div>
          </div>
        ))}
      </div>

      <h3 style={styles.sectionLabel}>Constraint Activity (% of orbit)</h3>
      <div style={styles.grid}>
        {constraintMetrics.map((m) => (
          <div key={m.label} style={styles.card}>
            <div style={styles.cardLabel}>{m.label}</div>
            <div style={{ ...styles.cardValue, color: m.color || "#212529" }}>
              {m.value}<span style={styles.cardUnit}> {m.unit}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
  },
  sectionLabel: {
    margin: "0.5rem 0 0 0",
    fontSize: "0.9rem",
    fontWeight: 600,
    color: "#495057",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(155px, 1fr))",
    gap: "0.6rem",
  },
  card: {
    padding: "0.75rem",
    background: "#fff",
    border: "1px solid #dee2e6",
    borderRadius: "8px",
    textAlign: "center",
  },
  cardLabel: {
    fontSize: "0.7rem",
    color: "#6c757d",
    marginBottom: "0.2rem",
    fontWeight: 500,
  },
  cardValue: {
    fontSize: "1.2rem",
    fontWeight: 700,
  },
  cardUnit: {
    fontSize: "0.75rem",
    fontWeight: 400,
    color: "#6c757d",
  },
};
