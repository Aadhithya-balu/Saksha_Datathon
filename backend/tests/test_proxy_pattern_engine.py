"""Proxy Pattern Detection engine tests (issue #225, PROXY-001..020).

Scenarios:
  * Rules catalog is complete (20 rules, PROXY-001..PROXY-020).
  * Balu/Kumar (shared phone + vehicle, conflicting DOB/address) → PROXY lead,
    persisted, always open (never auto-confirmed).
  * Probable-identity pairs are suppressed from the proxy engine entirely.
  * Unrelated records produce zero proxy emissions.
  * Review lifecycle is driven only by human decision.
"""
from datetime import date

from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink
from app.models.identity import ProxyPattern, ProxyPatternEvidence
from app.models.location import Location
from app.services.identity_service import run_identity_resolution, sync_identity_identifiers
from app.services.proxy_pattern_service import (
    PROXY_RULES,
    detect_proxy_patterns,
    rules_catalog,
)


def _criminal(db_session, name, *, dob=None, address=None, mo_summary="", aliases=None):
    cr = Criminal(full_name=name, aliases=aliases, date_of_birth=dob, address=address,
                  mo_summary=mo_summary or "No specifics recorded.", status="at_large")
    db_session.add(cr)
    db_session.flush()
    return cr


def _fir(db_session, case_no, fir_no, criminals, narrative="Statement recorded for the incident."):
    category = db_session.query(CrimeCategory).filter_by(name="Theft & Burglaries").first()
    if category is None:
        category = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="medium")
        db_session.add(category)
        db_session.flush()
    location = db_session.query(Location).filter(Location.station == "KR Puram").first()
    if location is None:
        location = Location(district="Bengaluru Urban", station="KR Puram Police Station",
                            latitude=13.0, longitude=77.7)
        db_session.add(location)
        db_session.flush()
    import datetime
    case = CrimeCase(case_number=case_no, category_id=category.id, location_id=location.id,
                     occurred_at=datetime.datetime(2026, 5, 1, tzinfo=datetime.timezone.utc),
                     status="open", description="Placeholder")
    db_session.add(case)
    db_session.flush()
    fir = FIR(fir_number=fir_no, crime_case_id=case.id, complainant_name="Complainant",
              sections="379", status="registered", narrative=narrative)
    db_session.add(fir)
    db_session.flush()
    for cr in criminals:
        db_session.add(FIRCriminalLink(fir_id=fir.id, criminal_id=cr.id, role="accused"))
    db_session.flush()
    return fir


def test_rules_catalog_complete_and_structured():
    catalog = rules_catalog()
    assert len(catalog) == 20
    ids = [r["rule_id"] for r in catalog]
    assert ids == [f"PROXY-{i:03d}" for i in range(1, 21)], "rules must be contiguous"
    for rule in catalog:
        assert rule["explanations"], "every rule needs innocent explanations"
        assert 0 < rule["weight"] <= 1
        assert rule["default_severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert len(PROXY_RULES) == 20


def _seed_proxy_pair(db_session):
    """Balu/Kumar: shared phone + vehicle, distinct DOB/address."""
    balu = _criminal(db_session, "Balu Swamy", dob=date(1992, 6, 11),
                     address="14, 5th Main, Whitefield, Bengaluru",
                     mo_summary="Uses contact 98450 12345; rides KA-01-MQ-4321.")
    kumar = _criminal(db_session, "Kumar Swamy", dob=date(1985, 3, 22),
                      address="88, MG Road, Mysuru",
                      mo_summary="Associate uses 98450 12345; moves goods on KA-01-MQ-4321.")
    db_session.flush()
    sync_identity_identifiers(db_session)
    return balu, kumar


def test_proxy_rules_fire_for_shared_identifier_pair(db_session):
    balu, kumar = _seed_proxy_pair(db_session)
    emissions = detect_proxy_patterns(db_session, persist=True)
    db_session.flush()

    assert emissions, "shared phone+vehicle across distinct persons must emit a proxy lead"
    pattern = emissions[0]
    assert pattern["assessment"] == "POSSIBLE_PROXY_RELATIONSHIP"
    assert {"PROXY-001", "PROXY-004"} <= set(pattern["rule_ids"])
    assert pattern["confidence"] >= 0.5
    assert pattern["possible_explanations"], "must preserve innocent explanations"

    # Persisted rows respect the lead-not-accusation contract.
    persisted = db_session.query(ProxyPattern).filter(
        ProxyPattern.grouping_key == pattern["grouping_key"]).all()
    assert persisted, "emissions must persist proxy pattern rows"
    assert all(p.status == "open" for p in persisted)
    evidence_rows = db_session.query(ProxyPatternEvidence).filter(
        ProxyPatternEvidence.pattern_id == persisted[0].id).all()
    assert evidence_rows, "persisted patterns carry expandable evidence"


def test_repeated_run_collapses_into_same_grouping(db_session):
    _seed_proxy_pair(db_session)
    first = detect_proxy_patterns(db_session, persist=True)
    db_session.flush()
    before = db_session.query(ProxyPattern).count()
    second = detect_proxy_patterns(db_session, persist=True)
    db_session.flush()
    after = db_session.query(ProxyPattern).count()
    assert first and second
    assert after == before, "re-running must not duplicate proxy pattern rows"
    # observation count should have incremented on the shared grouping key
    pattern = db_session.query(ProxyPattern).first()
    assert pattern.observation_count >= 2


def test_probable_identity_pair_is_not_a_proxy_lead(db_session):
    """Same DOB + same address (probable identity) suppressed from proxy engine."""
    balu = _criminal(db_session, "Balu Swamy", dob=date(1992, 6, 11),
                     address="14, 5th Main, Whitefield, Bengaluru",
                     mo_summary="No identifiers mentioned.")
    ramu = _criminal(db_session, "Ramu Kumar", dob=date(1992, 6, 11),
                     address="14, 5th Main, Whitefield, Bengaluru",
                     mo_summary="No identifiers mentioned.")
    _fir(db_session, "CR-ID-002", "FIR-ID-002", [balu, ramu])
    db_session.flush()
    sync_identity_identifiers(db_session)
    run_identity_resolution(db_session, persist=True)
    db_session.flush()

    emissions = detect_proxy_patterns(db_session, persist=True)
    db_session.flush()

    for p in emissions:
        names = {e["name"] for e in p["entities"]}
        assert names != {"Balu Swamy", "Ramu Kumar"}, \
            "probable identity pair must not be double-flagged as proxy"


def test_unrelated_records_produce_no_proxy(db_session):
    _criminal(db_session, "Deepak Sharma", dob=date(1993, 7, 25), mo_summary="No contact details.")
    _criminal(db_session, "Naveen Reddy", dob=date(1992, 3, 20), mo_summary="No contact details.")
    db_session.flush()
    sync_identity_identifiers(db_session)
    emissions = detect_proxy_patterns(db_session, persist=True)
    assert emissions == []


def test_proxy_review_lifecycle_requires_human(db_session):
    _seed_proxy_pair(db_session)
    detect_proxy_patterns(db_session, persist=True)
    db_session.flush()
    row = db_session.query(ProxyPattern).first()
    assert row.status == "open", "system never auto-confirms a proxy accusation"
    row.status = "in_review"
    db_session.flush()
    assert row.status == "in_review"


