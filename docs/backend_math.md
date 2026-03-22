# Backend Mathematics and Engineering Reference

**Repository:** `sat-solar-beta-app`
**Document scope:** Backend calculation pipeline — orbital mechanics, eclipse geometry, solar array kinematics, power model, and V3 articulation constraints.

---

## 1. Purpose and Scope

This document describes how the backend of `sat-solar-beta-app` transforms a set of orbit and hardware parameters into per-sample arrays of sun angles, gimbal angles, incidence angles, power output, and constraint flags over one complete orbit.

The intended audience is an engineer who wants to:

- Understand the coordinate frames and sign conventions used throughout the code.
- Trace a single API request from input JSON through every calculation layer to the response JSON.
- Verify or extend the mathematical models.
- Understand the distinction between **ideal (unconstrained) tracking** and **achieved (constrained) tracking**.

The backend is a stateless REST API. All physics is single-orbit, steady-state: one call computes one orbit's worth of data for a single altitude, beta angle, and set of hardware parameters. No orbital propagation, no multi-orbit state is maintained between calls.

---

## 2. Version Evolution

The app was built in three successive versions. Each version is a strict superset of the previous one. All three API endpoints remain active.

### Version 1 — Orbit and Eclipse

Inputs: altitude, beta angle, number of orbit samples.

Computes:
- Orbital radius and period (Kepler).
- Eclipse geometry: Earth angular radius, critical beta angle, eclipse half-angle, eclipse fraction and duration.
- Sun unit vector in the VVLH body frame sampled over one orbit.
- Sun azimuth and elevation angles from the VVLH vector.
- A boolean eclipse mask over the sampled orbit.

### Version 2 — Dual-Wing Solar Array and Ideal Power

Adds: solar array area, cell efficiency, degradation factor, required bus power.

Extends V1 by computing:
- **Ideal** dual-axis gimbal angles for each wing, solved analytically so that the wing normal exactly aligns with the sun vector (perfect pointing, no constraints).
- Wing normal vectors in the body frame.
- Incidence angle (angle between wing normal and sun vector) for each sample — always 0° under ideal tracking.
- Cosine efficiency (`max(0, cos(incidence))`).
- Per-wing and total electrical power, zeroed during eclipse.
- Orbit-averaged and peak/min power summary statistics.

### Version 3 — Constrained Articulation Tracking

Adds: per-axis angle limits, gimbal rate limits, rectangular keep-out zones in angle space.

Extends V2 by propagating a **constrained achieved state** sequentially through the orbit:

1. Ideal angles from V2 are used as the commanded target.
2. Keep-out zone violations are resolved by projecting to the nearest zone boundary.
3. Angle limits clip the command to the hard-stop range.
4. Rate limits restrict how far the gimbal can move per time step from its previous achieved position.
5. Achieved wing normals, incidence angles, power, and per-sample constraint flags are computed from the final achieved angles.

Both ideal and achieved outputs are preserved in the V3 response for direct comparison.

---

## 3. Backend Architecture Overview

```
backend/app/
├── main.py                        Entry point; registers the router with FastAPI
├── models.py                      Pydantic request/response schemas (V1, V2, V3)
├── routers/
│   └── analysis.py                Three POST endpoints: /v1, /v2, /v3
│                                  Also contains _compute_v1_base() helper shared
│                                  by all three handlers
└── services/
    ├── constants.py               Physical constants (R_earth, GM, solar constant)
    ├── orbit.py                   Kepler orbital mechanics
    ├── eclipse.py                 Eclipse geometry (cylindrical shadow model)
    ├── sun_geometry.py            Sun unit vector and angles in VVLH; eclipse mask
    ├── solar_array_geometry.py    Rotation matrices, wing normal formula, ideal
    │                              tracking solution, batch computation over orbit
    ├── power.py                   Per-wing power; orbit summary statistics
    ├── constraints.py             Angle-limit clipping, rate-limit enforcement,
    │                              keep-out zone detection and resolution
    └── tracking.py                Per-sample constrained tracking loop (V3)
```

### Request processing flow

```
POST /api/analyze/v3
        │
        ▼
_compute_v1_base()          ← orbit scalars, eclipse scalars, orbit-angle array,
                              sun vector arrays (sx, sy, sz), eclipse mask
        │
        ▼
compute_wing_arrays()        ← ideal angles, wing normals, incidence, cos_eff
(per wing, V2)
        │
        ▼
compute_wing_power()         ← ideal power arrays (zeroed in eclipse)
(per wing, V2)
        │
        ▼
compute_constrained_tracking()   ← achieved angles, incidence, cos_eff,
(per wing, V3)                     constraint flags (per sample)
        │
        ▼
compute_wing_power()         ← achieved power arrays
(per wing, V3)
        │
        ▼
Summary metrics              ← orbit averages, loss percentages, energy ratio,
                               constraint activity fractions
        │
        ▼
AnalysisResponseV3           ← serialised JSON response
```

