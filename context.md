# Saksha -- Complete Project Context

## Project Summary

**Saksha** is a **Crime Intelligence & Analytical Platform** built for the **Karnataka State Police (KSP)** as part of **Datathon 2026 Challenge 2**. It transforms raw crime records into actionable intelligence by combining a full-stack web application with AI/ML predictive models, graph-based criminal network analysis, real-time notifications, and a MLOps pipeline. The platform is designed for 4 distinct user roles: Admin, Crime Analyst (SCRB), Investigator (IO), and Policymaker (SP).

**Author:** Aadhithya Balu S  
**License:** MIT (2026)  
**Command:** `npm run dev:all` (launches both backend and frontend)

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| **Framework** | FastAPI (Python 3.12) |
| **ORM** | SQLAlchemy 2.0 (async-compatible) |
| **Schema Validation** | Pydantic v2 |
| **Primary Database** | PostgreSQL 16 (Supabase-hosted on AWS ap-northeast-1) |
| **Graph Database** | Neo4j 5.24 Community (Neo4j Aura) |
| **Authentication** | JWT (HS256) via python-jose, SHA-256 salt-based password hashing |
| **Authorization** | 7 RBAC roles with route-level permission guards |
| **Server** | Uvicorn with hot-reload |
| **Containerization** | Docker (python:3.12-slim) |

### Frontend
| Layer | Technology |
|---|---|
| **Framework** | React 18 + TypeScript 5.9 |
| **Build Tool** | Vite 5.1 |
| **Styling** | Tailwind CSS 3.4 + custom CSS variables |
| **State Management** | Zustand 4.5 (5 stores) |
| **Data Fetching** | Axios + TanStack React Query 5.22 |
| **Charting** | Recharts 2.12, D3.js 7.8 |
| **3D Visualization** | Three.js 0.185, React Three Fiber 8.15, @react-three/drei 9.99 |
| **Graph Visualization** | react-force-graph-3d |
| **Mapbox** | mapbox-gl 3.1, react-map-gl 7.1 |
| **Deck.gl** | @deck.gl/core + layers + react 8.9 |
| **Animation** | Framer Motion 11.0, GSAP 3.12 |
| **Face Auth** | face-api.js 0.22, react-webcam 7.2 |
| **Icons** | Lucide React 0.344 |
| **Dev Proxy** | Vite dev server proxies `/api` -> `localhost:8000` |

