"""HTTP smoke tests for all live API endpoints."""
import httpx
import sys

BASE = "http://127.0.0.1:8000/api/v2"
OK = 0
FAIL = 0

def api_test(name, method, url, payload=None, token=None):
    global OK, FAIL
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            if method == "POST":
                r = client.post(url, json=payload, headers=headers)
            else:
                r = client.get(url, headers=headers)
        status = r.status_code
        if status < 400:
            print(f"  [PASS] {name} (HTTP {status})")
            OK += 1
            try:
                return r.json()
            except Exception:
                return {"_raw": r.text[:200]}
        else:
            body = r.text[:300]
            print(f"  [FAIL] {name} (HTTP {status}): {body}")
            FAIL += 1
            return None
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        FAIL += 1
        return None

# 1. Auth
print("\n=== AUTH ===")
resp = api_test("Login (admin)", "POST", f"{BASE}/auth/login", {"username": "admin", "password": "564738"})
token = resp.get("access_token") if resp else None
if not token:
    print("FATAL: Cannot get auth token")
    sys.exit(1)

# 2. Core CRUD (no trailing slash - httpx will follow redirect)
print("\n=== CORE CRUD ===")
api_test("GET /criminals", "GET", f"{BASE}/criminals", token=token)
api_test("GET /victims", "GET", f"{BASE}/victims", token=token)
api_test("GET /firs", "GET", f"{BASE}/firs", token=token)
api_test("GET /officers", "GET", f"{BASE}/officers", token=token)
api_test("GET /evidence", "GET", f"{BASE}/evidence", token=token)
api_test("GET /notifications", "GET", f"{BASE}/notifications", token=token)

# 3. Dashboard
print("\n=== DASHBOARD ===")
api_test("GET /dashboard/summary", "GET", f"{BASE}/dashboard/summary", token=token)
api_test("GET /dashboard/crime-trends", "GET", f"{BASE}/dashboard/crime-trends", token=token)
api_test("GET /dashboard/category-breakdown", "GET", f"{BASE}/dashboard/category-breakdown", token=token)
api_test("GET /dashboard/district-comparison", "GET", f"{BASE}/dashboard/district-comparison", token=token)
api_test("GET /dashboard/risk-prediction", "GET", f"{BASE}/dashboard/risk-prediction", token=token)
api_test("GET /dashboard/forecast", "GET", f"{BASE}/dashboard/forecast", token=token)
api_test("GET /dashboard/officer-stats", "GET", f"{BASE}/dashboard/officer-stats", token=token)
api_test("GET /dashboard/recent-incidents", "GET", f"{BASE}/dashboard/recent-incidents", token=token)

# 4. AI/ML endpoints
print("\n=== AI/ML ENDPOINTS ===")
api_test("GET /ai/hotspot/model-info", "GET", f"{BASE}/ai/hotspot/model-info", token=token)
api_test("GET /ai/predictions/model-info", "GET", f"{BASE}/ai/predictions/model-info", token=token)
api_test("GET /ai/predictions/risk-scores (GET)", "GET", f"{BASE}/ai/predictions/risk-scores", token=token)
api_test("POST /ai/predictions/risk-scores", "POST", f"{BASE}/ai/predictions/risk-scores", {
    "records": [{"case_id":"T1","district":"Bengaluru Urban","category":"Theft",
                 "occurred_at":"2026-07-01","priority":"high","status":"open"}]
}, token=token)
api_test("POST /ai/predictions/forecast", "POST", f"{BASE}/ai/predictions/forecast", {
    "records": [
        {"district":"Bengaluru Urban","occurred_at":"2026-01-15","category":"Theft"},
        {"district":"Bengaluru Urban","occurred_at":"2026-02-10","category":"Assault"},
        {"district":"Bengaluru Urban","occurred_at":"2026-03-20","category":"Theft"},
        {"district":"Mysuru","occurred_at":"2026-01-05","category":"Narcotics"},
        {"district":"Mysuru","occurred_at":"2026-02-18","category":"Theft"},
        {"district":"Mysuru","occurred_at":"2026-03-12","category":"Assault"},
    ]
}, token=token)

api_test("GET /ai/criminal/{id}/risk", "GET", f"{BASE}/ai/criminal/f0000000-0000-0000-0000-000000000001/risk", token=token)
api_test("GET /ai/criminal/{id}/repeat-offender", "GET", f"{BASE}/ai/criminal/f0000000-0000-0000-0000-000000000001/repeat-offender", token=token)
api_test("GET /ai/criminal/{id}/similar", "GET", f"{BASE}/ai/criminal/f0000000-0000-0000-0000-000000000001/similar", token=token)
api_test("GET /ai/criminal/{id}/cluster", "GET", f"{BASE}/ai/criminal/f0000000-0000-0000-0000-000000000001/cluster", token=token)
api_test("GET /ai/criminal/{id}/recommendations", "GET", f"{BASE}/ai/criminal/f0000000-0000-0000-0000-000000000001/recommendations", token=token)
api_test("POST /ai/anomaly/detect", "POST", f"{BASE}/ai/anomaly/detect", {}, token=token)
api_test("GET /ai/predictions/anomalies", "GET", f"{BASE}/ai/predictions/anomalies", token=token)

# 5. Network
print("\n=== NETWORK ===")
api_test("GET /network/graph", "GET", f"{BASE}/network/graph?limit=10", token=token)
api_test("GET /network/gangs", "GET", f"{BASE}/network/gangs", token=token)
api_test("GET /network/insights", "GET", f"{BASE}/network/insights", token=token)

# 6. Reports
print("\n=== REPORTS ===")
api_test("GET /reports/statistics/summary", "GET", f"{BASE}/reports/statistics/summary", token=token)

# 7. Admin
print("\n=== ADMIN ===")
api_test("GET /admin/users", "GET", f"{BASE}/admin/users", token=token)
api_test("GET /admin/audit-logs", "GET", f"{BASE}/admin/audit-logs", token=token)
api_test("GET /admin/roles", "GET", f"{BASE}/admin/roles", token=token)
api_test("GET /admin/settings", "GET", f"{BASE}/admin/settings", token=token)

sep = "=" * 50
print(f"\n{sep}")
print(f"RESULTS: {OK} passed, {FAIL} failed out of {OK+FAIL} endpoint tests")