---

## 4. Coordinate Frames and Conventions

### 4.1 VVLH Body Frame

The spacecraft body frame is aligned with the **Vehicle-Velocity-Local-Horizontal (VVLH)** frame. This is a rotating frame fixed to the satellite that follows its orbital motion.

| Axis | Direction | Notes |
|------|-----------|-------|
| **+X** | Velocity direction (along-track) | Tangent to orbit, forward |
| **+Y** | −orbit normal (cross-track) | Y = Z × X; points opposite to the angular momentum vector |
| **+Z** | Nadir (toward Earth center) | Equal to −r̂ (negative radial outward) |

In terms of classical orbital basis vectors {e_v, e_n, e_r}:

```
VVLH +X =  e_v   (velocity)
VVLH +Y = -e_n   (negative orbit normal)
VVLH +Z = -e_r   (nadir = negative radial outward)
```

> **Nadir-positive Z:** Throughout the code, the +Z axis points *toward* Earth, not away from it. This is an important sign convention that affects the sun vector formula and the solar array inner-axis tilt direction.

### 4.2 Orbit Angle Convention

The orbit angle `θ` (theta) is measured from the **subsolar point** — the location in the orbit directly "above" the sun (i.e., where the sun is at zenith / anti-nadir).

- `θ = 0°`: Sun directly at zenith (anti-nadir). Sun vector in VVLH is (0, 0, −1).
- `θ = 90°`: Satellite has moved 90° from the subsolar point. Sun is in the orbital plane, pointing along ±X.
- `θ = 180°`: Sun directly below the satellite (toward Earth). This is the center of the eclipse zone.

The orbit is sampled uniformly from `θ = 0°` to `θ = 360°` with `endpoint=False` so the sample spacing is exactly `360° / N` and there is no duplicate sample at 360° = 0°.

**Source:** `routers/analysis.py` → `_compute_v1_base()`, line:
```python
angles = np.linspace(0.0, 360.0, num_samples, endpoint=False)
```

### 4.3 Beta Angle

The **beta angle** β is the angle between the orbit plane and the Sun vector. It is a direct input to the API, not derived from orbital elements.

- β = 0°: Sun lies in the orbit plane.
- β > 0°: Sun is above the orbit plane (toward +Y side, i.e., the anti-orbit-normal direction).
- |β| ≥ β\*: Orbit is fully sunlit (no eclipse).

### 4.4 Wing Frame and Gimbal Conventions

Each solar array wing has two rotational degrees of freedom:

| Axis | Label | Rotates About | Physical Interpretation |
|------|-------|---------------|------------------------|
| Outer | `α_o` | Body +Z (VVLH nadir axis) | Yaw-like rotation in the spacecraft XY plane |
| Inner | `α_i` | Wing-local +X after outer rotation | Tilt / elevation relative to the orbital plane |

The **outer gimbal** is attached to the spacecraft body and rotates about the fixed body +Z axis.
The **inner gimbal** is carried by the outer gimbal and rotates about the +X axis of the wing's rotated frame (i.e., the wing-local X axis after the outer rotation has been applied).

This is an **intrinsic Z-then-X rotation sequence**: outer about body Z first, then inner about wing-local X.

### 4.5 Wing Zero-Angle Normals

At zero outer and zero inner angle, the wing panels face in the cross-track direction:

| Wing | Zero-angle normal `n₀` |
|------|------------------------|
| Right wing | `[0, +1, 0]` (faces in +Y / anti-orbit-normal direction) |
| Left wing  | `[0, −1, 0]` (faces in −Y / orbit-normal direction) |

The two wings are symmetric about the spacecraft XZ plane.

---

## 5. Orbit and Eclipse Calculations

**Sources:** `services/orbit.py`, `services/eclipse.py`, `services/constants.py`

### 5.1 Physical Constants

| Symbol | Value | Description |
|--------|-------|-------------|
| R_⊕ | 6 371.0 km | Earth mean radius |
| μ | 398 600.4418 km³/s² | Earth gravitational parameter (GM) |
| E_☉ | 1 361.0 W/m² | Solar irradiance (mean, fixed) |

### 5.2 Orbital Radius and Period

For a circular orbit at altitude `h`:

```
r = R_⊕ + h                     [km]

T = 2π √(r³ / μ)                [seconds]
```

The model assumes a **perfectly circular orbit**. Eccentricity, inclination, RAAN, and argument of perigee are not inputs. The only geometric inputs are altitude (determines r and T) and beta angle (determines sun geometry).

### 5.3 Eclipse Geometry — Cylindrical Shadow Model

The shadow is modelled as a **cylinder** (parallel rays from a sun at infinity, spherical Earth). Penumbra is ignored. The key quantity is the **Earth angular radius** as seen from the satellite:

