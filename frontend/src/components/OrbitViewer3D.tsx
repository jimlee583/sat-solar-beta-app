import { useRef, useState, useMemo, useCallback, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Line, Edges } from "@react-three/drei";
import * as THREE from "three";
import type { AnalysisResponse } from "../types/analysis";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";

const DEG = Math.PI / 180;
const R_EARTH_KM = 6371.0;
const EARTH_VISUAL_RADIUS = 0.4;

/* ------------------------------------------------------------------ */
/*  Geometry helpers                                                    */
/* ------------------------------------------------------------------ */

function orbitPosition(thetaDeg: number, r: number): [number, number, number] {
  const t = thetaDeg * DEG;
  return [r * Math.sin(t), 0, r * Math.cos(t)];
}

function sunDirection(betaDeg: number): THREE.Vector3 {
  const b = betaDeg * DEG;
  return new THREE.Vector3(0, Math.sin(b), Math.cos(b)).normalize();
}

/** Build the VVLH→scene rotation matrix for a given orbit angle. */
function vvlhMatrix(thetaDeg: number): THREE.Matrix4 {
  const t = thetaDeg * DEG;
  const ct = Math.cos(t);
  const st = Math.sin(t);
  // columns: X_body(velocity), Y_body(-orbit normal), Z_body(nadir)
  return new THREE.Matrix4().set(
    ct, 0, -st, 0,
    0, -1, 0, 0,
    -st, 0, -ct, 0,
    0, 0, 0, 1,
  );
}

/** Compute wing normal in scene coords from gimbal angles + VVLH rotation.
 *  Rz(outer) * Rx(inner) * n0, then transform by VVLH matrix.  */
function wingNormalScene(
  outerDeg: number,
  innerDeg: number,
  isRight: boolean,
  thetaDeg: number,
): THREE.Vector3 {
  const ao = outerDeg * DEG;
  const ai = innerDeg * DEG;
  const co = Math.cos(ao), so = Math.sin(ao);
  const ci = Math.cos(ai), si = Math.sin(ai);
  const sign = isRight ? 1 : -1;

  // n_body = Rz(ao) @ Rx(ai) @ n0  where n0 = [0, ±1, 0]
  const nx = -sign * so * ci;
  const ny = sign * co * ci;
  const nz = sign * si;

  const bodyVec = new THREE.Vector3(nx, ny, nz);
  bodyVec.applyMatrix4(vvlhMatrix(thetaDeg));
  return bodyVec.normalize();
}

/** Build wing quaternion so the panel mesh faces wing normal direction. */
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

  // The wing mesh is a plane in XZ with normal along +Y (right) or -Y (left).
  // We need to rotate from the body frame wing mount to the gimbal state.
  // The base orientation already accounts for the wing being on +Y or -Y side.
  if (!isRight) {
    const flipMat = new THREE.Matrix4().makeRotationZ(Math.PI);
    combined.multiply(flipMat);
  }

  const q = new THREE.Quaternion();
  q.setFromRotationMatrix(combined);
  return q;
}

/* ------------------------------------------------------------------ */
/*  Sub-components rendered inside the Canvas                          */
/* ------------------------------------------------------------------ */

function EarthMesh() {
  return (
    <group>
      <mesh>
        <sphereGeometry args={[EARTH_VISUAL_RADIUS, 48, 48]} />
        <meshStandardMaterial color="#2e6cb5" roughness={0.8} />
      </mesh>
      <mesh>
        <sphereGeometry args={[EARTH_VISUAL_RADIUS * 1.002, 24, 24]} />
        <meshBasicMaterial color="#5a9bd5" wireframe transparent opacity={0.15} />
      </mesh>
    </group>
  );
}

