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

function boolToNum(arr: boolean[]): number[] {
  return arr.map((v) => (v ? 1 : 0));
}

export default function PlotSection({ data }: PlotSectionProps) {
  const angles = data.orbit_angle_deg;
  const shapes = eclipseShapes(data);

  return (
    <div style={styles.container}>
      {/* ---- V3: Ideal vs Achieved Total Power ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: data.ideal_total_power_w,
              name: "Ideal Total",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 2 },
            },
            {
              x: angles,
              y: data.achieved_total_power_w,
              name: "Achieved Total",
              type: "scatter",
              mode: "lines",
              line: { color: "#6610f2", width: 2 },
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Ideal vs Achieved Total Power" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: { title: { text: "Power [W]" }, rangemode: "tozero" },
            shapes,
          }}
          useResizeHandler
          style={{ width: "100%", height: "350px" }}
          config={{ responsive: true }}
        />
      </div>

      {/* ---- V3: Per-Wing Achieved Power ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: data.right_ideal_power_w,
              name: "Right Ideal",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 1.5, dash: "dot" },
            },
            {
              x: angles,
              y: data.right_achieved_power_w,
              name: "Right Achieved",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 2 },
            },
            {
              x: angles,
              y: data.left_ideal_power_w,
              name: "Left Ideal",
              type: "scatter",
              mode: "lines",
              line: { color: "#dc3545", width: 1.5, dash: "dot" },
            },
            {
              x: angles,
              y: data.left_achieved_power_w,
              name: "Left Achieved",
              type: "scatter",
              mode: "lines",
              line: { color: "#dc3545", width: 2 },
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Per-Wing Power: Ideal vs Achieved" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: { title: { text: "Power [W]" }, rangemode: "tozero" },
            shapes,
          }}
          useResizeHandler
          style={{ width: "100%", height: "350px" }}
          config={{ responsive: true }}
        />
      </div>

      {/* ---- V3: Ideal vs Achieved Gimbal Angles (Right Wing) ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: data.right_ideal_outer_angle_deg,
              name: "Ideal Outer",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 1.5, dash: "dot" },
            },
            {
              x: angles,
              y: data.right_achieved_outer_angle_deg,
              name: "Achieved Outer",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 2 },
            },
            {
              x: angles,
              y: data.right_ideal_inner_angle_deg,
              name: "Ideal Inner",
              type: "scatter",
              mode: "lines",
              line: { color: "#198754", width: 1.5, dash: "dot" },
            },
            {
              x: angles,
              y: data.right_achieved_inner_angle_deg,
              name: "Achieved Inner",
              type: "scatter",
              mode: "lines",
              line: { color: "#198754", width: 2 },
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Right Wing Gimbal Angles: Ideal vs Achieved" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: { title: { text: "Angle [deg]" } },
            shapes,
          }}
          useResizeHandler
          style={{ width: "100%", height: "350px" }}
          config={{ responsive: true }}
        />
      </div>

      {/* ---- V3: Ideal vs Achieved Gimbal Angles (Left Wing) ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: data.left_ideal_outer_angle_deg,
              name: "Ideal Outer",
              type: "scatter",
              mode: "lines",
              line: { color: "#dc3545", width: 1.5, dash: "dot" },
            },
            {
              x: angles,
              y: data.left_achieved_outer_angle_deg,
              name: "Achieved Outer",
              type: "scatter",
              mode: "lines",
              line: { color: "#dc3545", width: 2 },
            },
            {
              x: angles,
              y: data.left_ideal_inner_angle_deg,
              name: "Ideal Inner",
              type: "scatter",
              mode: "lines",
              line: { color: "#fd7e14", width: 1.5, dash: "dot" },
            },
            {
              x: angles,
              y: data.left_achieved_inner_angle_deg,
              name: "Achieved Inner",
              type: "scatter",
              mode: "lines",
              line: { color: "#fd7e14", width: 2 },
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Left Wing Gimbal Angles: Ideal vs Achieved" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: { title: { text: "Angle [deg]" } },
            shapes,
          }}
          useResizeHandler
          style={{ width: "100%", height: "350px" }}
          config={{ responsive: true }}
        />
      </div>

      {/* ---- V3: Ideal vs Achieved Incidence Angles ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: data.right_ideal_incidence_deg,
              name: "Right Ideal",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 1.5, dash: "dot" },
            },
            {
              x: angles,
              y: data.right_achieved_incidence_deg,
              name: "Right Achieved",
              type: "scatter",
              mode: "lines",
              line: { color: "#0d6efd", width: 2 },
            },
            {
              x: angles,
              y: data.left_ideal_incidence_deg,
              name: "Left Ideal",
              type: "scatter",
              mode: "lines",
              line: { color: "#dc3545", width: 1.5, dash: "dot" },
            },
            {
              x: angles,
              y: data.left_achieved_incidence_deg,
              name: "Left Achieved",
              type: "scatter",
              mode: "lines",
              line: { color: "#dc3545", width: 2 },
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Incidence Angle: Ideal vs Achieved" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: { title: { text: "Incidence [deg]" }, range: [-5, 95] },
            shapes,
          }}
          useResizeHandler
          style={{ width: "100%", height: "350px" }}
          config={{ responsive: true }}
        />
      </div>

      {/* ---- V3: Constraint Event Traces (Right Wing) ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: boolToNum(data.right_outer_angle_limited).map((v) => v * 3),
              name: "Outer Ang Lim",
              type: "scatter",
              mode: "lines",
              fill: "tozeroy",
              line: { color: "#0d6efd", width: 1 },
              fillcolor: "rgba(13,110,253,0.15)",
            },
            {
              x: angles,
              y: boolToNum(data.right_inner_angle_limited).map((v) => v * 2.5),
              name: "Inner Ang Lim",
              type: "scatter",
              mode: "lines",
              fill: "tozeroy",
              line: { color: "#198754", width: 1 },
              fillcolor: "rgba(25,135,84,0.15)",
            },
            {
              x: angles,
              y: boolToNum(data.right_outer_rate_limited).map((v) => v * 2),
              name: "Outer Rate Lim",
              type: "scatter",
              mode: "lines",
              fill: "tozeroy",
              line: { color: "#fd7e14", width: 1 },
              fillcolor: "rgba(253,126,20,0.15)",
            },
            {
              x: angles,
              y: boolToNum(data.right_inner_rate_limited).map((v) => v * 1.5),
              name: "Inner Rate Lim",
              type: "scatter",
              mode: "lines",
              fill: "tozeroy",
              line: { color: "#dc3545", width: 1 },
              fillcolor: "rgba(220,53,69,0.15)",
            },
            {
              x: angles,
              y: boolToNum(data.right_in_keepout).map((v) => v * 1),
              name: "Keep-Out",
              type: "scatter",
              mode: "lines",
              fill: "tozeroy",
              line: { color: "#6c757d", width: 1 },
              fillcolor: "rgba(108,117,125,0.2)",
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Right Wing Constraint Events" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: {
              title: { text: "Active" },
              range: [-0.1, 3.5],
              showticklabels: false,
            },
            shapes,
          }}
          useResizeHandler
          style={{ width: "100%", height: "280px" }}
          config={{ responsive: true }}
        />
      </div>

      {/* ---- V3: Constraint Event Traces (Left Wing) ---- */}
      <div style={styles.plotWrapper}>
        <Plot
          data={[
            {
              x: angles,
              y: boolToNum(data.left_outer_angle_limited).map((v) => v * 3),
              name: "Outer Ang Lim",
              type: "scatter",
              mode: "lines",
              fill: "tozeroy",
              line: { color: "#0d6efd", width: 1 },
              fillcolor: "rgba(13,110,253,0.15)",
            },
            {
              x: angles,
              y: boolToNum(data.left_inner_angle_limited).map((v) => v * 2.5),
              name: "Inner Ang Lim",
              type: "scatter",
              mode: "lines",
              fill: "tozeroy",
              line: { color: "#198754", width: 1 },
              fillcolor: "rgba(25,135,84,0.15)",
            },
            {
              x: angles,
              y: boolToNum(data.left_outer_rate_limited).map((v) => v * 2),
              name: "Outer Rate Lim",
              type: "scatter",
              mode: "lines",
              fill: "tozeroy",
              line: { color: "#fd7e14", width: 1 },
              fillcolor: "rgba(253,126,20,0.15)",
            },
            {
              x: angles,
              y: boolToNum(data.left_inner_rate_limited).map((v) => v * 1.5),
              name: "Inner Rate Lim",
              type: "scatter",
              mode: "lines",
              fill: "tozeroy",
              line: { color: "#dc3545", width: 1 },
              fillcolor: "rgba(220,53,69,0.15)",
            },
            {
              x: angles,
              y: boolToNum(data.left_in_keepout).map((v) => v * 1),
              name: "Keep-Out",
              type: "scatter",
              mode: "lines",
              fill: "tozeroy",
              line: { color: "#6c757d", width: 1 },
              fillcolor: "rgba(108,117,125,0.2)",
            },
          ]}
          layout={{
            ...LAYOUT_DEFAULTS,
            title: { text: "Left Wing Constraint Events" },
            xaxis: { title: { text: "Orbit Angle [deg]" }, range: [0, 360] },
            yaxis: {
              title: { text: "Active" },
              range: [-0.1, 3.5],
              showticklabels: false,
            },
            shapes,
          }}
          useResizeHandler
          style={{ width: "100%", height: "280px" }}
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
