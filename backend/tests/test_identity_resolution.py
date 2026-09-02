"""Identity Resolution engine tests (issue #225).

Service-level scenarios backed by the in-memory SQLite fixture, mirroring the
acceptance personas seeded by ``_seed_identity_demo``:

  * Ramu Kumar / Balu Swamy  — same DOB + same address, no name overlap:
    PROBABLE identity (never auto-confirmed).
  * Balu Swamy / Kumar Swamy — shared phone + vehicle, conflicting DOB/address:
    POSSIBLE association (proxy territory), never identity.
  * Same name + shared phone + conflicting DOB: capped at POSSIBLE identity.

Every test also enforces the conservative design rules (nothing auto-confirmed,
single attributes never merge, identifiers stored hashed).
"""
from datetime import date, datetime, timezone

from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink
from app.models.identity import (
    IdentityConflict,
    IdentityEvidence,
    IdentityIdentifier,
    IdentityRelationship,
    IntegrityAlert,
    REL_STATUS_OPEN,
    SEVERITY_HIGH,
)
from app.models.location import Location
from app.services.identity_service import (
    run_identity_resolution,
    search_identity,
    sync_identity_identifiers,
)

_MY_DOB = date(1992, 6, 11)
_OTHER_DOB = date(1985, 3, 22)


def _category_location(db_session):
    category = db_session.query(CrimeCategory).filter_by(name="Theft & Burglaries").first()
    if category is None:
        category = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="medium")
        db_session.add(category)
    location = db_session.query(Location).filter(Location.station == "KR Puram").first()
    if location is None:
        location = Location(district="Bengaluru Urban", station="KR Puram Police Station",
                            latitude=13.0, longitude=77.7)
        db_session.add(location)
    db_session.flush()
    return category, location


def _fir(db_session, category, location, case_no, fir_no, criminals, narrative):
    case = CrimeCase(
        case_number=case_no, category_id=category.id, location_id=location.id,
        occurred_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        reported_at=datetime(2026, 5, 1, 4, 0, tzinfo=timezone.utc),
        description=narrative, status="open",
    )
    db_session.add(case)
    db_session.flush()
    fir = FIR(fir_number=fir_no, crime_case_id=case.id, complainant_name="Complainant",
              sections="379", status="registered",
              filed_at=datetime(2026, 5, 1, 3, 0, tzinfo=timezone.utc),
              narrative=narrative)
    db_session.add(fir)
    db_session.flush()
    for cr in criminals:
        db_session.add(FIRCriminalLink(fir_id=fir.id, criminal_id=cr.id, role="accused"))
    db_session.flush()
    return fir


def _criminal(db_session, name, *, dob=None, address=None, mo_summary="", aliases=None):
    cr = Criminal(full_name=name, aliases=aliases, date_of_birth=dob, address=address,
                  mo_summary=mo_summary or "No specifics recorded.", status="at_large")
    db_session.add(cr)
    db_session.flush()
    return cr


def _rel_between(db_session, name_a, name_b):
    """Return the IdentityRelationship row spanning the two given profiles."""
    from app.routes.identity import _resolve_names
    for rel in db_session.query(IdentityRelationship).all():
        sa, sb = _resolve_names(db_session, rel)
        if {sa, sb} == {name_a, name_b}:
            return rel
    return None


def _populate_ramu_balu(db_session):
    """Ramu Kumar + Balu Swamy: identical DOB/address, no name overlap."""
    category, location = _category_location(db_session)
    ramu = _criminal(db_session, "Ramu Kumar", dob=_MY_DOB,
                     address="14, 5th Main, Whitefield, Bengaluru",
                     mo_summary="Fields reports of encroachment near a sub-station.")
    balu = _criminal(db_session, "Balu Swamy", dob=_MY_DOB,
                     address="14, 5th Main, Whitefield, Bengaluru",
                     mo_summary="Reported in connection with premises entry attempts.")
    _fir(db_session, category, location, "CR-ID-001", "FIR-ID-001", [ramu, balu],
         "Complainant reports repeated premises entry attempts by known suspects.")
    db_session.flush()
    return ramu, balu


def test_same_dob_and_address_is_probable_identity(db_session):
    ramu, balu = _populate_ramu_balu(db_session)
    sync_identity_identifiers(db_session)
    summary = run_identity_resolution(db_session, persist=True)
    db_session.flush()

    rel = _rel_between(db_session, "Ramu Kumar", "Balu Swamy")
    assert rel is not None, "pair must be surfaced as a candidate"
    assert rel.assessment == "PROBABLE_IDENTITY_MATCH"
    assert rel.relationship_type == "SAME_PERSON_PROBABLE"
    assert rel.confidence >= 60.0
    assert rel.status == REL_STATUS_OPEN, "nothing is auto-confirmed"

    # Explainable evidence: DOB + address (no name/exact-name signal).
    signals = {e.signal_type for e in db_session.query(IdentityEvidence).filter_by(relationship_id=rel.id).all()}
    assert "dob_match" in signals
    assert "shared_address" in signals
    assert not ({s for s in signals if "name" in s} & {"normalized_name_exact", "name_initial_overlap"})
    assert summary["relationships_proposed"] >= 1


