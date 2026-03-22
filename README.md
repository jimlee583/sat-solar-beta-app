# sat-solar-beta-app

Satellite solar environment analysis tool for circular low-Earth orbits with
dual-wing solar array geometry and power generation model.

---

## Version History

### Version 1 — Orbit & Eclipse
Orbital period, eclipse geometry, Sun-vector analysis using altitude and beta
angle.

### Version 2 — Dual-Wing Solar Array & Power  *(current)*
Adds two symmetrically-mounted solar array wings with ideal dual-axis Sun
tracking, incidence angle computation, and per-wing / total power generation.

---

## What Version 2 Computes

| Output | Description |
|---|---|
| Orbital period | Keplerian period for a circular orbit |
| Eclipse duration & fraction | Time and fraction of orbit in Earth's shadow |
| Critical beta angle (β*) | Beta above which no eclipse occurs |
| Sun vector (VVLH) | Unit Sun direction in body/VVLH over one orbit |
| Sun azimuth & elevation | Angular Sun direction in VVLH |
| Eclipse mask | Boolean sunlit vs. eclipse at each sample |
| Gimbal angles | Outer (Z-axis) and inner (X-axis) per wing |
| Wing normals | Panel normal vector components in body frame |
| Incidence angle | Angle between wing normal and Sun vector |
| Cosine efficiency | max(0, dot(n̂, ŝ)) |
| Power per wing | P = 1361 × area × η_cell × degradation × cos_eff |
| Total power | Sum of left and right wing power |
| Summary statistics | Averages, peaks, min, % of required bus power |

Six interactive Plotly charts are displayed:
1. Solar array power (left, right, total) vs. orbit angle
2. Gimbal angles (outer/inner for each wing) vs. orbit angle
3. Incidence angle (left, right) vs. orbit angle
4. Sun azimuth & elevation vs. orbit angle
5. Sun VVLH components vs. orbit angle
6. Eclipse state vs. orbit angle

---

## Spacecraft & Array Geometry

### VVLH Frame Convention

The spacecraft body frame is aligned with VVLH:

| Axis | Direction |
|---|---|
| **+X** | Velocity (in the local horizontal plane) |
| **+Y** | Completes right-handed triad (Y = Z × X ≈ −orbit normal) |
| **+Z** | Nadir (toward Earth center) |

### Wing Mounting

Two solar array wings are mounted symmetrically on the spacecraft body:

| Wing | Mount Side | Zero-Angle Normal |
|---|---|---|
| Right | +Y side | n₀ = [0, +1, 0] |
| Left  | −Y side | n₀ = [0, −1, 0] |

### Gimbal Axes (per wing)

Each wing has two degrees of freedom:

| Axis | Rotation About | Interpretation |
|---|---|---|
| **Outer** | Body +Z | Yaw-like rotation in the XY plane |
| **Inner** | Wing-local +X | Tilt/elevation after outer rotation |

### Wing Normal Formula

The panel normal after articulation:

```
n = Rz(outer_angle) × Rx(inner_angle) × n₀
```

Expanded for each wing:

```
Right wing:  n = [-sin(α_o)cos(α_i),  cos(α_o)cos(α_i),  sin(α_i)]
Left  wing:  n = [ sin(α_o)cos(α_i), -cos(α_o)cos(α_i), -sin(α_i)]
```

### Ideal Tracking Solution

Given Sun unit vector s = [sx, sy, sz] in body/VVLH:

```
Right wing:   α_inner = arcsin(sz)       α_outer = atan2(-sx, sy)
Left  wing:   α_inner = arcsin(-sz)      α_outer = atan2(sx, -sy)
```

When |cos(α_inner)| ≈ 0 (Sun along ±Z), α_outer is set to 0 (gimbal lock).

---

## Key Formulas

### Orbital Period

```
T = 2π √(r³ / μ)       r = R_earth + altitude
```

### Earth Angular Radius

```
ρ = arcsin(R_earth / r)
```

### Critical Beta Angle

```
β* = 90° − ρ
```

### Eclipse Half-Angle

```
φ_eclipse = arccos( cos(ρ) / cos(β) )
eclipse_fraction = φ_eclipse / 180°
```

### Sun Unit Vector in VVLH

θ = orbit angle from subsolar point (0° = Sun at zenith).

