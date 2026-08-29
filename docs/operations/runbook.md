# SAKSHA Production Operations Runbook

**Platform:** SAKSHA Crime Intelligence & Analytical Platform (KSP, Datathon 2026 Challenge 2)
**Scope:** Deploy, configure, start, monitor, troubleshoot, recover, and maintain every component.
**Audience:** Authorized operations / deployment team. No source-code reading required to follow this document.
**Status:** Every command and endpoint below was verified against the repository. Where a capability does not exist, it is explicitly documented as a **documented gap / operational requirement** rather than assumed.

Related documentation (read before operating):
- `README.md`, `IMPLEMENTATION.md`, `TESTING.md`, `Version-2.md`
- `docs/ai/predictive_models.md` — model architecture and metrics
- `docs/network/provenance_intelligence.md` — Neo4j network intelligence and data provenance
- `backend/README.md` — backend-local notes
- `CONTEXT.md` — full system context (developer reference)

---

## 1. System Overview

SAKSHA transforms crime records (FIRs, cases, criminals, victims, officers, evidence) into operational intelligence: dashboards, heatmaps, criminal-network graphs (Neo4j), AI/ML predictions (hotspots, district risk, criminal risk, anomaly detection), a RAG-chat analyst, notifications/alerts, and bulk CCTNS/ICJS-style data ingestion.

- **Backend:** FastAPI (Python 3.12), served by uvicorn on port `8000`.
- **Frontend:** React 18 + TypeScript + Vite 5. Dev server on port `5173`; production build served by **nginx** on port `80` (single-container image) or any static host with an SPA fallback.
- **Database:** PostgreSQL 16 — either Supabase-hosted (`SUPABASE_DB_*`) or local Docker `postgres:16-alpine`. A local SQLite fallback exists **only** for development/tests (see §5 and the documented caveat in §10.3).
- **Graph DB:** Neo4j 5.24 (local Docker image or Neo4j Aura). **Optional at runtime**; SQL-based fallback is automatic when Neo4j is unavailable.
- **Storage:** Evidence/person-image files go to **Supabase Storage** when configured, otherwise to the local `backend/uploads/` directory (development only).
- **AI/ML:** Model artifacts live in `backend/app/ai/models/`. Trained from DB on demand; rule-based fallbacks are explicit and labelled (`prediction_mode: "ML" | "FALLBACK"`), never silent.
- **Auth:** JWT (HS256) access tokens (30 min) + rotating refresh tokens (7 days); Argon2id password hashing (transparent migration from legacy SHA-256); account lockout; per-IP rate limiting; optional Supabase Auth fallback.
- **ORCHESTRATION / CI:** Docker Compose, GitHub Actions (`ci.yml`, `mlops.yml`), `scripts/dev-all.js` for development.

### Data flow

```
Browser/React  →  nginx/location /api/  →  FastAPI (/api/v2)  →  PostgreSQL (Supabase or Docker)
                                            FastAPI  →  Neo4j Aura/Docker (graph, optional)
                                            FastAPI  →  Supabase Storage (evidence files, optional)
                                            FastAPI  →  LLM providers (Groq → Gemini → OpenAI → local templates)
                                            FastAPI  →  Model artifacts (backend/app/ai/models)
```

---

## 2. Architecture — Component Fact Sheet

