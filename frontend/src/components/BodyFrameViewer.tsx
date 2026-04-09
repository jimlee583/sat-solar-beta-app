import { useRef, useState, useMemo, useCallback, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Line, Edges, Html } from "@react-three/drei";
import * as THREE from "three";
import type { AnalysisResponse } from "../types/analysis";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";

const DEG = Math.PI / 180;
const SUN_DIST = 3.0;
const AXIS_LEN = 1.5;

/*
 * VVLH body frame convention:
 *   +X = velocity direction
 *   +Y = completes RH triad (−orbit normal)
 *   +Z = nadir (toward Earth)
 *
 * Sun VVLH components (from backend):
 *   S_x = −sin(θ)·cos(β)
 *   S_y = −sin(β)
 *   S_z = −cos(θ)·cos(β)
 *
 * This view places the satellite body at the origin so the sun
 * appears to move around the spacecraft as θ advances.
 */

/* ------------------------------------------------------------------ */
/*  Geometry helpers                                                    */
/* ------------------------------------------------------------------ */

function wingQuaternion(
  outerDeg: number,
  innerDeg: number,
  isRight: boolean,
): THREE.Quaternion {
  const ao = outerDeg * DEG;
  const ai = innerDeg * DEG;

  const rzMat = new THREE.Matrix4().makeRotationZ(ao);
  const rxMat = new THREE.Matrix4().makeRotationX(ai);
  const combined = new THREE.Matrix4().multiplyMatrices(rzMat, rxMat);

  if (!isRight) {
    combined.multiply(new THREE.Matrix4().makeRotationZ(Math.PI));
  }

  const q = new THREE.Quaternion();
  q.setFromRotationMatrix(combined);
  return q;
}

function wingNormalBody(
  outerDeg: number,
  innerDeg: number,
  isRight: boolean,
): THREE.Vector3 {
  const ao = outerDeg * DEG;
  const ai = innerDeg * DEG;
  const co = Math.cos(ao), so = Math.sin(ao);
  const ci = Math.cos(ai), si = Math.sin(ai);
  const sign = isRight ? 1 : -1;

  return new THREE.Vector3(
    -sign * so * ci,
    sign * co * ci,
    sign * si,
  ).normalize();
}

/* ------------------------------------------------------------------ */
/*  Body frame axes with labels                                        */
/* ------------------------------------------------------------------ */

function BodyAxes() {
  const axes: { dir: [number, number, number]; color: string; label: string }[] = [
    { dir: [AXIS_LEN, 0, 0], color: "#ff4444", label: "+X (vel)" },
    { dir: [0, AXIS_LEN, 0], color: "#44ff44", label: "+Y" },
    { dir: [0, 0, AXIS_LEN], color: "#4488ff", label: "+Z (nadir)" },
  ];

  return (
    <group>
      {axes.map(({ dir, color, label }) => (
        <group key={label}>
          <Line points={[[0, 0, 0], dir]} color={color} lineWidth={2} />
          <mesh position={dir}>
            <sphereGeometry args={[0.03, 8, 8]} />
            <meshBasicMaterial color={color} />
          </mesh>
          <Html
            position={[dir[0] * 1.12, dir[1] * 1.12, dir[2] * 1.12]}
            center
            style={{
              color,
              fontSize: "11px",
              fontWeight: 700,
              fontFamily: "monospace",
              textShadow: "0 0 4px rgba(0,0,0,0.9)",
              whiteSpace: "nowrap",
              pointerEvents: "none",
              userSelect: "none",
            }}
          >
            {label}
          </Html>
        </group>
      ))}

      {axes.map(({ dir, color, label }) => (
        <Line
          key={`neg-${label}`}
          points={[
            [0, 0, 0],
            [-dir[0] * 0.3, -dir[1] * 0.3, -dir[2] * 0.3],
          ]}
          color={color}
          lineWidth={1}
          dashed
          dashSize={0.04}
          gapSize={0.03}
        />
      ))}

      <mesh position={[0, 0, AXIS_LEN * 0.85]}>
        <sphereGeometry args={[0.06, 16, 16]} />
        <meshBasicMaterial color="#2e6cb5" transparent opacity={0.6} />
      </mesh>
    </group>
  );
}

