"""Identity module security tests (issue #225).

RBAC: review/confirm/run endpoints are gated to REVIEW_ROLES (admin, crime
analyst, investigator, inspector). Read-only identity endpoints are open to all
authenticated roles. PII is never leaked through the identifier registry.
"""
from datetime import date

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink
from app.models.location import Location
from app.models.role import Role
from app.models.user import User

ID = "/api/v2/identity"
SEARCH = f"{ID}/search"


def _role(db_session, name):
    role = db_session.query(Role).filter_by(name=name).first()
    if role is None:
        role = Role(name=name, description=name.title())
        db_session.add(role)
        db_session.flush()
    return role


def _make_user(db_session, username, role_name):
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username.title(),
        hashed_password=hash_password("Password123!"),
        role_id=_role(db_session, role_name).id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def bind_user(client, db_session):
    def _bind(username, role_name):
        user = _make_user(db_session, username, role_name)
        client.app.dependency_overrides[get_current_user] = lambda: user
        return user
    yield _bind
    client.app.dependency_overrides.pop(get_current_user, None)


def _seed_provable_pair(db_session):
    """Same-DOB/address pair linked by one FIR → probable identity candidate."""
    category = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="medium")
    location = Location(district="Bengaluru Urban", station="KR Puram",
                        latitude=13.0, longitude=77.7)
    db_session.add_all([category, location])
    db_session.flush()
    a = Criminal(full_name="Balu Swamy", date_of_birth=date(1992, 6, 11),
                 address="14, 5th Main, Whitefield, Bengaluru", status="at_large",
                 mo_summary="Rides KA-01-MQ-4321 and uses 98450 12345.")
    b = Criminal(full_name="Ramu Kumar", date_of_birth=date(1992, 6, 11),
                 address="14, 5th Main, Whitefield, Bengaluru", status="at_large",
                 mo_summary="Same house; no identifiers.")
    db_session.add_all([a, b])
    db_session.flush()
    case = CrimeCase(case_number="CR-ID-003", category_id=category.id, location_id=location.id,
                     occurred_at=date(2026, 5, 1), status="open", description="D")
    db_session.add(case)
    db_session.flush()
    fir = FIR(fir_number="FIR-ID-003", crime_case_id=case.id, complainant_name="C",
              sections="379", status="registered", narrative="Nothing hashed.")
    db_session.add(fir)
    db_session.flush()
    db_session.add(FIRCriminalLink(fir_id=fir.id, criminal_id=a.id, role="accused"))
    db_session.add(FIRCriminalLink(fir_id=fir.id, criminal_id=b.id, role="accused"))
    db_session.commit()
    return a, b


def test_identity_endpoints_require_authentication(client):
    assert client.get(SEARCH + "?q=ram").status_code == 401
    assert client.get(f"{ID}/dashboard").status_code == 401


def test_read_endpoints_open_to_all_authenticated_roles(client, db_session, bind_user):
    _seed_provable_pair(db_session)
    for role in ("viewer", "investigator", "crime_analyst", "policymaker", "admin"):
        bind_user(f"u-{role}", role)
        assert client.get(SEARCH + "?q=ram").status_code == 200
        assert client.get(f"{ID}/relationships").status_code == 200
        assert client.get(f"{ID}/alerts").status_code == 200
        assert client.get(f"{ID}/proxy/rules").status_code == 200


def test_relationship_review_requires_review_role(client, db_session, bind_user):
    a, b = _seed_provable_pair(db_session)
    from app.services.identity_service import run_identity_resolution, sync_identity_identifiers
    sync_identity_identifiers(db_session)
    run_identity_resolution(db_session, persist=True)
    db_session.commit()

    from app.models.identity import IdentityRelationship
    rel = db_session.query(IdentityRelationship).first()
    assert rel is not None
    url = f"{ID}/relationships/{rel.id}/review?decision=confirm_same&note=verified"

    bind_user("review-role-user", "investigator")
    ok = client.post(url)
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "confirmed_same"

    db_session.refresh(rel)
    assert rel.status == "confirmed_same"


def test_data_errors_and_viewers_cannot_review(client, db_session, bind_user):
    a, b = _seed_provable_pair(db_session)
    from app.services.identity_service import run_identity_resolution, sync_identity_identifiers
    sync_identity_identifiers(db_session)
    run_identity_resolution(db_session, persist=True)
    db_session.commit()

    from app.models.identity import IdentityRelationship
    rel = db_session.query(IdentityRelationship).first()
    url = f"{ID}/relationships/{rel.id}/review?decision=reject"

    for role in ("viewer", "forensic", "policymaker"):
        bind_user(f"no-review-{role}", role)
        resp = client.post(url)
        assert resp.status_code in (401, 403), f"{role} must be denied, got {resp.status_code}"


def test_run_requires_review_role(client, db_session, bind_user):
    _seed_provable_pair(db_session)
    bind_user("view-runner", "viewer")
    denied = client.post(f"{ID}/run")
    assert denied.status_code in (401, 403)

    bind_user("analyst-runner", "crime_analyst")
    ok = client.post(f"{ID}/run")
    assert ok.status_code == 200
    body = ok.json()
    assert "relationships_proposed" in body and "proxy_patterns_detected" in body


def test_identifiers_endpoint_never_exposes_raw_pii(client, db_session, bind_user):
    a, _ = _seed_provable_pair(db_session)
    from app.services.identity_service import sync_identity_identifiers
    sync_identity_identifiers(db_session)
    db_session.commit()
    bind_user("review-pii", "crime_analyst")

    resp = client.get(f"{ID}/identifiers?entity_type=criminal&entity_id={a.id}")
    assert resp.status_code == 200
    payload = resp.json()["results"]
    assert payload
    raw = "\n".join(str(r.get("display_value", "")) for r in payload) + \
        "\n" + "\n".join(r.get("value_hash", "") for r in payload)
    assert "9845012345" not in raw, "raw PII must never leak from the registry"


def _seed_proxy_pair(db_session):
    """Distinct-biometrics pair sharing phone + vehicle → proxy-eligible pair."""
    a = Criminal(full_name="Arjun Pai", date_of_birth=date(1991, 4, 2),
                 address="10, 2nd Cross, Jayanagar, Bengaluru", status="at_large",
                 mo_summary="Uses 98450 12345; rides KA-05-AB-1234.")
    b = Criminal(full_name="Kiran Nair", date_of_birth=date(1987, 9, 15),
                 address="3, MG Road, Mysuru", status="at_large",
                 mo_summary="Associate uses 98450 12345; drives KA-05-AB-1234.")
    db_session.add_all([a, b])
    db_session.commit()
    return a, b


def test_proxy_review_requires_review_role(client, db_session, bind_user):
    _seed_proxy_pair(db_session)
    from app.services.identity_service import sync_identity_identifiers
    from app.services.proxy_pattern_service import detect_proxy_patterns
    sync_identity_identifiers(db_session)
    detect_proxy_patterns(db_session, persist=True)
    db_session.commit()

    from app.models.identity import ProxyPattern
    row = db_session.query(ProxyPattern).first()
    assert row is not None, "shared phone+vehicle must generate a proxy pattern"
    url = f"{ID}/proxy/{row.id}/review?decision=investigate"

    bind_user("public-checker", "viewer")
    denied = client.post(url)
    assert denied.status_code in (401, 403)

    bind_user("lead-investigator", "investigator")
    ok = client.post(url)
    assert ok.status_code == 200
    assert ok.json()["status"] == "in_review"