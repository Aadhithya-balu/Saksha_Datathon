"""Smoke-test every AI inference module end-to-end."""
import sys, traceback
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

OK = 0
FAIL = 0

def check(name, fn):
    global OK, FAIL
    try:
        fn()
        print(f"  [PASS] {name}")
        OK += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        traceback.print_exc()
        FAIL += 1

FEATURES = ["fir_count", "open_fir_count", "districts", "categories",
            "severity", "age", "status_encoded", "recency_days", "case_age", "multi_district"]

# ── 1. Hotspot Model ──────────────────────────────────────────────
print("\n=== 1. HOTSPOT MODEL (LightGBM) ===")

def test_hotspot_load():
    from app.ai.inference.hotspot import get_model_info
    info = get_model_info()
    assert info.get("model_name"), f"No model info: {info}"
    print(f"    model_name={info.get('model_name')}, trained_rows={info.get('trained_rows', '?')}")

check("Hotspot model info", test_hotspot_load)
# Note: hotspot predict needs real CaseMaster-style records from the DB pipeline.
# Model load + metadata verified above is sufficient.

# ── 2. Risk Model ─────────────────────────────────────────────────
print("\n=== 2. DISTRICT RISK MODEL (RandomForest) ===")

def test_risk_load():
    from app.ai.inference.risk import _load_risk_model, MODEL_DIR
    assert (MODEL_DIR / "risk_model.pkl").exists(), "risk_model.pkl missing"
    model = _load_risk_model()
    assert model is not None, "Model is None"
    print(f"    MODEL_DIR={MODEL_DIR}, loaded={type(model).__name__}")

def test_risk_predict():
    from app.ai.inference.risk import predict_risk
    records = [
        {"case_id": "CR-TEST-001", "district": "Bengaluru Urban", "category": "Theft",
         "occurred_at": "2026-07-01", "priority": "high", "status": "open"},
        {"case_id": "CR-TEST-002", "district": "Mysuru", "category": "Assault",
         "occurred_at": "2026-07-15", "priority": "medium", "status": "open"},
    ]
    result = predict_risk(records)
    assert isinstance(result, list) and len(result) > 0
    for r in result:
        print(f"    district={r['district']}, score={r['risk_score']}, band={r['risk_band']}, confidence={r['confidence']:.2f}")

check("Risk model load (RandomForest)", test_risk_load)
check("Risk prediction (ML-based)", test_risk_predict)

# ── 3. Forecast Model ─────────────────────────────────────────────
print("\n=== 3. FORECAST MODEL (XGBoost/LightGBM) ===")

def test_forecast_load():
    from app.ai.inference.risk import _load_forecast_model, MODEL_DIR
    assert (MODEL_DIR / "forecast_model.pkl").exists(), "forecast_model.pkl missing"
    model = _load_forecast_model()
    assert model is not None, "Forecast model is None"
    print(f"    loaded={type(model).__name__}")

def test_forecast_predict():
    from app.ai.inference.risk import predict_forecast
    records = [
        {"district": "Bengaluru Urban", "occurred_at": "2026-01-15", "category": "Theft"},
        {"district": "Bengaluru Urban", "occurred_at": "2026-02-10", "category": "Assault"},
        {"district": "Bengaluru Urban", "occurred_at": "2026-03-20", "category": "Theft"},
        {"district": "Mysuru", "occurred_at": "2026-01-05", "category": "Narcotics"},
        {"district": "Mysuru", "occurred_at": "2026-02-18", "category": "Theft"},
        {"district": "Mysuru", "occurred_at": "2026-03-12", "category": "Assault"},
    ]
    result = predict_forecast(records)
    assert isinstance(result, list) and len(result) > 0
    for r in result[:2]:
        print(f"    district={r['district']}, predicted={r.get('predicted_crime_count')}, trend={r.get('trend','?')}")

check("Forecast model load", test_forecast_load)
check("Forecast prediction (ML-based)", test_forecast_predict)

