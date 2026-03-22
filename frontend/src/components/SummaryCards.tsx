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
    {
      label: "Orbit Radius",
      value: data.orbit_radius_km.toFixed(1),
      unit: "km",
    },
    {
      label: "Orbital Period",
      value: data.orbital_period_min.toFixed(2),
      unit: "min",
    },
    {
      label: "Critical β*",
      value: data.critical_beta_deg_for_no_eclipse.toFixed(2),
      unit: "deg",
    },
    {
      label: "Eclipse Duration",
      value: data.eclipse_duration_min.toFixed(2),
      unit: "min",
    },
    {
      label: "Eclipse Fraction",
      value: (data.eclipse_fraction * 100).toFixed(2),
      unit: "%",
    },
    {
      label: "Sunlight Fraction",
      value: (data.sunlight_fraction * 100).toFixed(2),
      unit: "%",
    },
  ];

  const powerMetrics: Metric[] = [
    {
      label: "Avg Total Power",
      value: data.average_total_power_w.toFixed(1),
      unit: "W",
      color: "#0d6efd",
    },
    {
      label: "Peak Total Power",
      value: data.peak_total_power_w.toFixed(1),
      unit: "W",
      color: "#198754",
    },
    {
      label: "Avg Left Wing",
      value: data.average_left_power_w.toFixed(1),
      unit: "W",
    },
    {
      label: "Avg Right Wing",
      value: data.average_right_power_w.toFixed(1),
      unit: "W",
    },
    {
      label: "% Bus Power (avg)",
      value: data.percent_of_required_bus_power_avg.toFixed(1),
      unit: "%",
      color:
        data.percent_of_required_bus_power_avg >= 100 ? "#198754" : "#dc3545",
    },
    {
      label: "Min Total Power",
      value: data.min_total_power_w.toFixed(1),
      unit: "W",
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
              {m.value}
              <span style={styles.cardUnit}> {m.unit}</span>
            </div>
          </div>
        ))}
      </div>

      <h3 style={styles.sectionLabel}>Solar Array Power</h3>
      <div style={styles.grid}>
        {powerMetrics.map((m) => (
          <div key={m.label} style={styles.card}>
            <div style={styles.cardLabel}>{m.label}</div>
            <div style={{ ...styles.cardValue, color: m.color || "#212529" }}>
              {m.value}
              <span style={styles.cardUnit}> {m.unit}</span>
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
    gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))",
    gap: "0.75rem",
  },
  card: {
    padding: "0.85rem",
    background: "#fff",
    border: "1px solid #dee2e6",
    borderRadius: "8px",
    textAlign: "center",
  },
  cardLabel: {
    fontSize: "0.75rem",
    color: "#6c757d",
    marginBottom: "0.25rem",
    fontWeight: 500,
  },
  cardValue: {
    fontSize: "1.3rem",
    fontWeight: 700,
  },
  cardUnit: {
    fontSize: "0.8rem",
    fontWeight: 400,
    color: "#6c757d",
  },
};
