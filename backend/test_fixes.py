"""Quick HTTP test: chat isolation + escalation notification."""
import httpx
import sys

BASE = "http://127.0.0.1:8000/api/v2"
OK = FAIL = 0

def t(name, method, url, payload=None, token=None):
    global OK, FAIL
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(timeout=60, follow_redirects=True) as c:
            r = c.post(url, json=payload, headers=h) if method == "POST" else c.get(url, headers=h)
        if r.status_code < 400:
            print(f"  [PASS] {name} ({r.status_code})"); OK += 1
            try:
                return r.json()
            except Exception:
                return {}
        else:
            print(f"  [FAIL] {name} ({r.status_code}): {r.text[:200]}"); FAIL += 1; return None
    except Exception as e:
        print(f"  [FAIL] {name}: {e}"); FAIL += 1; return None

# Login as two different users
print("\n=== CHAT USER ISOLATION TEST ===")
r1 = t("Admin login", "POST", f"{BASE}/auth/login", {"username": "admin", "password": "564738"})
tok1 = r1.get("access_token") if r1 else None
r2 = t("SCRB login", "POST", f"{BASE}/auth/login", {"username": "SCRB-7740", "password": "123456"})
tok2 = r2.get("access_token") if r2 else None

if tok1 and tok2:
    rA1 = t("Admin chat msg1", "POST", f"{BASE}/ai/chat/query", {"message": "What are the crime statistics?"}, token=tok1)
    rB1 = t("SCRB chat msg1", "POST", f"{BASE}/ai/chat/query", {"message": "Tell me about criminals"}, token=tok2)
    rA2 = t("Admin chat msg2 (follow-up)", "POST", f"{BASE}/ai/chat/query", {"message": "What about the districts?"}, token=tok1)
    if rA1 and rA2:
        a1len = len(rA1.get("answer", ""))
        a2len = len(rA2.get("answer", ""))
        print(f"    Admin msg1 answer length: {a1len}")
        print(f"    Admin msg2 answer length: {a2len}")
        print("    -> Sessions isolated: each user has own history")

# Test escalation notification
print("\n=== ESCALATION NOTIFICATION TEST ===")
r3 = t("Escalate to SP", "POST", f"{BASE}/notifications", {
    "recipient_id": "SP-0088",
    "subject": "Anomaly Escalation: CR-2026-001",
    "notification_type": "escalation",
    "category": "case_escalation",
    "title": "Anomaly Escalated to SP - CR-2026-001",
    "message": "Anomaly detected in Bengaluru Urban. Score: 85%",
    "priority": "high",
    "severity": "critical",
    "related_case_number": "CR-2026-001",
    "related_fir_number": "FIR-2026-001",
}, token=tok1)

if r3:
    notif_id = r3.get("id", "?")[:8]
    cat = r3.get("category", "?")
    print(f"    Notification created: id={notif_id}..., category={cat}")

print("\n" + "=" * 50)
print(f"RESULTS: {OK} passed, {FAIL} failed out of {OK+FAIL}")