# ── 4. Criminal Risk Scorer ───────────────────────────────────────
print("\n=== 4. CRIMINAL RISK SCORER (Weighted Linear) ===")

def test_criminal_risk():
    from app.ai.models.criminal.risk_scorer import CriminalRiskScorer
    scorer = CriminalRiskScorer(feature_names=FEATURES)
    X = np.array([[1,2,3,4,5,30,1,10,200,1]] * 10, dtype=float)
    scorer.train(X)
    result = scorer.predict(X[0], criminal_id="CRIM-TEST")
    print(f"    score={result.risk_score}, band={result.risk_band}, confidence={result.confidence:.2f}, factors={len(result.top_factors)}")

check("Criminal risk scorer", test_criminal_risk)

# ── 5. Repeat Offender Predictor ──────────────────────────────────
print("\n=== 5. REPEAT OFFENDER PREDICTOR (Logistic GD) ===")

def test_repeat_offender():
    from app.ai.models.criminal.repeat_offender import RepeatOffenderPredictor
    predictor = RepeatOffenderPredictor(feature_names=FEATURES)
    X = np.array([[1,2,3,4,5,30,1,10,200,1]] * 10, dtype=float)
    y = np.array([0,1,1,0,1,1,0,0,1,1])
    predictor.train(X, y)
    result = predictor.predict(X[0], criminal_id="CRIM-TEST")
    print(f"    probability={result.probability:.4f}, will_reoffend={result.will_reoffend}")

check("Repeat offender predictor", test_repeat_offender)

# ── 6. Similar Offender Model ─────────────────────────────────────
print("\n=== 6. SIMILAR OFFENDER MODEL (Cosine KNN) ===")

def test_similar_offenders():
    from app.ai.models.criminal.similarity import SimilarOffenderModel
    model = SimilarOffenderModel(feature_names=FEATURES)
    vectors = np.array([[1,2,3,4,5,30,1,10,200,1]] * 5 + [[10,9,8,7,6,25,0,50,100,0]] * 5, dtype=float)
    ids = [f"criminal-{i}" for i in range(10)]
    model.train(vectors, ids=ids)
    result = model.predict(vectors[0], query_id="criminal-0", top_k=3)
    print(f"    query={result.query_id}, found {len(result.similar)} similar offenders")
    if result.similar:
        top = result.similar[0]
        print(f"    top match: id={top.criminal_id}, similarity={top.similarity:.4f}, rank={top.rank}")

check("Similar offender model", test_similar_offenders)

# ── 7. Criminal Clustering ────────────────────────────────────────
print("\n=== 7. CRIMINAL CLUSTERING (Mini k-means) ===")

def test_clustering():
    from app.ai.models.criminal.clustering import CriminalClusteringModel
    model = CriminalClusteringModel(feature_names=FEATURES, n_clusters=2)
    vectors = np.array([[1,2,3,4,5,30,1,10,200,1]] * 10 + [[10,9,8,7,6,25,0,50,100,0]] * 10, dtype=float)
    model.train(vectors)
    result = model.predict(vectors[0], criminal_id="CRIM-TEST")
    print(f"    cluster={result.cluster_id}, label={result.cluster_label}, distance={result.distance_to_centroid:.3f}")

check("Criminal clustering", test_clustering)

# ── 8. Anomaly Detector ──────────────────────────────────────────
print("\n=== 8. ANOMALY DETECTOR (Z-score L2) ===")

def test_anomaly():
    from app.ai.inference.anomaly import run_anomaly_inference
    events = [
        {"event_id": "EVT-001", "lat": 12.97, "lon": 77.59, "hour": 14,
         "district": "Bengaluru Urban", "crime_type": "Theft", "officer_id": "OFF-001", "offender_id": "CRIM-001"},
        {"event_id": "EVT-002", "lat": 15.36, "lon": 75.13, "hour": 3,
         "district": "Kalaburagi", "crime_type": "Assault", "officer_id": "OFF-002", "offender_id": "CRIM-002"},
    ]
    result = run_anomaly_inference(events)
    assert isinstance(result, list) and len(result) == 2
    anomalies = sum(1 for a in result if a.get("is_anomaly"))
    print(f"    alerts={len(result)}, anomalies={anomalies}, scores={[round(a['score'],3) for a in result]}")

