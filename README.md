# sat-solar-beta-app

Satellite solar environment analysis tool for circular low-Earth orbits with
dual-wing solar array geometry, constrained articulation tracking, and power
generation model.

---

## Version History

### Version 1 — Orbit & Eclipse
Orbital period, eclipse geometry, Sun-vector analysis using altitude and beta
angle.

### Version 2 — Dual-Wing Solar Array & Power
Adds two symmetrically-mounted solar array wings with ideal dual-axis Sun
tracking, incidence angle computation, and per-wing / total power generation.

### Version 3 — Constrained Articulation *(current)*
Extends Version 2 with realistic first-order articulation constraints:
- Per-axis angle limits
- Gimbal rate limits
- Keep-out zones

Compares ideal (unconstrained) tracking against constrained achievable tracking.

---

## What Version 3 Adds Beyond Version 2

| Feature | Description |
|---|---|
| Angle limits | Per-axis min/max bounds for outer and inner gimbals on each wing |
| Rate limits | Maximum angular velocity (deg/s) for each gimbal axis |
| Keep-out zones | Rectangular forbidden regions in (outer, inner) angle space per wing |
| Constrained tracking | Sequential propagation of achieved angles respecting all constraints |
| Ideal vs achieved comparison | Both ideal and constrained outputs preserved for direct comparison |
| Constraint event tracking | Per-sample boolean flags for angle-limited, rate-limited, and keep-out |
| Summary metrics | Energy ratio, constraint activity fractions, tracking loss percentages |

---

## What Version 3 Computes

| Output | Description |
|---|---|
| All V1/V2 outputs | Preserved unchanged (orbit, eclipse, ideal tracking, ideal power) |
| Achieved gimbal angles | Outer/inner angles after applying all constraints |
| Achieved incidence angle | Angle between achieved wing normal and Sun vector |
| Achieved power per wing | Power with constrained pointing |
| Ideal vs achieved total power | Both arrays for direct comparison |
| Constraint flags | Per-sample: angle-limited, rate-limited, in keep-out |
| Energy ratio | achieved_avg / ideal_avg over one orbit |
| Tracking loss | % loss from maximum possible power (ideal and constrained) |
| Constraint fractions | % of orbit each constraint is active |

Ten interactive Plotly charts are displayed:
1. Ideal vs achieved total power vs orbit angle
2. Per-wing power (ideal vs achieved) vs orbit angle
3. Right wing gimbal angles (ideal vs achieved) vs orbit angle
4. Left wing gimbal angles (ideal vs achieved) vs orbit angle
5. Incidence angles (ideal vs achieved) vs orbit angle
6. Right wing constraint events vs orbit angle
7. Left wing constraint events vs orbit angle
8. Sun azimuth & elevation vs orbit angle
9. Sun VVLH components vs orbit angle
10. Eclipse state vs orbit angle

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

## Version 3 Constraint Models

### Angle Limit Model

Each gimbal axis has independent min/max bounds:
```
achieved_angle = clamp(commanded_angle, min_deg, max_deg)
```

Defaults: outer ±180°, inner ±90°. Left and right wings can have
independent limits.

### Rate Limit Model

Gimbal angular rate is limited between successive time samples:
```
max_delta = rate_limit_deg_per_s × dt_s
achieved = prev + clamp(commanded - prev, -max_delta, +max_delta)
```

Where `dt_s = orbital_period / num_samples_per_orbit`.

Default rate limit: 1.0 deg/s for both axes.

### Keep-Out Zone Model

Each keep-out zone is a rectangular forbidden region in (outer_deg, inner_deg)
angle space:

```
Zone = { outer_min..outer_max } × { inner_min..inner_max }
```

Multiple zones can be defined per wing. A point is "in keep-out" if it lies
within the closed rectangle (inclusive boundaries).

### Keep-Out Resolution Strategy (Version 3 Approximation)

When the ideal angle pair falls inside a keep-out zone:
1. Project to each of the four boundary edges of the rectangle
2. Apply a small nudge (1e-6 deg) so the candidate lies strictly outside
3. Clip each candidate to angle limits
4. Discard any candidate that still falls inside any keep-out zone
5. Select the nearest candidate by Euclidean distance in angle space