```
ρ = arcsin(R_⊕ / r)             [radians or degrees]
```

This is the half-angle subtended by the Earth's disk as seen from the satellite. `ρ ≈ 66.7°` at 500 km altitude.

#### Critical Beta Angle

Eclipse only occurs when the orbit plane is close enough to the Sun–Earth line. The threshold is:

```
β* = 90° − ρ
```

- If `|β| ≥ β*`: orbit is fully sunlit, no eclipse.
- If `|β| < β*`: orbit experiences eclipse centred at θ = 180°.

At 500 km, `ρ ≈ 66.7°` so `β* ≈ 23.3°`.

#### Eclipse Half-Angle

When `|β| < β*`, the half-arc of the eclipse in the orbit plane is:

```
φ_e = arccos( cos(ρ) / cos(β) )      [degrees]
```

This is the half-width of the shadow arc measured as an orbit angle from θ = 180°. The satellite is in eclipse when:

```
|θ − 180°| ≤ φ_e
```

#### Eclipse Fraction and Duration

```
eclipse_fraction = φ_e / 180°         (fraction of one orbit in shadow)

eclipse_duration = eclipse_fraction × T   [seconds]
```

The factor 180° (not 360°) is correct: `φ_e` is a *half*-arc, so the full eclipse arc is `2φ_e` out of the full orbit circle `360°`, giving `2φ_e / 360° = φ_e / 180°`.

**Numerical safety:** Before computing `arccos`, the argument `cos(ρ) / cos(β)` is clamped to [−1, +1] to prevent floating-point errors near the boundary `|β| = β*`.

### 5.4 Eclipse Mask

The boolean eclipse mask for the discrete orbit-angle samples is computed in `sun_geometry.py → eclipse_mask()`:

```python
angle = np.mod(orbit_angle_deg, 360.0)
in_eclipse = np.abs(angle - 180.0) <= half_angle
```

> **Important:** The analytic `eclipse_fraction` value in the response is computed from the continuous formula above. The discrete `in_eclipse` mask used for power calculation is derived from the discrete orbit-angle samples. At low sample counts (< ~100 samples) these two representations of eclipse fraction may differ by a few percent.

---

## 6. Sun-Vector Calculations in VVLH

**Source:** `services/sun_geometry.py`

### 6.1 Sun Unit Vector Formula

Given orbit angle `θ` (from subsolar point) and beta angle `β`, the Sun unit vector in the VVLH body frame is:

```
S_x = −sin(θ) cos(β)
S_y = −sin(β)
S_z = −cos(θ) cos(β)
```

`S` is a unit vector: `|S|² = sin²(θ)cos²(β) + sin²(β) + cos²(θ)cos²(β) = cos²(β)(sin²θ + cos²θ) + sin²β = 1` ✓

**Derivation:** The sun direction is constant in inertial space. Projecting it onto the rotating VVLH frame:
- The component along the orbit normal (cross-track) is `−sin(β)`, independent of orbital position.
- The in-plane component rotates with the satellite: at θ = 0 (subsolar point), the sun is at zenith (`S_z = −cos(β)`); at θ = 90° it is at the horizon along −X.

#### Sign-Convention Sanity Checks

| θ | β | Expected | S = (S_x, S_y, S_z) | Check |
|---|---|----------|----------------------|-------|
| 0° | 0° | Sun at zenith (anti-nadir, −Z direction) | (0, 0, −1) | ✓ |
| 180° | 0° | Sun below (nadir direction, +Z) | (0, 0, +1) | ✓ eclipse zone |
| 0° | 90° | Sun along −Y | (0, −1, 0) | ✓ |
| 90° | 0° | Sun along −X | (−1, 0, 0) | ✓ |

### 6.2 Sun Azimuth and Elevation

Azimuth and elevation are derived from the VVLH sun vector in `sun_geometry.py → sun_angles_vvlh()`:

```
azimuth   = atan2(S_y, S_x)     [degrees, range −180° to +180°]
elevation = arcsin(S_z)          [degrees, range −90° to +90°]
```

> **Non-standard elevation convention:** In this code, positive elevation means the Sun is toward nadir (+Z). At the subsolar point (θ=0, β=0), elevation = −90° (Sun at zenith / anti-nadir). This is the **opposite** of the standard aerospace convention (elevation = 0° at horizon, +90° at zenith). This is inherent to using the VVLH +Z = nadir axis as the reference. The raw VVLH sun-vector components (`sun_vvlh_z`) plotted over the orbit show this convention directly.

---

## 7. Solar Wing Geometry and Kinematics

**Source:** `services/solar_array_geometry.py`

### 7.1 Wing Normal Formula

The panel normal vector after applying outer angle `α_o` and inner angle `α_i` is:

