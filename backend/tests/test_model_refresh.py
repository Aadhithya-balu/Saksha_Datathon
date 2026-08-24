"""Staleness-aware model refresh tests (issue #145: gaps 133.1-133.5)."""
import os
import sys
import types
from datetime import datetime, timedelta, timezone

import pytest

from app.ai.inference import refresh as refresh_mod
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.location import Location


# ---------------------------------------------------------------------------
# Timestamp parsing + artifact introspection
# ---------------------------------------------------------------------------

def test_parse_iso_handles_naive_z_and_garbage():
    naive = refresh_mod._parse_iso("2026-07-11T08:37:21.724753")
    assert naive is not None and naive.tzinfo is timezone.utc
    zulu = refresh_mod._parse_iso("2026-08-24T10:47:35Z")
    assert zulu is not None and zulu.tzinfo is timezone.utc
    aware = refresh_mod._parse_iso("2026-08-24T10:47:35+00:00")
    assert aware == zulu
    assert refresh_mod._parse_iso("not-a-date") is None
    assert refresh_mod._parse_iso(None) is None
    assert refresh_mod._parse_iso(12345) is None


def test_criminal_artifact_reports_training_timestamp():
    trained_at = refresh_mod.artifact_trained_at("criminal")
    assert trained_at is not None
    assert trained_at.tzinfo is timezone.utc


def test_spec_dirs_match_inference_load_paths():
    """Regression: registry must watch exactly where inference loads from.

    Risk/anomaly inference resolve to app/models/<name> while criminal and
    hotspot live under app/ai/models/<name> — a mismatch silently breaks
    staleness detection (issue #145 follow-up).
    """
    from app.ai.inference.anomaly import DEFAULT_MODEL_PATH as ANOMALY_PATH
    from app.ai.inference.hotspot import MODEL_DIR as HOTSPOT_DIR
    from app.ai.inference.risk import MODEL_DIR as RISK_DIR

    risk_dirs = {p.parent for p in refresh_mod.SPECS["risk"].artifact_files}
    assert RISK_DIR.resolve() in {d.resolve() for d in risk_dirs}

    anomaly_dirs = {p.parent for p in refresh_mod.SPECS["anomaly"].artifact_files}
    assert ANOMALY_PATH.parent.resolve() in {d.resolve() for d in anomaly_dirs}

    hotspot_dirs = {p.parent for p in refresh_mod.SPECS["hotspot"].artifact_files}
    assert HOTSPOT_DIR.resolve() in {d.resolve() for d in hotspot_dirs}

    from app.ai.inference import criminal as criminal_inf

    criminal_dirs = {p.parent for p in refresh_mod.SPECS["criminal"].artifact_files}
    assert criminal_inf._MODEL_DIR.resolve() in {d.resolve() for d in criminal_dirs}


def test_trainer_available_respects_optional_packages(monkeypatch):
    def fake_find_spec(name):
        class _Spec:
            pass
        if name == "optuna":
            return None  # simulate missing optional dependency
        return _Spec()

    monkeypatch.setattr(refresh_mod.importlib.util, "find_spec", fake_find_spec)
    assert refresh_mod.trainer_available("hotspot") is False   # needs optuna
    assert refresh_mod.trainer_available("risk") is True       # no optional gate


def test_signature_falls_back_to_mtime(tmp_path, monkeypatch):
    spec = refresh_mod.ModelSpec(
        key="fake", label="Fake",
        artifact_files=(tmp_path / "model.json",),
        metadata_keys=("model.json",),
        trainer_module="app.ai.pipelines.criminal.train",
        invalidator_module="app.ai.inference.criminal",
        probes=(),
    )
    monkeypatch.setitem(refresh_mod.SPECS, "fake", spec)
    assert refresh_mod.artifact_signature("fake") == 0.0
    assert refresh_mod.artifact_trained_at("fake") is None  # no artifact -> no stamp

    payload = tmp_path / "model.json"
    payload.write_text('{"trained_at": "2026-01-02T03:04:05+00:00"}', encoding="utf-8")
    past = datetime.now(timezone.utc).replace(year=2020).timestamp()
    os.utime(payload, (past, past))
    stamp = refresh_mod.artifact_trained_at("fake")
    assert stamp is not None and stamp.year == 2026  # metadata wins over mtime

    stripped_dir = tmp_path / "nostamp"
    stripped_dir.mkdir()
    plain = stripped_dir / "plain.json"
    plain.write_text("{}", encoding="utf-8")
    spec2 = refresh_mod.ModelSpec(
        key="fake2", label="Fake2", artifact_files=(plain,),
        metadata_keys=("missing.json",), trainer_module="",
        invalidator_module="", probes=(),
    )
    monkeypatch.setitem(refresh_mod.SPECS, "fake2", spec2)
    fallback = refresh_mod.artifact_trained_at("fake2")
    assert fallback is not None  # mtime fallback when metadata key absent


# ---------------------------------------------------------------------------
# Database staleness probes
# ---------------------------------------------------------------------------