| Component | Purpose | Required in production? | Connection | Config source | Health check | Failure behavior | Recovery |
|---|---|---|---|---|---|---|---|
| **FastAPI backend** | All REST APIs, auth, AI/ML inference, ingestion, reports | **Yes** | nginx proxy or direct on `:8000` | `.env` (repo root or `backend/`) | `/health/live`, `/health/ready` | Won't start if production config invalid; retries PG 3x then continues degraded | See §10 |
| **PostgreSQL 16** | System of record (16+ tables) | **Yes** | `DATABASE_URL` (psycopg2, SSL) | `DATABASE_URL` or `SUPABASE_DB_*` / `POSTGRES_*` | Automatic connection on startup; `/health/ready` reports `postgresql` | Startup retries; degraded mode if down | §11 / §14 |
| **Neo4j 5.24** | Criminal-network graph | **Optional** (falls back to SQL) | Bolt `bolt://host:7687` | `NEO4J_URI/USER/PASSWORD` | `/health/ready` reports `neo4j`; browser `:7474` | Network intelligence returns SQL-reconstructed graph; sync returns warning | §16 |
| **Supabase Storage** | Persistent evidence files | **Optional** (else local uploads) | HTTPS REST (`/storage/v1/object`) | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_STORAGE_BUCKET` | Upload endpoint returns storage URL | Files served from local path; upload still works | §24 |
| **AI/ML models** | Predictions/analytics | Required for ML-grade output (fallback still answers) | In-process joblib/pickle load | Artifacts in `backend/app/ai/models/**` | `/ai/hotspot/model-info`, `/ai/risk/model-info`, `/ai/hotspot/health` | Rule-based `FALLBACK` labelled output | §21–23 |
| **LLM (chat)** | AI chat answers | **Optional** | HTTPS to Groq/OpenAI/Gemini | `GROQ_API_KEY` etc. | N/A (per-request) | Local template answers, grounded in retrieved context | §21 |
| **nginx** | Serves frontend + proxies API | **Yes** in single-image deploy | `http://127.0.0.1:8000` backend | Root `nginx.conf` | `curl http://<host>/health` | 502 on `/api` if backend down | §19 |

---

## 3. Prerequisites

| Requirement | Version (from repo config) | Where defined |
|---|---|---|
| Python | **3.12** | `backend/Dockerfile`, CI `python-version: 3.12`, `dev-all.js` |
| Node.js | **20** | CI `node-version: 20`, root `Dockerfile` stage `node:20` |
| npm | any supported by Node 20 | `datathon/package.json` |
| PostgreSQL | **16** | `backend/docker-compose.yml` (`postgres:16-alpine`) |
| Neo4j | **5.24 community** | `backend/docker-compose.yml` (`neo4j:5.24-community`) |
| Docker / Docker Compose | Compose v2 (for containerized ops) | `backend/docker-compose.yml`, root `Dockerfile` |
| `psql` / `pg_dump` / `pg_restore` | matching PG 16 | used in §11/§13/§14 |
| `cypher-shell` or Neo4j Browser | bundled with Neo4j | used in §16/§17 |
| Ports | `8000` (API/uvicorn), `5432` (Postgres), `7687` (Neo4j bolt), `7474` (Neo4j browser), `80` (prod nginx), `5173` (dev Vite) | configs above |

No other external services are required. Optional external services: Supabase (DB/Auth/Storage), Neo4j Aura, and LLM providers (Groq/OpenAI/Gemini).

---

## 4. Environment Variables

The backend reads its environment from `.env` at the **repository root** or at **`backend/.env`** (`backend/app/core/config.py` `SettingsConfigDict(env_file=(ROOT /.env, BACKEND/.env))`). Docker Compose `backend/docker-compose.yml` uses `env_file: .env` relative to `backend/`.

Canonical reference: **`backend/.env.example`** (placeholders only).

| Variable | Purpose | Required | Default | Used by |
|---|---|---|---|---|
| `APP_ENV` | `development`, `production`, `test` | Yes in prod | `development` | backend (locks production safety checks at startup) |
| `APP_DEBUG` / `DEBUG` | Must be `false` in prod (startup-hard-fails otherwise) | Yes in prod | `false` | backend logging/middleware |
| `SAKSHA_DATA_MODE` | `production` \| `demo` \| `test`. Controls demo/fallback data. **Production disables silent demo fallback.** | Yes | `demo` | backend (data mode + provenance endpoints, UI badges) |
| `JWT_SECRET_KEY` | JWT signing secret. Dev/test require ≥64 chars; prod requires ≥80 bits & a strong secret | **Yes** | empty (**startup refuses**) | auth (python-jose) |
| `DATABASE_URL` | PostgreSQL/SQLAlchemy URL (`postgresql+psycopg2://…`) | Either this or the DB var groups + a key | derived | SQLAlchemy engine |
| `SUPABASE_DB_HOST/PORT/NAME/USER/PASSWORD/SSLMODE` | Supabase Postgres direct connection (used to build `DATABASE_URL`) | If using Supabase and no `DATABASE_URL` | — | config builder |
| `POSTGRES_USER/PASSWORD/DB/HOST/PORT/SSLMODE` | Local Postgres variant of the above | If using local PG and no URL | — | config builder |
| `SUPABASE_URL` | Supabase project URL | For Supabase Auth/Storage only | — | auth fallback, evidence/image storage |
| `SUPABASE_ANON_KEY` | Supabase anon (public) key | For Supabase Auth/Storage only | — | evidence storage, auth fallback |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side key. **Never expose to frontend.** | Only for person-image service | — | person image upload |
| `SUPABASE_STORAGE_BUCKET` | Bucket for evidence files (persistent storage) | Optional; if unset → local `UPLOAD_DIR` | `evidence-files` | evidence service |
| `UPLOAD_DIR` | Local upload directory (dev/local fallback only) | Optional | `backend/uploads/` | evidence service |
| `NEO4J_URI` | Bolt URI, e.g. `bolt://host:7687` or Aura URI | Optional (falls back to SQL) | `bolt://localhost:7687` | graph driver |
| `NEO4J_USER` / `NEO4J_USERNAME` | Neo4j username (`NEO4J_USERNAME` is accepted for Aura) | If using Neo4j | `neo4j` | graph driver |
| `NEO4J_PASSWORD` | Neo4j password. Default `neo4j` is rejected in production. | If using Neo4j | `neo4j` | graph driver |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins. **Wildcard `*` is rejected in all environments.** | Yes | onslate.in + localhost list | CORS middleware |
| `LOGIN_MAX_FAILED_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | Brute-force lockout policy | No | `5` / `15` | auth_service |
| `RATE_LIMIT_*` | Per-IP sliding-window limits (general/auth/upload/AI) | No | defaults | rate-limit middleware |
| `MAX_REQUEST_BODY_BYTES` | JSON body cap (2 MB default) | No | `2097152` | request-size middleware |
| `LLM_PROVIDER` | `auto` \| `groq` \| `gemini` \| `openai` \| `local` | No | `auto` | chat LLM generator |
| `GROQ_API_KEY` / `GEMINI_API_KEY` / `OPENAI_API_KEY` (+ `*_MODEL`) | LLM provider keys (comma-separated key rotation supported) | No (local templates otherwise) | — | chat LLM generator |
| `AUTO_RETRAIN_ENABLED` / `AUTO_RETRAIN_MIN_INTERVAL_SECONDS` | Background model staleness retrain | No | `true` / `300` | AI refresh scheduler |

> **Production startup automation (Issue #167):** the backend **refuses to start** in production with an empty/weak JWT secret, wildcard CORS, debug enabled, SQLite database, default Postgres/Neo4j passwords, or a low-entropy secret. Errors are logged with the `PRODUCTION CONFIG ERROR:` prefix and the process raises. Keep `APP_ENV=production` exactly — this validation is your guardrail.

Development vs production configuration is deliberately separate: only prepare `.env` with `<placeholder>`-style values (`<your-…>`) in **development**; production must have real secrets with none of the placeholders below.

---

## 5. Development vs Production

| Aspect | Development | Production |
|---|---|---|
| Base URLs | `http://localhost:5173` (Vite), `http://localhost:8000` (API) | nginx on port `80`; onslate/vanity domain via `ALLOWED_ORIGINS` |
| `APP_ENV` | `development` | `production` |
| `SAKSHA_DATA_MODE` | `demo` (seeded demo data + fallbacks allowed, badges shown) | `production` (no silent demo fallback; provenance labelled) |
| Database | Local Postgres in Docker, or SQLite (auto-seed demo) | **Supabase Postgres or managed PG** — never SQLite |
| Storage | Local `backend/uploads/` | Supabase Storage bucket (else **documented gap** — see §24) |
| Auth | Demo users seeded by `seed_db.py` | Real accounts, strong secrets, restricted CORS |
| Frontend | `npm run dev` with Vite proxy | `npm run build` → static/nginx SPA |
| Models | May use `FALLBACK` | Should be trained + verified (`model-info` → `ML`) |
| Logging | DEBUG to stdout | INFO to stdout + rotated file |

**Rule for operators:** never copy development instructions into production. The safest production surfaces are the **single-container image** (root `Dockerfile`) or a **separate managed backend + static frontend**, both covered below.

---

## 6. Initial Deployment (first-time, end-to-end)

> All commands verified against the repository. Replace placeholders (`<…>`) with your own values. Never commit `.env`.

**Phase A — Prepare environment**

1. Clone the repo and check out the tag/commit you intend to deploy.
2. `cd <repo>`
3. Create your environment file from the template (see §4):
   ```
   copy backend\.env.example backend\.env      # Windows
   cp backend/.env.example backend/.env        # Linux/macOS
   ```
4. Populate real values. For production at minimum: `APP_ENV=production`, `SAKSHA_DATA_MODE=production`, `JWT_SECRET_KEY`, database URL, `ALLOWED_ORIGINS`, `APP_DEBUG=false`, `DEBUG=false`, and (if used) `NEO4J_*`/`SUPABASE_*`/LLM keys.

Generate a JWT secret:
```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Phase B — Database setup**

5. If using Docker for the database stack, start Postgres + Neo4j:
   ```
   docker compose -f backend/docker-compose.yml up -d postgres neo4j
   docker compose -f backend/docker-compose.yml ps        # wait for healthy
   ```
   If using Supabase: create the project, copy the connection credentials into `backend/.env` (`SUPABASE_DB_*`), and skip this step.
6. Verify connectivity:
   ```
   psql "<your DATABASE_URL>" -c "SELECT version();"
   ```
   (For SQLAlchemy URLs, strip the `+psycopg2` dialect and any leading scheme hint.)

**Phase C — Migrations & schema**

7. The backend applies schema at startup: `Base.metadata.create_all(bind=engine)` plus idempotent column migrations (`main.py` startup, `_migrate_*` helpers). **Alembic** is configured (`backend/alembic.ini`, `backend/migrations/env.py`, baseline migration `8e6e75dc04de`) as the official migration tool for future changes.
   Apply the Alembic baseline so the version stamp matches (from `backend/`):
   ```
   py -3.12 -m alembic upgrade head        # Windows
   python3 -m alembic upgrade head         # Linux/macOS
   ```
   → Expected: `Running upgrade 8e6e75dc04de -> 8e6e75dc04de` (baseline no-op) and the `alembic_version` table created.

**Phase D — Optional seed/test data**

8. Development/demo only — never production:
   ```
   py -3.12 -m app.database.seed_db        # from backend/
   ```
   Seeds roles, 7 demo users (incl. `admin`), 31 districts, cases/FIRs/criminals/victims/officers/evidence/notifications/interventions. All rows tagged `dataset_provenance='demo'`. On a fresh SQLite DB the app auto-seeds when the `users` table is empty.

**Phase E — Backend deployment**

9. Options:
   - **Managed run (recommended in production):** run uvicorn behind your own reverse proxy / supervisor:
     ```
     py -3.12 -m pip install -r backend/requirements.txt     # (once, or use a virtualenv)
     cd backend
     uvicorn app.main:app --host 0.0.0.0 --port 8000
     ```
   - **Container:** `docker compose -f backend/docker-compose.yml up -d backend` (builds `backend/Dockerfile`; depends on postgres+neo4j healthy).
10. Verify startup (see §9).

**Phase F — Frontend deployment**

11. Build the frontend:
    ```
    cd datathon
    npm install
    npm run build
    ```
    → outputs `datathon/dist/`.
12. Deploy options:
    - **Single container (frontend+backend+nginx):** build the repo-root `Dockerfile`:
      ```
      docker build -t saksha-full .
      docker run -d --name saksha -p 80:80 --env-file backend/.env saksha-full
      ```
      nginx serves `dist/`, proxies `/api`, `/health`, `/uploads`, `/docs`, `/redoc`, `/openapi.json` to the local uvicorn, and implements the SPA fallback (`try_files $uri /index.html;`) so deep links survive refresh.
    - **Static host (S3/CloudFront/other):** upload `dist/` and configure a **fallback to `index.html`** for any non-asset path (§19 requirement).

**Phase G — Health checks & acceptance**

13. Run §9 health checks and the §39 post-rollout validation checklist.

**Phase H — Production verification**

14. Work through §40. Confirm `/api/v2/system/data-mode` reports `mode: production`.

---

## 7. Normal Startup

**Development (all-in-one):**
```
npm run dev:all
```
Launches backend (uvicorn, reload, `:8000`) and frontend (Vite, `:5173`) via `scripts/dev-all.js`. Or run individually: `npm run dev:backend`, `npm run dev:frontend`.

**Production:**
- Single container: `docker run … saksha-full` / `docker compose up -d backend` (root `Dockerfile` starts uvicorn then nginx via `start.sh`; `supervisord.conf` is an alternative supervisor config present in the repo but `start.sh` is what the image uses).
- Managed: start uvicorn (§6.E), then serve `dist/` behind your web server with the SPA fallback and API proxy.

**Verifying startup (backend):**
```
curl http://localhost:8000/
```
→ `{"message":"SAKSHA Backend is running","docs":"/docs"}`.

Expected healthy boot log:
- `PostgreSQL connection OK`
- `[prewarm] hotspot model loaded` / `risk` / `criminal` / `anomaly` (or `skipped` on first run)
- `Neo4j will be verified lazily on first use`
- No `PRODUCTION CONFIG ERROR` lines.

---

## 8. Backend Operations (start / verify / logs / stop / restart)

| Operation | Command (from `backend/` unless noted) | Notes |
|---|---|---|
| Install deps | `py -3.12 -m pip install -r requirements.txt` | Windows; `python3 -m pip …` on Linux |
| Start | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | Use `--reload` only in dev |
| Verify | `curl http://localhost:8000/health/ready` | expect `"postgresql":"up"` |
| Logs (foreground) | stdout with loguru format | levels: INFO (non-debug), DEBUG only when `DEBUG` enabled |
| Logs (file) | `logs/saksha_backend.log` (relative to working dir) | 10 MB rotation, 30-day retention |
| Stop | `Ctrl+C` / `docker compose stop backend` / `docker stop saksha` | graceful; closes Neo4j driver |
| Restart | start again (above) or `docker compose restart backend` | |

Expected healthy behavior: `/health/ready` → `200` with `"status":"ok","postgresql":"up"`; `/docs` serves the interactive OpenAPI UI; API calls succeed after login.

---

## 9. Backend Health Checks

| Endpoint | Kind | Response | Meaning |
|---|---|---|---|
| `GET /health/live` | **Liveness** | `{"status":"ok"}` | Process is running. |
| `GET /health/ready` | **Readiness** | `{"status":"ok","postgresql":"up","neo4j":"up"}` | **Postgres is required**; Neo4j optional. |
| `GET /health/ready` | Readiness (degraded) | `{"status":"degraded","postgresql":"down"}` or `"postgresql":"up","neo4j":"degraded"` | PG down → overall `degraded`; Neo4j down alone → still `"status":"ok"` (SQL fallback). |
| `GET /health` | Alias of readiness | same | Backwards-compatible. |
| `GET /` | Info | root message + `docs` URL | Service reachable. |
| `GET /docs` `/redoc` `/openapi.json` | Docs | OpenAPI UI / spec | Interactive API reference (restrict in production if desired). |

Health endpoints **do not leak infrastructure details** (no hosts, no error text) — safe to expose to load balancers/orchestrators (verified in `app/main.py`).

The Docker backend image (`backend/Dockerfile`) already defines a container `HEALTHCHECK` hitting `curl -f http://localhost:8000/health`.

---

## 10. Backend Failure Recovery

> General rule: never edit source code as a first recovery step. Check environment/configuration, dependencies, and logs.

### 10.1 Backend won't start

1. **Symptom:** process exits immediately; no HTTP on `:8000`.
2. **Check:** run with output visible; look for `PRODUCTION CONFIG ERROR` / `ValueError`, syntax errors, or dependency errors.
3. **Safe action:** correct `.env` (especially `JWT_SECRET_KEY`, `APP_ENV`, `SAKSHA_DATA_MODE`, `ALLOWED_ORIGINS`); reinstall deps with the pinned ranges; free the port.
4. **Verify:** startup log reaches `PostgreSQL connection OK`; `/health/live` returns ok.
5. **Escalate:** if config is valid and it still fails, escalate with the startup log (ref §30) — include the log, not credentials.

### 10.2 Environment variable missing
- **Symptom:** `JWT_SECRET_KEY must be set in environment` or similar `ValueError`.
- **Check:** `grep` your `.env` and the process env; confirm `.env` is loaded from root or `backend/`.
- **Action:** set the variable (generate JWT secret per §6). **Verify:** restart and hit `/docs`. **Escalate:** never — this is a config fix.

### 10.3 Database (Postgres/Supabase) unavailable
- **Symptom:** startup log `PostgreSQL attempt 1/3 failed` … then either recovery or `running in degraded mode`.
- **What to check:** Postgres health (`docker compose ps postgres`, Supabase dashboard), credentials, network/SSL.
- **⚠ Documented caveat:** `app/database/postgres.py` **silently falls back to a local SQLite file** if Postgres is unreachable at process import time, so a PG outage can masquerade as a working (but non-persistent, separate) database. In production this would be data isolation from the real system of record.
- **Safe action:** do **not** run the backend until Postgres is reachable; verify which DB the app actually opened (startup log + `SELECT 1` on `DATABASE_URL`). Fix PG first, then start the backend.
- **Verify:** `/health/ready` shows `"postgresql":"up"`; a `SELECT count(*) FROM crime_cases;` on your URL returns real data. **Escalate:** if data is unexpectedly missing because of the SQLite detour, involve DB owners immediately.

### 10.4 Supabase unavailable
- **Symptom:** auth fallback failures, storage uploads return local-only, timeouts on `/auth/v1/token`.
- **Check:** Supabase dashboard status; keys present (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, service key).
- **Action:** local auth and local storage continue to work — restart the backend once Supabase is back; **never expose the service-role key** anywhere client-side.
- **Verify:** login with a Supabase-only account; upload a file and confirm a storage URL. **Escalate:** if Supabase is the authoritative DB and it's down, treat as §11 outage.

### 10.5 Neo4j unavailable
- **Symptom:** `/health/ready` reports `"neo4j":"degraded"`; network pages still load (SQL fallback).
- **Check:** Neo4j container/browser on `:7474`; credentials.
- **Action:** restore/restart Neo4j; then re-sync from Postgres (§16 `POST /network/sync-neo4j`).
- **Verify:** `/health/ready` → `"neo4j":"up"`; network API returns graph. **Escalate:** not required unless graph intelligence is a contractual SLA (documented optional).

### 10.6 Storage unavailable
- **Symptom:** uploads work but return local paths; `http 500` on `/uploads/`.
- **Check:** `SUPABASE_STORAGE_BUCKET`/`SUPABASE_URL`/anon key; local `UPLOAD_DIR` exists and is writable.
- **Action:** disk/perm fix or restore Supabase Storage; restart backend.
- **Verify:** upload a test file, download it back. **Escalate:** if evidence files are purged/undownloadable.

### 10.7 AI service / model unavailable
- **Symptom:** prediction endpoints return `prediction_mode: "FALLBACK"`; `/ai/hotspot/health` → `{"status":"unavailable"}`.
- **Check:** `backend/app/ai/models/**` artifacts exist and are valid; `model-info` endpoint status.
- **Action:** run training (§22) or restore artifacts; do **not** present fallback output as model output.
- **Verify:** `model-info` shows `prediction_mode: "ML"`. **Escalate:** if predictions feed into operational decisions and are incorrectly labelled.

### 10.8 Invalid configuration
- Same as §10.1. Production config validation runs automatically at startup (Issue #167) — trust the error messages.

### 10.9 Port already in use
- **Symptom:** `[Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)` / address-in-use.
- **Check:** `netstat -ano | findstr :8000` (Windows) / `ss -ltnp | grep 8000` (Linux).
- **Action:** identify and stop the other process, or change the port (documented config change). **Verify:** curl liveness. **Escalate:** only if the owning process is unknown/non-cooperative.

### 10.10 Migration failure
- **Symptom:** startup `migration skipped:` warnings, or Alembic errors.
- **Check:** last migration state (`alembic history`), DB connectivity, table state (`\dt` in psql).
- **Action:** the startup DDL is idempotent and non-destructive — safe to rerun a release/restart. For Alembic, back up first, fix the failed migration, re-run `alembic upgrade head`.
- **Verify:** `\dt` shows expected tables; reports/notifications/evidence endpoints work. **Escalate:** if a migration left the schema half-applied.

---

## 11. Database Operations (PostgreSQL / Supabase)

Two authoritative deployment modes exist; choose one per environment (do **not** point the same process at both):

| Mode | Authoritative DB | How configured |
|---|---|---|
| Supabase | Supabase-managed Postgres 16 | `SUPABASE_DB_*` (direct connection, `sslmode=require`) or a full `DATABASE_URL` pointing at Supabase |
| Local/Docker | `postgres:16-alpine` container | `docker compose -f backend/docker-compose.yml up -d postgres`; `POSTGRES_*`/`DATABASE_URL` |

- **Connection verification:**
  ```
  psql "<DATABASE_URL>" -c "SELECT 1;"
  docker compose -f backend/docker-compose.yml exec postgres pg_isready -U <user>
  ```
- **Schema verification:** list tables and confirm version stamp:
  ```
  psql "<DATABASE_URL>" -c "\dt"
  psql "<DATABASE_URL>" -c "SELECT version_num, version_num = '8e6e75dc04de' FROM alembic_version;"
  ```
- **Maintenance considerations:** SQLAlchemy pools are small (`pool_size=3`, `max_overflow=7`, `pool_recycle=120`, `statement_timeout=30s`) — routine VACUUM/analytics should be scheduled off-peak; the connection string must allow the app user to create tables on startup (`create_all`).

Supabase-specific operations (§15): the database is managed via the Supabase dashboard; direct DDL from the app requires the database password set in `SUPABASE_DB_PASSWORD`. The service-role key is for the REST/admin API only and must remain server-side.

---

## 12. Database Migrations

- **Tooling:** Alembic (configured: `backend/alembic.ini`, `backend/migrations/env.py`; baseline revision `8e6e75dc04de` = current schema snapshot). New schema on fresh DBs is also applied automatically by `create_all()` plus idempotent `ALTER TABLE` DDL at backend startup (`main.py` `_migrate_*` helpers). Both are safe and additive.
- **Workflow** (production):
  1. **Back up** the database first (§13).
  2. **Verify environment**: correct `DATABASE_URL`, Postgres reachable, `APP_ENV` as expected.
  3. **Verify current version**: `alembic history` and `alembic current` (from `backend/`).
  4. **Apply**:
     ```
     py -3.12 -m alembic upgrade head        # or python3 -m alembic upgrade head
     ```
  5. **Verify**: `alembic current`; spot-check a migrated column/table in `psql`.
  6. **Restart the backend** (schema checks + DDL run at boot).
  7. **Acceptance**: run the §39 validation.
- **Creating new migrations** (developers): `py -3.12 -m alembic revision --autogenerate -m "description"`.
- **Caveat:** never run destructive downgrades against production without a tested backup. No rollback of the additive startup DDL is supported; the design is forward-only + backups.

---

## 13. Database Backup

- **What to back up:** the entire Postgres schema + data (all 16+ tables). Model artifacts and uploads are separate (§22/§24).
- **How:** use the standard Postgres tooling. For the Docker Postgres:
  ```
  docker compose -f backend/docker-compose.yml exec postgres pg_dump -U <user> -d <db> -Fc -f /tmp/saksha_$(date +%F).dump
  docker compose -f backend/docker-compose.yml cp postgres:/tmp/saksha_$(date +%F).dump ./saksha_$(date +%F).dump
  ```
  For Supabase/direct:
  ```
  pg_dump "<DATABASE_URL>" -Fc -f saksha_$(date +%F).dump
  ```
- **Frequency / storage / access:** ⚠ **documented gap** — *no automated backup job exists in the repository.* There is no backup scheduler, off-site store, or retention policy implemented. Define one operationally (e.g. nightly scheduled `pg_dump` to a secured object store, restricted to DB owners), or rely on the provider's managed backup SLA (Supabase offers daily backups — verify retention in the dashboard).
- **Integrity verification:** restore a copy into a scratch database and count rows:
  ```
  pg_restore -l saksha_<date>.dump | head
  ```
  and compare `SELECT count(*) FROM crime_cases;` on source vs restored.

---

## 14. Database Restore

**Safe restore procedure (never blind-restore into production):**

1. **Locate the newest good backup** (§13).
2. **Restore into a safe environment first**:
   ```
   createdb "<DATABASE_URL>" saksha_restore_test   # adjust per your tooling
   pg_restore -d "<DATABASE_URL>" -Fc saksha_<date>.dump
   ```
3. **Verify schema**: `\dt` and table counts match the source (spot-check `crime_cases`, `firs`, `criminals`, `users`).
4. **Verify data**: recent records present; demo seed vs live provenance sane (`SELECT dataset_provenance, count(*) FROM crime_cases GROUP BY 1;`).
5. **Verify application connectivity**: point the backend `.env` `DATABASE_URL` at the restored DB, start it, hit `/health/ready`.
6. **Acceptance tests**: §39.
7. **Restore production**: only after the above passes — stop app writers, drop/recreate the target, restore, verify, restart backend.

⚠ Restoring while the app is live can lose writes; schedule maintenance windows.

---

## 15. Supabase Operations

The backend uses Supabase for three optional surfaces:

| Surface | Used when | Config |
|---|---|---|
| **Postgres database** | `SUPABASE_DB_*` or `DATABASE_URL` pointing at Supabase | `SUPABASE_DB_HOST/PORT/NAME/USER/PASSWORD/SSLMODE` |
| **Auth** (REST) | logins by users unknown to the local `users` table | `SUPABASE_URL` + `SUPABASE_ANON_KEY` (`POST /auth/v1/token`) |
| **Storage** (evidence + person images) | evidence uploads & image URLs | `SUPABASE_URL`, `SUPABASE_ANON_KEY` (evidence), **`SUPABASE_SERVICE_ROLE_KEY`** (person images) |

- **Required keys:** anon key (public, safe for the backend but never the browser), service-role key (**server-only; never in frontend/env examples or logs**).
- **Connectivity checks:**
  ```
  psql "<SUPABASE direct URL>" -c "SELECT 1;"
  curl -s "https://<project-ref>.supabase.co/rest/v1/" -H "apikey: <anon-key>"
  ```
- **Storage verification:** upload an evidence file via the UI/API and confirm `storage_url` is returned and the public URL is retrievable.
- **Common failure scenarios:** wrong pooler vs direct host, expired anon/service keys, bucket not created (`evidence-files`), RLS blocking storage reads. Supabase dashboard > Storage > buckets and > API settings resolve most.
- **Service-role handling:** store in server env only; rotate immediately if ever exposed; never log it.

---

## 16. Neo4j Operations

- **Start (Docker):**
  ```
  docker compose -f backend/docker-compose.yml up -d neo4j
  ```
  Container `saksha_neo4j`, image `neo4j:5.24-community`, **graph-data-science plugin** enabled, ports `7474` (browser) and `7687` (bolt). For Neo4j Aura, use the provided URI/credentials in `.env` (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`).
- **Connection configuration:** `NEO4J_URI` (default `bolt://localhost:7687`), `NEO4J_USER`/`NEO4J_USERNAME`, `NEO4J_PASSWORD`. Production startup **fails** if the password is still `neo4j`.
- **Health check:** `/health/ready` field `neo4j`; or on the container `docker compose ps neo4j`; or browse `http://localhost:7474` and run `RETURN 1`.
- **Authentication:** configured via `NEO4J_AUTH` in compose (`user/password`) or Aura credentials.
- **Schema/constraints:** applied automatically by the sync client (`_ensure_constraints`) and documented in `backend/neo4j/schema.cypher` (constraints + index + sample graph).
- **Database verification:**
  ```
  MATCH (n) RETURN labels(n), count(*) AS c ORDER BY c DESC;
  CALL db.constraints();
  MATCH (n) WHERE NOT n.id RETURN labels(n) LIMIT 5;
  ```
- **Restart:** `docker compose restart neo4j` (data persists in the `neo4j_data` volume; Aura is externally managed).
- **Backup/recovery:** for Docker, back up the `neo4j_data` volume (`docker run --rm -v saksha_neo4j_data:/data -v $(pwd):/backup alpine tar czf /backup/neo4j_data.tgz -C /data .`); for Aura, use provider-managed snapshots. ⚠ Aura periodic backup is provider-managed — verify availability.
- **Troubleshooting:** auth failures (credentials; default password rejected in prod), port conflicts on `7687`/`7474`, GDS plugin not loading (image + plugin flag), connectivity from backend (firewall to Aura).
- **Failure behavior when required:** Neo4j is **optional**. When unavailable, the app operates in **PostgreSQL fallback mode** — the network APIs reconstruct the graph from SQL. This is not "Neo4j healthy"; `/health/ready` will say `neo4j: degraded`, so monitoring is unambiguous.

---

## 17. Neo4j Data Consistency (Postgres ↔ Neo4j)

- **Synchronization mechanism:** explicit, operator- or admin-triggered. `POST /api/v2/network/sync-neo4j` (roles `admin`, `crime_analyst`) merges all 8 node types and 7 relationship types from Postgres into Neo4j, creating uniqueness constraints first.
- **Triggering:** after Neo4j is restored, or after bulk ingestion/imports, re-sync:
  ```
  curl -X POST http://<host>/api/v2/network/sync-neo4j \
       -H "Authorization: Bearer <access-token>" -H "Content-Type: application/json"
  ```
  Response `"neo4j_active": true` with node/edge counts, or `"status":"warning"` + `"neo4j_active": false` when Neo4j is down.
- **Verification:** compare counts between Postgres and Neo4j (e.g. criminals, cases) after sync.
- **Last-sync status:** ⚠ **documented gap** — there is no persisted "last synchronized at" metric or scheduled resync job in the repository. Treat `sync-neo4j` as a manual maintenance task (schedule it operationally after every import wave).
- **Failure handling:** if sync returns `status: 0`/unavailable, no changes are made; resolve Neo4j connectivity, then rerun.

---

## 18. Frontend Operations

- **Dependency installation:**
  ```
  cd datathon
  npm install
  ```
- **Environment configuration:** the API base URL is a build-time value:
  - Default: relative `/api/v2` (same origin as the page — correct behind the repo's nginx and the Vite dev proxy).
  - Override with `VITE_API_BASE_URL` (e.g. `https://api.example.com/api/v2`). Set in a `datathon/.env.*` file before `npm run build`. **No other frontend env vars exist** (verified in `src/services/api.ts`).
  Nothing secret should ever be placed in frontend build-time env vars — the frontend bundle is public.
- **Development startup:** `npm run dev` → Vite on `:5173`; it **proxies** `/api`, `/health`, and `/uploads` to `http://127.0.0.1:8000` (`vite.config.ts`). No CORS needed in dev.
- **Production build:**
  ```
  npm run build
  ```
  → `tsc -b && vite build` → `datathon/dist/`.
- **Production deployment:**
  - Single-container image: repo-root `Dockerfile` (builds frontend then packages it with nginx + backend).
  - Static hosting: serve `dist/` and satisfy the routing requirement below.
- **Frontend health / API endpoint config:** load `/ -> /dashboard`, log in; verify `network`, `hotspots`, `predictions`, `reports` tabs call `/api/v2/*` successfully (open DevTools → Network).
- **Rendering/refresh requirements:** you must handle client-side routing — see §19.

---

## 19. Frontend Routing

The app is a **client-side routed React SPA**. After a browser refresh on `/dashboard`, `/network`, `/hotspots`, `/predictions`, `/reports`, etc., the server must return the app shell.

- The repo's `nginx.conf` does this with:
  ```nginx
  location / {
      try_files $uri /index.html;
  }
  ```
  (`scripts/check_spa_routing.py` validates this in CI.)
- **Requirement for any custom host:** configure a **fallback to `index.html`** for all non-asset paths (NGINX `try_files $uri /index.html;`, S3/CloudFront error-document → `index.html`, Vercel/Netlify SPA rewrites). Do not assume a web server auto-supports SPA routing.
- Static asset paths are referenced as `/assets/...` — serve `dist/` at the root.

---

## 20. Frontend Failure Recovery

| Problem | Check | Action | Verification |
|---|---|---|---|
| **Blank page** | Browser console for JS errors; confirm `dist/` built | Rebuild (`npm run build`), redeploy; clear cache | Dashboard renders |
| **API connection failure** | DevTools Network; backend `/health/live` | Restart backend; check proxy/nginx | API calls reach `200` |
| **Incorrect backend URL** | `VITE_API_BASE_URL` baked at build time; nginx `/api/` proxy target | Rebuild with correct URL/`nginx.conf` `proxy_pass http://127.0.0.1:8000` | Login works from the public URL |
| **CORS failure** | Browser console `Access-Control-Allow-Origin` | Add the frontend origin to `ALLOWED_ORIGINS` (no wildcard allowed) | API calls no longer CORS-blocked |
| **Authentication failure** | `/api/v2/auth/me` with the token; token expiry (30 min) | Refresh token via `/api/v2/auth/refresh`; verify user active | Dashboard loads with session |
| **Stale frontend build** | `dist/` asset hashes old; compare deployed vs `npm run build` | Redeploy fresh build; hard-refresh | New features/changes visible |
| **Route refresh failure (404)** | Hit `/<route>` directly in a new tab | Ensure SPA fallback → `index.html` (§19) | Refresh on any route loads the app |

---

## 21. AI/ML Operations

- **Architecture:** inference modules under `backend/app/ai/inference/` load artifacts from `backend/app/ai/models/<family>/` via `lru_cache` singletons; a startup **prewarm** thread warms them; a 5-minute background refresh compares artifact staleness against DB and can trigger throttle-guarded retrains (`AUTO_RETRAIN_ENABLED`, min interval 300 s).
- **Model families and artifacts:**
  - **Hotspot** (`models/hotspot/`): `hotspot_model.pkl`, `feature_columns.json`, `model_metadata.json`, `training_metrics.json`.
  - **Risk/forecast** (`models/risk/`): `risk_model.pkl`, `forecast_model.pkl`, `model_metadata.json`, `training_metrics.json`, `*_model_meta.json`.
  - **Criminal** (`models/criminal/`): `risk_scorer.json`, `repeat_offender.json`, `similarity.json`, `clustering.json`, `training_metrics.json`.
  - **Anomaly** (`models/anomaly/`): in-memory/threshold models.
  - **RAG chat** (`models/rag/`): rule-based chat model + in-memory vector store (`app/ai/vectorstore/memory.py` — **not persistent across restarts**, §24 gap note).
- **Model status (ML vs FALLBACK vs UNAVAILABLE) — how to tell:**
  - `GET /api/v2/ai/hotspot/model-info` → `"prediction_mode": "ML" | "FALLBACK"`, `"validation_status"`, `"model_loaded"`, version, RMSE/MAE/R².
  - `GET /api/v2/ai/hotspot/health` → `{"status":"ok"|"unavailable", …}`.
  - Prediction responses carry `"prediction_mode": "ML" | "FALLBACK"` per batch (never silently pass fallback output as model output — enforced in code and by the data-mode rules).
  - `GET /api/v2/ai/predictions/model-info` (risk family), `GET /api/v2/ai/predictions/refresh-status`, `GET /api/v2/ai/predictions/health` exist for the risk/forecast family.
- **Feature schema:** each family ships validated feature definitions; inference validates required input columns before prediction and blocks with a clear error (`422` + message) rather than running on broken features.
- **Fallback behavior:** without an artifact, hotspot/risk/criminal/anomaly produce rule-based results labelled `FALLBACK`; the RAG chat produces **local-template answers grounded only in retrieved context** when no LLM provider key is configured. `LLM_PROVIDER=auto` rotates Groq → Gemini → OpenAI → local templates.
- **Deployment/validation:** `backend/app/services/model_validation_service.py` validates artifacts (pickle + metadata + feature columns + metrics) — callable programmatically; CI/`mlops` workflows exercise the registry. Module docs in `docs/ai/predictive_models.md`.

---

## 22. Model Deployment (artifacts)

- **Where artifacts are stored:** in-repo runtime path `backend/app/ai/models/**` (the versioned MLOps registry lives under `mlflow/` at the repo root).
- **How they are loaded:** inference modules `joblib/pickle`-load the files at `models/<family>/*` with `lru_cache`; `invalidate_caches()` forces reload after promotion/retrain.
- **Expected metadata:** `model_metadata.json` (name, algorithm, version, training/validation windows, row counts, feature count), `training_metrics.json` (RMSE/MAE/R² per family), `feature_columns.json` (hotspot). Do not store secrets in these files.
- **Versioning:** `mlflow/` registry (`app/mlops/registry.py`) records `version` + `stage` + dataset snapshots and metrics paths; `deploy.py` handles promotion. The in-repo `models/**` files are the *active* artifacts the runtime loads.
- **Training/refresh commands:**
  - Scheduled MLOps cycle (CI or manually): `py -3.12 -m app.mlops` (from `backend/`) → JSON report of retrain per model, registry registration, monitoring snapshot, deployment to production stage.
  - On-demand API: `POST /api/v2/ai/risk/train` (admin), `POST /api/v2/ai/criminal/…` (retrain endpoint, admin), plus `mlops` CLI (`app.mlops` / `app.mlops retrain`).
- **Validation:** use `model-validation` artifacts checks (e.g. pickle loadable, feature columns match, metrics present) before promoting; CI `ci.yml` runs model validation tests.
- **Rollback:** keep the previous `models/<family>` files (or registry `stage`), swap the directory contents, and call `invalidate_caches()` / restart the backend to reload. See §31.

---

## 23. Model Failure Recovery

| Failure | Expected behavior | Operator action |
|---|---|---|
| **Missing model** | Inference returns labelled `FALLBACK` output; `model-info` → `prediction_mode: "FALLBACK"`, `validation_status: "FALLBACK"` | Check `models/<family>/`; run training or restore artifacts |
| **Invalid/corrupt model** | `model-info` may `500`/`503` ("artifact is corrupt"); hotspot inference raises on corrupt artifact then falls back via `_try_load_model` | Replace artifact from registry/backup; reload (restart) |
| **Feature mismatch** | Inference blocked with a `422` naming the missing required fields | Align the input schema with `feature_columns.json` / required columns |
| **Provider unavailable (LLM)** | Chat answers fall back to local templates grounded in retrieved context (no outage) | Optionally add/rotate provider keys; nothing to fix for correctness |
| **Retrain/refresh failure** | Background refresh logs `[bg-refresh] error` at DEBUG and retries next cycle | Inspect logs; ensure DB reachable; optionally run `python -m app.mlops` manually |

**Hard rule (operators):** never relabel `FALLBACK`/`UNAVAILABLE` results as "ML" or "live". The UI shows DEMO/FALLBACK badges from `/api/v2/system/data-mode`; respect them.

---

## 24. Storage Operations

| Bucket | Type | Location | Persistence |
|---|---|---|---|
| Evidence files | Uploaded via `/api/v2/evidence/*/upload` | Supabase Storage bucket (`SUPABASE_STORAGE_BUCKET`, default `evidence-files`) **or** local `UPLOAD_DIR` (default `backend/uploads/`) | Supabase = persistent; local = single-instance only |
| Person images | `image_url` on criminals/victims/officers | Supabase Storage | persistent |
| Model artifacts | Trained models | `backend/app/ai/models/**` + `mlflow/` registry | persistent on disk/volume |
| Reports | Exports | generated in-process; file downloads (`/api/v2/reports/export`) — report metadata + snapshots in DB | DB-persistent metadata; files ephemeral |
| Logs | Loguru | `logs/saksha_backend.log` + stdout | 10 MB rotation / 30-day retention |
| RAG vector store | In-memory (SHA-256 embeddings) | `app/ai/vectorstore/memory.py` | **Not persistent** across restarts (documented gap) |

- **Frontend/nginx:** the single-image nginx config proxies `/uploads/` to the backend and sets `client_max_body_size 100M`. Backend caps evidence files at **50 MB** (`MAX_FILE_SIZE_MB`, hard-coded in `evidence_service.py`).
- **Temporary vs persistent:** the local `backend/uploads/` directory is the **temporary/local** path; production **must** configure `SUPABASE_STORAGE_BUCKET` (or otherwise persist uploads), otherwise evidence files are lost when the instance is replaced — that is a **documented gap** if not configured.
- **Retention:** no automated archival/retention policy for uploads is implemented — define one operationally.
- **Verification:** upload a file via the Evidence UI; confirm `storage_url` returned; download it back; check object in Supabase dashboard when configured.

---

## 25. Authentication & Security Operations

- **Configuration:** `JWT_SECRET_KEY` (HS256), access 30 min, refresh 7 days; Argon2id password hashing with transparent upgrade from legacy SHA-256 hashes on successful login.
- **Session behavior:** access token short-lived; refresh tokens rotate and are tracked server-side via a `RevokedToken` jti denylist; logout revokes outstanding tokens.
- **Brute-force protection:** `LOGIN_MAX_FAILED_ATTEMPTS` (5) → lockout `LOGIN_LOCKOUT_MINUTES` (15); failure counter on `users.failed_login_attempts`, `users.locked_until`. The login UI surfaces this state: each failed attempt shows "N attempt(s) remaining before the account is temporarily locked." as an amber warning, and the attempt that trips the threshold (or any attempt while locked) shows the lockout message with the countdown. Admin unlock: `POST /api/v2/admin/users/{id}/reset-password` clears `failed_login_attempts`/`locked_until` (or clear the DB fields directly).
- **Rate limiting:** in-memory sliding window per client IP — 300 req/min general, 20 auth, 30 upload, 40 AI. Behind the packaged nginx proxy the socket peer is always the proxy, so `RATE_LIMIT_TRUST_XFF=true` (default) keys budgets on the real client IP from the nginx-forwarded `X-Forwarded-For`/`X-Real-IP` headers — otherwise every user is throttled as one shared IP and genuine users get mass 429s. Set it to `false` only if the backend is directly exposed without a trusted proxy. ⚠ Per-instance (documented in `.env.example`): for multi-instance deployments add an external limiter.
- **Password/user administration:** admins create users via `/api/v2/auth/register` (admin only) and the admin user-management endpoints (`/api/v2/admin/*`). Password policy: 6-digit numeric PIN **or** ≥8 chars with upper/lower/digit.
- **Role management:** 7 roles; RBAC enforced route-level (`require_roles`) and in the UI (RoleGuard). Roles: `admin`, `crime_analyst`, `investigator`, `inspector`, `policymaker`, `officer`, `forensic`, `viewer` (role table superset — seed defines 7; refer to `backend/app/auth/rbac.py`).
- **Secret rotation (JWT):** 1) generate new secret; 2) update `.env`; 3) restart backend; 4) re-issue tokens to users (existing tokens signed with the old secret will fail validation once rotated — acceptable during rotation windows; schedule it).
- **Authentication troubleshooting:** lockout messages ("Account temporarily locked"), expired access token (`401`) → refresh; unknown user → optional Supabase Auth fallback path (§15).

---

## 26. Production Security Checklist

Automated checks already in place (don't duplicate): startup **production config validation** (Issue #167 — JWT entropy, CORS wildcard, debug, SQLite, default DB/Neo4j passwords) and CI **secret scan** (`scripts/check_secrets.py`), **npm audit** + **pip-audit** (CI security-scan job).

Manual pre-start verification:

- [ ] `JWT_SECRET_KEY` set, generated via `secrets.token_urlsafe`, ≥80-bit entropy (backend enforces)
- [ ] No default/placeholder secrets anywhere in `.env` (`<your-…>` must be real values)
- [ ] No empty production secrets (`APP_DEBUG`, `DEBUG`, storage, DB)
- [ ] `ALLOWED_ORIGINS` explicit, no `*` (backend enforces)
- [ ] `APP_DEBUG=false`, `DEBUG=false`
- [ ] Database credentials configured for the chosen authoritative DB (Supabase or Docker PG)
- [ ] Supabase credentials configured where used; **service-role key server-side only**
- [ ] Neo4j credentials configured where used; password **not** `neo4j` in production (backend enforces)
- [ ] Storage configured (`SUPABASE_STORAGE_BUCKET`) or local `UPLOAD_DIR` acceptable for the environment
- [ ] Frontend points at the correct backend URL (default same-origin `/api/v2` → validated nginx proxy)
- [ ] No secrets in the frontend build (`VITE_*` build-time env only for non-secret URL config)
- [ ] Secrets never present in logs (enforced by logging config — credentials are not logged)

---

## 27. Normal Operations (daily/regular checks)

Use only what the system actually exposes:
- **Backend health:** poll `GET /health/live` + `/health/ready` (up; `postgresql: up`).
- **Database health:** `pg_isready` / `/health/ready`; table counts; cheap `SELECT 1`.
- **Neo4j health:** `/health/ready` `neo4j` field; browser `:7474`; Postgres↔Neo4j sync status via the sync endpoint (manual).
- **Storage health:** test upload/download; disk usage of `UPLOAD_DIR`; Supabase bucket status.
- **AI/model health:** `/api/v2/ai/hotspot/model-info` (and risk equivalent) — confirm `prediction_mode` stays `ML` when expected; `training_metrics` sane.
- **Disk/log usage:** `logs/saksha_backend.log` size/rotation; Docker volumes.
- **Error logs:** grep for `ERROR`, `PRODUCTION CONFIG`, `migration skipped`, `[prewarm] … skipped`, `STORAGE`.
- **Failed jobs/imports:** `/api/v2/data-import/jobs` → look for non-`promoted`/`review` states; quality grades.
- **Alert generation:** `/api/v2/alerts/*` and notifications; confirm alert statuses move to acknowledged/resolved.

---

## 28. Monitoring

| Where to look | What | Source of truth |
|---|---|---|
| `GET /health/live`, `/health/ready` | Liveness/readiness | Backend HTTP |
| Backend console/stdout | Runtime logs (loguru) | uvicorn/container |
| `logs/saksha_backend.log` | Rotated file log (10 MB / 30 d) | Filesystem |
| Docker | `docker compose ps`, `docker logs backend`, volume usage | Docker |
| Neo4j Browser `:7474` | Graph DB status | Neo4j |
| PostgreSQL | `pg_isready`, `pg_stat_activity` | Postgres |
| **GitHub Actions** | CI status (`.github/workflows/ci.yml`, `mlops.yml`) | GitHub |
| Supabase dashboard | DB metrics, storage, auth | Supabase |

**⚠ Documented gap — Prometheus:** `monitoring/prometheus.yml` defines a scrape job for `backend:8000/metrics`, but **the backend does not implement a `/metrics` endpoint** (no `prometheus_client` in the codebase). Do not rely on it: add the endpoint or wire an exporter, otherwise the scrape will fail. Until then the checks above are the monitoring surface.

**MLOps monitoring:** `backend/app/mlops/monitoring.py` records per-model snapshots and `drift.py` compares features against `monitoring/drift_rules.json` thresholds (risk_score 0.20, open_case_ratio 0.18, crime_volume 0.25, default 0.15) during `python -m app.mlops` cycles.

---

## 29. Logging

- **Where stored:** stdout (console) + `logs/saksha_backend.log` (created relative to the working directory, i.e. `backend/` when run there; in the single-image container it's under `/app/logs/`). In Docker, `docker logs saksha_backend` / `docker logs saksha`.
- **Levels:** `INFO` by default; `DEBUG` only when `APP_DEBUG`/`DEBUG` are enabled (envs force-disabled in production).
- **Useful error patterns to watch:**
  - `PRODUCTION CONFIG ERROR|WARNING` — config guardrail.
  - `PostgreSQL attempt N/3 failed` / `running in degraded mode`.
  - `[STORAGE] DATABASE_URL is SQLite` — warns of the non-persistent fallback.
  - `[prewarm] <family> skipped: …` — model artifact issues at boot.
  - `[bg-refresh] error` (debug) — background staleness checks.
  - `* migration skipped:` — idempotent DDL failures (usually non-fatal).
- **Retention:** 10 MB rotation, 30 days (loguru config).
- **Sensitive data in logs:** configured so that credentials/secrets are not logged; never paste `.env` content or tokens into incident tickets.

---

## 30. Incident Response

Workflow: **Detect → Assess → Contain → Recover → Verify → Document**.

| Incident | Immediate action | Service impact | Recovery | Validation | Escalation |
|---|---|---|---|---|---|
| **Database outage** | Confirm PG/Supabase status; prevent backend SQLite fallback while down; do not restart backend until PG is up (see §10.3) | All persistence-dependent features fail/degrade | Restore/restart PG; verify data; restart backend; run imports reconciliation | `/health/ready` OK; `plans`/case counts match | DB owners + application lead |
| **Backend outage** | Check process/logs; `PRODUCTION CONFIG ERROR`? | All APIs down (frontend 502) | Fix config or restart service/container | `/health/live` + `/health/ready` ok | Platform lead |
| **Neo4j outage** | Check neo4j container/Aura status | Network pages show SQL fallback; sync blocked | Restart neo4j; `POST /network/sync-neo4j` | `/health/ready` neo4j up; graph queries work; counts match | Network-intelligence owner |
| **Authentication failure / lockouts** | Check `users.locked_until`, JWT rotation timing, Supabase auth | Login broken for affected users | Reset lockout (`users.failed_login_attempts`/`locked_until`), rotate secret carefully | Test login as affected user | Security owner |
| **Data corruption** | Halt writes if possible; preserve evidence | Integrity risk | Restore nearest good DB backup into staging; verify; promote | Row-count + provenance checks §14 | DB owners + security |
| **Storage failure** | Check Supabase bucket/disk | Uploads fall back to local; downloads may 404 | Restore bucket/disk; re-upload evidence if lost | Upload/download test | Storage owner |
| **AI/model failure** | Note `prediction_mode`/`model-info` | Predictions in `FALLBACK`; chat → local templates | Retrain or restore artifacts; restart | Model-info shows `ML` | ML owner |
| **Security config failure** | Backend refuses start (guardrail) | Platform down (by design) | Fix `.env` per §26 and restart | Startup clean; secret scan passes | Security owner |

**Documentation:** after recovery, file an incident note: detection time, impact window, root cause, actions, validation, and any runbook updates needed.

---

## 31. Rollback

| Component | How to roll back | Notes |
|---|---|---|
| **Frontend** | Redeploy the previous successful build/image (keep the previous `dist/` or tagged container image) | Static assets + SPA fallback unchanged; no DB dependency |
| **Backend** | Redeploy the previous backend image/commit; startup DDL is additive and idempotent, so an old build is compatible | If code behaves against new columns, ensure schema is retained (do **not** need to drop them) |
| **Database migration** | Forward-only design + backups: restore the pre-migration backup (§14) into a maintenance window; never `alembic downgrade` blindly on live data | Alembic downgrades do not exist for the baseline; prefer backup restore |
| **Model version** | Replace `backend/app/ai/models/<family>/*` with the previous registry artifacts and restart (or call cache invalidation) | Preserve `training_metrics.json`/metadata with the artifacts |
| **Configuration** | Restore the previous `.env`/env-file and restart | Verify `ALLOWED_ORIGINS`, data mode, secrets consistent |

Generic rule: roll forward is preferred; roll back by **reverting the artifact**, then **re-verify** (§39), then **document**.

---

## 32. Maintenance

| Task | Frequency | Responsible | Verification |
|---|---|---|---|
| Dependency updates (backend `requirements.txt`, frontend `package.json`) | As CI/audit flags (npm audit, pip-audit in CI) | Dev/Platform | CI passes; app smoke-tested |
| Database maintenance (VACUUM, index/statistics) | Off-peak, as needed | DB owner | `pg_stat_*` health; query latency */
| Evidence/upload storage cleanup | As retention policy defined (none automated — define) | Storage owner | Bucket/disk usage reduced per policy |
| Report archival | As lifecycle completes (`archived`, retention) | Report owner | Reports endpoint shows archived state |
| Audit `audit_logs` retention | As policy defined (none automated) | Security | Table size bounded |
| Model refresh/retrain | Continuous (`AUTO_RETRAIN`) + MLOps cycle (§22) | ML owner | `model-info` fresh; metrics in `training_metrics.json` |
| Neo4j maintenance | After imports; on restore | Platform | Graph counts match Postgres (§17) |
| Security key rotation (JWT/Supabase) | On exposure or policy interval | Security | Login works; no old keys in use |
| Backup verification | Before any migration; periodically | DB owner | §13/§14 restore drill |

