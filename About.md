# Saksha — Crime Intelligence & Analytical Platform for Karnataka State Police

## Quick Start (One Command)

```bash
# From workspace root:
npm run dev:all
```

- Backend API → http://localhost:8000 (FastAPI + Supabase PostgreSQL)
- Frontend UI → http://localhost:5173 (React + Vite)
- API Docs → http://localhost:8000/docs

---

## Demo Logins

| Badge ID   | Password      | Role           | Access Level |
|------------|---------------|----------------|--------------|
| SCRB-7740  | 123456        | Crime Analyst  | Full access  |
| IO-3921    | 123456        | Investigator   | Field access |
| SP-0088    | 123456        | Policymaker    | Read-only    |
| admin      | ChangeMe123!  | Admin          | System admin |

---

## First-Time Setup

```bash
# 1. Install frontend dependencies
cd datathon && npm install && cd ..

# 2. Install backend dependencies
cd backend && py -3.12 -m pip install -r requirements.txt && cd ..

# 3. Initialize database tables (Supabase)
cd backend && py -3.12 -m app.database.init_db && cd ..

# 4. Seed demo data
cd backend && py -3.12 -m app.database.seed_db && cd ..

# 5. Start everything
npm run dev:all
```

---

## Architecture

```
Crime Data Sources (incl. CCTNS-style CSV/XLSX bulk imports)
       ↓
Supabase PostgreSQL (22 SQLAlchemy models) + Neo4j Aura graph
       ↓
FastAPI Backend (75+ REST endpoints under /api/v2)
       ↓
React Frontend (18 intelligence modules)
```

---

## Platform Modules

| Module | Page | Backend Endpoints |
|--------|------|-------------------|
| Crime Intelligence Dashboard | Overview | /dashboard/* |
| Geospatial Hotspot Detection | Hotspots | /ai/hotspots |
| Criminal Network Analysis | Network | /network/*, /ai/network/person/* |
| Predictive Intelligence | Predictions | /ai/risk/*, /ai/hotspot/* |
| Anomaly Detection | Anomalies | /ai/anomaly/detect |
| Offender Registry | Offenders | /dashboard/offender-dossiers |
| Reports Center | Reports | /reports (PDF/DOCX/TXT/CSV/XLSX export) |
| FIR Management | FIR | /firs/* |
| Investigation Workspace | Investigation | /investigation/* |
| Crime Cases | Crime Cases | /crime-cases/* |
| Sociological Intelligence | Sociological | /sociological/* (dataset-backed indicators) |
| Strategic Command | Strategic | /strategic/*, /interventions/* (before/after effectiveness) |
| Victimology Analytics | Victims | /victimology/* (repeat-victimization, vulnerability index) |
| Semantic MO Search | AI tools | /ai/mo/search, /ai/mo/extract-* |
| Bulk Data Import (CCTNS profiles) | Admin → Import tab | /data-import/* |
| Notifications | Notifications | /notifications/* |
| Evidence Chain of Custody | Evidence | /evidence/* |
| Settings & Help | Settings | /admin/* |

---

## Database Schema (Supabase PostgreSQL)

Core tables created by `app/models/` (applied via SQLAlchemy `create_all`):
- `roles`, `users` — authentication & RBAC
- `crime_categories`, `locations`, `officers`, `criminals`, `victims`
- `crime_cases`, `firs`, `fir_criminal_links`, `fir_victim_links`
- `evidence`, `evidence_metadata`, `evidence_timeline`,
  `evidence_assignment`, `chain_of_custody`, `evidence_ai_summary`
- `reports`, `audit_logs`, `notifications`, `investigation_notes`
- `import_jobs` — bulk CSV/XLSX ingestion audit (issue #139)
- `interventions` — prevention programs + effectiveness tracking (issue #139)
- `socioeconomic_indicators` — optional Supabase-side reference table
  (see `backend/scripts/socioeconomic_indicators.sql`; demo data, <50 KB)

---

## Tech Stack

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Zustand, Recharts, Three.js, react-force-graph-3d, Framer Motion

**Backend:** FastAPI, SQLAlchemy 2, Pydantic v2, python-jose (JWT), SHA-256 salted password hashing, Neo4j driver

**Database:** Supabase PostgreSQL (hosted), Neo4j Aura (graph)

**AI/Analytics:** LightGBM hotspot prediction, RandomForest risk scoring, XGBoost/LightGBM forecasting, Z-score L2 anomaly detection, custom NumPy criminal-risk/repeat-offender models, TF-IDF+LSA semantic MO search — each with rule-based fallbacks when no trained artifact exists.

---

## Windows Notes

- Uses `py -3.12` launcher (Python 3.12 required, not 3.14)
- Backend runs from `backend/` directory with its own `cwd`
- Frontend proxies `/api` → `localhost:8000` via Vite config

---

## See Also

- `IMPLEMENTATION.md` — full technical memory, API reference, ER mapping
- `CONTEXT.md` — complete project context (architecture, schema, endpoints)
- `CCTNS_ICJS_INTEROP.md` — legacy data ingestion & interop spec (issue #139)
- `backend/scripts/socioeconomic_indicators.sql` — Supabase reference-indicator table
- `backend/app/database/seed_db.py` — demo data definitions
- `datathon/src/services/api.ts` — all frontend API calls
