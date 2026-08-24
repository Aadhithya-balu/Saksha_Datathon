# SAKSHA Challenge Audit — Missing Work and GitHub Issues

## Audit verdict

This repository is a substantial prototype and a credible engineering foundation, but it is not yet a fully validated challenge-complete production system.

The key rule for this audit is: do not treat a visible page, button, or mock dataset as proof of completion. The actual SAKSHA database, backend services, and real data paths are the source of truth.

### Verified status

- There is a real FastAPI backend with DB-backed routes, auth, RBAC, dashboard analytics, and network/data services.
- There is a real frontend React app with pages and API wiring for hotspots, network, predictive dashboards, AI tools, and admin modules.
- There is a real PostgreSQL/Supabase-style data model and a live Neo4j integration path.
- There are explicit rule-based / fallback paths in the AI inference modules when trained models are absent.
- There is a large seeded demo dataset that makes the app look more complete than it is if used without careful provenance checks.

### Environment verification note

The actual verification command was run in the workspace and completed successfully:

`python -m pytest backend/tests -q`

Result:

`295 passed, 51 warnings in 61.62s (0:01:01)`

This means the audit below is grounded in both code inspection and a fresh passing backend test run, with the warnings noted as non-blocking deprecations rather than test failures.

---

## What is already implemented and credible

| Challenge area | Status | Evidence | Notes |
|---|---|---|---|
| Unified backend app bootstrap and routing | ✅ Implemented | `backend/app/main.py`, `backend/app/api/v2.py` | Real app startup, route aggregation, CORS, health checks |
| Authentication and RBAC | ✅ Implemented | `backend/app/auth/rbac.py`, `backend/app/services/auth_service.py` | Local auth + Supabase fallback + role guards |
| Dashboard and crime analytics | ✅ Implemented | `backend/app/routes/dashboard.py`, `backend/app/services/dashboard.py` | Structured analytics endpoints exist |
| Hotspot detection and geospatial analytics | ✅ Implemented | `backend/app/services/analytics_service.py`, `backend/app/routes/ai_hotspot.py` | Real analytics and route-level aggregation |
| Predictive risk / forecast endpoints | ⚠️ Partial | `backend/app/ai/inference/risk.py` | Rule-based fallback is explicitly used when no model exists |
| Hotspot model inference | ⚠️ Partial | `backend/app/ai/inference/hotspot.py` | Works with trained artifacts or rule-based fallback |
| Anomaly detection | ⚠️ Partial | `backend/app/ai/inference/anomaly.py` | Statistical fallback path is intentionally used |
| Criminal network / link analysis | ✅ Implemented | `backend/app/services/network/network_service.py`, `backend/app/routes/network.py` | Graphs are built from DB/Neo4j data, with seed provenance markers |
| AI investigation chat | ⚠️ Partial | `backend/app/ai/chat/*`, `backend/app/routes/ai_chat.py` | Real orchestration exists, but grounding and production evaluation are still not proven |
| Socio-economic intelligence | ⚠️ Partial | `backend/app/services/sociological_service.py` | Dataset-backed but needs stronger validation and operational use |
| Frontend intelligence pages | ✅ Implemented | `datathon/src/pages/*` | Reaches real API layer; not purely decorative |
| Data seeding / demo dataset | ✅ Implemented | `backend/app/database/seed_db.py` | Useful for bootstrapping, but it creates a large demo provenance problem |
| Containerized deployment setup | ✅ Implemented | `backend/docker-compose.yml`, `Dockerfile`, `nginx.conf` | Structure exists, but runtime hardening and production config not proven |
| Security / secrets / deployment hardening | ❌ Missing or incomplete | config + environment patterns | JWT secret requirement exists, but production review is not complete |
| Comprehensive automated testing | ✅ Verified in this environment | `backend/tests/*` | `python -m pytest backend/tests -q` completed successfully with 295 passing tests |

---

## Areas that are credible but not fully challenge-complete

### 1) Predictive intelligence is partially real, not fully validated

Evidence:
- `backend/app/ai/inference/risk.py`
- `backend/app/ai/inference/hotspot.py`
- `backend/app/ai/models/*`

The inference code is real, but the fallback logic explicitly warns and switches to rule-based scoring when trained model artifacts do not exist. That is legitimate engineering, but it means the platform is not yet proven to be model-driven in production. The challenge requires validated predictive value, not just a fallback formula.

### 2) Network intelligence is buildable from the database, but provenance needs stronger verification

Evidence:
- `backend/app/services/network/network_service.py`
- `backend/app/database/seed_db.py`

The network service deliberately flags demo-seeded records with `isSeed`/`is_demo_derived` metadata, which is a good honesty mechanism. However, the app still needs a stronger verification process to distinguish truly live investigative links from seeded demo correlations before it is treated as operational evidence.