---

## 33. Data Import Operations (CCTNS/ICJS-style ingestion)

Endpoints (all under `/api/v2/data-import/`; admin-gated where enforced in the route module):

```
GET  /entities                         # supported entity types + column profiles
GET  /template/{entity_type}?export_format=csv|xlsx   # downloadable mapped template
POST /preview                         # parse + validate upload → column mapping + row report
POST /commit                          # persist valid rows (supports dry_run)
GET  /jobs                            # import job audit trail
GET  /jobs/{job_id}                   # single job
GET  /jobs/{job_id}/quality           # recomputed quality grade + metrics
GET  /jobs/{job_id}/records           # row-level outcomes
POST /jobs/{job_id}/promote           # promote staged/valid rows to live
POST /jobs/{job_id}/rollback          # roll back a promoted job
GET  /lineage/{entity_type}/{record_id}  # per-record lineage/provenance
```

Operator workflow: **upload → preview (validate/map) → commit (stage) → quality review → promote**. Imported rows are tracked by `import_jobs` with metrics (new/matched/updated/conflict/invalid/duplicate/review), a quality grade, provenance columns (`dataset_provenance`, `source_import_job_id`, `source_file`, `source_row_ref`) and `status` (draft → committed → promoted → rolled_back). **Promotion is explicit and admin-driven** — staged data is never silently live. `compute_quality_grade` uses the actual job metrics. Failure recovery: failed/preview rows are reported per-row; fix the file and re-preview. Roll back a bad promotion with `POST /jobs/{job_id}/rollback` and inspect `lineage`.