If no valid candidate is found (e.g., overlapping zones fill the allowed space),
the ideal angles are clipped to angle limits as a fallback.

**This is a first-order approximation.** It does not guarantee globally optimal
pointing recovery, and it does not account for rate-limit interactions during
resolution.

### Constrained Tracking Pipeline

At each orbit sample, for each wing:
1. Compute ideal angles from V2 tracking solution
2. Resolve keep-out zone violations
3. Apply angle limits
4. Apply rate limits from previous achieved state
5. Compute achieved wing normal
6. Compute achieved incidence angle and cosine efficiency
7. Compute achieved power (zero during eclipse)

Initial condition: the first achieved angles are set equal to the first
resolved/clipped commanded angles (no rate limiting at t=0).

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

### Sun Azimuth and Elevation (VVLH convention)

```
azimuth   = atan2(S_y, S_x)   [deg]
elevation = arcsin(S_z)        [deg]
```

**Note:** Elevation uses the VVLH +Z (nadir) axis as reference. Positive
elevation means the Sun is toward nadir (+Z). This is the opposite of the
standard aerospace convention where elevation = 0° at the horizon and +90°
at zenith. At the subsolar point (θ=0, β=0), elevation = −90° (Sun at
anti-nadir/zenith in VVLH).

### Solar Power (per wing)

```
P_wing = 1361 [W/m²] × area [m²] × η_cell × degradation × cos_eff
```

Where `cos_eff = max(0, dot(n̂, ŝ))`.  During eclipse: `P_wing = 0`.

```
P_total = P_left + P_right
```

### Tracking Loss (Version 3)

```
max_possible_power = 1361 × 2 × area × η_cell × degradation
ideal_loss_% = (1 − avg_ideal / max_possible) × 100
constrained_loss_% = (1 − avg_achieved / max_possible) × 100
energy_ratio = avg_achieved / avg_ideal
```

---

## Assumptions and Limitations

### Carried from Version 2
- **Spherical Earth** — radius 6 371 km, no oblateness (J2 = 0).
- **Circular orbit** — altitude is constant; no eccentricity.
- **Sun at infinity** — parallel illumination; cylindrical shadow (umbra only).
- **Beta angle is a direct input** — not derived from inclination/RAAN/epoch.
- **No attitude offsets** — spacecraft body frame is aligned with VVLH.
- **Front-side power only** — back side of panel contributes zero.
- **No body shadowing** — no blockage of array by spacecraft bus.
- **Solar constant** — 1361 W/m² (fixed, no seasonal variation).

### Version 3 Limitations
- Keep-out resolution uses nearest-boundary projection (not optimization).
- Rate limits are applied after keep-out resolution, not jointly.
- Initial achieved state at first sample has no rate-limit constraint.
- No cable-wrap accumulation logic beyond simple angle limits.
- No motor torque dynamics, structural flexibility, or drive jitter.
- No thermal effects on gimbal performance.
- No fault modes or redundancy modeling.
- No back-side power generation.
- Keep-out zones are rectangular in angle space only.

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
│   │   ├── models.py                        # Pydantic V1 + V2 + V3 models
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── analysis.py                  # POST /api/analyze/v1, /v2, /v3
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── constants.py                 # Physical constants
│   │       ├── orbit.py                     # Circular orbit mechanics
│   │       ├── eclipse.py                   # Eclipse geometry
│   │       ├── sun_geometry.py              # Sun vector & angles in VVLH
│   │       ├── solar_array_geometry.py      # Wing normals & ideal tracking (V2)
│   │       ├── power.py                     # Power generation model (V2)
│   │       ├── constraints.py               # Angle/rate limits, keep-out (V3)
│   │       └── tracking.py                  # Constrained tracking loop (V3)
│   └── tests/
│       ├── __init__.py
│       ├── test_orbit.py
│       ├── test_eclipse.py
│       ├── test_sun_geometry.py
│       ├── test_solar_array_geometry.py     # V2 geometry tests
│       ├── test_power.py                    # V2 power tests
│       ├── test_analysis_v2.py              # V2 endpoint smoke tests
│       ├── test_constraints.py              # V3 constraint unit tests
│       └── test_analysis_v3.py              # V3 endpoint integration tests
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── firebase.json                        # Firebase Hosting config
    ├── .firebaserc                          # Firebase project selector
    ├── .env.example                         # Local dev env template
    ├── .env.production                      # Prod build env (loaded by Vite)
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── vite-env.d.ts
        ├── api/
        │   ├── client.ts                    # API base URL & fetch wrapper
        │   └── analysis.ts                  # Analysis endpoint caller
        ├── components/
        │   ├── InputPanel.tsx               # Orbit, array, constraint inputs
        │   ├── SummaryCards.tsx              # Ideal + achieved summary metrics
        │   └── PlotSection.tsx              # 10 interactive Plotly charts
        └── types/
            └── analysis.ts                  # V3 request/response types