### AI/ML
| Algorithm | Purpose | Library |
|---|---|---|
| LightGBM + Optuna | Crime hotspot prediction | lightgbm, optuna |
| RandomForest | District-level risk scoring | scikit-learn |
| XGBoost/LightGBM | District crime forecasting | xgboost, lightgbm |
| Weighted Linear (variance-based) | Criminal risk scoring | Custom numpy |
| Logistic Regression (GD) | Repeat offender prediction | Custom numpy |
| Cosine Similarity KNN | Similar offender matching | Custom numpy |
| Mini k-means | Criminal clustering | Custom numpy |
| Z-score L2 Deviation | Anomaly detection | Custom numpy |
| In-Memory Vector Store (SHA-256) | RAG chat with case context | Custom |
| TF-IDF + TruncatedSVD (LSA) cosine | Semantic MO search (issue #139 M6) | scikit-learn |
| Rule-based NER (regex/gazetteer) | Plates, phones, weapons, places, dates, money extraction | Custom |
| Composite vulnerability index | Victimology risk scoring (issue #139 M5) | Custom |
| Pre/post window comparison | Intervention effectiveness verdicts (issue #139 M7) | Custom SQL/numpy |

### Infrastructure
| Component | Technology |
|---|---|
| **CI/CD** | GitHub Actions (ci.yml, mlops.yml) |
| **Containerization** | Docker + Docker Compose |
| **Monitoring** | Prometheus (scrapes `/metrics` every 30s) |
| **Drift Detection** | Custom JSON threshold rules |
| **MLOps Registry** | Filesystem-backed (mlflow/ directory) |
| **Orchestration** | Node.js dev-all.js script |

---

## Architecture

```
+------------------+     +-------------------+     +------------------+
|   Crime Data     |     |  Supabase         |     |   Neo4j Aura     |
|   Sources        |---->|  PostgreSQL 16    |---->|   Graph DB       |
+------------------+     |  (16 tables)      |     |   (8 node types) |
                         +-------------------+     +------------------+
                                  |                         |
                                  v                         v
+--------------------------------------------------------------------+
|                    FastAPI Backend (Python 3.12)                     |
|  +-----------+  +-----------+  +---------+  +-------------------+  |
|  | Auth/RBAC |  | Services  |  | Routes  |  | AI/ML Engine      |  |
|  | JWT+SHA256|  | 13 files  |  | 21 files|  | 40 files (8 algo) |  |
|  +-----------+  +-----------+  +---------+  +-------------------+  |
|  +-----------+  +-----------+  +---------------------------------+  |
|  | MLOps     |  | Database  |  | RAG Chat + Vector Store         |  |
|  | Pipeline  |  | ORM + Neo4j|  | (in-memory SHA-256 embeddings) |  |
|  +-----------+  +-----------+  +---------------------------------+  |
+--------------------------------------------------------------------+
                                  |
                                  v (REST API /api/v2)
+--------------------------------------------------------------------+
|               React Frontend (TypeScript + Vite)                     |
|  +----------+  +--------+  +--------+  +----------+  +-----------+  |
|  | Sidebar  |  | Header |  | Pages  |  | Charts   |  | 3D/Graph  |  |
|  | (collaps)|  | (bell) |  | (18)   |  | (Recharts|  | (Three.js |  |
|  +----------+  +--------+  +--------+  |  D3)     |  |  r3f, force|  |
|  +----------+  +--------+  +--------+  +----------+  |  graph)   |  |
|  | Zustand  |  | Maps   |  | Auth   |  | Framer   |  +-----------+  |
|  | (5 store)|  | Mapbox |  | FaceID |  | Motion   |                 |
|  +----------+  | Deck.gl|  +--------+  +----------+                 |
|                +--------+                                           |
+--------------------------------------------------------------------+
```

### Data Flow
1. Crime data ingested into **Supabase PostgreSQL** (16 tables)
2. Graph relationships stored in **Neo4j** (8 node types, 7 relationship types)
3. **FastAPI** serves 59+ REST API endpoints under `/api/v2`
4. **AI/ML Engine** trains models on-demand from DB, auto-loads artifacts on inference
5. **React Frontend** consumes APIs via Vite dev proxy, renders dashboards/maps/graphs/charts
6. **RAG Chat** provides conversational AI over case context with citations
7. **MLOps Pipeline** handles model training, registry, monitoring, drift detection
8. **Notifications** provide real-time intelligence alerts across the platform

---

## Repository Layout

```
Saksha_Datathon/
|-- backend/                    # FastAPI Python backend
|   |-- app/
|   |   |-- main.py            # FastAPI app entry point
|   |   |-- core/              # config, security, exceptions
|   |   |-- database/          # postgres.py, neo4j.py, seed_db.py
|   |   |-- auth/              # rbac.py, dependencies.py
|   |   |-- models/            # 24 SQLAlchemy ORM models (incl. ImportJob, Intervention)
|   |   |-- schemas/           # Pydantic v2 request/response schemas
|   |   |-- services/          # 17 service modules
|   |   |   |-- base_service.py
|   |   |   |-- analytics_service.py
|   |   |   |-- crime_service.py
|   |   |   |-- evidence_service.py
|   |   |   |-- investigation_service.py
|   |   |   |-- audit_service.py
|   |   |   |-- sociological_service.py  # demographics + dataset-backed indicators (issue #139 M3)
|   |   |   |-- strategic_service.py     # command briefing, resource allocation
|   |   |   |-- ingest_service.py        # CSV/XLSX bulk import engine, CCTNS profile (issue #139 M1/M2)
|   |   |   |-- victimology_service.py   # repeat-victimization + vulnerability index (issue #139 M5)
|   |   |   |-- mo_semantic_service.py   # TF-IDF+LSA MO search, rule-based NER (issue #139 M6)
|   |   |   |-- intervention_service.py  # before/after effectiveness (issue #139 M7)
|   |   |   |-- network/       # network_service.py
|   |   |   |-- neo4j/         # client.py
|   |   |   |-- dashboard/     # dashboard_service.py
|   |   |   |-- notifications/ # notification_service.py, activity_service.py
|   |   |   |-- chat/          # chat_service.py
|   |   |   |-- rag/           # rag_service.py
|   |   |-- routes/            # 25 route modules (75+ endpoints)
|   |   |-- ai/                # 40 AI/ML files
|   |   |   |-- inference/     # hotspot.py, risk.py, criminal.py, anomaly.py
|   |   |   |-- models/        # risk/, criminal/, anomaly/, rag/
|   |   |   |-- features/      # hotspot/, risk/, criminal/, anomaly/
|   |   |   |-- pipelines/     # hotspot/, risk/, criminal/, anomaly/
|   |   |   |-- vectorstore/   # memory.py (in-memory vector store)
|   |   |   |-- prompts/       # chat.py (system prompts)
|   |   |-- mlops/             # registry, pipeline, monitoring, drift, deploy, cli
|   |   |-- tests/             # 10 test files (pytest)
|   |-- neo4j/                 # schema.cypher, queries_reference.cypher
|   |-- scripts/               # retrain_hotspot_rf.py, setup_officers_evidence.sql, socioeconomic_indicators.sql
|   |-- data/socioeconomic/    # versioned demo indicator dataset (all 30 districts, issue #139 M3)
|   |-- uploads/               # Evidence file uploads
|   |-- Dockerfile
|   |-- docker-compose.yml
|   |-- requirements.txt
|   |-- README.md
|
|-- datathon/                  # React + Vite + TypeScript frontend
|   |-- src/
|   |   |-- App.tsx            # Main app with tab-based routing
|   |   |-- main.tsx           # Entry point
|   |   |-- pages/             # 18 page components
|   |   |-- components/        # 51 component files across 12 directories
|   |   |   |-- admin/
|   |   |   |-- auth/          # BadgeLogin, FaceIDScanner, SessionTimer
|   |   |   |-- chat/          # MarkdownRenderer, ContextSelector, CitationBadge
|   |   |   |-- charts/        # TrendChart, DonutChart, ForecastChart, etc.
|   |   |   |-- dashboard/     # StatCard, KPICounter, AlertFeed, SpatialCube3D, etc.
|   |   |   |-- fir/           # FIRForm, FIRTimeline, FIRRiskScore, FIRAttachments
|   |   |   |-- investigation/ # InvestigationDashboard, AIChatPanel, CaseProgress, etc.
|   |   |   |-- layout/        # Sidebar, Header, RoleGuard
|   |   |   |-- map/           # KarnatakaMap, TimeSlider
|   |   |   |-- network/       # CriminalGraph3D, GangNetworkView, ShortestPathPanel, etc.
|   |   |   |-- notifications/ # NotificationBell, NotificationCenter, ActivityFeed, etc.
|   |   |   |-- reports/
|   |   |   |-- three/         # GlobeScene, ParticleField (Three.js 3D scenes)
|   |   |-- store/             # 5 Zustand stores (auth, alert, audit, map, notification)
|   |   |-- hooks/             # 4 custom hooks (useFaceAuth, useAuditLog, useNetwork, useRBAC)
|   |   |-- services/          # api.ts (800+ lines, all API calls + TS interfaces)
|   |   |-- utils/             # downloader.ts
|   |   |-- index.css, App.css
|   |-- package.json
|   |-- vite.config.ts
|   |-- tailwind.config.js
|   |-- tsconfig.json, tsconfig.app.json, tsconfig.node.json
|
|-- scripts/
|   |-- dev-all.js             # Node.js orchestrator (starts backend + frontend)
|
|-- docker/
|   |-- mlops.Dockerfile
|   |-- mlops-compose.yml
|
|-- monitoring/
|   |-- prometheus.yml         # Scrape config (backend:8000/metrics, 30s)
|   |-- drift_rules.json       # Feature drift thresholds
|
|-- mlflow/                    # Filesystem-backed model registry
|
|-- .github/
|   |-- workflows/ci.yml       # Backend pytest + Frontend build + Docker config validation
|   |-- workflows/mlops.yml    # MLOps cycle + Python compilation check (weekly + on push)
|   |-- ISSUE_TEMPLATE/        # Bug report template
|
|-- package.json               # Root workspace (npm run dev:all)
|-- README.md, IMPLEMENTATION.md, About.md, TODO.md
|-- CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md
|-- agent_rules.md, Merge_rules
|-- LICENSE (MIT)
```

---

## Database Schema (16 Tables)

### Core Tables
| Table | Purpose | Key Relationships |
|---|---|---|
| `roles` | 7 RBAC roles | Referenced by users |
| `users` | All platform users | FK to roles, officer_id |
| `officers` | Police officer details | badge_id, rank, district |
| `crime_categories` | Crime type classification | Referenced by crime_cases |
| `locations` | Geographic locations | district, lat, lon, state |

### Crime & Case Management
| Table | Purpose | Key Relationships |
|---|---|---|
| `crime_cases` | Master case records | FK to categories, locations |
| `firs` | First Information Reports | FK to crime_cases |
| `fir_criminal_links` | Many-to-many FIR-Criminal | Links FIRs to criminals |
| `fir_victim_links` | Many-to-many FIR-Victim | Links FIRs to victims |
| `criminals` | Criminal profiles | linked_cases, gang_affiliation |
| `victims` | Victim/witness profiles | linked_cases |

### Evidence & Investigation
| Table | Purpose | Key Relationships |
|---|---|---|
| `evidence` | Physical/digital evidence | FK to crime_cases, officers |
| `evidence_metadata` | Evidence file metadata | file_type, hash, size |
| `evidence_timeline` | Evidence lifecycle events | timestamps |
| `evidence_assignment` | Officer-evidence assignment | chain of custody |
| `chain_of_custody` | Evidence custody trail | transfer records |
| `evidence_ai_summary` | AI-generated summaries | LLM analysis |

### Audit & System
| Table | Purpose | Key Relationships |
|---|---|---|
| `audit_logs` | Activity audit trail | user_id, action, resource |
| `reports` | Generated reports | FK to crime_cases |
| `notifications` | Real-time alerts | type, severity, read status |
| `investigation_notes` | Case notes | FK to crime_cases, officers |
| `system_settings` | Admin system config | key-value pairs |
| `role_permissions` | Granular permissions | FK to roles |

### Gap-Closure Modules (issue #139)
| Table | Purpose | Key Relationships |
|---|---|---|
| `import_jobs` | Bulk CSV/XLSX ingestion audit (M1/M2) | FK to users; entity_type, status, row report JSON |
| `interventions` | Prevention programs + effectiveness windows (M7) | district, intervention_type, started/ended_at |

Optional Supabase-side reference table: `socioeconomic_indicators`
(31 rows, <50 KB — see `backend/scripts/socioeconomic_indicators.sql`;
loaded by the sociological service with the bundled CSV as offline fallback).

---

## Neo4j Graph Schema

### Node Types (8)
| Node | Properties |
|---|---|
| Criminal | name, age, risk_score, gang_affiliation |
| Victim | name, age |
| Officer | name, badge_id, rank, district |
| Case | case_number, crime_type, status |
| Vehicle | type, registration |
| Weapon | type, description |
| Organization | name, type |
| Location | name, lat, lon |

### Relationship Types (7)
| Relationship | From -> To |
|---|---|
| KNOWS | Criminal -> Criminal |
| ASSOCIATED_WITH | Criminal -> Organization |
| USED | Criminal -> Vehicle/Weapon |
| ARRESTED_BY | Criminal -> Officer |
| LINKED_TO | Criminal -> Case |
| OCCURRED_AT | Case -> Location |
| VICTIM_OF | Victim -> Case |

---

## API Endpoints (75+ Routes)

### Authentication (`/api/v2/auth/`)
- `POST /login` - JWT token generation
- `POST /refresh` - Token refresh
- `GET /me` - Current user profile
- `POST /register` - New user registration (admin only)

### Admin (`/api/v2/admin/`)
- Full CRUD for users, roles, audit logs, system settings, permissions (19 routes)

### Crime Management
- `GET/POST /api/v2/criminals/` - Criminal list/create
- `GET/PUT/DELETE /api/v2/criminals/{id}` - Criminal detail/update/delete
- `GET /api/v2/criminals/search` - Criminal search
- `GET/POST /api/v2/victims/` - Victim list/create
- `GET/POST /api/v2/firs/` - FIR list/create
- `GET/POST /api/v2/officers/` - Officer list/create
- `GET/POST /api/v2/crime-cases/` - Crime case list/create (12 routes total)

### Evidence (`/api/v2/evidence/`)
- CRUD + upload, download, assign, accept, complete, return, reject, summary (11 routes)

### Reports (`/api/v2/reports/`)
- list, statistics, preview, generate, export (PDF/DOCX/TXT/CSV/XLSX)

### Notifications (`/api/v2/notifications/`)
- list, count, recent, read, read-all, dismiss, activity-feed, live-timeline (8 routes)

### Investigation (`/api/v2/investigation/`)
- dashboard, timeline, history, chat

### Dashboard Analytics (`/api/v2/dashboard/`)
- summary, trends, categories, districts, risk, hotspots, anomalies, offender-dossiers, network, chat

### Network Analysis (`/api/v2/network/`)
- full graph, person graph, case graph, gangs, shortest-path, link-analysis, AI insights

### Sociological (`/api/v2/sociological/`)
- demographics, urban-rural, socioeconomic (dataset-backed incl. unemployment correlation), population-correlation, temporal-demographics, offender-demographics, dataset-info

### Strategic (`/api/v2/strategic/`)
- briefing, daily-summary, high-risk-districts, emerging-trends, resource-allocation

### Data Import (`/api/v2/data-import/`, issue #139 M1/M2)
- `GET /entities` - supported entity specs and column profiles
- `GET /template/{entity_type}?export_format=csv|xlsx` - downloadable template with profile mapping
- `POST /preview` - parse + validate upload, return column mapping & row report
- `POST /commit` - persist valid rows (supports dry_run)
- `GET /jobs`, `GET /jobs/{id}` - import job audit trail

### Victimology (`/api/v2/victimology/`, issue #139 M5)
- `GET /overview` - repeat-victimization rate, gender split, top risk districts
- `GET /repeat-victims?min_fir_count=` - repeat-victim registry
- `GET /vulnerability-index` - composite vulnerability scores with cited risk factors

### Semantic MO Search (`/api/v2/ai/mo/`, issue #139 M6)
- `GET /search?q=&k=&kinds=` - TF-IDF+LSA cosine similarity over MO summaries/narratives (substring fallback without sklearn)
- `POST /extract-entities` - rule-based NER over free text (plates, phones, weapons, places, dates, money)
- `GET /extract-case/{case_id}` - entity extraction over a case's description + FIRs

### Interventions (`/api/v2/interventions/`, issue #139 M7)
- CRUD for prevention programs
- `GET /{id}/effectiveness` - equal pre/post window crime comparison with verdict

### AI/ML Endpoints
- `POST /api/v2/ai/chat` - Streaming RAG chat
- `POST /api/v2/ai/hotspot/predict` - Hotspot prediction
- `GET /api/v2/ai/hotspot/model-info` - Model metadata
- `POST /api/v2/ai/risk/predict` - District risk scoring
- `POST /api/v2/ai/risk/forecast` - Time-series forecasting
- `POST /api/v2/ai/risk/train` - Retrain risk models
- `POST /api/v2/ai/criminal/risk` - Criminal risk assessment
- `POST /api/v2/ai/criminal/repeat-offender` - Repeat offender prediction
- `POST /api/v2/ai/criminal/similar` - Similar offender matching
- `POST /api/v2/ai/criminal/cluster` - Criminal clustering
- `POST /api/v2/ai/criminal/recommendations` - Investigation recommendations
- `POST /api/v2/ai/anomaly/detect` - Anomaly detection

### MLOps (`/api/v2/mlops/`)
- register, promote, latest, models, retrain

---

## RBAC System (7 Roles)

| Role | Access Level |
|---|---|
| `admin` | All routes + user management + registration |
| `crime_analyst` | All read routes + dashboard + AI analytics |
| `investigator` | CRUD for crimes, FIRs, criminals, victims |
| `inspector` | Extended investigator + officer management |
| `policymaker` | Read-only dashboard + AI analytics |
| `officer` | Basic read access + evidence handling |
| `viewer` | Read-only access |

### Demo Users
| Username | Password | Role | Full Name |
|---|---|---|---|
| `admin` | `564738` | admin | Admin User |
| `SCRB-7740` | `123456` | crime_analyst | Priya Sharma |
| `IO-3921` | `456789` | investigator | Inspector Ravi Kumar |
| `SP-0088` | `987654` | inspector | Superintendent Arun Mehta |

---

## AI/ML Module Architecture

### Feature Engineering

| Model | Features | Count |
|---|---|---|
| **Hotspot** | H3 spatial indices, temporal (hour/day/month/week), lag features, rolling averages, EMA, neighbor aggregation, station proximity | 31 |
| **Risk** | District-level monthly aggregation, lag features, rolling windows, year-over-year comparison | 11 |
| **Forecast** | Monthly time-series lag, rolling, EMA, momentum, seasonal indicators | 14 |
| **Criminal** | fir_count, open_fir_count, districts, categories, severity, age, status, recency, case_age, multi_district | 10 |
| **Anomaly** | day_seconds, lat/lon, district/crime/officer/offender bucketing | 7 |

### Model Interface
All models implement a standard interface:
- `train()` - Train from database records
- `evaluate()` - Compute metrics (accuracy, MAE, F1, etc.)
- `predict()` - Generate predictions
- `save_model()` - Persist artifacts to filesystem
- `load_model()` - Load from filesystem
- Auto-train on first inference if no artifact exists

### Design Patterns
- `lru_cache` singletons for model loading per process
- Rule-based fallbacks when no trained model is available
- All services fall back to SQL when Neo4j is offline
- PDF export generated from raw PDF spec (no external PDF library)
- RAG uses custom SHA-256 hash-based in-memory vector store (no external vector DB)

---

## Frontend Pages & Components

### Pages (18)
| Page | Route Tab | Description |
|---|---|---|
| Login | (auth) | Badge login + Face ID scanner |
| Overview | `dashboard` | KPI cards, trend charts, alert feed, 3D spatial cubes |
| FIR | `fir` | FIR lifecycle management, forms, timeline, risk scores |
| Hotspots | `hotspot` | Karnataka SVG map with heatmap overlay, time slider |
| Network | `network` | 3D criminal network graph, gang view, link analysis |
| Predictions | `predictive` | Risk scores, forecast charts, model info |
| Anomalies | `anomaly` | Real-time anomaly alert feed |
| Crime Cases | `crime_cases` | Case CRUD, detail view, linked entities |
| Investigation | `investigation` | Unified investigation dashboard with AI chat panel |
| Notifications | `notifications` | Real-time notifications, activity feed, system health |
| Offenders | `offenders` | Offender dossiers with AI recommendations |
| Criminals | `criminals` | Criminal registry with risk scores |
| Victims | `victims` | Victim/witness index + Victimology analytics toggle (repeat-victimization, vulnerability index) |
| Officers | `officers` | Officer directory |
| Evidence | `evidence` | Evidence chain of custody management |
| Reports | `reports` | Report generation, preview, export (CSV/PDF/DOCX/TXT/XLSX) |
| AI Chat | `ai_chat` | RAG-powered conversational AI crime analyst |
| Admin/Settings | `settings_help` | User management, roles, system settings, Data Import tab (bulk CSV/XLSX) |

### Key Components (51)
- **Auth:** BadgeLogin (badge-id entry), FaceIDScanner (face-api.js), SessionTimer
- **Dashboard:** StatCard, KPICounter, AlertFeed, SpatiotemporalHeatmap, SpatialCube3D, ActiveAlerts3D
- **Charts:** TrendChart, DonutChart, ForecastChart, CorrelationChart, WeatherCorrelationChart
- **Maps:** KarnatakaMap (custom SVG vector map), TimeSlider
- **Network:** CriminalGraph3D (react-force-graph-3d), GangNetworkView, ShortestPathPanel, LinkAnalysisPanel, NodeDetailPanel, GraphExplorerToolbar, NetworkTimelineSlider, AIGraphInsightsModal
- **FIR:** FIRForm, FIRTimeline, FIRRiskScore, FIRAttachments
- **Investigation:** InvestigationDashboard, InvestigationTimeline, CaseProgress, AIRecommendations, AIChatPanel, LinkedCriminals, LinkedFIRs, LinkedEvidence
- **Chat:** MarkdownRenderer, ContextSelector, CitationBadge
- **Notifications:** NotificationBell, NotificationCenter, ActivityFeed, LiveEventTimeline, SystemHealth
- **3D:** GlobeScene, ParticleField (Three.js scenes)
- **Layout:** Sidebar (collapsible), Header (with notification bell), RoleGuard (RBAC enforcement)
- **Admin:** Admin panel with user/role management + DataImportPanel (bulk CSV/XLSX ingestion)
- **Reports:** Report generation and export

### Zustand Stores (5)
| Store | Purpose |
|---|---|
| `authStore` | JWT tokens, user session, hydration, login/logout |
| `alertStore` | Real-time alert state |
| `auditStore` | Audit log tracking (page views, actions) |
| `mapStore` | Map layer state, selected location |
| `notificationStore` | Notification list, unread count, real-time updates |

### Custom Hooks (4)
| Hook | Purpose |
|---|---|
| `useFaceAuth` | Face detection authentication via face-api.js |
| `useAuditLog` | Automatic audit logging for user actions |
| `useNetwork` | Network graph data fetching and state |
| `useRBAC` | Role-based access control checks |

### API Service (`api.ts`)
- 800+ lines of TypeScript
- All REST API endpoint functions with typed request/response interfaces
- Axios instance with Bearer token interceptor
- Vite dev proxy handles CORS in development

---

## UI/UX Design System

### Color Palette (CSS Custom Properties)
| Token | Usage |
|---|---|
| `--primary-bg` | Dark background (#080E1B) |
| `--secondary-bg` | Slightly lighter background |
| `--card-bg` | Card/panel backgrounds |
| `--border-color` | Subtle borders |
| `--accent-blue` | Primary actions (#1E6FD9) |
| `--accent-teal` | Success/positive |
| `--accent-amber` | Warning |
| `--accent-coral` | Danger/critical |
| `--accent-purple` | AI/special features |
| `--primary-text` | Main text (#E8EDF5) |
| `--secondary-text` | Secondary text |
| `--muted-text` | Muted/hint text |

### Typography
- **Primary Font:** Inter (sans-serif)
- **Monospace Font:** JetBrains Mono
- **Design Language:** Military/law-enforcement tactical dashboard aesthetic

### UI Effects
- Glow shadows (`glow-blue`, `glow-teal`, `glow-amber`, `glow-coral`, `glow-purple`)
- Cyber grid aesthetic background
- Custom scrollbar styling
- Framer Motion page transitions
- GSAP animations
- "CLASSIFIED TELEMETRY DATABASES LOCK" footer stamp

---

## CI/CD Pipelines

### `ci.yml` (Saksha CI)
- **Trigger:** Push to main, all PRs
- **Jobs:**
  1. **backend:** Python 3.12, install requirements, `pytest`, `compileall`
  2. **frontend:** Node.js 20, `npm ci`, `npm run build`
  3. **docker-config:** Validate `backend/docker-compose.yml`

### `mlops.yml` (Saksha MLOps)
- **Trigger:** Push to main, all PRs, weekly (Sunday 2AM UTC)
- **Jobs:**
  1. Python 3.12, install requirements
  2. Run MLOps cycle: `python -m app.mlops`
  3. Smoke compile all Python files

---

## MLOps Pipeline

### Components
| Module | Purpose |
|---|---|
| `registry.py` | Filesystem-backed model registry (versioning, metadata) |
| `pipeline.py` | Orchestrates training -> evaluate -> register flow |
| `monitoring.py` | Model performance monitoring |
| `drift.py` | Data drift detection against thresholds |
| `deploy.py` | Model deployment/promotion |
| `dataset_versioning.py` | Dataset snapshot versioning |
| `cli.py` | Command-line interface for MLOps operations |

### Drift Detection Thresholds
```json
{
  "defaults": { "threshold": 0.15 },
  "features": {
    "risk_score": 0.20,
    "open_case_ratio": 0.18,
    "crime_volume": 0.25
  }
}
```

---

## Seed Data

- **8 Crime Categories:** Cyber Crime, Theft & Burglaries, Narcotics, Smuggling, Assault, Illegal Mining, Domestic Violence, Property Disputes
- **10 Locations** across Karnataka districts: Bengaluru Urban (Whitefield, KR Puram), Mysuru, Mangaluru, Belagavi, Ballari, Kalaburagi, Hassan, Tumkuru, Dharwad
- **5 Criminals** with aliases, DOB, identifying marks, MO summaries, and statuses (Ramu Swamy, Vikram Yadav, Sayed Ibrahim, Karthik Gowda, Mohsin Pasha)
- **5 Victims** with contact, address, gender, age, and statements
- **11 Crime Cases** with case numbers (CR-2026-*), categories, locations, statuses, priorities, progress, MO tags, and FIR numbers
- **11 FIRs** linked to cases, criminals, and victims with sections, narratives, and attachments
- **Evidence records** for each case (digital or document type)
- **4 Demo Users** with roles and badge numbers
- **Officers** created for users with badge numbers (IO-3921, SP-0088)
- **Pre-seeded Neo4j sample graph** with Criminal, Victim, Officer, Case, Vehicle, Weapon, Organization, and Location nodes with relationships

---

## Known Limitations & Stubs

1. **Empty hotspot feature files:** `temporal_features.py`, `spatial_features.py`, `station_features.py`, `historical_features.py` are all empty stubs (consolidated into `feature_engineering.py`)
2. **No Alembic migrations** - schema applied directly via SQLAlchemy `create_all()`
3. **In-memory vector store** for RAG (not persistent across restarts)
4. **PDF export** built from raw PDF spec (no external PDF library)
5. **Face authentication** is client-side only (face-api.js) - logs in as SCRB-7740
6. **WebSocket** not yet implemented (notifications are polling-based)
7. **App.css** contains Vite boilerplate styles (hero, counter, ticks) that are unused
8. **Custom scrollbar** is defined in index.css but referenced as `custom-scrollbar` class in App.tsx (missing class definition)
9. **Some sidebar navigation items** (officers, evidence, notifications) are implemented but not all appear in the Sidebar component navigation
10. **Socio-economic indicators are demo data** - Census 2011 base figures with approximated income/unemployment; updatable via `backend/scripts/socioeconomic_indicators.sql` without code changes
11. **MO semantic search** requires scikit-learn for TF-IDF+LSA; falls back to substring matching when unavailable

---

## Development Commands

| Command | Description |
|---|---|
| `npm run dev:all` | Start both backend + frontend |
| `npm run dev:backend` | Start backend only (port 8000) |
| `npm run dev:frontend` | Start frontend only (port 5173) |
| `cd backend && py -3.12 -m pytest` | Run backend tests |
| `cd datathon && npm run build` | Production frontend build |
| `cd datathon && npm run lint` | ESLint check |
| `cd backend && py -3.12 -m app.mlops` | Run MLOps cycle |

---

## File Statistics

| Category | Count |
|---|---|
| Backend Python files | ~80+ |
| Frontend TSX/TS files | ~85+ |
| AI/ML model files | 40 |
| Service modules | 17 |
| Route modules | 25 |
| ORM models | 24 |
| React components | 52+ |
| Zustand stores | 5 |
| Custom hooks | 4 |
| Test files | 14+ |
| CI/CD workflows | 2 |
| Docker files | 3 |
| Documentation files | 11 |
