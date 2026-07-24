"""Quick integration smoke test for the chat endpoints."""
import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DEBUG"] = "false"
os.environ["APP_DEBUG"] = "false"

import json
from app.main import app
from fastapi.testclient import TestClient
from app.auth.dependencies import get_current_user
from app.database.postgres import Base, engine


class DummyUser:
    id = "00000000-0000-0000-0000-000000000001"
    username = "testuser"
    email = "test@saksha.gov"


Base.metadata.create_all(bind=engine)
app.dependency_overrides[get_current_user] = lambda: DummyUser()

client = TestClient(app)

print("=== Test 1: /query endpoint (non-streaming) ===")
resp = client.post("/api/v1/ai/chat/query", json={"message": "What are the crime statistics?"})
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Answer length: {len(data.get('answer', ''))}")
print(f"Sources: {data.get('sources', [])}")
print(f"Classification: {data.get('classification', '')}")
print(f"Answer preview: {data.get('answer', '')[:200]}")
print()

print("=== Test 2: / endpoint (non-streaming) ===")
resp2 = client.post("/api/v1/ai/chat", json={"message": "Show all FIRs", "stream": False})
print(f"Status: {resp2.status_code}")
data2 = resp2.json()
print(f"Answer length: {len(data2.get('answer', ''))}")
print(f"Answer preview: {data2.get('answer', '')[:200]}")
print()

print("=== Test 3: / endpoint (streaming) ===")
resp3 = client.post("/api/v1/ai/chat", json={"message": "hello", "stream": True})
print(f"Status: {resp3.status_code}")
print(f"Content-Type: {resp3.headers.get('content-type', '')}")
lines = [l for l in resp3.text.split("\n") if l.strip()]
print(f"Stream lines: {len(lines)}")
for line in lines[:5]:
    parsed = json.loads(line)
    ctype = parsed.get("type")
    content = str(parsed.get("content", ""))[:120]
    print(f"  [{ctype}] {content}")

print()
print("=== Test 4: Criminal query ===")
resp4 = client.post("/api/v1/ai/chat/query", json={"message": "Tell me about Ramu Swamy"})
print(f"Status: {resp4.status_code}")
data4 = resp4.json()
print(f"Classification: {data4.get('classification', '')}")
print(f"Entities: {data4.get('entities', [])}")
print(f"Answer preview: {data4.get('answer', '')[:200]}")
print()

print("=== All tests completed ===")