function OrbitRing({
  orbitRadius,
  inEclipse,
}: {
  orbitRadius: number;
  inEclipse: boolean[];
}) {
  const { sunlit, eclipse } = useMemo(() => {
    const n = 720;
    const sunPts: THREE.Vector3[] = [];
    const eclPts: THREE.Vector3[] = [];

    for (let i = 0; i <= n; i++) {
      const frac = i / n;
      const sampleIdx = Math.min(
        Math.floor(frac * inEclipse.length),
        inEclipse.length - 1,
      );
      const deg = frac * 360;
      const t = deg * DEG;
      const pt = new THREE.Vector3(
        orbitRadius * Math.sin(t),
        0,
        orbitRadius * Math.cos(t),
      );

      if (inEclipse[sampleIdx]) {
        eclPts.push(pt);
      } else {
        sunPts.push(pt);
      }
    }
    return { sunlit: sunPts, eclipse: eclPts };
  }, [orbitRadius, inEclipse]);

  return (
    <group>
      {sunlit.length > 1 && (
        <Line points={sunlit} color="#66ccff" lineWidth={1.5} />
      )}
      {eclipse.length > 1 && (
        <Line points={eclipse} color="#444444" lineWidth={1.5} />
      )}
    </group>
  );
}

function SunMarker({ betaDeg }: { betaDeg: number }) {
  const dir = useMemo(() => sunDirection(betaDeg), [betaDeg]);
  const pos = useMemo(
    () => [dir.x * 6, dir.y * 6, dir.z * 6] as [number, number, number],
    [dir],
  );

  return (
    <group>
      <mesh position={pos}>
        <sphereGeometry args={[0.25, 16, 16]} />
        <meshBasicMaterial color="#ffdd44" />
      </mesh>
      <directionalLight
        position={pos}
        intensity={1.5}
        color="#ffffff"
      />
    </group>
  );
}

function SatelliteGroup({
  thetaDeg,
  orbitRadius,
  rightOuter,
  rightInner,
  leftOuter,
  leftInner,
  betaDeg,
}: {
  thetaDeg: number;
  orbitRadius: number;
  rightOuter: number;
  rightInner: number;
  leftOuter: number;
  leftInner: number;
  betaDeg: number;
}) {
  const groupRef = useRef<THREE.Group>(null);

  const pos = useMemo(
    () => orbitPosition(thetaDeg, orbitRadius),
    [thetaDeg, orbitRadius],
  );

  // Satellite body orientation: align to VVLH frame
  const bodyQuat = useMemo(() => {
    const mat = vvlhMatrix(thetaDeg);
    const q = new THREE.Quaternion();
    q.setFromRotationMatrix(mat);
    return q;
  }, [thetaDeg]);

  const rightWingQ = useMemo(
    () => wingQuaternion(rightOuter, rightInner, true),
    [rightOuter, rightInner],
  );
  const leftWingQ = useMemo(
    () => wingQuaternion(leftOuter, leftInner, false),
    [leftOuter, leftInner],
  );

  // Wing normal arrows (in scene coordinates)
  const rightNormal = useMemo(
    () => wingNormalScene(rightOuter, rightInner, true, thetaDeg),
    [rightOuter, rightInner, thetaDeg],
  );
  const leftNormal = useMemo(
    () => wingNormalScene(leftOuter, leftInner, false, thetaDeg),
    [leftOuter, leftInner, thetaDeg],
  );

  const sunDir = useMemo(() => sunDirection(betaDeg), [betaDeg]);

  // Sun line from satellite toward sun
  const sunLineEnd = useMemo(() => {
    return new THREE.Vector3(
      pos[0] + sunDir.x * 0.6,
      pos[1] + sunDir.y * 0.6,
      pos[2] + sunDir.z * 0.6,
    );
  }, [pos, sunDir]);

  const ARROW_LEN = 0.15;

  // Wing normal arrow endpoints (scene coords)
  const rightArrow = useMemo(() => {
    const mat = vvlhMatrix(thetaDeg);
    const base = new THREE.Vector3(pos[0], pos[1], pos[2]).add(
      new THREE.Vector3(0, -1, 0).applyMatrix4(mat).multiplyScalar(0.09),
    );
    const tip = base.clone().add(rightNormal.clone().multiplyScalar(ARROW_LEN));
    return { base, tip };
  }, [pos, thetaDeg, rightNormal]);

  const leftArrow = useMemo(() => {
    const mat = vvlhMatrix(thetaDeg);
    const base = new THREE.Vector3(pos[0], pos[1], pos[2]).add(
      new THREE.Vector3(0, 1, 0).applyMatrix4(mat).multiplyScalar(0.09),
    );
    const tip = base.clone().add(leftNormal.clone().multiplyScalar(ARROW_LEN));
    return { base, tip };
  }, [pos, thetaDeg, leftNormal]);

  return (
    <group ref={groupRef}>
      {/* Satellite body (oriented to VVLH) */}
      <group position={pos} quaternion={bodyQuat}>
        <mesh>
          <boxGeometry args={[0.06, 0.04, 0.04]} />
          <meshStandardMaterial color="#cccccc" roughness={0.4} metalness={0.6} />
          <Edges color="white" />
        </mesh>

        {/* Right wing (+Y side in body frame) */}
        <group position={[0, 0.07, 0]} quaternion={rightWingQ}>
          <mesh position={[0, 0.02, 0]}>
            <boxGeometry args={[0.10, 0.003, 0.04]} />
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
        <group position={[0, -0.07, 0]} quaternion={leftWingQ}>
          <mesh position={[0, 0.02, 0]}>
            <boxGeometry args={[0.10, 0.003, 0.04]} />
            <meshStandardMaterial
              color="#1a3a6e"
              roughness={0.3}
              metalness={0.7}
              side={THREE.DoubleSide}
            />
            <Edges color="white" />
          </mesh>
        </group>
      </group>

      {/* Wing normal arrows (line-based, scene coords) */}
      <Line
        points={[
          [rightArrow.base.x, rightArrow.base.y, rightArrow.base.z],
          [rightArrow.tip.x, rightArrow.tip.y, rightArrow.tip.z],
        ]}
        color="#00ff88"
        lineWidth={2}
      />
      <Line
        points={[
          [leftArrow.base.x, leftArrow.base.y, leftArrow.base.z],
          [leftArrow.tip.x, leftArrow.tip.y, leftArrow.tip.z],
        ]}
        color="#00ff88"
        lineWidth={2}
      />

      {/* Sun direction line from satellite */}
      <Line
        points={[pos, [sunLineEnd.x, sunLineEnd.y, sunLineEnd.z]]}
        color="#ffdd44"
        lineWidth={1}
        dashed
        dashSize={0.03}
        gapSize={0.02}
      />
    </group>
  );
}