/* ------------------------------------------------------------------ */
/*  Sun path trace over one orbit                                      */
/* ------------------------------------------------------------------ */

function SunPath({
  sunX,
  sunY,
  sunZ,
  inEclipse,
}: {
  sunX: number[];
  sunY: number[];
  sunZ: number[];
  inEclipse: boolean[];
}) {
  const { sunlit, eclipse } = useMemo(() => {
    const sunPts: THREE.Vector3[] = [];
    const eclPts: THREE.Vector3[] = [];

    for (let i = 0; i < sunX.length; i++) {
      const pt = new THREE.Vector3(
        sunX[i] * SUN_DIST,
        sunY[i] * SUN_DIST,
        sunZ[i] * SUN_DIST,
      );
      if (inEclipse[i]) {
        eclPts.push(pt);
      } else {
        sunPts.push(pt);
      }
    }
    return { sunlit: sunPts, eclipse: eclPts };
  }, [sunX, sunY, sunZ, inEclipse]);

  return (
    <group>
      {sunlit.length > 1 && (
        <Line points={sunlit} color="#ffdd44" lineWidth={1.5} />
      )}
      {eclipse.length > 1 && (
        <Line points={eclipse} color="#555555" lineWidth={1.5} />
      )}
    </group>
  );
}

/* ------------------------------------------------------------------ */
/*  Orbit angle markers on the sun path                                */
/* ------------------------------------------------------------------ */

function SunPathMarkers({
  sunX,
  sunY,
  sunZ,
}: {
  sunX: number[];
  sunY: number[];
  sunZ: number[];
}) {
  const markers = useMemo(() => {
    const n = sunX.length;
    const angles = [0, 90, 180, 270];
    return angles.map((deg) => {
      const idx = Math.round((deg / 360) * n) % n;
      const pos: [number, number, number] = [
        sunX[idx] * SUN_DIST,
        sunY[idx] * SUN_DIST,
        sunZ[idx] * SUN_DIST,
      ];
      const len = Math.sqrt(pos[0] ** 2 + pos[1] ** 2 + pos[2] ** 2) || 1;
      const labelPos: [number, number, number] = [
        pos[0] + (pos[0] / len) * 0.25,
        pos[1] + (pos[1] / len) * 0.25,
        pos[2] + (pos[2] / len) * 0.25,
      ];
      return { pos, labelPos, label: `${deg}°` };
    });
  }, [sunX, sunY, sunZ]);

  return (
    <group>
      {markers.map(({ pos, labelPos, label }) => (
        <group key={label}>
          <mesh position={pos}>
            <sphereGeometry args={[0.04, 8, 8]} />
            <meshBasicMaterial color="#aaaaaa" />
          </mesh>
          <Html
            position={labelPos}
            center
            style={{
              color: "#999999",
              fontSize: "9px",
              fontWeight: 600,
              fontFamily: "monospace",
              textShadow: "0 0 3px rgba(0,0,0,0.8)",
              whiteSpace: "nowrap",
              pointerEvents: "none",
              userSelect: "none",
            }}
          >
            θ={label}
          </Html>
        </group>
      ))}
    </group>
  );
}

/* ------------------------------------------------------------------ */
/*  Sun marker at current position                                     */
/* ------------------------------------------------------------------ */

function SunMarkerBody({
  sx,
  sy,
  sz,
  inEclipse,
}: {
  sx: number;
  sy: number;
  sz: number;
  inEclipse: boolean;
}) {
  const pos = useMemo(
    () =>
      [sx * SUN_DIST, sy * SUN_DIST, sz * SUN_DIST] as [
        number,
        number,
        number,
      ],
    [sx, sy, sz],
  );

  return (
    <group>
      <mesh position={pos}>
        <sphereGeometry args={[0.15, 16, 16]} />
        <meshBasicMaterial color={inEclipse ? "#555555" : "#ffdd44"} />
      </mesh>
      {!inEclipse && (
        <directionalLight position={pos} intensity={1.5} color="#ffffff" />
      )}
      <Line
        points={[[0, 0, 0], pos]}
        color={inEclipse ? "#444444" : "#ffdd44"}
        lineWidth={1}
        dashed
        dashSize={0.06}
        gapSize={0.04}
      />
    </group>
  );
}