def _seed_case(db_session):
    category = CrimeCategory(name="Refresh Cat", section_code="IPC 1", severity="low")
    location = Location(district="Refreshpur", station="RS-1", latitude=1.0, longitude=2.0)
    db_session.add_all([category, location])
    db_session.flush()
    case = CrimeCase(
        case_number="CR-RFSH-0001", category_id=category.id, location_id=location.id,
        occurred_at=datetime(2026, 6, 1, tzinfo=timezone.utc), status="open",
    )
    db_session.add(case)
    db_session.commit()
    return case


def test_newest_data_ts_empty_then_seeded(db_session):
    assert refresh_mod.newest_data_ts(db_session, "risk") is None
    case = _seed_case(db_session)
    newest = refresh_mod.newest_data_ts(db_session, "risk")
    assert newest is not None
    assert newest.tzinfo is timezone.utc  # service normalizes naive stamps
    occurred = case.occurred_at
    if occurred.tzinfo is None:
        occurred = occurred.replace(tzinfo=timezone.utc)
    assert newest >= occurred - timedelta(seconds=1)


def test_is_stale_reasons(db_session, monkeypatch):
    monkeypatch.setattr(refresh_mod, "artifact_trained_at", lambda key: datetime.now(timezone.utc))
    stale, info = refresh_mod.is_stale(db_session, "criminal")
    assert not stale
    assert info["stale_reasons"] == []

    state = refresh_mod._states["criminal"]
    state.dirty = True
    try:
        stale, info = refresh_mod.is_stale(db_session, "criminal")
        assert stale and "crud_dirty" in info["stale_reasons"]
    finally:
        state.dirty = False


def test_monitoring_flagged_reads_drift_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh_mod, "_MONITORING_DIR", tmp_path)
    assert refresh_mod.monitoring_flagged("criminal") is False

    snapshot = tmp_path / "criminal-latest.json"
    snapshot.write_text('{"drift": [{"feature": "x", "drift_detected": true}]}', encoding="utf-8")
    assert refresh_mod.monitoring_flagged("criminal") is True

    snapshot.write_text('{"drift": [{"feature": "x", "drift_detected": false}]}', encoding="utf-8")
    assert refresh_mod.monitoring_flagged("criminal") is False


# ---------------------------------------------------------------------------
# Engine guarding + scheduling gates
# ---------------------------------------------------------------------------

def test_same_engine_guard(tmp_path):
    assert refresh_mod._same_engine(None) is True

    # A session bound to a throwaway file DB must never look like the app engine.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    foreign = sessionmaker(bind=create_engine(f"sqlite:///{(tmp_path / 'other.db').as_posix()}"))()
    try:
        assert refresh_mod._same_engine(foreign) is False
    finally:
        foreign.close()


def test_mark_data_changed_sets_dirty_without_scheduling(db_session):
    # AUTO_RETRAIN_ENABLED=false under pytest -> no threads; dirty flag sticks.
    scheduled = refresh_mod.mark_data_changed("crime_case", db=db_session)
    assert scheduled == []
    assert refresh_mod._states["hotspot"].dirty is True
    assert refresh_mod._states["risk"].dirty is True
    refresh_mod._states["hotspot"].dirty = False
    refresh_mod._states["risk"].dirty = False


# ---------------------------------------------------------------------------
# External promotion detection (gap 133.4)
# ---------------------------------------------------------------------------

def test_check_external_updates_invalidates_on_signature_change(monkeypatch):
    invalidated = []

    def fake_invalidate(key, reason):
        invalidated.append((key, reason))
        return True

    monkeypatch.setattr(refresh_mod, "_invalidate", fake_invalidate)
    refresh_mod.observe_signatures()

    updated = refresh_mod.check_external_updates()
    assert updated == []

    # Simulate an external process rewriting artifacts (mtime bump).
    import time

    target = refresh_mod.SPECS["criminal"].artifact_files[0]
    if target.exists():
        future = time.time() + 120
        os.utime(target, (future, future))
        updated = refresh_mod.check_external_updates()
        assert "criminal" in updated
        assert any(key == "criminal" for key, _reason in invalidated)
        # Second pass sees the recorded signature -> no repeat invalidation.
        assert refresh_mod.check_external_updates() == []


# ---------------------------------------------------------------------------
# Synchronous refresh path
# ---------------------------------------------------------------------------

def test_refresh_model_skips_domains_without_trainer():
    summary = refresh_mod.refresh_model(None, "anomaly", reason="test")
    assert summary["status"] == "skipped"
    assert "no DB trainer" in summary["detail"]


