"""Auth flow tests: register (via seeded role) -> login -> access protected route."""
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User


def _seed_admin(db_session):
    role = Role(name="admin", description="Administrator")
    db_session.add(role)
    db_session.flush()
    user = User(
        username="testadmin",
        email="testadmin@example.com",
        full_name="Test Admin",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_login_success(client, db_session):
    _seed_admin(db_session)
    response = client.post("/api/v2/auth/login", json={"username": "testadmin", "password": "Password123!"})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_wrong_password(client, db_session):
    _seed_admin(db_session)
    response = client.post("/api/v2/auth/login", json={"username": "testadmin", "password": "wrong"})
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/v2/auth/me")
    assert response.status_code == 401
