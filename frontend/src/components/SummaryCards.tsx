import type { AnalysisResponse } from "../types/analysis";

interface SummaryCardsProps {
  data: AnalysisResponse;
}

interface Metric {
  label: string;
  value: string;
  unit: string;
}

export default function SummaryCards({ data }: SummaryCardsProps) {
  const metrics: Metric[] = [
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

  return (
    <div style={styles.grid}>
      {metrics.map((m) => (
        <div key={m.label} style={styles.card}>
          <div style={styles.cardLabel}>{m.label}</div>
          <div style={styles.cardValue}>
            {m.value}
            <span style={styles.cardUnit}> {m.unit}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
    gap: "0.75rem",
  },
  card: {
    padding: "1rem",
    background: "#fff",
    border: "1px solid #dee2e6",
    borderRadius: "8px",
    textAlign: "center",
  },
  cardLabel: {
    fontSize: "0.8rem",
    color: "#6c757d",
    marginBottom: "0.25rem",
    fontWeight: 500,
  },
  cardValue: {
    fontSize: "1.4rem",
    fontWeight: 700,
    color: "#212529",
  },
  cardUnit: {
    fontSize: "0.85rem",
    fontWeight: 400,
    color: "#6c757d",
  },
};