### 3) AI chat is real, but not sufficient as a production-ready police assistant

Evidence:
- `backend/app/ai/chat/*`
- `backend/app/routes/ai_chat.py`

There is orchestration, retrieval, and prompt layering, but the platform still needs stronger evidence of result quality, schema-grounding, and safe output validation for police operational use.

### 4) Frontend pages are real, but UI completeness does not equal business reality

Evidence:
- `datathon/src/pages/Hotspots.tsx`
- `datathon/src/pages/Network.tsx`
- `datathon/src/pages/Predictions.tsx`
- `datathon/src/services/api.ts`

The frontend calls live data services, but several pages have fallback data and demo logic. This means the UI can appear highly complete while the underlying intelligence remains partial or synthetic.

---

## Clear “demo / mock / hardcoded” classification

These are not necessarily wrong, but they are not full challenge completion:

- Large seed dataset in `backend/app/database/seed_db.py` makes the app feel operationally rich, but it is a demo/prototype dataset and not necessarily a live operational dataset.
- Frontend fallback arrays such as `BASELINE_HOTSPOTS` in `datathon/src/pages/Hotspots.tsx` are useful for resilience, but they should not be treated as proof of live hotspot intelligence.
- AI model inference with explicit rule-based fallback is valid engineering but should be classified as partial, not fully trained/deployed AI.
- Realtime or production-grade trust assumptions must not be made without verifying the actual database and model artifacts in the target environment.

---

## Missing work to create as independent GitHub issues

### P0 — Critical production-readiness work

#### Issue 1 — Enforce a single source-of-truth data policy and separate demo vs live records
- Title: `P0: separate seeded demo data from live SAKSHA operational data`
- Scope:
  - Add an explicit dataset provenance model or flag to all core records.
  - Prevent seeded/demo records from being presented as live operational intelligence without clear labeling.
  - Add an admin-level data quality report that distinguishes demo, migrated, and live data.
- Acceptance:
  - Seed records are tagged and filtered in all dashboards and graphs.
  - Operational queries cannot silently mix seeded records with production records without warning.
- Relevant files: `backend/app/database/seed_db.py`, `backend/app/services/network/network_service.py`

#### Issue 2 — Validate and harden the actual predictive AI pipeline end-to-end
- Title: `P0: prove predictive risk and hotspot models are trained, versioned, and deployed correctly`
- Scope:
  - Validate the model artifact pipeline and metadata generation.
  - Confirm model and feature columns match the actual input schema.
  - Require real training artifacts before claiming predictive intelligence is live.
- Acceptance:
  - Every prediction endpoint exposes model provenance and loaded status.
  - Production deployment blocks if model artifacts are missing or mismatched.
- Relevant files: `backend/app/ai/inference/risk.py`, `backend/app/ai/inference/hotspot.py`, `backend/app/ai/models/*`

#### Issue 3 — Establish evidence-grade graph and relationship integrity checks
- Title: `P0: validate network graph results against the live database before treating them as operational intelligence`
- Scope:
  - Add lineage checks for criminal, case, victim, and officer relationship edges.
  - Ensure graph queries can handle missing or partial records gracefully.
  - Add explicit warnings when graph data includes seed/demo provenance.
- Acceptance:
  - Graph API output includes provenance summary and record counts.
  - Suspicious or partial graph paths are marked as low-confidence.
- Relevant files: `backend/app/services/network/network_service.py`, `backend/app/routes/network.py`

#### Issue 4 — Complete security and deployment review for real deployment readiness
- Title: `P0: harden configuration, secrets, and deployment posture for non-demo environments`
- Scope:
  - Review JWT secret handling, CORS, DB credentials, storage keys, and deployment environment variables.
  - Remove assumptions that local development config is safe for real deployment.
  - Add production validation for Supabase/Neo4j/Postgres connectivity and failure behavior.
- Acceptance:
  - No unguarded empty secrets in production config.
  - Environment-specific deployment checklist exists and is enforced.
- Relevant files: `backend/app/core/config.py`, `backend/docker-compose.yml`, root configs

---

### P1 — High-value challenge completion work

#### Issue 5 — Build a real, documented data ingestion and reconciliation pipeline
- Title: `P1: ingest and reconcile CCTNS/ICJS-style data with the SAKSHA database source of truth`
- Scope:
  - Define field mapping, validation, deduplication, and reconciliation process for live crime data.
  - Add ingestion status and quality grading for imported records.
  - Document how bulk CSV/XLSX records become trusted SAKSHA data.
- Acceptance:
  - Import jobs produce traceable lineage records.
  - Duplicate or corrupt records are excluded or flagged.
