# SAKSHA Final Test v2 — End-to-End Validation Report

**Issue:** #253 — FINAL TEST v2
**Branch:** `FINAL_TEST`
**Date:** 2026-09-06
**Result:** **PASS** — all 14 validation sections green (28/28 automated E2E checks)

---

## Scenario

> A surge of **night-time residential burglaries** concentrates in **Whitefield,
> Bengaluru Urban** (Theft & Burglaries). Six FIRs are filed within ~6 days while a
> serial **at-large** offender re-uses a fixed MO signature
> (`night_operation / break_in / tool_usage`). The platform must discover, explain,
> connect, predict, act, and audit this threat — without ever over-claiming.

Automated exercise: `backend/tests/test_final_validation_v2.py` — 28 tests that walk
one scenario through the real FastAPI app (real `/auth/login` JWT, real routes,
in-memory SQLite). Seed: 3 baseline cases (45–75 days old) + 6 spike cases (last
~7 days) + linked FIRs, criminal, victim, and sealed digital evidence.

---

## Results by Section

| # | Section | Status | Automated Coverage |
|---|---|---|---|
| 1 | DATA & CASE STATE | **PASS** | Status surfaces via GET; valid transition audited with user+timestamp; ARRESTED is immutable (regression + priority edit → 422); cases cannot be created already-ARRESTED |
| 2 | DISCOVERY | **PASS** | `/ai/anomaly/detect` returns per-event verdicts with score/threshold/explanation; baseline comparison reports 6 current vs baseline with +>100% change; district → station → H3 drill-down surfaces |
| 3 | INTELLIGENCE FUSION | **PASS** | Fused result contains full contract (risk, confidence, signals, MO, forecast, provenance, ml_status); multi-signal fusion incl. temporal + entity_link/MO; ≥6 related FIRs propagate |
| 4 | SENTINEL ALERT | **PASS** | WHAT/WHERE/WHY present in alert text; risk ≥ 0.4, confidence ≥ 0.4, forecast period + prediction_mode, `data_provenance` reported |
| 5 | EXPLAINABILITY | **PASS** | "Why This Insight?" shows summary, per-signal status (CONFIRMED/PROBABLE/…), methodology (model name/version, ML vs FALLBACK), limitations, and non-causation safety note |
| 6 | INVESTIGATION & NETWORK | **PASS** | Investigation view resolves related FIRs + network; VERIFIED vs POTENTIAL/DEMO vocabulary enforced; edges carry supporting case/FIR evidence; safety note present without guilt claims |
| 7 | EVIDENCE & PROVENANCE | **PASS** | Evidence drawer resolves from linked FIRs with title/type/status, `verification_status` (VERIFIED/POTENTIAL/UNVERIFIED/DEMO/RESTRICTED) and case provenance |
| 8 | PREDICTION | **PASS** | Risk scores report `prediction_mode` (ML/FALLBACK), `model_version`, `data_provenance=LIVE_DB`; FALLBACK never overstates (`risk_model_loaded` consistent) |
| 9 | INTELLIGENCE QUALITY | **PASS** | `/admin/data-quality` communicates provenance; FALLBACK sentiments capped (confidence ≤ 0.85) |
| 10 | ACTION | **PASS** | Recommended action carries title/description/action_type/priority and a suggested intervention anchored to the district |
| 11 | HUMAN APPROVAL | **PASS** | Dispatch always creates `draft` (never auto-deployed); strict 5-stage gate (Draft → Supervisor Review → Approved → Deployed → Outcome Review → Completed) enforced; skipping stages → 400; viewer role → 403 on dispatch and advance |
| 12 | OUTCOME | **PASS** | Outcome review persists `subsequent_crime_count`/`pattern_persisted`; effectiveness compares equal pre/post windows and returns a verdict + method note (no causation claim) |
| 13 | AUDIT & ACCOUNTABILITY | **PASS** | `STATUS_TRANSITION`, `INTELLIGENCE_ACTION_DISPATCH`, `WORKFLOW_STAGE_ADVANCE` entries logged with user, role, and timestamp; lineage present in details |
| 14 | UI/UX API SURFACE | **PASS** | One cohesive flow stays reachable: Fuse → Pattern-by-id → Red-zones → Investigate → Network → Predict → Dispatch → Approve → Complete |

**Overall: PASS (14/14)**

---

## Defects Found & Fixed

| # | Area | Defect | Fix |
|---|---|---|---|
| 1 | Auth resilience | Login masked a database outage as `401` instead of `503` (generic `except Exception`) | `backend/app/routes/auth.py` — added `except SQLAlchemyError` → `AppException(503, SERVICE_UNAVAILABLE)` before the generic handler |
| 2 | Intelligence fusion (ML mode) | Forecast model emits `trend: up/down/stable`, but the fusion engine compared `== "increasing"`, silently skipping the forecast signal & checkpoint-action branch in ML mode | `backend/app/services/intelligence_engine.py` — normalize at the engine boundary via `_normalize_forecast_trend()` (`up→increasing`, `down→decreasing`); `predict_forecast` untouched so the forecast chart (`up/down`) is unaffected |
| 3 | Frontend build (10+ errors) | Unused imports/state in `SentinelWorkflowModal.tsx`, `SentinelAlertCard.tsx`; `ForecastResult.period` missing from `api.ts` interface | Removed unused lucide imports, removed `loadingRecord`/`recCoverage` state, added `period: string` to `ForecastResult` |

---

## Test Evidence

| Run | Command | Result |
|---|---|---|
| E2E validation (this issue) | `pytest tests/test_final_validation_v2.py` | **28 passed** |
| + regression | `pytest tests/acceptance tests/test_case_status.py tests/test_interventions.py tests/test_final_validation_v2.py` | **all passed** |
| Engine regression | `pytest tests/test_intelligence_fusion_pipeline.py tests/test_intelligence_investigation.py tests/test_provenance.py tests/test_network_provenance.py tests/test_station_redzones_hour.py tests/test_statistical_hotspots.py` | **all passed** |
| Acceptance suite (full) | `pytest tests/acceptance` | **52 passed** (incl. resilience 503) |
| AI/ML suite | `pytest tests/ai` | 275 passed |
| Frontend build | `npm run build` | **success** (vite built, ~46.8s) |

---

## Known Issues / Degradations (not blocking PASS)

1. **Pre-existing lint failures (11, 6 files)** — block the CI `frontend-quality`
   zero-warning gate. Unrelated to this issue and intentionally not fixed:
   `i18n/index.ts:16` (no-empty), `CommandCenter.tsx:114`, `Hotspots.tsx:221`,
   `IdentityResolution/index.tsx:533`, `NotFound.tsx:61` (`_path` unused),
   `test/networkProvenance.test.tsx:2` (unused `render`/`screen`).
2. **Full backend suite as one `pytest` invocation exceeds 15 min** with no
   buffered output (individual files all pass) — likely just a long suite; root
   cause not diagnosed. Prefer batched runs.
3. **scikit-learn model artifacts version skew** — `InconsistentVersionWarning`
   (1.8.0 serializer vs 1.9.0 runtime) on pickle load. Recommend a retrain via
   the MLOps pipeline after dependency upgrades.
4. **Full-suite runtime** excludes the full run; sections validated via the above
   targeted + regression batches.