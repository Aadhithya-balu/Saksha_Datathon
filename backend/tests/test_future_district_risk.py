from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User


def _seed_admin(db_session):
    role = Role(name="admin", description="Administrator")
    db_session.add(role)
    db_session.flush()
    user = User(
        username="futureadmin",
        email="futureadmin@example.com",
        full_name="Future Admin",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_future_district_risk_endpoint(client, db_session):
    _seed_admin(db_session)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "futureadmin", "password": "Password123!"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/analytics/future-district-risk",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "district": "Bengaluru Urban",
            "year": 2026,
            "violent_crime": 120,
            "property_crime": 300,
            "women_crime": 80,
            "previous_year_crime": 1100,
            "crime_growth": 0.12,
            "rolling_avg": 950,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "Random Forest Regressor"
    assert payload["risk_level"] in {"LOW", "MEDIUM", "HIGH", "VERY_HIGH"}
    assert payload["predicted_crime_count"] >= 0
    assert payload["metrics"]["r2"] == 0.9534
