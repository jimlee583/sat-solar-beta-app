import Plot from "react-plotly.js";
import type { AnalysisResponse } from "../types/analysis";

interface PlotSectionProps {
  data: AnalysisResponse;
}

const LAYOUT_DEFAULTS: Partial<Plotly.Layout> = {
  autosize: true,
  margin: { l: 60, r: 30, t: 40, b: 50 },
  font: { family: "Inter, system-ui, sans-serif", size: 12 },
  paper_bgcolor: "#fff",
  plot_bgcolor: "#f8f9fa",
  legend: { orientation: "h", y: -0.25, x: 0.5, xanchor: "center" },
};

function eclipseShapes(data: AnalysisResponse): Partial<Plotly.Shape>[] {
  const shapes: Partial<Plotly.Shape>[] = [];
  let start: number | null = null;
  const angles = data.orbit_angle_deg;

  for (let i = 0; i < data.in_eclipse.length; i++) {
    if (data.in_eclipse[i] && start === null) {
      start = angles[i];
    }
    if (
      (!data.in_eclipse[i] || i === data.in_eclipse.length - 1) &&
      start !== null
    ) {
      shapes.push({
        type: "rect",
        xref: "x",
        yref: "paper",
        x0: start,
        x1: angles[i - (data.in_eclipse[i] ? 0 : 1)],
        y0: 0,
        y1: 1,
        fillcolor: "rgba(0,0,0,0.08)",
        line: { width: 0 },
        layer: "below",
      });
      start = null;
    }
  }
  return shapes;
}

export default function PlotSection({ data }: PlotSectionProps) {
  const angles = data.orbit_angle_deg;
  const shapes = eclipseShapes(data);

  return (
    <div style={styles.container}>
      {/* ---- V2: Power vs Orbit Angle ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: data.left_power_w,
              name: "Left Wing",
              type: "scatter",
              mode: "lines",
              line: { color: "#dc3545", width: 2 },
            },
            {
              x: angles,
              y: data.right_power_w,
              name: "Right Wing",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 2 },
            },
            {
              x: angles,
              y: data.total_power_w,
              name: "Total",
              type: "scatter",
              mode: "lines",
              line: { color: "#212529", width: 2.5 },
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Solar Array Power vs Orbit Angle" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: { title: { text: "Power [W]" }, rangemode: "tozero" },
            shapes,
          }}
          useResizeHandler
          style={{ width: "100%", height: "350px" }}
          config={{ responsive: true }}
        />
      </div>

      {/* ---- V2: Gimbal Angles vs Orbit Angle ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: data.right_outer_angle_deg,
              name: "Right Outer",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 2 },
            },
            {
              x: angles,
              y: data.right_inner_angle_deg,
              name: "Right Inner",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 2, dash: "dash" },
            },
            {
              x: angles,
              y: data.left_outer_angle_deg,
              name: "Left Outer",
              type: "scatter",
              mode: "lines",
              line: { color: "#dc3545", width: 2 },
            },
            {
              x: angles,
              y: data.left_inner_angle_deg,
              name: "Left Inner",
              type: "scatter",
              mode: "lines",
              line: { color: "#dc3545", width: 2, dash: "dash" },
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Gimbal Angles vs Orbit Angle" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: { title: { text: "Angle [deg]" } },
            shapes,
          }}
          useResizeHandler
          style={{ width: "100%", height: "350px" }}
          config={{ responsive: true }}
        />
      </div>

      {/* ---- V2: Incidence Angle vs Orbit Angle ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: data.right_incidence_deg,
              name: "Right Wing",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 2 },
            },
            {
              x: angles,
              y: data.left_incidence_deg,
              name: "Left Wing",
              type: "scatter",
              mode: "lines",
              line: { color: "#dc3545", width: 2 },
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Incidence Angle vs Orbit Angle" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: {
              title: { text: "Incidence [deg]" },
              range: [-5, 95],
            },
            shapes,
          }}
          useResizeHandler
          style={{ width: "100%", height: "350px" }}
          config={{ responsive: true }}
        />
      </div>

      {/* ---- V1: Sun Azimuth & Elevation ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: data.sun_az_deg,
              name: "Azimuth",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 2 },
            },
            {
              x: angles,
              y: data.sun_el_deg,
              name: "Elevation",
              type: "scatter",
              mode: "lines",
              line: { color: "#dc3545", width: 2 },
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Sun Azimuth & Elevation vs Orbit Angle" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: { title: { text: "Angle [deg]" } },
            shapes,
          }}
          useResizeHandler
          style={{ width: "100%", height: "350px" }}
          config={{ responsive: true }}
        />
      </div>

      {/* ---- V1: Sun VVLH Components ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: data.sun_vvlh_x,
              name: "S_x (vel)",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 2 },
            },
            {
              x: angles,
              y: data.sun_vvlh_y,
              name: "S_y (cross)",
              type: "scatter",
              mode: "lines",
              line: { color: "#198754", width: 2 },
            },
            {
              x: angles,
              y: data.sun_vvlh_z,
              name: "S_z (nadir)",
              type: "scatter",
              mode: "lines",
              line: { color: "#dc3545", width: 2 },
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Sun Unit Vector (VVLH) vs Orbit Angle" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: { title: { text: "Component" }, range: [-1.1, 1.1] },
            shapes,
          }}
          useResizeHandler
          style={{ width: "100%", height: "350px" }}
          config={{ responsive: true }}
        />
      </div>

      {/* ---- V1: Eclipse State ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: data.in_eclipse.map((v) => (v ? 1 : 0)),
              name: "In Eclipse",
              type: "scatter",
              mode: "lines",
              fill: "tozeroy",
              line: { color: "#6c757d", width: 1 },
              fillcolor: "rgba(108,117,125,0.3)",
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Eclipse State vs Orbit Angle" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: {
              title: { text: "In Eclipse" },
              range: [-0.1, 1.3],
              tickvals: [0, 1],
              ticktext: ["Sunlit", "Eclipse"],
            },
          }}
          useResizeHandler
          style={{ width: "100%", height: "280px" }}
          config={{ responsive: true }}
        />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
  },
  plotWrapper: {
    background: "#fff",
    borderRadius: "8px",
    border: "1px solid #dee2e6",
    padding: "0.5rem",
  },
};