/* ------------------------------------------------------------------ */
/*  Animation driver (runs inside Canvas)                              */
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
  const samplesPerSecond = (sampleCount / 10) * speed; // full orbit in ~10s at 1x

  useFrame((_, delta) => {
    if (!playing) return;
    accum.current += delta * samplesPerSecond;
    if (accum.current >= 1) {
      const steps = Math.floor(accum.current);
      accum.current -= steps;
      const next = (sampleIndex + steps) % sampleCount;
      onSampleChange(next);
    }
  });

  return null;
}

/* ------------------------------------------------------------------ */
/*  Camera controller for view presets                                 */
/* ------------------------------------------------------------------ */

type CameraView = "free" | "sun" | "top";

function CameraController({
  view,
  betaDeg,
  controlsRef,
  onApplied,
}: {
  view: CameraView;
  betaDeg: number;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
  onApplied: () => void;
}) {
  const { camera } = useThree();
  const lastApplied = useRef<CameraView | null>(null);

  useEffect(() => {
    if (view === "free" || view === lastApplied.current) return;

    let pos: THREE.Vector3;
    const target = new THREE.Vector3(0, 0, 0);

    if (view === "sun") {
      const dir = sunDirection(betaDeg);
      pos = dir.clone().multiplyScalar(4);
    } else {
      // top-down
      pos = new THREE.Vector3(0, 4, 0);
    }

    camera.position.copy(pos);
    camera.lookAt(target);
    camera.updateProjectionMatrix();

    if (controlsRef.current) {
      controlsRef.current.target.copy(target);
      controlsRef.current.update();
    }

    lastApplied.current = view;
    onApplied();
  }, [view, betaDeg, camera, controlsRef, onApplied]);

  return null;
}

/* ------------------------------------------------------------------ */
/*  Nadir line from satellite to Earth surface                         */
/* ------------------------------------------------------------------ */