def test_refresh_model_runs_trainer_and_clears_dirty(monkeypatch):
    calls = {"trained": 0, "invalidated": 0}

    fake_pkg = types.ModuleType("app.fake_trainers.criminal")
    fake_pkg.run_training = lambda db_session=None: calls.__setitem__("trained", calls["trained"] + 1) or {"ok": True}
    fake_inv = types.ModuleType("app.fake_trainers.criminal_inv")
    fake_inv.invalidate_caches = lambda: calls.__setitem__("invalidated", calls["invalidated"] + 1)

    monkeypatch.setitem(sys.modules, "app.fake_trainers.criminal", fake_pkg)
    monkeypatch.setitem(sys.modules, "app.fake_trainers.criminal_inv", fake_inv)

    spec = refresh_mod.ModelSpec(
        key="fake3", label="Fake3", artifact_files=(),
        metadata_keys=(),
        trainer_module="app.fake_trainers.criminal",
        invalidator_module="app.fake_trainers.criminal_inv",
        probes=(),
    )
    monkeypatch.setitem(refresh_mod.SPECS, "fake3", spec)

    refresh_mod._states["fake3"] = refresh_mod.ModelState(dirty=True)
    try:
        summary = refresh_mod.refresh_model(None, "fake3", reason="unit")
        assert summary["status"] == "ok"
        assert calls == {"trained": 1, "invalidated": 1}
        state = refresh_mod._states["fake3"]
        assert state.dirty is False
        assert state.last_error is None
        assert state.last_refreshed_at is not None
    finally:
        refresh_mod._states.pop("fake3", None)


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------

def _override_user(client, db_session, role_name, username):
    from app.auth.dependencies import get_current_user
    from app.core.security import hash_password
    from app.models.role import Role
    from app.models.user import User

    role = db_session.query(Role).filter_by(name=role_name).first()
    if role is None:
        role = Role(name=role_name, description=role_name)
        db_session.add(role)
        db_session.flush()
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username.title(),
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    return user


def test_refresh_status_endpoint(client, db_session):
    _override_user(client, db_session, "crime_analyst", "refresh-analyst")
    resp = client.get("/api/v2/ai/predictions/refresh-status")
    client.app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body["models"].keys()) == {"criminal", "risk", "hotspot", "anomaly"}
    for model in body["models"].values():
        assert {"stale", "trainer_available", "artifact_present", "stale_reasons"} <= set(model)


def test_train_route_retrains_and_invalidates(client, db_session, monkeypatch):
    _override_user(client, db_session, "admin", "refresh-admin")

    import app.ai.pipelines.risk.train as risk_train_mod

    invalidated = []
    monkeypatch.setattr(risk_train_mod, "run_training", lambda: {"risk": {"r2": 0.9}, "forecast": {"mae": 0.1}})
    monkeypatch.setattr(
        "app.routes.ai_risk.invalidate_caches",
        lambda: invalidated.append("risk"),
    )

    resp = client.post("/api/v2/ai/predictions/train")
    client.app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    assert body["retrained_by"] == "refresh-admin"
    assert body["metrics"]["risk"]["r2"] == 0.9
    assert invalidated == ["risk"]


def test_documented_alias_path_ai_risk_train(client, db_session, monkeypatch):
    """CONTEXT.md documents POST /api/v2/ai/risk/train — it must exist (gap 133.3)."""
    _override_user(client, db_session, "admin", "alias-admin")

    import app.ai.pipelines.risk.train as risk_train_mod

    monkeypatch.setattr(risk_train_mod, "run_training", lambda: {"risk": {"r2": 0.8}, "forecast": {"mae": 0.2}})
    monkeypatch.setattr("app.routes.ai_risk.invalidate_caches", lambda: None)

    resp = client.post("/api/v2/ai/risk/train")
    client.app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Post-retrain notification (gap 133.2: CRUD -> notification loop)
# ---------------------------------------------------------------------------

def test_retrain_success_creates_broadcast_notification(db_session):
    from sqlalchemy import func

    from app.models.notification import Notification

    before = (
        db_session.query(func.count(Notification.id))
        .filter(Notification.notification_type == "model_retrained")
        .scalar()
    )
    refresh_mod._notify_retrain_success(
        db_session, "criminal", {"status": "ok", "reason": "crud:fir"}
    )
    row = (
        db_session.query(Notification)
        .filter(Notification.notification_type == "model_retrained")
        .order_by(Notification.created_at.desc())
        .first()
    )
    after = (
        db_session.query(func.count(Notification.id))
        .filter(Notification.notification_type == "model_retrained")
        .scalar()
    )
    assert after == before + 1
    assert row is not None
    assert row.is_broadcast is True
    assert row.resource_id == "criminal"
    assert row.status == "unread"
    assert "retrained" in row.title.lower()


def test_monitoring_flagged_defers_to_needs_retraining(tmp_path, monkeypatch):
    """133.5 fidelity: verdict comes from ModelMonitor.needs_retraining()."""
    monkeypatch.setattr(refresh_mod, "_MONITORING_DIR", tmp_path)
    snapshot = tmp_path / "risk-latest.json"
    snapshot.write_text(
        '{"drift": [{"feature_name": "crime_volume", "baseline_mean": 10.0,'
        ' "current_mean": 15.0, "absolute_shift": 5.0, "drift_detected": true}]}',
        encoding="utf-8",
    )
    assert refresh_mod.monitoring_flagged("risk") is True

    # Malformed payload -> safe False, never raises.
    snapshot.write_text("{not json", encoding="utf-8")
    assert refresh_mod.monitoring_flagged("risk") is False
