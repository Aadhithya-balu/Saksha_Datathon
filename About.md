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
Crime Data Sources
       ↓
Supabase PostgreSQL (11 tables per FIR ER diagram)
       ↓
FastAPI Backend (60 REST endpoints)
       ↓
React Frontend (8 intelligence modules)
```

---

## Platform Modules

| Module | Page | Backend Endpoints |
|--------|------|-------------------|
| Crime Intelligence Dashboard | Overview | /dashboard/* |
| Geospatial Hotspot Detection | Hotspots | /ai/hotspots |
| Criminal Network Analysis | Network | /ai/network/person/* |
| Predictive Intelligence | Predictions | /ai/predictions/* |
| Anomaly Detection | Anomalies | /ai/predictions/anomalies |
| Offender Registry | Offenders | /ai/offenders/dossiers |
| Reports Center | Reports | static + /reports |
| Settings & Help | Settings | static |

---

## Database Schema (Supabase PostgreSQL)

Tables created per Police FIR ER Diagram:
- `roles`, `users` — authentication & RBAC
- `crime_categories` — IPC section classifications
- `locations` — district/station geo coordinates
- `criminals` — offender registry
- `victims` — victim/complainant records
- `officers` — investigating officer profiles
- `crime_cases` — central incident records
- `firs` — First Information Reports
- `fir_criminal_links` — FIR ↔ Criminal (many-to-many)
- `fir_victim_links` — FIR ↔ Victim (many-to-many)
- `evidence` — physical/digital evidence chain
- `reports` — generated intelligence reports
- `audit_logs` — system access audit trail

---

## Tech Stack

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Zustand, Recharts, Three.js, react-force-graph-3d, Framer Motion

**Backend:** FastAPI, SQLAlchemy 2, Pydantic v2, python-jose (JWT), passlib/bcrypt, Neo4j driver

**Database:** Supabase PostgreSQL (hosted), Neo4j Aura (graph)

**AI/Analytics:** Rule-based scoring engine in `analytics_service.py` (ready for ML model swap-in)

---

## Windows Notes

- Uses `py -3.12` launcher (Python 3.12 required, not 3.14)
- Backend runs from `backend/` directory with its own `cwd`
- Frontend proxies `/api` → `localhost:8000` via Vite config

---

## See Also

- `IMPLEMENTATION.md` — full technical memory, API reference, ER mapping
- `backend/app/services/analytics_service.py` — all AI/analytics logic
- `backend/app/database/seed_db.py` — demo data definitions
- `datathon/src/services/api.ts` — all frontend API calls