function NadirLine({
  thetaDeg,
  orbitRadius,
}: {
  thetaDeg: number;
  orbitRadius: number;
}) {
  const points = useMemo(() => {
    const t = thetaDeg * DEG;
    const satX = orbitRadius * Math.sin(t);
    const satZ = orbitRadius * Math.cos(t);
    const earthX = EARTH_VISUAL_RADIUS * Math.sin(t);
    const earthZ = EARTH_VISUAL_RADIUS * Math.cos(t);
    return [
      new THREE.Vector3(satX, 0, satZ),
      new THREE.Vector3(earthX, 0, earthZ),
    ];
  }, [thetaDeg, orbitRadius]);

  return <Line points={points} color="#ff6666" lineWidth={1} dashed dashSize={0.02} gapSize={0.02} />;
}

/* ------------------------------------------------------------------ */
/*  Main exported component                                            */
/* ------------------------------------------------------------------ */

interface OrbitViewer3DProps {
  data: AnalysisResponse;
  betaDeg: number;
}

export default function OrbitViewer3D({ data, betaDeg }: OrbitViewer3DProps) {
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
  const orbitRadius = data.orbit_radius_km / R_EARTH_KM;
  const thetaDeg = data.orbit_angle_deg[sampleIndex];
  const inEclipseNow = data.in_eclipse[sampleIndex];

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
          camera={{ position: [0, 2.5, 3], fov: 45, near: 0.01, far: 100 }}
          style={{ background: "#0a0a1a" }}
        >
          <ambientLight intensity={0.3} />
          <EarthMesh />
          <OrbitRing orbitRadius={orbitRadius} inEclipse={data.in_eclipse} />
          <SunMarker betaDeg={betaDeg} />
          <SatelliteGroup
            thetaDeg={thetaDeg}
            orbitRadius={orbitRadius}
            rightOuter={rightOuter}
            rightInner={rightInner}
            leftOuter={leftOuter}
            leftInner={leftInner}
            betaDeg={betaDeg}
          />
          <NadirLine thetaDeg={thetaDeg} orbitRadius={orbitRadius} />
          <AnimationDriver
            playing={playing}
            speed={speed}
            sampleCount={sampleCount}
            sampleIndex={sampleIndex}
            onSampleChange={handleSampleChange}
          />
          <CameraController
            view={cameraView}
            betaDeg={betaDeg}
            controlsRef={controlsRef}
            onApplied={handleViewApplied}
          />
          <OrbitControls ref={controlsRef} enableDamping dampingFactor={0.12} />
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
            onClick={() => setCameraView("sun")}
            style={styles.viewBtn}
          >
            Sun View
          </button>
          <button
            onClick={() => setCameraView("top")}
            style={styles.viewBtn}
          >
            Top View
          </button>
        </div>

        <div style={styles.sliderRow}>
          <span style={styles.angleReadout}>
            {thetaDeg.toFixed(1)}°
          </span>
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
          {inEclipseNow && (
            <span style={styles.eclipseTag}>ECLIPSE</span>
          )}
        </div>

        {/* Solar array angle readout */}
        <div style={styles.arrayReadout}>
          <div style={styles.wingColumn}>
            <span style={styles.wingTitle}>Right Wing</span>
            <span style={styles.wingValue}>
              Outer: <strong>{rightOuter.toFixed(1)}°</strong>
            </span>
            <span style={styles.wingValue}>
              Inner: <strong>{rightInner.toFixed(1)}°</strong>
            </span>
            <span style={styles.wingValue}>
              Incidence: <strong>{rightIncidence.toFixed(1)}°</strong>
            </span>
          </div>
          <div style={styles.wingColumn}>
            <span style={styles.wingTitle}>Left Wing</span>
            <span style={styles.wingValue}>
              Outer: <strong>{leftOuter.toFixed(1)}°</strong>
            </span>
            <span style={styles.wingValue}>
              Inner: <strong>{leftInner.toFixed(1)}°</strong>
            </span>
            <span style={styles.wingValue}>
              Incidence: <strong>{leftIncidence.toFixed(1)}°</strong>
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
    minWidth: "52px",
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
  arrayReadout: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "0.75rem",
    padding: "0.5rem 0.25rem 0",
    borderTop: "1px solid #dee2e6",
  },
  wingColumn: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "0.15rem",
  },
  wingTitle: {
    fontSize: "0.75rem",
    fontWeight: 700,
    color: "#212529",
    marginBottom: "0.1rem",
  },
  wingValue: {
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
