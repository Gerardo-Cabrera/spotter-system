# Spotter — HOS Trip Planner

Full-stack app (Django + React) that turns trip inputs into an **HOS-compliant route** and **Driver's Daily Log sheets**. Built for the Full Stack Developer Assessment.

![Stack](https://img.shields.io/badge/Django-5.0-092E20?logo=django&logoColor=white) ![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black) ![Postgres](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white) ![Tailwind](https://img.shields.io/badge/Tailwind-3-38BDF8?logo=tailwindcss&logoColor=white) ![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)

> **Quick nav**: [Develop](#develop) · [Production](#production) · [API docs](#api)

## Features

- **Inputs**: current location, pickup, dropoff, and current cycle hours (70h / 8-day).
- **Interactive map** (Leaflet + OpenStreetMap) with a real road route via OSRM and markers differentiated by stop type (pickup, dropoff, fuel, 30-min break, 10h rest).
- **Daily log sheets** drawn in SVG, matching the blank FMCSA form and the reference video convention (horizontal line per status, vertical transitions, red dots at every status change, Remarks as `City, ST / activity`).
- **HOS rules enforced**: 11h driving, 14h window, 30-min break after 8h, 10h off-duty rest, 70h/8-day cycle, 34h restart when the cycle runs out, 1h pickup + 1h dropoff, fueling every 1000 miles.
- **Stateless by default**; optional persistence to **PostgreSQL** (`save=true` → `trip_id`).
- **Timezone** inferred geographically from the pickup via `timezonefinder` (the physical log belongs to the driver's home terminal).

## Repository layout

```
spotter/
├── backend/                  Django 5 + DRF + Postgres (+ Dockerfile)
├── frontend/                 Vite + React 18 + TS + Tailwind (+ Dockerfile)
├── .github/workflows/ci.yml  CI pipeline (tests + build + docker)
└── docker-compose.yml        Full local stack
```

## Develop

Two equivalent local workflows — pick whichever is most convenient:

### 🐳 A · Docker Compose (one command, recommended)

**Requirements**: Docker 24+ and Docker Compose v2.

```bash
docker compose up --build
```

That's it. Open:
- Frontend   → http://localhost:5173
- Backend    → http://localhost:8000/api/health/
- API docs   → http://localhost:8000/api/docs/ (Swagger UI)
- Postgres   → `localhost:5432` (`spotter`/`spotter`/`spotter`)

Data persists in the `spotter_pgdata` named volume. Full reset: `docker compose down -v`.

### 🐍 B · Native install

**Requirements**: Python 3.10+, Node 18+. Without a local Postgres, the backend falls back to SQLite.

```bash
# Terminal 1 — Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver         # http://localhost:8000
```

```bash
# Terminal 2 — Frontend
cd frontend
npm install
cp .env.example .env
npm run dev                         # http://localhost:5173
```

Once both are running, the Swagger UI is available at `http://localhost:8000/api/docs/`.

---

## Production

**Backend + Postgres → Render** · **Frontend → Vercel** · ~15 min.

### 1. Backend on Render

Uses the `backend/render.yaml` blueprint:

- Render → **New → Blueprint** → select the repo → *Apply*.
- Provisions a Python web service (Gunicorn) + managed Postgres automatically.
- Set manually: `NOMINATIM_USER_AGENT="SpotterTripPlanner/1.0 (your-email)"` (required by Nominatim's policy). Optionally `ORS_API_KEY` for routing fallback.
- Verify: `curl https://<your-app>.onrender.com/api/health/` → `{"status":"ok"}`.

### 2. Frontend on Vercel

The Vite framework is auto-detected from `frontend/vercel.json`:

- Vercel → **Add New → Project** → *Root Directory*: `frontend`.
- Env var: `VITE_API_BASE_URL=https://<your-app>.onrender.com`.
- Deploy.

### 3. Wire up CORS

On Render, add the Vercel URL to `CORS_ALLOWED_ORIGINS` (CSV). The service restarts automatically.

### Notes

- Render's free tier sleeps after 15 minutes of inactivity (the first request takes ~30 s to wake up). Upgrading to Starter ($7/mo) removes this.
- Prefer Docker? The `Dockerfile`s under `backend/` and `frontend/` work on Fly.io, ECS, Cloud Run, etc.

---

## Useful scripts

### Backend
```bash
pytest                     # Run the HOS test suite
python manage.py migrate   # Apply migrations
python manage.py shell     # Django REPL
```

### Frontend
```bash
npm run dev         # Dev server with HMR
npm run typecheck   # tsc --noEmit (same check as CI)
npm run build       # Production build to ./dist
npm run preview     # Serve the built assets locally
```

---

## API

Interactive documentation is generated automatically from the code (`drf-spectacular`) and served by the backend:

| URL | Purpose |
|---|---|
| `GET /api/docs/` | **Swagger UI** — try every endpoint from the browser |
| `GET /api/redoc/` | **ReDoc** — clean reference-style rendering |
| `GET /api/schema/` | Raw **OpenAPI 3** schema (YAML) — import into Postman/Insomnia/codegen |

Endpoints at a glance:

| Method & path | Description |
|---|---|
| `POST /api/trips/plan/` | Plan a trip (stateless) or persist it when `save=true`. |
| `GET  /api/trips/<uuid>/` | Fetch a previously saved trip. |
| `GET  /api/geocode/?q=<query>` | Cached Nominatim proxy used for autocomplete. |
| `GET  /api/health/` | Liveness check. |

For the full response payload shape, open `/api/docs/` (Swagger UI) or fetch `/api/schema/` (raw OpenAPI 3 YAML).

---

## Environment variables

**Backend** (`backend/.env.example`):

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | `dev-insecure-change-me` | Django secret — **required in production**. |
| `DJANGO_DEBUG` | `True` | Set to `False` in production. |
| `DJANGO_ALLOWED_HOSTS` | `*` | Comma-separated list. |
| `DATABASE_URL` | *(empty → SQLite)* | e.g. `postgres://user:pass@host:5432/db` |
| `DATABASE_SSL_REQUIRE` | `False` | `True` on Render. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,...` | Allowed origins (CSV). |
| `NOMINATIM_BASE_URL` | `https://nominatim.openstreetmap.org` | |
| `NOMINATIM_USER_AGENT` | `SpotterTripPlanner/1.0` | **Must include a real contact** in production. |
| `OSRM_BASE_URL` | `https://router.project-osrm.org` | |
| `ORS_API_KEY` | `""` | Optional — routing fallback. |
| `ORS_BASE_URL` | `https://api.openrouteservice.org` | |

**Frontend** (`frontend/.env.example`):

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend URL. |
| `VITE_GITHUB_URL` | *(empty)* | When set, renders a GitHub icon in the header. |

---

## Testing & CI

- **Backend**: `pytest` — 5 tests covering the HOS rules (11h, 14h, break, rest, restart, fuel).
- **Frontend**: `npm run typecheck` + `npm run build` guarantee the TS ↔ backend contract.
- **CI (GitHub Actions)**: every push/PR to `main` runs backend + frontend + Docker image builds. See `.github/workflows/ci.yml`.

---

## Notes

- **External APIs**: public Nominatim + OSRM (free, no API key). OpenRouteService is an optional fallback.
- **Caching**: in-memory caches for geocoding (7 days) and routing (24 h) keep us well inside rate limits.
- **Stateless by default**: `Trip` is persisted only when `save=true`. The stored data is an immutable JSONField snapshot.

License: MIT.