```
S_x = −sin(θ) cos(β)
S_y = −sin(β)
S_z = −cos(θ) cos(β)
```

### Solar Power (per wing)

```
P_wing = 1361 [W/m²] × area [m²] × η_cell × degradation × cos_eff
```

Where `cos_eff = max(0, dot(n̂, ŝ))`.  During eclipse: `P_wing = 0`.

```
P_total = P_left + P_right
```

---

## Assumptions (Version 2)

- **Spherical Earth** — radius 6 371 km, no oblateness (J2 = 0).
- **Circular orbit** — altitude is constant; no eccentricity.
- **Sun at infinity** — parallel illumination; cylindrical shadow (umbra only).
- **Beta angle is a direct input** — not derived from inclination/RAAN/epoch.
- **No attitude offsets** — spacecraft body frame is aligned with VVLH.
- **Ideal articulation** — no gimbal angle limits, rate limits, or cable-wrap constraints.
- **Front-side power only** — back side of panel contributes zero.
- **No body shadowing** — no blockage of array by spacecraft bus.
- **No keep-out zones** — gimbals can reach any orientation.
- **Solar constant** — 1361 W/m² (fixed, no seasonal variation).

---

## Project Structure

```
sat-solar-beta-app/
├── README.md
├── .gitignore
├── backend/
│   ├── pyproject.toml
│   ├── .python-version
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                          # FastAPI app entry point
│   │   ├── models.py                        # Pydantic V1 + V2 models
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── analysis.py                  # POST /api/analyze/v1 and /v2
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── constants.py                 # Physical constants
│   │       ├── orbit.py                     # Circular orbit mechanics
│   │       ├── eclipse.py                   # Eclipse geometry
│   │       ├── sun_geometry.py              # Sun vector & angles in VVLH
│   │       ├── solar_array_geometry.py      # Wing normals & tracking (V2)
│   │       └── power.py                     # Power generation model (V2)
│   └── tests/
│       ├── __init__.py
│       ├── test_orbit.py
│       ├── test_eclipse.py
│       ├── test_sun_geometry.py
│       ├── test_solar_array_geometry.py     # V2 geometry tests
│       ├── test_power.py                    # V2 power tests
│       └── test_analysis_v2.py              # V2 endpoint smoke tests
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── vite-env.d.ts
        ├── api/
        │   └── analysis.ts
        ├── components/
        │   ├── InputPanel.tsx
        │   ├── SummaryCards.tsx
        │   └── PlotSection.tsx
        └── types/
            └── analysis.ts
```

---

## Running Locally

### Backend

Requires [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

### Backend Tests

```bash
cd backend
uv run pytest
```

### Frontend

Requires Node.js ≥ 18.

```bash
cd frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:5173` and proxies `/api` requests
to the backend.

---

## API

### `POST /api/analyze/v1`  (backward compatible)

Version 1 orbit-only analysis. Request/response unchanged from V1.

### `POST /api/analyze/v2`

**Request body** (all fields have defaults):

```json
{
  "altitude_km": 500,
  "beta_deg": 0,
  "num_samples_per_orbit": 360,
  "solar_array_area_m2_per_wing": 5.0,
  "solar_cell_efficiency": 0.30,
  "degradation_factor": 0.85,
  "required_bus_power_w": 3000
}
```

**Response** includes all V1 fields plus:
- Per-wing sampled arrays: gimbal angles, normals, incidence, cosine efficiency, power
- Total power array
- Summary scalars: averages, peak, min, % bus power, incidence extremes

See `backend/app/models.py` for the full typed schema.

---

## Future Roadmap

### Version 3 — Constrained Articulation
- Hard gimbal angle limits (inner/outer bounds)
- Gimbal rate limits and rate-limited tracking
- Keep-out zones (e.g., avoid pointing arrays at Earth or thrusters)
- Body shadowing of the solar array by the spacecraft bus
- Cable-wrap constraints
- More realistic articulation profiles

### Version 4 — Advanced Models
- Seasonal Sun model (Sun declination as a function of day-of-year)
- Beta angle derived from inclination, RAAN, and epoch
- J2 secular RAAN drift
- Multi-panel / multi-wing configurations
- Battery depth-of-discharge estimation
- Export results to CSV / JSON
