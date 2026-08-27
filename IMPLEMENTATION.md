# Saksha — Implementation Rules & Memory

## Project Identity
- **Name:** Saksha — Crime Intelligence & Analytical Platform for Karnataka State Police (KSP)
- **Event:** Datathon 2026, Challenge 2
- **Stack:** FastAPI (Python 3.12) backend + React/TypeScript (Vite) frontend
- **Database:** Supabase PostgreSQL (hosted) + Neo4j Aura (graph)

---

## Repository Layout

```
Saksha_Datathon/
├── backend/              FastAPI app (Python 3.12)
│   ├── app/
│   │   ├── api/v2.py     All routers aggregated here
│   │   ├── auth/         JWT + RBAC
│   │   ├── core/         config, security, exceptions, logging
│   │   ├── database/     postgres.py, neo4j.py, init_db.py, seed_db.py
│   │   ├── models/       SQLAlchemy ORM models (matches ER diagram)
│   │   ├── routes/       One file per resource
│   │   ├── schemas/      Pydantic v2 schemas
│   │   └── services/     analytics_service.py (all AI/ML logic)
│   ├── .env              Supabase + Neo4j + JWT secrets (DO NOT COMMIT)
│   └── requirements.txt
├── datathon/             React + Vite frontend
│   └── src/
│       ├── pages/        One file per module page
│       ├── components/   layout/, charts/, map/, network/, three/, auth/
│       ├── services/api.ts  All fetch calls to /api/v2
│       ├── store/        Zustand stores (auth, audit, map, alert)
│       └── utils/
├── scripts/dev-all.js    Starts both backend + frontend
└── package.json          Root workspace scripts
```

---

## One-Command Dev Start

```bash
# From workspace root:
npm run dev:all
```

- Backend: `py -3.12 -m uvicorn app.main:app --reload --app-dir backend` → http://localhost:8000
- Frontend: `npm run dev --prefix datathon` → http://localhost:5173
- Frontend proxies `/api` → `http://localhost:8000` via Vite config

---

## Database

### Supabase PostgreSQL
- Host: `aws-0-ap-northeast-1.pooler.supabase.com`
- DB: `postgres`, User: `postgres.jxdbqtzlxwoemvchdfuh`
- Password in `backend/.env` as `SUPABASE_DB_PASSWORD`
- SSL: required

### Init & Seed (run once or after schema changes)
```bash
cd backend
py -3.12 -m app.database.init_db    # creates all tables
py -3.12 -m app.database.seed_db    # seeds demo data
```

### Demo Logins (after seed)
| Username   | Password      | Role           |
|------------|---------------|----------------|
| admin      | ChangeMe123!  | admin          |
| SCRB-7740  | 123456        | crime_analyst  |
| IO-3921    | 123456        | investigator   |
| SP-0088    | 123456        | policymaker    |

### Neo4j Aura
- URI: `neo4j+s://c2c53941.databases.neo4j.io`
- Used for graph network visualization (optional — app degrades gracefully if down)

---

## ER Diagram → Model Mapping (Police_FIR_ER_Diagram.pdf)

| ER Entity        | SQLAlchemy Model     | Table              |
|------------------|----------------------|--------------------|
| FIR              | FIR                  | firs               |
| Crime Case       | CrimeCase            | crime_cases        |
| Criminal/Suspect | Criminal             | criminals          |
| Victim           | Victim               | victims            |
| Officer          | Officer              | officers           |
| Location         | Location             | locations          |
| Crime Category   | CrimeCategory        | crime_categories   |
| Evidence         | Evidence             | evidence           |
| FIR↔Criminal     | FIRCriminalLink      | fir_criminal_links |
| FIR↔Victim       | FIRVictimLink        | fir_victim_links   |
| User (login)     | User                 | users              |
| Role             | Role                 | roles              |
| Audit Log        | AuditLog             | audit_logs         |

---

## API Endpoints (all under /api/v2)