/* ------------------------------------------------------------------ */
/*  Satellite model with articulating wings                            */
/* ------------------------------------------------------------------ */

const BODY_DIMS: [number, number, number] = [0.30, 0.20, 0.20];
const WING_MOUNT_Y = 0.14;
const WING_MESH_OFFSET_Y = 0.12;
const WING_DIMS: [number, number, number] = [0.50, 0.015, 0.20];
const NORMAL_ARROW_LEN = 0.7;

function SatelliteModel({
  rightOuter,
  rightInner,
  leftOuter,
  leftInner,
}: {
  rightOuter: number;
  rightInner: number;
  leftOuter: number;
  leftInner: number;
}) {
  const rightWingQ = useMemo(
    () => wingQuaternion(rightOuter, rightInner, true),
    [rightOuter, rightInner],
  );
  const leftWingQ = useMemo(
    () => wingQuaternion(leftOuter, leftInner, false),
    [leftOuter, leftInner],
  );

  const rightNorm = useMemo(
    () => wingNormalBody(rightOuter, rightInner, true),
    [rightOuter, rightInner],
  );
  const leftNorm = useMemo(
    () => wingNormalBody(leftOuter, leftInner, false),
    [leftOuter, leftInner],
  );

  const arrowBaseY = WING_MOUNT_Y + WING_MESH_OFFSET_Y;

  const rightArrowBase = useMemo(
    () => new THREE.Vector3(0, arrowBaseY, 0),
    [arrowBaseY],
  );
  const rightArrowTip = useMemo(
    () =>
      rightArrowBase
        .clone()
        .add(rightNorm.clone().multiplyScalar(NORMAL_ARROW_LEN)),
    [rightArrowBase, rightNorm],
  );

  const leftArrowBase = useMemo(
    () => new THREE.Vector3(0, -arrowBaseY, 0),
    [arrowBaseY],
  );
  const leftArrowTip = useMemo(
    () =>
      leftArrowBase
        .clone()
        .add(leftNorm.clone().multiplyScalar(NORMAL_ARROW_LEN)),
    [leftArrowBase, leftNorm],
  );

  return (
    <group>
      {/* Satellite body */}
      <mesh>
        <boxGeometry args={BODY_DIMS} />
        <meshStandardMaterial
          color="#cccccc"
          roughness={0.4}
          metalness={0.6}
        />
        <Edges color="white" />
      </mesh>

      {/* Right wing (+Y side in body frame) */}
      <group position={[0, WING_MOUNT_Y, 0]} quaternion={rightWingQ}>
        <mesh position={[0, WING_MESH_OFFSET_Y, 0]}>
          <boxGeometry args={WING_DIMS} />
          <meshStandardMaterial
            color="#1a3a6e"
            roughness={0.3}
            metalness={0.7}
            side={THREE.DoubleSide}
          />
          <Edges color="white" />
        </mesh>
      </group>

      {/* Left wing (-Y side in body frame) */}
      <group position={[0, -WING_MOUNT_Y, 0]} quaternion={leftWingQ}>
        <mesh position={[0, WING_MESH_OFFSET_Y, 0]}>
          <boxGeometry args={WING_DIMS} />
          <meshStandardMaterial
            color="#1a3a6e"
            roughness={0.3}
            metalness={0.7}
            side={THREE.DoubleSide}
          />
          <Edges color="white" />
        </mesh>
      </group>

      {/* Right wing normal arrow */}
      <Line
        points={[
          [rightArrowBase.x, rightArrowBase.y, rightArrowBase.z],
          [rightArrowTip.x, rightArrowTip.y, rightArrowTip.z],
        ]}
        color="#00ff88"
        lineWidth={2.5}
      />
      <mesh position={[rightArrowTip.x, rightArrowTip.y, rightArrowTip.z]}>
        <sphereGeometry args={[0.025, 8, 8]} />
        <meshBasicMaterial color="#00ff88" />
      </mesh>

      {/* Left wing normal arrow */}
      <Line
        points={[
          [leftArrowBase.x, leftArrowBase.y, leftArrowBase.z],
          [leftArrowTip.x, leftArrowTip.y, leftArrowTip.z],
        ]}
        color="#00ff88"
        lineWidth={2.5}
      />
      <mesh position={[leftArrowTip.x, leftArrowTip.y, leftArrowTip.z]}>
        <sphereGeometry args={[0.025, 8, 8]} />
        <meshBasicMaterial color="#00ff88" />
      </mesh>
    </group>
  );
}