- Relevant files: `backend/app/routes/data_import.py`, `backend/app/services/ingest_service.py`

#### Issue 6 — Add real evaluation for the AI chat assistant and responder grounding
- Title: `P1: evaluate AI chat quality, grounding, and safety before operational use`
- Scope:
  - Add evaluation set for domain questions and edge cases.
  - Validate that responses cite real dataset records and do not invent connections.
  - Add fail-safe behavior when evidence is missing.
- Acceptance:
  - Chat answers include explicit evidence provenance.
  - Unsupported questions return safe, bounded responses.
- Relevant files: `backend/app/ai/chat/*`, `backend/app/routes/ai_chat.py`

#### Issue 7 — Strengthen the socio-economic analytics with trusted evidence and policy-ready outputs
- Title: `P1: make socio-economic analysis evidence-driven and explainable`
- Scope:
  - Validate dataset coverage and district mappings.
  - Add confidence scores and metadata to all socioeconomic indicators.
  - Ensure analysis panels are backed by queryable records, not only UI formatting.
- Acceptance:
  - Every analytic output shows source dataset and date validity.
  - Missing district records are clearly marked.
- Relevant files: `backend/app/services/sociological_service.py`, `backend/app/routes/sociological.py`

#### Issue 8 — Add end-to-end acceptance testing and CI gate for challenge-level scenarios
- Title: `P1: create an end-to-end verification suite for dashboard, network, hotspot, and auth flows`
- Scope:
  - Create automated tests for authentication, dashboard endpoints, graph responses, and prediction endpoints.
  - Ensure CI failures block merges when core functionality is broken.
- Acceptance:
  - The project has a runnable acceptance suite in CI.
  - At least the critical challenge scenarios are covered.
- Relevant files: `backend/tests/*`, root package scripts

#### Issue 9 — Reconcile the UI fallback behavior with honest backend status messaging
- Title: `P1: surface fallback and demo-mode warnings in the UI when the backend is not operating on live trained models`
- Scope:
  - Add clear frontend warnings when predictions are using rule-based or demo fallback paths.
  - Ensure users understand the confidence and provenance level of displayed outputs.
- Acceptance:
  - UI labels identify when a page is running on fallback or demo data.
  - No screen suggests production-grade automated intelligence without the status indicator.
- Relevant files: `datathon/src/pages/Hotspots.tsx`, `datathon/src/pages/Predictions.tsx`, `datathon/src/services/api.ts`

---

### P2 — Product polish and operational maturity

#### Issue 10 — Standardize alerting, thresholds, and incident prioritization
- Title: `P2: formalize red-zone, anomaly, and incident-priority thresholds in a single policy`
- Scope:
  - Standardize detection thresholds and alerting logic.
  - Document how districts and crime categories are ranked.
  - Tie alerts to evidence and investigation workflows.
- Relevant files: `backend/app/routes/alerts.py`, `backend/app/services/redzone_service.py`

#### Issue 11 — Improve the admin and reporting workflow for non-demo deployments
- Title: `P2: add a production-ready reporting and audit lifecycle for investigations and evidence`
- Scope:
  - Standardize generation of reports and audit logs.
  - Ensure report outputs are tied to source records and user actions.
- Relevant files: `backend/app/routes/reports.py`, `backend/app/models/*`

#### Issue 12 — Document deployment and runbook quality for operators
- Title: `P2: create runbooks for backend, database, Neo4j, and frontend operations`
- Scope:
  - Define startup, health checks, failure recovery, onboarding, and maintenance steps.
- Acceptance:
  - Operational team can recover the app without code-level assumptions.

---

## Recommended parallel workstreams

### Workstream A — Data truth and provenance
- Issue 1
- Issue 5
- Issue 8

### Workstream B — AI / prediction quality
- Issue 2
- Issue 6
- Issue 7

### Workstream C — Graph / investigation intelligence
- Issue 3
- Issue 10

### Workstream D — Security / deployment / operability
- Issue 4
- Issue 12

### Workstream E — Product honesty and UX boundaries
- Issue 9

---

## Challenge coverage conclusion

The repository is not “missing everything.” It already contains a strong prototype foundation and some genuinely useful backend/data layer work. The real gap is not a total absence of functionality; it is the lack of production-grade validation, provenance controls, and operational trust.

### Minimal honest summary

- Real app foundation: Yes
- Real data model and routes: Yes
- Real analytics and graph logic: Yes
- Real predictive AI with proven trained artifacts: Not yet demonstrated
- Demo vs live data separation: Partially started but not yet enforced
- Production-grade security and release checks: Not yet complete
- Automated challenge-level validation: Not currently proven in this environment

The remaining work should be treated as a set of independent GitHub issues, with the first priority being business truth, model validation, and deployment safety — not cosmetic feature completion.