```
n = Rz(α_o) @ Rx(α_i) @ n₀
```

where `Rz` and `Rx` are standard right-hand-rule rotation matrices:

```
       ⎡ cos(α_o)  −sin(α_o)  0 ⎤
Rz =   ⎢ sin(α_o)   cos(α_o)  0 ⎥
       ⎣    0          0       1 ⎦

       ⎡ 1      0          0    ⎤
Rx =   ⎢ 0   cos(α_i)  −sin(α_i) ⎥
       ⎣ 0   sin(α_i)   cos(α_i) ⎦
```

This is an **intrinsic ZX rotation**: first rotate about body Z (outer), then rotate about the wing-local X axis that has been carried by the outer gimbal (inner). The matrix product `Rz @ Rx` applied right-to-left correctly implements this: Rx acts in the outer-rotated frame.

#### Expanded Form

For the **right wing** (`n₀ = [0, +1, 0]`):

```
n_right = [ −sin(α_o) cos(α_i),
             cos(α_o) cos(α_i),
             sin(α_i) ]
```

For the **left wing** (`n₀ = [0, −1, 0]`):

```
n_left  = [  sin(α_o) cos(α_i),
            −cos(α_o) cos(α_i),
            −sin(α_i) ]
```

These can be verified by substituting `α_o = 0, α_i = 0`, which recovers `n₀` for each wing.

### 7.2 Ideal Tracking Solution

Given a sun unit vector `S = (S_x, S_y, S_z)`, the ideal gimbal angles that achieve `n = S` are found analytically by inverting the above expressions.

**Right wing:**

```
α_i = arcsin(S_z)                          [from n_z = sin(α_i)]
α_o = atan2(−S_x, S_y)                     [from n_x = −sin(α_o)cos(α_i), n_y = cos(α_o)cos(α_i)]
```

**Left wing:**

```
α_i = arcsin(−S_z)                         [from n_z = −sin(α_i)]
α_o = atan2(S_x, −S_y)                     [from n_x = sin(α_o)cos(α_i), n_y = −cos(α_o)cos(α_i)]
```

The `atan2` form is preferred over `acos/asin` for `α_o` because it uses both components to determine the correct quadrant, giving an unambiguous result in [−π, +π].

**Numerical safety:** `S_z` is clipped to [−1, +1] before the `arcsin` call to prevent domain errors from floating-point rounding.

### 7.3 Gimbal Lock

When the sun vector is aligned with the body ±Z axis, `α_i = ±90°` and `cos(α_i) ≈ 0`. In this configuration the outer gimbal has no effect on the wing normal (the panel is perpendicular to the orbital plane regardless of outer angle), so `α_o` is indeterminate.

The code detects this when `|cos(α_i)| < 1×10⁻¹⁰` and sets `α_o = 0` as a consistent default. The wing normal still correctly equals S (verified by substitution: `n_z = sin(±90°) = ±1`).

### 7.4 Batch Computation

`compute_wing_arrays()` loops over all `N` orbit samples. For each sample it:

1. Normalises the sun vector (handles the degenerate zero-vector case by setting angles to 0 and `cos_eff = 0`).
2. Calls `solve_dual_axis_tracking()` for the ideal angles.
3. Calls `compute_wing_normal()` to reconstruct the normal from the angles (re-normalises numerically).
4. Computes incidence angle and cosine efficiency:

```
incidence_deg = arccos( clamp(dot(n, S_hat), −1, +1) )

cosine_efficiency = max(0, dot(n, S_hat))
```

Under ideal tracking, `dot(n, S_hat) = 1` exactly (by construction), so `incidence = 0°` and `cos_eff = 1.0` for all sunlit samples. The `max(0, …)` prevents back-side irradiance — only the front face of the panel generates power.

---

## 8. Incidence Angle and Solar Power Calculations

**Source:** `services/power.py`

### 8.1 Power Model

The electrical power generated by one wing at a given orbit sample is:

```
P_wing = E_☉ × A × η_cell × ε_deg × cos_eff × (1 if sunlit, 0 if eclipse)
```

| Symbol | Parameter | Default |
|--------|-----------|---------|
| E_☉ | Solar irradiance | 1 361 W/m² (fixed, mean value) |
| A | Panel area per wing | input [m²] |
| η_cell | Solar cell BOL efficiency | input [0–1] |
| ε_deg | End-of-life degradation factor | input [0–1] |
| cos_eff | `max(0, dot(n̂, Ŝ))` | computed per sample |

Total power:

```
P_total = P_left + P_right
```

Eclipse is enforced by multiplying by the `~in_eclipse` boolean array: eclipse samples have zero power regardless of pointing.

The `max(0, …)` on `cos_eff` ensures the back side of the panel contributes zero power. There is no partial shading or body-shadowing model.

