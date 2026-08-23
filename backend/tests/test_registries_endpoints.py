from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.criminal import Criminal
from app.models.victim import Victim
from app.models.role import Role
from app.models.user import User

def _seed_dbs(db: Session):
    role = db.query(Role).filter(Role.name == "admin").first()
    if not role:
        role = Role(name="admin", description="admin")
        db.add(role)
        db.flush()

    user = db.query(User).filter(User.username == "registry_test").first()
    if not user:
        user = User(
            username="registry_test",
            email="registry@saksha.local",
            full_name="Registry Tester",
            hashed_password=hash_password("TestPass1!"),
            role_id=role.id,
            is_active=True,
        )
        db.add(user)

    criminal = Criminal(
        full_name="John Doe Offender",
        aliases="Johnny",
        date_of_birth=date(1991, 1, 1),
        gender="Male",
        status="at_large",
        mo_summary="Modus operandi details here"
    )
    db.add(criminal)

    victim = Victim(
        full_name="Jane Doe Victim",
        contact_number="9876543210",
        address="123 Street",
        gender="Female",
        age=30,
        statement="Victim narrative statement"
    )
    db.add(victim)
    db.flush()
    return user, criminal, victim

def _get_token(client, username, password):
    resp = client.post(
        "/api/v2/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]

def test_criminals_registry_endpoints(client: TestClient, db_session: Session):
    user, criminal, victim = _seed_dbs(db_session)
    token = _get_token(client, "registry_test", "TestPass1!")
    headers = {"Authorization": f"Bearer {token}"}

    # Test list criminals
    resp = client.get("/api/v2/criminals", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(c["full_name"] == "John Doe Offender" for c in data["results"])

    # Test search criminals
    resp = client.get("/api/v2/criminals?q=Johnny", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert any(c["full_name"] == "John Doe Offender" for c in data["results"])

    # Test get criminal detail (intelligence enriched)
    resp = client.get(f"/api/v2/criminals/{criminal.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "John Doe Offender"
    assert "ai_risk" in data
    assert "ai_repeat" in data
    assert "ai_similar" in data
    assert "network" in data

def test_victims_registry_endpoints(client: TestClient, db_session: Session):
    user, criminal, victim = _seed_dbs(db_session)
    token = _get_token(client, "registry_test", "TestPass1!")
    headers = {"Authorization": f"Bearer {token}"}

    # Test list victims
    resp = client.get("/api/v2/victims", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(v["full_name"] == "Jane Doe Victim" for v in data["results"])

    # Test search victims
    resp = client.get("/api/v2/victims?q=Street", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert any(v["full_name"] == "Jane Doe Victim" for v in data["results"])

    # Test get victim detail
    resp = client.get(f"/api/v2/victims/{victim.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Jane Doe Victim"
    assert data["contact_number"] == "9876543210"
    assert "firs" in data
    assert "network" in data
