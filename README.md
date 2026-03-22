# sat-solar-beta-app

Satellite solar environment analysis tool for circular low-Earth orbits.
Version 1 focuses on orbital period, eclipse geometry, and Sun-vector analysis
using altitude and beta angle as primary inputs.

---

## What Version 1 Does

Given an orbital **altitude** and a **beta angle**, the tool computes:

| Output | Description |
|---|---|
| Orbital period | Keplerian period for a circular orbit |
| Eclipse duration & fraction | Time and fraction of orbit spent in Earth's shadow |
| Critical beta angle (β*) | Beta above which the orbit is fully sunlit |
| Sun vector (VVLH) | Unit Sun direction in the body-fixed VVLH frame sampled over one orbit |
| Sun azimuth & elevation | Angular representation of the Sun direction in VVLH |
| Eclipse mask | Boolean trace indicating sunlit vs. eclipse at each sample point |

Three interactive Plotly charts are displayed in the frontend:
1. Sun azimuth & elevation vs. orbit angle
2. Sun VVLH vector components vs. orbit angle
3. Eclipse state vs. orbit angle

---

## Assumptions (Version 1)

- **Spherical Earth** — radius 6 371 km, no oblateness (J2 = 0).
- **Circular orbit** — altitude is constant; no eccentricity.
- **Sun at infinity** — parallel illumination; cylindrical shadow (umbra only).
- **Beta angle is a direct input** — not derived from inclination, RAAN, or epoch.
- **No attitude offsets** — spacecraft body frame is aligned with VVLH.
- **No solar array model** — no gimbal, no power generation, no body shadowing.

---

## VVLH Frame Convention

| Axis | Direction |
|---|---|
| **+X** | Velocity (in the local horizontal plane) |
| **+Y** | Completes right-handed triad (Y = Z × X ≈ −orbit normal) |
| **+Z** | Nadir (toward Earth center) |

Mapping to orbital basis vectors:

```
VVLH +X  =  e_velocity
VVLH +Y  = −e_orbit_normal
VVLH +Z  = −e_radial_outward   (= nadir)
```

---

## Key Formulas

### Orbital period

```
T = 2π √(r³ / μ)
r = R_earth + altitude
```

### Earth angular radius (from satellite)

```
ρ = arcsin(R_earth / r)
```

### Critical beta angle

```
β* = 90° − ρ
```

Eclipse exists only when |β| < β*.

### Eclipse half-angle (in the orbit plane)

```
φ_eclipse = arccos( cos(ρ) / cos(β) )

eclipse_fraction = φ_eclipse / 180°
```

### Sun unit vector in VVLH

θ = orbit angle measured from the subsolar point (0° = Sun at zenith).

```
S_x = −sin(θ) cos(β)
S_y = −sin(β)
S_z = −cos(θ) cos(β)
```

### Sun angles

```
azimuth   = atan2(S_y, S_x)
elevation = arcsin(S_z)
```

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
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── models.py            # Pydantic request/response models
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── analysis.py      # POST /api/analyze/v1
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── constants.py     # Physical constants
│   │       ├── orbit.py         # Circular orbit mechanics
│   │       ├── eclipse.py       # Eclipse geometry
│   │       └── sun_geometry.py  # Sun vector & angles in VVLH
│   └── tests/
│       ├── __init__.py
│       ├── test_orbit.py
│       ├── test_eclipse.py
│       └── test_sun_geometry.py
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
to the backend at `http://localhost:8000`.

---

## API

### `POST /api/analyze/v1`

**Request body** (all fields have defaults):

```json
{
  "altitude_km": 500,
  "beta_deg": 0,
  "num_samples_per_orbit": 360
}
```

**Response** includes scalar metrics and sampled arrays over one orbit.
See `backend/app/models.py` for the full schema.

---

## Future Roadmap

### Version 2 — Solar Array Geometry
- Single-wing solar array with one-axis gimbal (Sun-tracking)
- Projected area and cosine-loss calculation
- Gimbal angle profile over one orbit
- Gimbal rate computation and rate-limit checks

### Version 3 — Power Generation
- Solar cell efficiency and array area inputs
- Instantaneous and orbit-average power
- Power during sunlight vs. eclipse duty cycle
- Battery depth-of-discharge estimation

### Version 4 — Advanced Models
- Seasonal Sun model (Sun declination as a function of day-of-year)
- Beta angle derived from inclination, RAAN, and epoch
- J2 secular RAAN drift
- Body-shadowing of the solar array
- Multi-panel / multi-wing configurations
- Export results to CSV / JSON