```

---

## Production URLs

| Service | URL |
|---|---|
| Frontend (Firebase Hosting) | https://sat-solar-app.web.app |
| Backend (Cloud Run) | https://sat-solar-backend-89232339151.us-west4.run.app |
| Backend API docs | https://sat-solar-backend-89232339151.us-west4.run.app/docs |

---

## Local Development

### Backend

Requires [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8005
```

The API will be available at `http://localhost:8005`.
Interactive docs at `http://localhost:8005/docs`.

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
to the backend at port 8005 via the Vite dev-server proxy (configured in
`vite.config.ts`).

> **Local dev vs production:** In local development the frontend sends
> relative `/api/…` requests that the Vite proxy forwards to the backend on
> `localhost:8005`. In production there is no proxy — the frontend calls the
> Cloud Run backend URL directly (see *Frontend Deployment* below).

#### API Base URL Behavior

The frontend uses the `VITE_API_BASE_URL` environment variable to decide
where API requests are sent:

| Environment | `VITE_API_BASE_URL` | API calls go to |
|---|---|---|
| Local dev (`npm run dev`) | **unset** (default) | Relative `/api/…` paths — handled by the Vite dev proxy → `localhost:8005` |
| Production build (`npm run build`) | Read from `frontend/.env.production` | Full URL, e.g. `https://sat-solar-backend-89232339151.us-west4.run.app/api/…` |

Vite automatically loads `frontend/.env.production` when it builds in
production mode, so a plain `npm run build` always produces a
deploy-ready bundle. The file lives at the Vite project root
(`frontend/.env.production`) — **not** inside `src/`. Env files under
`src/` are ignored by Vite.

To override in local development (e.g. to point at the remote backend):

```bash
VITE_API_BASE_URL=https://sat-solar-backend-89232339151.us-west4.run.app npm run dev
```

To override during a production build (e.g. to point a preview deploy at
a staging backend):

```bash
VITE_API_BASE_URL=https://staging-backend.run.app npm run build
```

---

## Deployment — Backend (Cloud Run)

The backend is a Dockerized FastAPI service deployed to **Google Cloud Run**.

| Detail | Value |
|---|---|
| GCP Project | `sat-solar-app` |
| Artifact Registry region | `us-west4` |
| Artifact Registry repo | `sat-solar-backend` |
| Cloud Run service | `sat-solar-backend` |
| Image path | `us-west4-docker.pkg.dev/sat-solar-app/sat-solar-backend/sat-solar-backend` |

### Prerequisites (one-time)

- [Docker](https://docs.docker.com/get-docker/) with `buildx` (bundled with
  Docker Desktop)