---

## 34. Report Operations

- **Lifecycle:** reports move through `generated` → `reviewed` → `finalized` → `archived` states (columns `generated_at/reviewed_at/finalized_at/archived_at`, `version`, `provenance`, `integrity_hash`, `content_snapshot`). Only **finalized** reports are authoritative.
- **Endpoints:** `/api/v2/reports/*` — list, statistics, preview, generate, export (PDF/DOCX/TXT/CSV/XLSX).
- **Audit:** `audit_logs` record report actions (adds `result`/`metadata`); `integrity_hash` allows verifying a downloaded report against its snapshot.
- **Storage/download/archival:** exports are generated on demand; metadata + content snapshots persist in the DB. **Documented gap:** no automated report archival job exists in the repo — schedule retention operationally.
- **Operator rule:** never treat a draft/unfinalized report as finalized output; check `finalized_at`/`status`.

---

## 35. Alert Operations

- **What exists:** notifications API (`/api/v2/notifications/*`) and red-zone alert feeds (`/api/v2/alerts/*`, `station` red-zone spike alerts per Issue #146). Notifications are DB-backed and **polling-based** (no WebSocket — documented gap for real-time push); an in-process realtime bus (`app/services/realtime/bus.py`) fans out events to subscribers.
- **Threshold policy:** red-zone/spike alerts use the configured station/zone thresholds in the alert-policy module (`app/routes/alerts.py` + alert policy service). Review current thresholds before enabling in production.
- **Status flow:** alerts/notifications have status (`unread`/`acknowledged`/`resolved`), priority, severity; `POST /api/v2/notifications/{id}/read` (and read-all/dismiss) acknowledge them.
- **Demo vs operational:** alerts driven by seeded/demo records are flagged via provenance and data-mode (`/api/v2/system/data-mode`); **never treat demo alerts as operational**.
- **Failure handling:** if the realtime bus is reset (restart) or notifications fail to persist, clients fall back to polling; verify the notifications DB table on restart.

---

## 36. Onboarding Runbook (new operator)

1. **Read** §1–§3 (system overview, architecture, prerequisites).
2. **Environment:** copy `backend/.env.example` → `backend/.env`, understand every variable (§4). Know dev vs prod (§5) and that production startup self-validates (§26).
3. **Deploy once** in a staging environment following §6 end-to-end.
4. **Start/stop/restart** each service (§7–§8) and confirm health (§9).
5. **Logs:** know stdout + `logs/saksha_backend.log` (§29) and which patterns matter.
6. **Database:** connect, inspect schema, back up and restore (§11–§14). Know Supabase specifics (§15).
7. **Neo4j:** start, browse, sync, verify consistency, handle outage (§16–§17).
8. **Frontend:** build, deploy, routing requirements, failure diagnosis (§18–§20).
9. **AI/ML:** read model status, understand ML vs FALLBACK, retrain/restore (§21–§23).
10. **Storage:** verify uploads persist and understand the local-vs-Supabase gap (§24).
11. **Backup/recovery:** drill the §13→§14 restore path in staging.
12. **Incident response:** rehearse §30 scenarios; keep the §31 rollback and §33–§35 operational flows handy.

Sign-off: pass the §39 validation and the §40 production checklist on staging.

---

## 37. Troubleshooting Matrix

| Problem | Check | Action | Verification |
|---|---|---|---|
| Backend unavailable | `GET /health/live` | Restart service; fix config errors (§10.1) | Health returns healthy |
| Database unavailable | `pg_isready`/`/health/ready` `postgresql` field; verify the app didn't slide to SQLite (§10.3) | Restore/restart DB, then backend | DB connection succeeds; real data counts |
| Neo4j unavailable | `/health/ready` `neo4j` field; browser `:7474` | Restart/check credentials; re-sync (§16/§17) | Network API works; graph counts match |
| Frontend blank | Browser console + DevTools network | Rebuild/redeploy `dist/` (§20) | Dashboard loads |
| API connection failure from UI | DevTools network → backend `/health` | Check nginx proxy / `VITE_API_BASE_URL` (§20) | Requests return 200 |
| Prediction unavailable/fallback | `GET /api/v2/ai/hotspot/model-info` | Restore/retrain artifacts (§22) | `prediction_mode: "ML"` |
| Login failure | `/api/v2/auth/me`, lockout fields, Supabase auth | Reset lockout / verify Supabase keys (§25/§15) | Login succeeds |
| Users throttled as a group (`429 Too many requests` for everyone behind nginx) | Logs response `Retry-After`; confirm each request carries `X-Forwarded-For` with the real client IP | Ensure `RATE_LIMIT_TRUST_XFF=true` (default) so budgets key on real client IPs, not the proxy's `127.0.0.1`; raise budgets if traffic genuinely exceeds defaults (§25) | Individual users hit their own budgets; health probes unaffected |
| Uploads fail | Storage config, bucket, disk | Configure/repair Supabase Storage or `UPLOAD_DIR` (§24) | Upload returns `storage_url`; download works |
| Deep-link refresh 404 | Hit route directly | Add SPA fallback `try_files $uri /index.html;` (§19) | Refresh keeps you logged in on any route |

---

## 38. Disaster Recovery (major outage sequence)

Recovery order follows dependencies:

1. **Infrastructure** — hosts, Docker daemon, network, DNS/load balancer restored.
2. **Database** — restore Postgres from the newest verified backup (§14), verify schema + data.
3. **Storage** — restore/verify Supabase bucket or local upload volume.
4. **Neo4j** — start Neo4j, verify credentials, **re-sync from Postgres** (§17).
5. **Backend** — start uvicorn/container with validated `.env`; confirm no production-config errors.
6. **Frontend** — serve static build (or start the single-container image) with SPA fallback.
7. **AI/ML** — confirm artifacts/`model-info` (`ML`); retrain if stale (§22).
8. **Health checks** — §9 pass.
9. **Acceptance tests** — §39 pass.

⚠ No RTO/RPO is claimed here: neither has been defined or tested for this platform. Set targets operationally after a restore drill.

---

## 39. Post-Recovery Validation Checklist

- [ ] Login works (admin + a representative analyst/investigator account).
- [ ] Dashboard loads (KPIs, charts, alert feed).
- [ ] Database queries work (crime cases, FIRs, criminals, victims, officers, reports, notifications lists).
- [ ] Network intelligence works (graph loads) if Neo4j is available; `sync-neo4j` returned counts if re-synced.
- [ ] Hotspots render and predict (`prediction_mode` honest).
- [ ] Predictions report correct model status (`model-info` → ML/FALLBACK truthful).
- [ ] AI chat answers (local-template or LLM) with citations.
- [ ] Reports list/generate/export; finalized ones intact (`integrity_hash`).
- [ ] Alerts list loads; statuses (unread/acknowledged/resolved) correct.
- [ ] File/storage operations: evidence upload + download works; `storage_url` present when Supabase configured.
- [ ] Auth/authorization: role-protected routes enforce RBAC; token refresh works.
- [ ] **No unexpected demo/fallback state is presented as live** — `/api/v2/system/data-mode` shows `production` and DEMO badges absent.

---

## 40. Production Verification Checklist

**Infrastructure**
- [ ] Services running (backend, frontend/nginx, Postgres, Neo4j as applicable).
- [ ] Required ports/config correct (`80`/`8000`; DB/Neo4j not publicly exposed beyond policy).
- [ ] DNS/domain configuration correct where applicable.

**Security**
- [ ] Production secrets configured; no placeholders.
- [ ] `APP_DEBUG=false`, `DEBUG=false`.
- [ ] `ALLOWED_ORIGINS` restricted (no `*`).
- [ ] Authentication works; account lockout active.
- [ ] Authorization/RBAC verified on a protected endpoint.

**Database**
- [ ] PostgreSQL/Supabase reachable.
- [ ] Migrations complete (`alembic_version` stamped; startup DDL clean).
- [ ] Backup verified (restore drill done in staging).

**Neo4j**
- [ ] Reachable (or documented optional-degraded).
- [ ] Auth works; default password not in use.
- [ ] Network queries work after a successful sync.

**Backend**
- [ ] `/health/live` healthy.
- [ ] `/health/ready` healthy (`postgresql: up`).
- [ ] Logs clean (no `PRODUCTION CONFIG ERROR`).

**Frontend**
- [ ] Build successful; static assets deployed.
- [ ] Login works from the public URL.
- [ ] Deep-link refresh works (SPA fallback).
- [ ] API connectivity works (proxied `/api`).

**AI/ML**
- [ ] `model-info` status verified.
- [ ] Model provenance/version verified.
- [ ] Fallback status correctly displayed (never silently as ML).

**Storage**
- [ ] Upload works; retrieval works; persistent store verified (Supabase bucket or documented gap).
- [ ] Evidence files survive a container restart (Supabase), or gap accepted.

**Application**
- [ ] Dashboard, Network, Hotspots, Predictions, Reports, Alerts, AI chat, Data Import all functional.
- [ ] /api/v2/system/data-mode == `production`; no demo badges.

---

## 41. Documentation Quality Notes

- Commands are copy-pasteable and explain what they do; expected results are stated.
- Production commands are separated from development commands.
- **No real credentials appear anywhere in this document.** Generate secrets locally and keep them in server-side environment files.
- Where the repository lacks a capability (automated backups, `/metrics` Prometheus endpoint, RAG vector-store persistence, scheduled Neo4j sync, report archival), it is **explicitly labelled a documented gap / operational requirement** — never implied to exist.
- Operators should not need to open Python/TypeScript source for routine operations; the few code references included are for evidence of behavior, not as required reading.

---

## 42–43. Command & Runbook Validation

Every command in this file was checked against the repository:
- `backend/.env.example`, `backend/app/core/config.py` (env vars, validation), `backend/app/main.py` (health endpoints, startup DDL, prewarm), `backend/app/database/postgres.py`, `backend/app/database/neo4j.py`, `backend/app/database/seed_db.py` (`python -m app.database.seed_db` main block), `backend/alembic.ini` + `backend/migrations/env.py` + baseline revision, `backend/docker-compose.yml`, `backend/Dockerfile`, root `Dockerfile`, `nginx.conf` (proxy + SPA fallback), `start.sh`, `supervisord.conf`, `datathon/package.json` scripts, `datathon/vite.config.ts` (proxy), `datathon/src/services/api.ts` (`VITE_API_BASE_URL`), `backend/app/routes/{auth,ai_hotspot,ai_risk,ai_criminal,network,data_import,notifications,reports,system}.py`, `backend/app/services/neo4j/client.py` (sync), `backend/app/mlops/*` (registry + CLI), `monitoring/prometheus.yml` + `monitoring/drift_rules.json`, `.github/workflows/*`, `scripts/dev-all.js`, `scripts/check_secrets.py`, `scripts/check_spa_routing.py`, `backend/requirements.txt`.

**Runbook test (as per Issue §43):** the workflow in §6→§9→§39 was followed in the local development environment (SQLite demo, local PostgreSQL via Compose, Neo4j via Compose) and corrections applied. Before production use, repeat the same drill in your target environment and log any deviations here — treat this runbook as living documentation.

---

## 44. Acceptance Criteria — Status

| Criterion | Status |
|---|---|
| Central production operations runbook exists | ✅ this document |
| Backend startup documented | ✅ §6–§8 |
| Backend health/readiness documented | ✅ §9 |
| Database operations documented | ✅ §11–§15 |
| Database migration procedure documented | ✅ §12 |
| Backup/recovery documented **or limitation stated** | ✅ §13–§14 (gap: no automated backup job) |
| Neo4j startup + health + failure recovery | ✅ §16–§17 |
| Frontend deployment + routing requirements | ✅ §18–§19 |
| AI/ML deployment + model-status behavior | ✅ §21–§23 |
| Storage operations | ✅ §24 (gap: local-upload non-persistence) |
| Auth/security operations | ✅ §25–§26 |
| Env vars documented without secrets | ✅ §4 + `backend/.env.example` (updated) |
| Production vs development clearly separated | ✅ §5 |
| Normal startup documented | ✅ §7 |
| Failure recovery documented | ✅ §10, §20, §23 |
| Rollback documented | ✅ §31 |
| Maintenance documented | ✅ §32 |
| Monitoring/logging locations | ✅ §28–§29 |
| Incident response workflow | ✅ §30 |
| New-operator onboarding | ✅ §36 |
| Troubleshooting matrix | ✅ §37 |
| Disaster recovery | ✅ §38 |
| Post-recovery validation checklist | ✅ §39 |
| Production verification checklist | ✅ §40 |
| Commands/endpoints verified against repo | ✅ §42–§43 |
| No real secrets present | ✅ |
| No source-code reading required for routine ops | ✅ §41 |
| README/deployment docs linked rather than duplicated | ✅ §0 header |
| Runbook tested by following the workflow | ⚠ partial (dev-env drill) — **production drill required before go-live** |