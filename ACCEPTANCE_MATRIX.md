# Saksha Issues #163–#167 — Acceptance Matrix

**Date:** 2026-08-26  
**Test suite:** 495/495 pass · Frontend build clean  
**Author:** Aadhithya Balu S

---

## Issue #164 — Data Provenance & Seed Data Integrity

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | `ImportProvenanceMixin` on Location, FIR, Evidence, Officer | ✅ PASS | All 7 models inherit it: Location, FIR, Evidence, Officer, Criminal, CrimeCase, Victim |
| 2 | `seed_db.py` tags all seed records as `dataset_provenance='demo'` | ✅ PASS | Officers, locations, criminals, victims, cases, FIRs, evidence all tagged; backfill for existing `None/live/unknown` |
| 3 | `_migrate_provenance_columns()` runs at startup | ✅ PASS | `main.py:164` — adds 4 columns to 4 tables (idempotent DDL, non-fatal) |
| 4 | `data_quality_service.py` created | ✅ PASS | `get_provenance_summary()`, `get_data_quality_warnings()`, `get_admin_data_quality_report()` |
| 5 | `GET /api/v2/admin/data-quality` endpoint | ✅ PASS | Returns provenance summary + entity breakdown + warnings |
| 6 | Frontend `DataQualityPanel.tsx` | ✅ PASS | Rendered in Admin "quality" tab — provenance summary, entity table, warnings |
| 7 | Tests (11 provenance tests) | ✅ PASS | `tests/test_provenance.py` — 11/11 |

---

## Issue #165 — ML Model Validation

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | `model_validation_service.py` created | ✅ PASS | `_check_artifact_exists`, `_validate_json_artifact`, `validate_hotspot_model`, `validate_risk_model`, `get_all_model_health` |
| 2 | `GET /api/v2/ai/model-health` endpoint | ✅ PASS | Returns per-model health with VALID/DEGRADED status |
| 3 | `get_all_model_health()` `risk_dir` path fix | ✅ PASS | Fixed `parents[2]` → `parents[1]` |
| 4 | Frontend `ModelHealthPanel.tsx` | ✅ PASS | Rendered in Admin "quality" tab — model cards with status badges |
| 5 | `hotspot.py` dual loader (strict + safe) | ✅ PASS | `_load_model()` raises on corrupt, `_try_load_model()` returns None for inference fallback |
| 6 | Route handles corrupt model gracefully | ✅ PASS | `ai_hotspot.py` catches exceptions, returns 500 instead of crash |
| 7 | Tests (12 model validation tests) | ✅ PASS | `tests/test_model_validation.py` — 12/12 |

---

## Issue #166 — Network Graph Validation

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | `NetworkGraphResponse` has `entity_counts`, `warnings`, `confidence_summary` | ✅ PASS | `models/network.py:89-103` — all 3 fields present |
| 2 | `_graph_response()` populates new fields | ✅ PASS | `network_service.py:408-452` — Counter builds entity_counts, warnings from MIXED provenance |
| 3 | Frontend `NetworkGraphResponse` TS interface updated | ✅ PASS | `api.ts:287` — mirrors all backend fields |
| 4 | Network page shows metadata bar | ✅ PASS | Entity counts, confidence badges, warning banners rendered below filter |
| 5 | Tests (10 network provenance tests) | ✅ PASS | `tests/test_network_provenance.py` — 10/10 (original set) |

---

## Issue #167 — Config Safety Validation

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | `validate_production_config()` model validator | ✅ PASS | `core/config.py:169` — JWT entropy check, CORS validation, debug mode guard |
| 2 | `_estimate_jwt_entropy()` helper | ✅ PASS | Estimates bit-entropy of JWT secret key |
| 3 | Startup warning/error logging | ✅ PASS | Production config issues logged at startup (non-fatal) |
| 4 | Tests (13 config tests) | ✅ PASS | `tests/test_config_production.py` — 13/13 |

---

## Issue #159 (pre-existing) — Network Provenance & Scope Filter

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Provenance filter buttons (All, Verified, Analytical) | ✅ PASS | `Network.tsx` — filter state + API query params |
| 2 | Exclude demo records checkbox | ✅ PASS | `Network.tsx` — `excludeDemo` state |
| 3 | Full graph vs Officer focus toggle | ✅ PASS | `Network.tsx` — `viewScope` state |
| 4 | Link provenance colors (green=verified, amber=analytical, purple=demo) | ✅ PASS | `CriminalGraph3D.tsx:getLinkColor()` |

---

## Section 25 — Network UI Overhaul

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Backend entity search endpoint `GET /network/search?q=` | ✅ PASS | Searches criminals, victims, officers, FIRs, cases, locations |
| 2 | Frontend search bar with debounced dropdown | ✅ PASS | 300ms debounce, type-colored results dropdown |
| 3 | Click-to-focus loads entity subgraph | ✅ PASS | Uses `getNetworkPerson`/`getNetworkCase` endpoints |
| 4 | Progressive expansion (depth 1→4) | ✅ PASS | Expand button, depth badge, max depth=4 |
| 5 | Graph viewport controls (zoom in/out/fit) | ✅ PASS | ZoomIn, ZoomOut, Maximize2 buttons in bottom-right |
| 6 | Sparse graph handling (empty state) | ✅ PASS | `GraphFallback` shows "No network records" message |
| 7 | Graph stats overlay (node/edge count) | ✅ PASS | "X nodes, Y edges" in legend |
| 8 | Network search tests (8 tests) | ✅ PASS | `tests/test_network_provenance.py:TestNetworkSearchEndpoint` — 8/8 |

---

## Cross-Cutting: Full Test Suite

| Suite | Count | Status |
|---|---|---|
| `tests/test_provenance.py` | 11 | ✅ |
| `tests/test_model_validation.py` | 12 | ✅ |
| `tests/test_network_provenance.py` | 18 | ✅ |
| `tests/test_config_production.py` | 13 | ✅ |
| All other tests | 441 | ✅ |
| **Total** | **495** | **✅ ALL PASS** |

| Build | Status |
|---|---|
| Frontend (`npm run build`) | ✅ Clean (0 TS errors) |
| Backend (`py_compile` all) | ✅ Clean |

---

## Summary

| Issue | Requirements | PASS | FAIL | PARTIAL |
|---|---|---|---|---|
| #164 Data Provenance | 7 | 7 | 0 | 0 |
| #165 ML Validation | 7 | 7 | 0 | 0 |
| #166 Network Validation | 5 | 5 | 0 | 0 |
| #167 Config Safety | 4 | 4 | 0 | 0 |
| Sec. 25 Network UI | 8 | 8 | 0 | 0 |
| **Total** | **31** | **31** | **0** | **0** |

**RESULT: ALL 31 REQUIREMENTS PASS — ISSUES #163–#167 COMPLETE**