- [`gcloud` CLI](https://cloud.google.com/sdk/docs/install) authenticated
  against the `sat-solar-app` project:
  ```bash
  gcloud auth login
  gcloud config set project sat-solar-app
  gcloud auth configure-docker us-west4-docker.pkg.dev
  ```

### Rebuild & Redeploy

Run from the **repository root** after making backend code changes. Pick a
**new, unique tag** for every release (e.g. `v3`, `v4`, …, or a git short
SHA). Reusing an existing tag makes rollbacks harder and can leave Cloud
Run on an older digest if a subsequent deploy is skipped.

**1. Pick a tag and export it:**

```bash
export TAG=v3   # bump this each release (v4, v5, …), or use: $(git rev-parse --short HEAD)
export IMAGE=us-west4-docker.pkg.dev/sat-solar-app/sat-solar-backend/sat-solar-backend:$TAG
```

**2. Build and push the Docker image** (linux/amd64 is required by Cloud
Run, even from an Apple Silicon Mac):

```bash
docker buildx build --platform linux/amd64 \
  -t "$IMAGE" \
  -f backend/Dockerfile backend \
  --push
```

**3. Deploy the new image to Cloud Run:**

```bash
gcloud run deploy sat-solar-backend \
  --image "$IMAGE" \
  --region us-west4 \
  --platform managed \
  --allow-unauthenticated
```

**4. Verify the deploy:**

```bash
curl -fsS https://sat-solar-backend-89232339151.us-west4.run.app/health
# → {"status":"ok"}
```

> **Why bump the tag?** `gcloud run deploy --image …:v2` resolves the tag
> to an image digest at deploy time. If you later `docker push` a new
> image to the same tag without running `gcloud run deploy` again, Cloud
> Run keeps serving the **old** digest. Using a fresh tag per release
> prevents this class of "I pushed but nothing changed" bug and makes
> rollbacks trivial (`gcloud run deploy … --image …:v2`).

### Rollback

```bash
gcloud run deploy sat-solar-backend \
  --image us-west4-docker.pkg.dev/sat-solar-app/sat-solar-backend/sat-solar-backend:<previous-tag> \
  --region us-west4 --platform managed --allow-unauthenticated
```

List previously-built tags:

```bash
gcloud artifacts docker images list \
  us-west4-docker.pkg.dev/sat-solar-app/sat-solar-backend/sat-solar-backend \
  --include-tags
```

---

## Deployment — Frontend (Firebase Hosting)

The frontend is a React + TypeScript + Vite SPA deployed to
**Firebase Hosting**.

### Prerequisites (one-time)

- [Firebase CLI](https://firebase.google.com/docs/cli) installed and
  authenticated (`firebase login`)
- `frontend/.firebaserc` references the Firebase project `sat-solar-app`

### Rebuild & Redeploy

Run from the **`frontend/` directory** after making frontend code changes:

```bash
cd frontend
npm install        # only if dependencies changed
npm run deploy     # builds with production env, then deploys hosting
```

`npm run deploy` is a shortcut for `npm run build && firebase deploy --only
hosting`. If you want to run the two steps separately:

```bash
npm run build                      # produces dist/ using frontend/.env.production
firebase deploy --only hosting     # uploads dist/ to Firebase Hosting
```

The build picks up `VITE_API_BASE_URL` from `frontend/.env.production`,
which points at the Cloud Run backend. The `firebase.json` is configured
for a single-page app — all routes rewrite to `index.html`.

### Changing the backend URL used by the frontend

Edit the one-line file:

```1:1:frontend/.env.production
VITE_API_BASE_URL=https://sat-solar-backend-89232339151.us-west4.run.app
```

then redeploy with `npm run deploy`. For a one-off build against a
different backend (e.g. a staging environment) without editing the file:

```bash
VITE_API_BASE_URL=https://staging-backend.run.app npm run build
firebase deploy --only hosting
```

---

## Deployment — Full Release Checklist

A typical end-to-end release from a clean `main` branch:

```bash
# --- 1. Backend ---
cd /path/to/sat-solar-beta-app
export TAG=v3   # bump this each release
export IMAGE=us-west4-docker.pkg.dev/sat-solar-app/sat-solar-backend/sat-solar-backend:$TAG
docker buildx build --platform linux/amd64 -t "$IMAGE" -f backend/Dockerfile backend --push
gcloud run deploy sat-solar-backend --image "$IMAGE" \
  --region us-west4 --platform managed --allow-unauthenticated
curl -fsS https://sat-solar-backend-89232339151.us-west4.run.app/health

# --- 2. Frontend ---
cd frontend
npm run deploy
```

If you change the backend URL in `frontend/.env.production`, remember to
also add the new hosting origin to the CORS allow-list in
`backend/app/main.py` and redeploy the backend (see *CORS* below).

---

## Notes & Gotchas

### CORS

The FastAPI backend must include every origin that will call it in its CORS
`allow_origins` list (`backend/app/main.py`). The current allowed origins
are:

| Origin | Purpose |
|---|---|
| `http://localhost:5173` | Local Vite dev server |
| `https://sat-solar-app.web.app` | Firebase Hosting (primary) |
| `https://sat-solar-app.firebaseapp.com` | Firebase Hosting (alternate) |

If you add a new hosting domain or change the Firebase project, update the
CORS list in `main.py` **and** redeploy the backend.

### Architecture Overview

```
┌─────────────────────┐         ┌─────────────────────────┐
│  Firebase Hosting    │  HTTPS  │  Google Cloud Run        │
│  (static SPA)        │ ──────► │  (FastAPI Docker image)  │
│  sat-solar-app.web.  │         │  sat-solar-backend-…     │
│  app                 │         │  .us-west4.run.app       │
└─────────────────────┘         └─────────────────────────┘
        ▲                                ▲
        │  npm run deploy                │  docker buildx build … --push
        │  (build + firebase deploy)     │  gcloud run deploy
        │                                │
   frontend/                        backend/
```

- **Local dev** — Vite proxies API requests (`localhost:5173` →
  `localhost:8005`); no CORS needed for local-to-local calls.
- **Production** — The browser loads the SPA from Firebase Hosting and makes
  direct `fetch()` calls to the Cloud Run backend URL. CORS headers are
  required because the two origins differ.

### Docker Platform

Cloud Run requires a `linux/amd64` image. The `--platform linux/amd64` flag
in the `docker buildx build` command ensures the image is built for the
correct architecture, even when building on an Apple Silicon (arm64) Mac.

---

## API

### `POST /api/analyze/v1`  (backward compatible)

Version 1 orbit-only analysis. Request/response unchanged from V1.

### `POST /api/analyze/v2`  (backward compatible)

Version 2 ideal tracking analysis. Request/response unchanged from V2.

### `POST /api/analyze/v3`

**Request body** (all fields have defaults):

```json
{
  "altitude_km": 500,
  "beta_deg": 0,
  "num_samples_per_orbit": 360,
  "solar_array_area_m2_per_wing": 5.0,
  "solar_cell_efficiency": 0.30,
  "degradation_factor": 0.85,
  "required_bus_power_w": 3000,
  "right_outer_min_deg": -180,
  "right_outer_max_deg": 180,
  "right_inner_min_deg": -90,
  "right_inner_max_deg": 90,
  "left_outer_min_deg": -180,
  "left_outer_max_deg": 180,
  "left_inner_min_deg": -90,
  "left_inner_max_deg": 90,
  "outer_rate_limit_deg_per_s": 1.0,
  "inner_rate_limit_deg_per_s": 1.0,
  "keepout_zones": []
}
```

**Keep-out zone example:**

```json
{
  "keepout_zones": [
    {
      "wing": "right",
      "outer_min_deg": -10,
      "outer_max_deg": 10,
      "inner_min_deg": -15,
      "inner_max_deg": 15,
      "label": "thruster plume"
    }
  ]
}
```

**Response** includes all V1/V2 fields plus:
- Per-wing ideal and achieved angle/incidence/power arrays
- Per-sample constraint flags (angle-limited, rate-limited, in keep-out)
- Total ideal and achieved power arrays
- Summary: average powers, energy ratio, tracking losses, constraint fractions

See `backend/app/models.py` for the full typed schema.

---

## Future Roadmap

### Version 4 — Advanced Models

Possible additions beyond Version 3:
- **Body shadowing** — blockage of arrays by spacecraft bus geometry
- **Cable-wrap logic** — cumulative wrap angle tracking and unwinding
- **Asymmetric wing mechanisms** — independent rate limits or geometry
- **Optimization-based keep-out avoidance** — replace nearest-boundary with optimizer
- **Bus attitude offsets from VVLH** — non-nadir-pointing spacecraft
- **Battery and eclipse energy storage modeling** — depth-of-discharge estimation
- **Seasonal Sun model** — Sun declination as a function of day-of-year
- **Beta angle from orbital elements** — derived from inclination, RAAN, and epoch
- **J2 secular RAAN drift** — long-term beta angle evolution
- **Multi-panel / multi-wing configurations**
- **Export results to CSV / JSON**
