# SAKSHA — Testing & Verification Guide

Issue 8 (P1): end-to-end verification suite for Dashboard, Network, Hotspot,
Prediction, and Authentication flows.

## Test Architecture

| Layer | Framework | Location | Scope |
|---|---|---|---|
| Backend unit/integration | pytest | `backend/tests/` | Services, models, routes (in-memory SQLite) |
| **Backend acceptance** | pytest (`-m acceptance`) | `backend/tests/acceptance/` | Full challenge workflows through the real FastAPI app |
| Frontend unit/component | Vitest + Testing Library | `datathon/src/test/` | Routing/reload, RBAC guard, API client, ML/FALLBACK provenance badges |

### Acceptance suite principles

- Tests run against the **real app** with a real (per-test, isolated in-memory
  SQLite) database. Only the DB session is injected; authentication always
  goes through the actual `/auth/login` endpoint and JWT dependency chain.
- The dataset is **deterministic** (`tests/acceptance/conftest.py`):
  2 categories, 2 districts, 3 criminals, 1 victim, 1 officer, 3 cases
  (one DEMO-provenance), 2 FIRs with criminal/victim links.
- No production credentials, no external services, no network calls.
  External identity (Supabase fallback) is disabled in tests.
- Model-artifact tests use a temporary model directory; real artifacts are
  restored after each test via cache invalidation.

## Covered challenge scenarios

| # | Scenario | Test module |
|---|---|---|
| 1 | Authentication (valid/invalid/expired/revoked tokens) | `test_acceptance_auth.py` |
| 2 | Dashboard loads DB-backed data (+ empty state, bad params) | `test_acceptance_dashboard.py` |
| 3 | Network graph contains seeded nodes/edges/relationships | `test_acceptance_network.py` |
| 4 | Partial/dangling records handled without fabrication | `test_acceptance_network.py` |
| 5 | Hotspot flow + honest `prediction_mode` (ML vs FALLBACK) | `test_acceptance_hotspot.py` |
| 6 | Prediction endpoints validate mode/model consistency | `test_acceptance_prediction.py` |
| 7 | Missing/corrupt artifact never claims validated ML | `test_acceptance_hotspot.py`, `test_acceptance_prediction.py` |
| 8 | Authorization: valid token ≠ access to restricted intel | `test_acceptance_authorization.py` |
| 9 | Database failure -> controlled JSON error, no leaks | `test_acceptance_resilience.py` |
| 10 | Route reload / deep-link restore (frontend) | `datathon/src/test/App.routing.test.tsx` |
| 11 | DEMO/LIVE provenance survives to the API boundary | dashboard lineage + network metadata tests |
| 12 | Production builds verified | CI (`npm run build`, `compileall`) |

Performance sanity: login/dashboard/network/hotspot/prediction must each
complete within a generous 30 s threshold (catastrophic-regression guard).

## Running tests locally

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
cd datathon && npm ci && cd ..

# 2. Everything (backend unit/integration/acceptance + frontend)
npm test            # from repo root

# Or individually:
npm run test:backend       # python -m pytest backend/tests -q
npm run test:frontend      # vitest (datathon)
npm run test:acceptance    # python -m pytest backend/tests/acceptance -m acceptance

# Acceptance suite only, verbose:
cd backend && python -m pytest tests/acceptance -m acceptance -v
```

No environment variables or running services are required: the test
configuration (`backend/tests/conftest.py`) pins an isolated in-memory SQLite
database, a throwaway JWT secret, and disables background retraining.

## CI behaviour

`.github/workflows/ci.yml` runs on every push/PR:

1. Repository sanity checks
2. Frontend quality gate: lint → typecheck → unit/component tests → production build → SPA deep-link validation
3. Backend quality gate: compileall → ruff → full pytest (unit + integration + acceptance) → explicit `-m acceptance` gate
4. Security scan (npm audit, pip-audit, secret scan)
5. Merge compatibility dry-run against main
6. Aggregate summary job fails if any critical gate failed

Failed runs upload JUnit XML + captured output as artifacts for debugging;
secrets are never printed (CI uses throwaway env values only).

Branch protection should require the `Saksha CI` workflow checks
(frontend-quality, backend-quality, security-scan, repo-validation) before
merge — critical acceptance failures are merge-blocking by design.

## Fixing failures

Do not weaken a test to make it pass. If an acceptance test exposes an
implementation bug (e.g. dangling FIR links crashed the network graph
builder), fix the implementation. If a test is flaky, fix the root cause
(state leakage, timing) rather than adding retries.