### Auth
- `POST /auth/login` — returns JWT access + refresh tokens
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET  /auth/me`
- `POST /auth/register` (admin only)

### Dashboard
- `GET /dashboard/summary`
- `GET /dashboard/crime-trends`
- `GET /dashboard/category-breakdown`
- `GET /dashboard/district-comparison`

### AI / Analytics
- `GET  /ai/hotspots?district_id=`
- `GET  /ai/predictions/risk-scores?window=next_7d&district_id=`
- `GET  /ai/predictions/anomalies`
- `GET  /ai/offenders/dossiers`
- `GET  /ai/network/person/{person_id}?depth=1`
- `POST /ai/chat/query` — `{message, session_id}`

### CRUD Resources
- `/crimes`, `/firs`, `/criminals`, `/victims`, `/officers`, `/locations`, `/evidence`, `/reports`, `/users`

---

## Frontend Pages → Backend Endpoints

| Page          | Endpoints Used                                              |
|---------------|-------------------------------------------------------------|
| Overview      | summary, crime-trends, category-breakdown, risk-scores, hotspots, anomalies |
| Hotspots      | hotspots, district-comparison, risk-scores                  |
| Network       | network/person/{id}                                         |
| Predictions   | risk-scores, anomalies                                      |
| Anomalies     | anomalies                                                   |
| Offenders     | offenders/dossiers                                          |
| Reports       | static local data (no backend call)                         |
| Settings/Help | static local data (no backend call)                         |

---

## RBAC Roles

| Role          | Access                                      |
|---------------|---------------------------------------------|
| admin         | All routes + register users                 |
| crime_analyst | All read + dashboard + AI endpoints         |
| investigator  | Crimes, FIRs, criminals, victims CRUD       |
| policymaker   | Read-only dashboard + AI                    |

Frontend RBAC in `useRBAC.ts` maps paths to allowed roles.

---

## AI/Analytics Engine (rule-based, no ML dependency)

All in `backend/app/services/analytics_service.py`:

- `dashboard_summary()` — counts from DB
- `crime_trends()` — monthly bucketing of crime_cases.occurred_at
- `category_breakdown()` — JOIN crime_cases + crime_categories
- `district_comparison()` — JOIN crime_cases + locations
- `risk_scores()` — weighted formula: volume + recency + open_ratio + severity
- `hotspots()` — per-location crime density + trend detection
- `anomalies()` — rule-based scoring on FIRs (severity, open status, MO tags, multi-suspect)
- `offender_dossiers()` — criminal profiles with risk scoring
- `network_person()` — builds nodes/edges from FIR criminal+victim links
- `chat_answer()` — returns DB summary as natural language

---

## Frontend Architecture

- **Auth flow:** Zustand `authStore` → `api.ts login()` → JWT stored in localStorage → `getMe()` hydrates user
- **API calls:** All in `src/services/api.ts` using `fetch` with Bearer token
- **Proxy:** Vite proxies `/api` → `localhost:8000` (no CORS issues in dev)
- **3D Network:** `react-force-graph-3d` with Canvas fallback when WebGL unavailable
- **Map:** Custom SVG vector map of Karnataka (no Mapbox token needed)
- **Charts:** Recharts (TrendChart, DonutChart, ForecastChart, CorrelationChart)

---

## Known Issues Fixed

1. **Overview.tsx syntax error** — escaped `\n` in JSX alert rows (fixed)
2. **Frontend build** — passes `tsc && vite build` cleanly
3. **DB tables** — created via `init_db`, seeded via `seed_db`
4. **CORS** — backend allows `localhost:3000` and `localhost:5173`
5. **Login** — `SCRB-7740 / 123456` works end-to-end via Supabase

---

## What's Implemented (Complete)

- [x] Login page with Face ID (demo) + Badge credential login
- [x] JWT auth with role-based access control
- [x] Overview dashboard with live backend data
- [x] Hotspot map (SVG Karnataka, district drill-down, time slider)
- [x] Criminal network graph (3D force-directed + Canvas fallback)
- [x] Predictive AI page (risk scores, anomalies, forecast charts)
- [x] Anomaly feed with review/escalate actions
- [x] Offender dossier registry with export
- [x] Reports center with classified document downloads
- [x] Settings & Help with IPC lookup
- [x] Audit log trail (Zustand, shown in Offenders page)
- [x] Session timer with auto-logout
- [x] Supabase PostgreSQL connected and seeded
- [x] All 11 crime data tables created per ER diagram
- [x] Full REST API for all entities

---

## Issue #176 — Production Report & Audit Lifecycle

A production-ready reporting lifecycle for investigations and evidence was added
on top of the existing Reports Center (legacy generate/export stays intact):

- **Lifecycle statuses:** `draft → generating -> generated -> under_review -> final ->
  archived` with a valid any-state `failed` transition.
- **Report model extensions** (`backend/app/models/report.py`): `report_type`, `title`,
  `case_id`, `provenance`, `integrity_hash`, `generation_method`, `analysis_fingerprint`,
  `failure_reason`, `source_record_count`, `evidence_count`, `generated_at`, `reviewed_at`,
  `finalized_at`, `archived_at`, `reviewed_by_id`, `finalized_by_id`, `version`,
  `content_snapshot`, `ai_reported`, `ai_metadata`.
- **New tables** via SQLAlchemy: `ReportVersion`, `ReportSourceLink`, `ReportEvidenceLink`
  (version history, cited-source provenance, and supporting-evidence links).
- **Audit extensions** (`backend/app/models/audit_log.py` + `audit_service.py`): `result`
  (`success`/`failure`) and `metadata` (JSON) added; every lifecycle transition is audited.
- **Integrity hashing:** immutable SHA-256 fingerprint over title + sorted source ids +
  sorted evidence ids + snapshot content; verified on finalize so tampering is detected.
- **Provenance tracking:** each report is tagged `live`, `migrated`, `demo`, or `mixed`;
  legacy exports derive provenance from the actual rows.
- **AI validation:** explicit `ai_reported` flag + `ai_metadata`, verified-reference
  gating so AI-generated citations must correspond to real records.
- **Access control:** an admin or the requesting user only; non-creators cannot view,
  download, or mutate another user's report; the audit trail is admin-only.
- **Endpoints** (`backend/app/routes/reports.py`, UUID-path so legacy routes are untouched):
  `POST /reports`, `GET /reports/{id}`, `POST /reports/{id}/generate`,
  `POST /reports/{id}/validate`, `GET|POST /reports/{id}/versions`,
  `POST /reports/{id}/review|finalize|archive`, `GET /reports/{id}/download`,
  `GET /reports/{id}/audit` (admin).
- **Frontend** (`datathon/src/components/reports/ManagedReportLifecycle.tsx` + `Reports.tsx`):
  lifecycle panel listing managed reports with status/provenance badges, per-user detail
  drawer (integrity hash, sources, evidence, audit trail for admins), and create/review/
  finalize/archive/version/download actions.
- **Tests** (`backend/tests/test_report_lifecycle.py`): 16 scenarios covering creation,
  access control, source/evidence linking, provenance, versioning, immutability on finalize,
  audit trail, failure state, traceability, AI reference validation/hallucination rejection,
  audit authorization, and download security.

---

## Next Steps / Enhancements

- [ ] Add real ML models (XGBoost/Random Forest) for risk scoring
- [ ] Integrate Neo4j for persistent graph storage
- [ ] Add Mapbox token for real satellite map tiles
- [ ] Add LLM/RAG for conversational AI chat
- [ ] Add Alembic migrations for schema versioning
- [ ] Add more seed data (100+ cases across all districts)
- [ ] Add WebSocket for real-time alert streaming
- [ ] Add PDF export using a server-side library