### 8.2 Power Summary Statistics

`compute_power_summary()` returns:

- `average_total/left/right_power_w`: arithmetic mean over all `N` samples (includes eclipse zeros)
- `peak_total_power_w`: maximum instantaneous total power
- `min_total_power_w`: minimum (typically 0 during eclipse, or near-zero at high incidence)
- `percent_of_required_bus_power_avg`: `(avg_total / required_bus_power) × 100`
- `max/min_left/right_incidence_deg`: extremes of the incidence angle array

### 8.3 V3 Tracking-Loss Metrics

Three summary metrics in the V3 response characterise the loss relative to maximum achievable power.

```
max_possible = E_☉ × 2A × η_cell × ε_deg          [W, both wings, perfect pointing, no eclipse]
```

The **pointing-loss percentages** are computed over **sunlit samples only**, so eclipse unavailability does not contaminate the tracking quality metric:

```
sunlit_samples = samples where in_eclipse = False

ideal_pointing_loss_%   = (1 − avg_ideal_sunlit / max_possible) × 100
constrained_loss_%      = (1 − avg_achieved_sunlit / max_possible) × 100
```

For the ideal tracker `avg_ideal_sunlit = max_possible` (perfect cos_eff = 1.0), so `ideal_pointing_loss_%` is always ≈ 0%. The eclipse effect is already captured by `eclipse_fraction` in the response.

The **energy ratio** compares achieved vs ideal over the full orbit (including eclipse), so eclipse cancels:

```
energy_ratio = avg_achieved_total / avg_ideal_total
```

This ratio being < 1 directly indicates the fraction of ideal energy that the constrained system achieves. It is independent of eclipse.

---

## 9. Constraint Handling (Version 3)

**Source:** `services/constraints.py`

The three constraint types are applied in order at each time step. They operate in **(outer_deg, inner_deg) angle space** — a 2D space where axis values are gimbal angles in degrees.

### 9.1 Angle Limits

Each gimbal axis has an independent min/max hard stop. The limit is applied by simple clipping:

```
achieved_angle = clamp(commanded_angle, min_deg, max_deg)

was_limited = (commanded_angle < min_deg) or (commanded_angle > max_deg)
```

**Source:** `apply_angle_limits()` — returns `(clipped_angle, was_clipped)`.

Default limits: outer ±180°, inner ±90° (effectively unconstrained for most orbits).

Points exactly at the boundary (e.g., `angle == max_deg`) are not clipped; `was_limited = False`.

### 9.2 Rate Limits

Between successive time samples, each gimbal axis is limited to a maximum angular velocity:

```
max_delta = rate_limit_deg_per_s × dt_s

delta = commanded − previous_achieved

if |delta| ≤ max_delta:
    achieved = commanded                    (not rate-limited)
else:
    achieved = previous_achieved + sign(delta) × max_delta   (rate-limited)
```

**Source:** `apply_rate_limit()` — returns `(achieved_angle, was_rate_limited)`.

The time step `dt_s = T / num_samples_per_orbit` is exact (computed from the orbital period, not a fixed 1-second step).

**Initial condition:** At the first orbit sample (i = 0), there is no prior achieved state. The rate limit is not applied; the achieved angle equals the command after keep-out and angle-limit processing.

### 9.3 Keep-Out Zones

A keep-out zone is a **rectangular forbidden region** in (outer_deg, inner_deg) angle space:

```
Zone = { outer_min ≤ α_o ≤ outer_max }  ×  { inner_min ≤ α_i ≤ inner_max }
```

Multiple zones can be defined per wing. Zones are checked independently per wing (a right-wing zone does not constrain the left wing).

Detection uses inclusive inequalities: a point exactly on the boundary is considered inside.

**Source:** `is_in_keepout_zone()` — returns `True` if inside or on the boundary.

#### Keep-Out Resolution Strategy

When the commanded angle pair (after ideal tracking) falls inside a zone, the code resolves the violation by projecting to the nearest boundary point of the zone in Euclidean angle-space distance:

1. For each zone the ideal point is inside, generate four candidate escape points — one on each edge of the rectangle — by clamping the off-axis coordinate and placing the on-axis coordinate just outside the boundary (`boundary ± 1×10⁻⁶°`).
2. Clip each candidate to the axis limits.
3. Discard any candidate that falls inside any other keep-out zone.
4. Select the candidate with minimum Euclidean distance from the ideal point.
5. If no valid candidate exists (all candidates rejected — e.g., overlapping zones fill the entire allowed angle space), fall back to clipping the ideal point to axis limits. The returned label is prefixed with `"UNRESOLVED:"` to signal this condition.

**Source:** `_project_to_rect_boundary()`, `resolve_keepout_violation()`.