def test_sibling_balu_kumar_shared_phone_vehicle_is_association(db_session):
    """Shared phone + vehicle but distinct biometrics → POSSIBLE association."""
    balu = _criminal(db_session, "Balu Swamy", dob=_MY_DOB,
                     address="14, 5th Main, Whitefield, Bengaluru",
                     mo_summary="Uses contact 98450 12345; rides KA-01-MQ-4321.")
    kumar = _criminal(db_session, "Kumar Swamy", dob=_OTHER_DOB,
                      address="88, MG Road, Mysuru",
                      mo_summary="Associate uses 98450 12345; moves goods on KA-01-MQ-4321.")
    db_session.flush()
    sync_identity_identifiers(db_session)
    run_identity_resolution(db_session, persist=True)
    db_session.flush()

    rel = _rel_between(db_session, "Balu Swamy", "Kumar Swamy")
    assert rel is not None
    assert rel.assessment == "POSSIBLE_ASSOCIATED"
    assert rel.relationship_type == "ASSOCIATED_WITH"
    assert rel.status == REL_STATUS_OPEN

    # Conflict surfaces honestly.
    conflicts = db_session.query(IdentityConflict).filter_by(relationship_id=rel.id).all()
    assert any(c.attribute == "dob" and c.severity == SEVERITY_HIGH for c in conflicts)


def test_single_shared_phone_never_merges(db_session):
    """One shared identifier alone must never become an identity claim."""
    a = _criminal(db_session, "Ramesh Rao", mo_summary="Reached on 98450 00011.")
    b = _criminal(db_session, "Suresh Rao", mo_summary="Reached on 98450 00011.")
    db_session.flush()
    sync_identity_identifiers(db_session)
    run_identity_resolution(db_session, persist=True)
    db_session.flush()

    rel = _rel_between(db_session, "Ramesh Rao", "Suresh Rao")
    assert rel is not None
    assert rel.assessment in ("POSSIBLE_ASSOCIATED", "REQUIRES_INVESTIGATOR_REVIEW")
    assert "SAME_PERSON" not in rel.relationship_type


def test_conflicting_dob_caps_identity_to_possible(db_session):
    """Exact same name + shared phone but different DOB → POSSIBLE, not PROBABLE."""
    a = _criminal(db_session, "Sameer Pai", dob=_MY_DOB, mo_summary="Uses 94802 22222.")
    b = _criminal(db_session, "Sameer Pai", dob=_OTHER_DOB, mo_summary="Uses 94802 22222.")
    db_session.flush()
    sync_identity_identifiers(db_session)
    run_identity_resolution(db_session, persist=True)
    db_session.flush()

    rel = _rel_between(db_session, "Sameer Pai", "Sameer Pai")
    assert rel is not None
    assert rel.assessment == "POSSIBLE_IDENTITY_MATCH"
    assert rel.relationship_type == "SAME_PERSON_POSSIBLE"
    assert rel.confidence < 60.0, "conflict must keep the pair out of probable"

    dob_conflicts = db_session.query(IdentityConflict).filter(
        IdentityConflict.relationship_id == rel.id,
        IdentityConflict.attribute == "dob",
    ).all()
    assert dob_conflicts, "conflicting DOB must be recorded"


def test_scan_is_idempotent(db_session):
    _populate_ramu_balu(db_session)
    db_session.flush()
    sync_identity_identifiers(db_session)
    first = run_identity_resolution(db_session, persist=True)
    db_session.flush()
    before = db_session.query(IdentityRelationship).count()
    second = run_identity_resolution(db_session, persist=True)
    db_session.flush()
    after = db_session.query(IdentityRelationship).count()
    assert first["relationships_proposed"] >= 1
    assert after == before, "re-running must not duplicate relationship rows"


def test_integrity_alert_raised_and_open(db_session):
    _populate_ramu_balu(db_session)
    db_session.flush()
    sync_identity_identifiers(db_session)
    run_identity_resolution(db_session, persist=True)
    db_session.flush()

    alerts = db_session.query(IntegrityAlert).all()
    assert alerts, "probable duplicate must raise an integrity alert"
    assert any(a.status == "open" and a.alert_type == "possible_duplicate" for a in alerts)


def test_identifiers_are_hashed_and_masked(db_session):
    _criminal(db_session, "Ramu Kumar", dob=_MY_DOB, mo_summary="Uses 98450 12345; rides KA-01-MQ-4321.")
    db_session.flush()
    written = sync_identity_identifiers(db_session)
    db_session.flush()

    identifiers = db_session.query(IdentityIdentifier).all()
    assert written >= 2
    assert identifiers, "identifiers must be persisted"
    for ident in identifiers:
        assert len(ident.value_hash) == 64, "raw values must never be stored"
    raw_phone_seen = any(i.display_value and "9845012345" in i.display_value for i in identifiers)
    assert not raw_phone_seen, "display values must be masked, not raw PII"


def test_search_identity_returns_person_and_matches(db_session):
    _populate_ramu_balu(db_session)
    db_session.flush()
    sync_identity_identifiers(db_session)
    run_identity_resolution(db_session, persist=True)
    db_session.flush()

    result = search_identity(db_session, "Ramu")
    hits = result.get("exact") or result.get("probable") or result.get("possible") or []
    assert hits, "search must surface the Ramu record"
    assert any(h["name"] == "Ramu Kumar" for h in hits), "search must surface the Ramu Kumar record"