/* ------------------------------------------------------------------ */
/*  Animation driver                                                   */
/* ------------------------------------------------------------------ */

function AnimationDriver({
  playing,
  speed,
  sampleCount,
  sampleIndex,
  onSampleChange,
}: {
  playing: boolean;
  speed: number;
  sampleCount: number;
  sampleIndex: number;
  onSampleChange: (i: number) => void;
}) {
  const accum = useRef(0);
  const samplesPerSecond = (sampleCount / 10) * speed;

  useFrame((_, delta) => {
    if (!playing) return;
    accum.current += delta * samplesPerSecond;
    if (accum.current >= 1) {
      const steps = Math.floor(accum.current);
      accum.current -= steps;
      onSampleChange((sampleIndex + steps) % sampleCount);
    }
  });

  return null;
}

/* ------------------------------------------------------------------ */
/*  Camera controller for view presets                                 */
/* ------------------------------------------------------------------ */

type CameraView = "free" | "along_x" | "along_y" | "along_z";

function CameraController({
  view,
  controlsRef,
  onApplied,
}: {
  view: CameraView;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
  onApplied: () => void;
}) {
  const { camera } = useThree();
  const lastApplied = useRef<CameraView | null>(null);

  useEffect(() => {
    if (view === "free" || view === lastApplied.current) return;

    const posMap: Record<string, THREE.Vector3> = {
      along_x: new THREE.Vector3(5, 0.3, 0.3),
      along_y: new THREE.Vector3(0.3, 5, 0.3),
      along_z: new THREE.Vector3(0.3, 0.3, 5),
    };

    const pos = posMap[view];
    const target = new THREE.Vector3(0, 0, 0);

    camera.position.copy(pos);
    camera.lookAt(target);
    camera.updateProjectionMatrix();

    if (controlsRef.current) {
      controlsRef.current.target.copy(target);
      controlsRef.current.update();
    }

    lastApplied.current = view;
    onApplied();
  }, [view, camera, controlsRef, onApplied]);

  return null;
}

/* ------------------------------------------------------------------ */
/*  Main exported component                                            */
/* ------------------------------------------------------------------ */

interface BodyFrameViewerProps {
  data: AnalysisResponse;
  betaDeg: number;
}