> **Approximation:** This is a first-order nearest-boundary projection, not a globally optimal solve. It does not jointly account for rate limits during resolution. In particular, after rate limiting is applied to the resolved command, the achieved angle can still be inside a keep-out zone if the rate limit prevents the gimbal from reaching the resolved boundary. The tracking loop detects this by checking the achieved angle (not the commanded angle) against keep-out zones after rate limiting.

> **Keep-out zone semantics:** Keep-out zones are defined in the gimbal angle space (outer_deg, inner_deg), not in physical pointing space. The same angular position corresponds to different sky directions at different orbit angles, so a keep-out zone defined around outer=0°, inner=0° excludes all times when the gimbal tries to be at those angles regardless of where the sun is.

---

## 10. Per-Sample Simulation Flow

**Source:** `services/tracking.py → compute_constrained_tracking()`

The following sequence is executed for each of the `N` orbit-angle samples, independently for each wing:

```
Step 1 — Set commanded angles from ideal tracking
  cmd_outer = ideal_outer_deg[i]
  cmd_inner = ideal_inner_deg[i]

Step 2 — Resolve keep-out zone violations
  (cmd_outer, cmd_inner) ← resolve_keepout_violation(...)
  kz_label = zone label if violated

Step 3 — Apply angle limits
  cmd_outer  ← clamp(cmd_outer,  outer_min, outer_max)
  cmd_inner  ← clamp(cmd_inner,  inner_min, inner_max)
  was_outer_limited, was_inner_limited = flags

Step 4 — Apply rate limits from previous achieved state
  if i == 0:
    ach_outer = cmd_outer          ← no rate constraint at first sample
    ach_inner = cmd_inner
  else:
    ach_outer ← rate_limit(achieved_outer[i-1], cmd_outer, rate, dt)
    ach_inner ← rate_limit(achieved_inner[i-1], cmd_inner, rate, dt)
  was_outer_rl, was_inner_rl = flags

Step 4b — Post-rate-limit keep-out validation
  Check (ach_outer, ach_inner) against all zones.
  in_keepout[i] = whether the ACHIEVED angle is in a keep-out zone.
  (A tight rate limit can prevent reaching the resolved boundary,
   causing the achieved angle to be in a keep-out zone even if the
   command was resolved to be outside it.)

Step 5 — Compute achieved wing normal and incidence
  n_vec = Rz(ach_outer) @ Rx(ach_inner) @ n0
  if in_eclipse[i] or |sun_vec| ≈ 0:
    incidence = 90°,  cos_eff = 0.0
  else:
    incidence = arccos(dot(n_vec, sun_hat))
    cos_eff   = max(0, dot(n_vec, sun_hat))

Output per sample:
  achieved_outer[i], achieved_inner[i]
  achieved_incidence[i], achieved_cos_eff[i]
  outer_angle_limited[i], inner_angle_limited[i]
  outer_rate_limited[i], inner_rate_limited[i]
  in_keepout[i], keepout_label[i]
```

**Key distinction — `in_keepout` semantics:** The flag `in_keepout[i]` reflects whether the **achieved angle** is inside a keep-out zone at that sample, not whether the ideal command was. This is the post-rate-limit check. If the ideal was inside a zone but the achieved was successfully moved outside (rate limits were not binding), `in_keepout[i] = False`.

---

## 11. Input / Output Data Model Overview

**Source:** `app/models.py`

### 11.1 V3 Request Fields

```
Orbit parameters
  altitude_km                    [km, > 0]
  beta_deg                       [deg, −90 to +90]
  num_samples_per_orbit          [integer, 10–3600]

Solar array parameters
  solar_array_area_m2_per_wing   [m², > 0]
  solar_cell_efficiency          [0–1, BOL efficiency]
  degradation_factor             [0–1, EOL degradation]
  required_bus_power_w           [W, > 0]

Angle limits — four pairs, one per axis per wing
  right_outer_min/max_deg        [deg, min < max enforced by validator]
  right_inner_min/max_deg        [deg, min < max enforced by validator]
  left_outer_min/max_deg         [deg, min < max enforced by validator]
  left_inner_min/max_deg         [deg, min < max enforced by validator]

Rate limits — shared by both wings
  outer_rate_limit_deg_per_s     [deg/s, > 0]
  inner_rate_limit_deg_per_s     [deg/s, > 0]

Keep-out zones
  keepout_zones: list of KeepOutZone
    wing                         "left" | "right"
    outer_min/max_deg            [deg, min < max enforced by validator]
    inner_min/max_deg            [deg, min < max enforced by validator]
    label                        string (optional, used in constraint flags)
```

### 11.2 V3 Response Fields

The V3 response contains three groups of outputs.

#### V1 scalar fields (orbit and eclipse)
`orbit_radius_km`, `orbital_period_s/min`, `eclipse_duration_s/min`, `eclipse_fraction`, `sunlight_fraction`, `critical_beta_deg_for_no_eclipse`