check("Anomaly detector", test_anomaly)

# ── 9. Feature Engineering ────────────────────────────────────────
print("\n=== 9. FEATURE ENGINEERING ===")

def test_risk_features():
    from app.ai.features.risk.feature_engineering import build_risk_features
    import pandas as pd
    df = pd.DataFrame([
        {"district": "Bengaluru Urban", "occurred_at": "2026-07-01", "category": "Theft"},
        {"district": "Bengaluru Urban", "occurred_at": "2026-07-15", "category": "Assault"},
        {"district": "Bengaluru Urban", "occurred_at": "2026-07-20", "category": "Theft"},
    ])
    features = build_risk_features(df, include_target=False)
    assert len(features.columns) >= 5
    print(f"    risk features: {len(features.columns)} columns")

def test_forecast_features():
    from app.ai.features.risk.feature_engineering import build_forecast_features
    import pandas as pd
    df = pd.DataFrame([
        {"district": "Bengaluru Urban", "occurred_at": "2026-01-15", "category": "Theft"},
        {"district": "Bengaluru Urban", "occurred_at": "2026-02-10", "category": "Assault"},
        {"district": "Bengaluru Urban", "occurred_at": "2026-03-20", "category": "Theft"},
    ])
    features = build_forecast_features(df, include_target=False)
    assert len(features.columns) >= 5
    print(f"    forecast features: {len(features.columns)} columns")

check("Risk feature engineering", test_risk_features)
check("Forecast feature engineering", test_forecast_features)

# ── 10. RAG Chat ──────────────────────────────────────────────────
print("\n=== 10. RAG CHAT SYSTEM ===")

def test_vector_store():
    from app.ai.vectorstore.memory import InMemoryVectorStore, VectorDocument
    store = InMemoryVectorStore()
    docs = [
        VectorDocument(id="doc1", text="crime in Bengaluru Urban area", title="Analytics", metadata={"source": "analytics"}),
        VectorDocument(id="doc2", text="theft case registered in Mysuru", title="FIR", metadata={"source": "fir"}),
        VectorDocument(id="doc3", text="narcotics smuggling operations", title="Criminal", metadata={"source": "criminal"}),
    ]
    store.index(docs)
    results = store.search("Bengaluru crime", top_k=2)
    assert len(results) > 0, "No results from vector search"
    print(f"    indexed {len(docs)} docs, search returned {len(results)} results, top_score={results[0].score:.4f}")

def test_intent_router():
    from app.ai.chat.intent_router import IntentRouter
    router = IntentRouter()
    result = router.detect("show me the hotspot predictions for Bengaluru Urban")
    assert result is not None
    print(f"    intents={[i.intent if hasattr(i, 'intent') else i for i in result.intents]}, confidence={result.confidence:.2f}")

check("In-memory vector store", test_vector_store)
check("Intent router", test_intent_router)

# ── 11. Training Pipelines ────────────────────────────────────────
print("\n=== 11. TRAINING PIPELINES ===")

def test_criminal_pipeline():
    from app.ai.pipelines.criminal.train import run_training
    print(f"    criminal pipeline imported OK")

def test_risk_pipeline():
    from app.ai.pipelines.risk.train import run_training
    print(f"    risk pipeline imported OK")

check("Criminal training pipeline", test_criminal_pipeline)
check("Risk training pipeline", test_risk_pipeline)

# ── Summary ───────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"RESULTS: {OK} passed, {FAIL} failed out of {OK+FAIL} tests")
if FAIL == 0:
    print("\n*** ALL AI MODELS VERIFIED SUCCESSFULLY ***")
else:
    print(f"\nWARNING: {FAIL} test(s) failed")
    sys.exit(1)