export default function BodyFrameViewer({
  data,
  betaDeg,
}: BodyFrameViewerProps) {
  void betaDeg;

  const [sampleIndex, setSampleIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [showIdeal, setShowIdeal] = useState(true);
  const [cameraView, setCameraView] = useState<CameraView>("free");
  const controlsRef = useRef<OrbitControlsImpl>(null);

  const handleViewApplied = useCallback(() => {
    setCameraView("free");
  }, []);

  const sampleCount = data.orbit_angle_deg.length;
  const thetaDeg = data.orbit_angle_deg[sampleIndex];
  const inEclipseNow = data.in_eclipse[sampleIndex];

  const sx = data.sun_vvlh_x[sampleIndex];
  const sy = data.sun_vvlh_y[sampleIndex];
  const sz = data.sun_vvlh_z[sampleIndex];

  const rightOuter = showIdeal
    ? data.right_ideal_outer_angle_deg[sampleIndex]
    : data.right_achieved_outer_angle_deg[sampleIndex];
  const rightInner = showIdeal
    ? data.right_ideal_inner_angle_deg[sampleIndex]
    : data.right_achieved_inner_angle_deg[sampleIndex];
  const leftOuter = showIdeal
    ? data.left_ideal_outer_angle_deg[sampleIndex]
    : data.left_achieved_outer_angle_deg[sampleIndex];
  const leftInner = showIdeal
    ? data.left_ideal_inner_angle_deg[sampleIndex]
    : data.left_achieved_inner_angle_deg[sampleIndex];
  const rightIncidence = showIdeal
    ? data.right_ideal_incidence_deg[sampleIndex]
    : data.right_achieved_incidence_deg[sampleIndex];
  const leftIncidence = showIdeal
    ? data.left_ideal_incidence_deg[sampleIndex]
    : data.left_achieved_incidence_deg[sampleIndex];

  const handleSampleChange = useCallback((i: number) => {
    setSampleIndex(i);
  }, []);

  return (
    <div style={styles.container}>
      <div style={styles.canvasWrap}>
        <Canvas
          camera={{
            position: [2.5, 2.0, 2.5],
            fov: 45,
            near: 0.01,
            far: 100,
          }}
          style={{ background: "#0a0a1a" }}
        >
          <ambientLight intensity={0.3} />
          <BodyAxes />
          <SunPath
            sunX={data.sun_vvlh_x}
            sunY={data.sun_vvlh_y}
            sunZ={data.sun_vvlh_z}
            inEclipse={data.in_eclipse}
          />
          <SunPathMarkers
            sunX={data.sun_vvlh_x}
            sunY={data.sun_vvlh_y}
            sunZ={data.sun_vvlh_z}
          />
          <SunMarkerBody
            sx={sx}
            sy={sy}
            sz={sz}
            inEclipse={inEclipseNow}
          />
          <SatelliteModel
            rightOuter={rightOuter}
            rightInner={rightInner}
            leftOuter={leftOuter}
            leftInner={leftInner}
          />
          <AnimationDriver
            playing={playing}
            speed={speed}
            sampleCount={sampleCount}
            sampleIndex={sampleIndex}
            onSampleChange={handleSampleChange}
          />
          <CameraController
            view={cameraView}
            controlsRef={controlsRef}
            onApplied={handleViewApplied}
          />
          <OrbitControls
            ref={controlsRef}
            enableDamping
            dampingFactor={0.12}
          />
        </Canvas>
      </div>

      {/* Playback controls */}
      <div style={styles.controls}>
        <div style={styles.controlRow}>
          <button
            onClick={() => setPlaying((p) => !p)}
            style={styles.playBtn}
          >
            {playing ? "Pause" : "Play"}
          </button>

          <label style={styles.speedLabel}>
            Speed
            <select
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              style={styles.select}
            >
              <option value={0.25}>0.25x</option>
              <option value={0.5}>0.5x</option>
              <option value={1}>1x</option>
              <option value={2}>2x</option>
              <option value={4}>4x</option>
            </select>
          </label>

          <label style={styles.toggleLabel}>
            <input
              type="checkbox"
              checked={!showIdeal}
              onChange={(e) => setShowIdeal(!e.target.checked)}
            />
            Show Achieved
          </label>

          <span style={styles.viewSep} />

          <button
            onClick={() => setCameraView("along_x")}
            style={styles.viewBtn}
          >
            +X View
          </button>
          <button
            onClick={() => setCameraView("along_y")}
            style={styles.viewBtn}
          >
            +Y View
          </button>
          <button
            onClick={() => setCameraView("along_z")}
            style={styles.viewBtn}
          >
            +Z View
          </button>
        </div>

        <div style={styles.sliderRow}>
          <span style={styles.angleReadout}>θ {thetaDeg.toFixed(1)}°</span>
          <input
            type="range"
            min={0}
            max={sampleCount - 1}
            value={sampleIndex}
            onChange={(e) => {
              setPlaying(false);
              setSampleIndex(Number(e.target.value));
            }}
            style={styles.slider}
          />
          {inEclipseNow && <span style={styles.eclipseTag}>ECLIPSE</span>}
        </div>

        {/* Readouts */}
        <div style={styles.readoutGrid}>
          <div style={styles.readoutCol}>
            <span style={styles.readoutTitle}>Right Wing</span>
            <span style={styles.readoutValue}>
              Outer: <strong>{rightOuter.toFixed(1)}°</strong>
            </span>
            <span style={styles.readoutValue}>
              Inner: <strong>{rightInner.toFixed(1)}°</strong>
            </span>
            <span style={styles.readoutValue}>
              Incidence: <strong>{rightIncidence.toFixed(1)}°</strong>
            </span>
          </div>
          <div style={styles.readoutCol}>
            <span style={styles.readoutTitle}>Left Wing</span>
            <span style={styles.readoutValue}>
              Outer: <strong>{leftOuter.toFixed(1)}°</strong>
            </span>
            <span style={styles.readoutValue}>
              Inner: <strong>{leftInner.toFixed(1)}°</strong>
            </span>
            <span style={styles.readoutValue}>
              Incidence: <strong>{leftIncidence.toFixed(1)}°</strong>
            </span>
          </div>
          <div style={styles.readoutCol}>
            <span style={styles.readoutTitle}>Sun (VVLH)</span>
            <span style={styles.readoutValue}>
              X: <strong>{sx.toFixed(3)}</strong>
            </span>
            <span style={styles.readoutValue}>
              Y: <strong>{sy.toFixed(3)}</strong>
            </span>
            <span style={styles.readoutValue}>
              Z: <strong>{sz.toFixed(3)}</strong>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Styles                                                              */
/* ------------------------------------------------------------------ */

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    borderRadius: "8px",
    overflow: "hidden",
    border: "1px solid #dee2e6",
    background: "#fff",
  },
  canvasWrap: {
    width: "100%",
    height: "520px",
  },
  controls: {
    padding: "0.75rem 1rem",
    background: "#f8f9fa",
    borderTop: "1px solid #dee2e6",
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
  },
  controlRow: {
    display: "flex",
    alignItems: "center",
    gap: "1rem",
    flexWrap: "wrap" as const,
  },
  playBtn: {
    padding: "0.4rem 1.2rem",
    background: "#0d6efd",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: "0.85rem",
  },
  speedLabel: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
    fontSize: "0.8rem",
    fontWeight: 500,
    color: "#495057",
  },
  select: {
    padding: "0.3rem",
    border: "1px solid #ced4da",
    borderRadius: "4px",
    fontSize: "0.8rem",
  },
  toggleLabel: {
    display: "flex",
    alignItems: "center",
    gap: "0.35rem",
    fontSize: "0.8rem",
    fontWeight: 500,
    color: "#495057",
    cursor: "pointer",
  },
  sliderRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
  },
  angleReadout: {
    fontFamily: "monospace",
    fontSize: "0.85rem",
    fontWeight: 600,
    color: "#212529",
    minWidth: "60px",
    textAlign: "right" as const,
  },
  slider: {
    flex: 1,
    cursor: "pointer",
  },
  eclipseTag: {
    fontSize: "0.7rem",
    fontWeight: 700,
    color: "#fff",
    background: "#495057",
    padding: "0.15rem 0.5rem",
    borderRadius: "3px",
    letterSpacing: "0.05em",
  },
  readoutGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gap: "0.75rem",
    padding: "0.5rem 0.25rem 0",
    borderTop: "1px solid #dee2e6",
  },
  readoutCol: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "0.15rem",
  },
  readoutTitle: {
    fontSize: "0.75rem",
    fontWeight: 700,
    color: "#212529",
    marginBottom: "0.1rem",
  },
  readoutValue: {
    fontSize: "0.78rem",
    fontFamily: "monospace",
    color: "#495057",
  },
  viewSep: {
    width: "1px",
    height: "1.2rem",
    background: "#ced4da",
    marginLeft: "0.25rem",
  },
  viewBtn: {
    padding: "0.35rem 0.8rem",
    background: "#495057",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: "0.78rem",
  },
};