#### V1 array fields (sampled over orbit, length = num_samples_per_orbit)
`orbit_angle_deg`, `sun_vvlh_x/y/z`, `sun_az_deg`, `sun_el_deg`, `in_eclipse`

#### V3 per-wing ideal arrays (length N, both wings)
```
right_ideal_outer_angle_deg      Ideal outer gimbal angle [deg]
right_ideal_inner_angle_deg      Ideal inner gimbal angle [deg]
right_ideal_incidence_deg        Incidence angle under ideal tracking [deg]
right_ideal_power_w              Ideal power [W]
(same for left wing)
```

#### V3 per-wing achieved arrays (length N, both wings)
```
right_achieved_outer_angle_deg   Achieved outer angle after all constraints [deg]
right_achieved_inner_angle_deg   Achieved inner angle after all constraints [deg]
right_achieved_incidence_deg     Incidence angle under achieved pointing [deg]
right_achieved_power_w           Achieved power [W]
right_outer_angle_limited        Boolean: outer axis at hard stop
right_inner_angle_limited        Boolean: inner axis at hard stop
right_outer_rate_limited         Boolean: outer axis rate-limited this step
right_inner_rate_limited         Boolean: inner axis rate-limited this step
right_in_keepout                 Boolean: achieved angle inside a keep-out zone
right_keepout_label              String: label of the violated zone (or "")
(same for left wing)
```

#### V3 total power arrays
`ideal_total_power_w`, `achieved_total_power_w` (both length N)

#### V3 summary scalars
```
average_ideal_total_power_w          Orbit-average ideal total power [W]
average_achieved_total_power_w       Orbit-average achieved total power [W]
average_ideal_left/right_power_w     Per-wing orbit averages [W]
peak_ideal_total_power_w             Peak ideal power over orbit [W]
min_ideal_total_power_w              Minimum ideal power (0 during eclipse) [W]
percent_of_required_bus_power_ideal/achieved_avg   % of bus power requirement
ideal_tracking_loss_percent          Sunlit-only loss vs max possible [%]
constrained_tracking_loss_percent    Sunlit-only loss vs max possible [%]
achieved_vs_ideal_energy_ratio       avg_achieved / avg_ideal [0–1]
max/min_left/right_incidence_deg     Ideal incidence angle extremes [deg]
right/left_fraction_outer/inner_angle_limited   Fraction of orbit at hard stop
right/left_fraction_outer/inner_rate_limited    Fraction of orbit rate-limited
right/left_fraction_in_keepout                  Fraction of orbit in keep-out
```

---

## 12. Assumptions and Limitations

### Orbital Mechanics

| Assumption | Impact |
|------------|--------|
| **Spherical Earth** (no J2, no oblateness) | Period and eclipse geometry are slightly off for real orbits (~0.1–1%) |
| **Circular orbit** (zero eccentricity) | Altitude is constant; no variation in solar irradiance with orbital position |
| **Beta angle is a direct input** | Not derived from inclination, RAAN, epoch, or date |
| **Sun at infinity** (parallel rays) | Cylindrical shadow — no penumbra modelled |
| **No atmospheric refraction** | Eclipse entry/exit is instantaneous (geometric) |
| **Fixed solar constant** (1 361 W/m²) | No seasonal variation (actual range ±3.5% over the year) |
| **One orbit per run** | No multi-orbit state (cable wrap, battery state, thermal history) |

### Spacecraft and Array Model

| Assumption | Impact |
|------------|--------|
| **Body frame = VVLH** (no attitude offset) | Nadir-pointing only; no slew, yaw steering, or off-pointing modes |
| **Front-side power only** | Back-side irradiance contributes zero |
| **No body shadowing** | Array is never blocked by the spacecraft bus |
| **No thermal effects** | Cell efficiency does not vary with temperature |
| **No structural flexibility** | Rigid panel, no vibration modes |
| **No motor dynamics** | Rate limit is a geometric constraint, not a torque/inertia model |
| **BOL efficiency × degradation = EOL factor** | Single combined factor; no per-cell variation, no radiation damage model |

### Version 3 Constraint Model

| Assumption | Impact |
|------------|--------|
| **Keep-out zones are rectangular in angle space** | Arbitrary shapes not supported |
| **Nearest-boundary resolution** | Not globally optimal; may not find the best escape direction |
| **Rate limits applied after keep-out resolution** | The two constraints are not jointly optimised |
| **Rate limits are shared between wings** | Left and right actuators cannot have independent rates |
| **No cable-wrap accumulation** | Angle limits enforce per-step range only; no tracking of total wrap angle |
| **Initial achieved state = first resolved command** | No assumed pre-existing gimbal position before orbit start |
| **Overlapping keep-out zones** | If zones fill the entire allowed space, fallback clips to axis limits (with UNRESOLVED label) |

---

## 13. Mapping of Backend Files to Responsibilities

| File | Primary Responsibility | Key Functions / Classes |
|------|----------------------|------------------------|
| `constants.py` | Physical constants | `R_EARTH_KM`, `MU_EARTH_KM3_S2`, `SOLAR_CONSTANT_W_M2` |
| `orbit.py` | Kepler orbital mechanics | `orbit_radius_km()`, `orbital_period_s()` |
| `eclipse.py` | Cylindrical shadow geometry | `earth_angular_radius_deg()`, `critical_beta_deg()`, `has_eclipse()`, `eclipse_half_angle_deg()`, `eclipse_fraction()`, `eclipse_duration_s()` |
| `sun_geometry.py` | Sun vector in VVLH; azimuth/elevation; eclipse mask | `sun_vector_vvlh()`, `sun_angles_vvlh()`, `eclipse_mask()` |
| `solar_array_geometry.py` | Rotation matrices; wing normal formula; ideal tracking solver; batch computation | `rotation_matrix_x/z()`, `compute_wing_normal()`, `solve_dual_axis_tracking()`, `compute_wing_arrays()`, `N0_RIGHT`, `N0_LEFT` |
| `power.py` | Per-wing electrical power; summary statistics | `compute_wing_power()`, `compute_power_summary()` |
| `constraints.py` | Angle limits; rate limits; keep-out detection and resolution | `apply_angle_limits()`, `apply_rate_limit()`, `is_in_keepout_zone()`, `find_keepout_violation()`, `resolve_keepout_violation()`, `AxisLimits` |
| `tracking.py` | V3 per-sample constrained tracking loop | `compute_constrained_tracking()` |
| `routers/analysis.py` | HTTP endpoints; orchestration of services | `analyze_v1/v2/v3()`, `_compute_v1_base()` |
| `models.py` | Pydantic request/response schemas; input validation | `AnalysisRequest/V2/V3`, `AnalysisResponse/V2/V3`, `KeepOutZone` |

---

## 14. Future Improvements

The following extensions are identified as the most valuable next steps, roughly in order of engineering impact.

### 14.1 Orbital Mechanics Extensions

- **Beta angle from orbital elements:** Derive β from inclination, RAAN, and epoch using the Sun's declination and right ascension. Add J2 secular RAAN drift to model long-term beta evolution over mission life.
- **Eccentric orbits:** Replace the circular orbit assumption with a Keplerian ellipse. Altitude variation affects eclipse geometry and solar irradiance.
- **Seasonal sun model:** Replace the fixed Sun direction with one computed from day-of-year, giving realistic seasonal variation in both β and irradiance.

### 14.2 Constraint Model Extensions

- **Cable-wrap accumulation:** Track the cumulative wrap angle of each gimbal rather than only the instantaneous angle. Enforce a total wrap limit (e.g., ±540°) and schedule unwinding manoeuvres.
- **Per-wing rate limits:** Allow independent rate limits for left and right wings to model different drive units or age-dependent performance.
- **Joint keep-out / rate-limit optimisation:** Replace nearest-boundary projection with a constrained optimiser (e.g., `scipy.optimize.minimize`) that accounts for both the keep-out boundary and the reachable set given rate limits in one step.
- **Non-rectangular keep-out zones:** Support arbitrary convex polygons in angle space, or keep-out zones defined in pointing (azimuth/elevation) space rather than gimbal angle space.

### 14.3 Power Model Extensions

- **Body shadowing:** Ray-cast the sun direction against a simplified spacecraft bus geometry to determine which parts of the array are blocked. This is particularly important for high-beta orbits where the bus shadow sweeps across the panel.
- **Back-side power generation:** If bifacial cells are used, add a back-side contribution (typically 10–20% of front-side).
- **Temperature-dependent efficiency:** Cell efficiency decreases at high temperatures and increases in cold eclipse recovery. A thermal model (even a simple lumped-parameter one) would give more realistic power budgets.
- **Battery and depth-of-discharge:** Extend the model to track energy flow (generation vs. load), state of charge, and depth-of-discharge over multiple orbits.

### 14.4 Architecture Extensions

- **Multi-orbit simulation:** Propagate gimbal state (achieved angles, cable wrap) across multiple orbits to study long-term trends, seasonal effects, and β evolution.
- **Vectorised `compute_wing_arrays()`:** Replace the Python loop with fully vectorised NumPy operations using the analytical formulas (see section 7.1). This will improve performance at high sample counts (N = 3 600).
- **Export functionality:** Add CSV / JSON / HDF5 download endpoints so engineers can post-process results in external tools.
- **3D visualisation:** Add a WebGL or Three.js view showing the spacecraft, orbit geometry, eclipse cone, and solar panel orientation as the orbit angle is swept.
