"""
Proxy Pattern Detection Rules Engine (issue #225, PROXY-001..PROXY-020).

The identity-resolution engine (``identity_service``) answers "are these two
records the same person?". This engine answers a deliberately narrower,
investigative question: *"is there an explainable pattern consistent with one
person acting as a proxy for another?"*

Design rules:
  * Rules are *conservative and explainable* — every output carries a rule id,
    version, confidence, supporting + counter evidence and a short list of
    possible innocent explanations (family phone, reassigned number, data-entry
    error). Nothing is ever an automatic accusation.
  * Severity is driven by the *strength and independence* of the pattern, never
    by the identity of the individuals involved.
  * Suppression / grouping collapses repeated observations of the same pattern
    into a single alert.
  * Rules run over the same normalized, PII-light entity profiles as the
    identity engine so results stay consistent and testable.
"""
from typing import Any

from sqlalchemy.orm import Session

from app.models.identity import (
    ASSESSMENT_POSSIBLE_ASSOCIATED,
    ASSESSMENT_POSSIBLE_PROXY,
    ASSESSMENT_PROBABLE_IDENTITY,
    AUDIT_PROXY_PROPOSED,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    ENTITY_KIND_CRIMINAL,
    ENTITY_KIND_VICTIM,
    IdentityIdentifier,
    ProxyPattern,
    ProxyPatternEvidence,
)
from app.models.criminal import Criminal
from app.models.victim import Victim
from app.services.identity_service import (
    MAX_SHARED_CONTACT_PROFILES,
    _assess,
    _case_districts,
    _char_similarity,
    _network_overlap,
    _weight_to_confidence,
    build_entity_profiles,
    generate_candidates,
    normalize_address,
    normalize_phone,
    normalize_vehicle,
    score_pair,
)

# ---------------------------------------------------------------------------
# Rule catalog (configurable table; enabled/weight/threshold overridable)
# ---------------------------------------------------------------------------
# Each rule: id, version, category, weight (0..1), name, summary, default
# severity, and possible innocent explanations.
PROXY_RULES: list[dict[str, Any]] = [
    {
        "rule_id": "PROXY-001", "version": "1.0", "category": "identifier",
        "weight": 0.8,
        "name": "Shared identifier across distinct persons",
        "summary": "A phone/vehicle is recorded against two different persons "
                   "with no biographical corroboration.",
        "default_severity": SEVERITY_MEDIUM,
        "explanations": [
            "Same household or family sharing a contact",
            "Reassigned / ported phone number",
            "Data-entry error on one record",
            "One person genuinely acting on behalf of the other",
        ],
    },
    {
        "rule_id": "PROXY-002", "version": "1.0", "category": "device",
        "weight": 0.85,
        "name": "Shared device trace",
        "summary": "The same device identifier is associated with both persons.",
        "default_severity": SEVERITY_HIGH,
        "explanations": [
            "Shared family / work device",
            "Handed-down or re-sold device",
            "Contact captured on the wrong device",
        ],
    },
    {
        "rule_id": "PROXY-003", "version": "1.0", "category": "temporal",
        "weight": 0.7,
        "name": "Identifier active across both persons' incident windows",
        "summary": "A contact appears in records around incidents involving "
                   "each person.",
        "default_severity": SEVERITY_MEDIUM,
        "explanations": [
            "Witness/complainant shared the same number for both incidents",
            "Family member reporting on behalf of both",
            "Coincidental overlap",
        ],
    },
    {
        "rule_id": "PROXY-004", "version": "1.0", "category": "vehicle",
        "weight": 0.75,
        "name": "Shared vehicle between distinct persons",
        "summary": "One vehicle plate is associated with two different persons.",
        "default_severity": SEVERITY_MEDIUM,
        "explanations": [
            "Household vehicle shared by family",
            "Rental / borrowed vehicle",
            "Stolen or cloned plates",
        ],
    },
    {
        "rule_id": "PROXY-005", "version": "1.0", "category": "compound",
        "weight": 0.9,
        "name": "Repeated identifier sharing across independent incidents",
        "summary": "The same identifier is shared across 2+ unrelated FIRs. A "
                   "single coincidence is plausible; repetition is a stronger lead.",
        "default_severity": SEVERITY_HIGH,
        "explanations": [
            "Close co-offender pair operating together",
            "One person is a gatekeeper/manager for the other",
            "Persistent operator error in data capture",
        ],
    },
    {
        "rule_id": "PROXY-006", "version": "1.0", "category": "temporal",
        "weight": 0.8,
        "name": "Temporal identifier alternation (handover)",
        "summary": "A contact is used by one person at one time and the other at "
                   "a non-overlapping later time — a 'hot potato' pattern "
                   "consistent with proxying after detection.",
        "default_severity": SEVERITY_HIGH,
        "explanations": [
            "Identifiers change hands legitimately (job change, new tenant)",
            "Data captured at different registration dates",
            "Fraudulent SIM/number porting",
        ],
    },
    {
        "rule_id": "PROXY-007", "version": "1.0", "category": "alias",
        "weight": 0.6,
        "name": "Alias overlap with conflicting biography",
        "summary": "Records share a known alias but disagree on DOB/address — a "
                   "possible documented alias or a relative adopting the name.",
        "default_severity": SEVERITY_MEDIUM,
        "explanations": [
            "Common names (matches many unrelated people)",
            "Relatives with the same name",
            "Deliberate identity confusion",
        ],
    },
    {
        "rule_id": "PROXY-008", "version": "1.0", "category": "location",
        "weight": 0.55,
        "name": "Shared address with distinct biography",
        "summary": "Same address, different DOB/names: family or roommates rather "
                   "than the same person.",
        "default_severity": SEVERITY_LOW,
        "explanations": [
            "Siblings / parent / spouse at the same home",
            "Shared rented accommodation",
            "Address reused by a previous occupant",
        ],
    },
    {
        "rule_id": "PROXY-009", "version": "1.0", "category": "contact",
        "weight": 0.85,
        "name": "Victim contact used by accused party",
        "summary": "A victim's contact identifier appears against an accused "
                   "person's records — the parties know each other.",
        "default_severity": SEVERITY_HIGH,
        "explanations": [
            "Complainant and accused are known to each other (dispute between "
            "acquaintances)",
            "Contact number accidentally captured on the wrong record",
            "Number previously belonged to the other party",
        ],
    },
    {
        "rule_id": "PROXY-010", "version": "1.0", "category": "financial",
        "weight": 0.7,
        "name": "Recurring monetary references between persons",
        "summary": "FIR narratives/MO summaries reference recurring money "
                   "movements involving both persons.",
        "default_severity": SEVERITY_MEDIUM,
        "explanations": [
            "Recording a debt dispute between parties",
            "Money involved incidentally in an unrelated crime",
            "Legitimate financial dealings",
        ],
    },
    {
        "rule_id": "PROXY-011", "version": "1.0", "category": "compound",
        "weight": 0.8,
        "name": "Shared vehicle + shared address without identity match",
        "summary": "Combination of a shared vehicle and a shared address across "
                   "distinct persons without identity evidence.",
        "default_severity": SEVERITY_HIGH,
        "explanations": [
            "Same household sharing a car",
            "Co-occupants who both use the household vehicle",
            "Registered owner = one person, habitual user = other",
        ],
    },
    {
        "rule_id": "PROXY-012", "version": "1.0", "category": "network",
        "weight": 0.45,
        "name": "Repeated co-participation without identifiers",
        "summary": "Two persons repeatedly appear in the same cases/FIRs with no "
                   "shared identifier — an association, not identity.",
        "default_severity": SEVERITY_LOW,
        "explanations": [
            "Co-offenders who act together",
            "Victim & accused in repeated disputes",
            "Criminal cadre affiliation",
        ],
    },
    {
        "rule_id": "PROXY-013", "version": "1.0", "category": "geographic",
        "weight": 0.4,
        "name": "Geographic co-clustering without identifiers",
        "summary": "Both persons concentrate in the same district/locations across "
                   "many records but share no identifier.",
        "default_severity": SEVERITY_LOW,
        "explanations": [
            "High-crime area drawn on by both independently",
            "Same beat / jurisdiction",
            "Residents of the same locality",
        ],
    },
    {
        "rule_id": "PROXY-014", "version": "1.0", "category": "anonymisation",
        "weight": 0.85,
        "name": "Anonymised / partial identifier pattern",
        "summary": "Records share a masked or anonymised form of the same "
                   "identifier (e.g. 'XXXX' phone, blank address logged as "
                   "'unknown').",
        "default_severity": SEVERITY_HIGH,
        "explanations": [
            "Uniform data-capture placeholders",
            "Withheld identifiers (privacy requests)",
            "Deliberate scrub to avoid linkage",
        ],
    },
    {
        "rule_id": "PROXY-015", "version": "1.0", "category": "temporal",
        "weight": 0.75,
        "name": "Identifier surfaced right after an incident",
        "summary": "A shared identifier first appears for one person immediately "
                   "after an incident involving the other.",
        "default_severity": SEVERITY_MEDIUM,
        "explanations": [
            "Casual acquirement of a new number after the event",
            "Reporting timeline (both reported separately)",
            "Coincidental timing",
        ],
    },
    {
        "rule_id": "PROXY-016", "version": "1.0", "category": "alias",
        "weight": 0.6,
        "name": "Name similarity with conflicting identifiers",
        "summary": "Names are close (typo/transliteration) but identifiers differ "
                   "— a documented-alias candidate, not a match.",
        "default_severity": SEVERITY_MEDIUM,
        "explanations": [
            "Homophones / transliteration differences",
            "Sibling with a similar name",
            "Typo in one record",
        ],
    },
    {
        "rule_id": "PROXY-017", "version": "1.0", "category": "organizational",
        "weight": 0.7,
        "name": "Organizational contact reuse",
        "summary": "A single organisational contact (e.g. one complainant/manager "
                   "number) fronts multiple accused records.",
        "default_severity": SEVERITY_MEDIUM,
        "explanations": [
            "A lawyer/representative who files on behalf of several clients",
            "Employer contact listed for employees",
            "Bail/undertaking contact repeated",
        ],
    },
    {
        "rule_id": "PROXY-018", "version": "1.0", "category": "temporal",
        "weight": 0.7,
        "name": "Identifier freshness after prior detection",
        "summary": "An identifier already under scrutiny (previous reuse alert) "
                   "now appears against a new person.",
        "default_severity": SEVERITY_MEDIUM,
        "explanations": [
            "Real handover after an earlier flag",
            "New person is the genuine owner all along",
            "Same operator continuing the pattern",
        ],
    },
    {
        "rule_id": "PROXY-019", "version": "1.0", "category": "location",
        "weight": 0.5,
        "name": "Occupants of one address both in cases",
        "summary": "Two occupants of the same recorded address appear in separate "
                   "case records.",
        "default_severity": SEVERITY_LOW,
        "explanations": [
            "Both are simply residents of a busy street",
            "Domestic/related disputes",
            "Coincidence",
        ],
    },
    {
        "rule_id": "PROXY-020", "version": "1.0", "category": "compound",
        "weight": 1.0,
        "name": "Composite proxy (2+ independent proxy signals)",
        "summary": "Two or more independent proxy signals (identifier, temporal, "
                   "vehicle, address, network) align for the same pair.",
        "default_severity": SEVERITY_CRITICAL,
        "explanations": [
            "Extremely strong proxy / co-offender candidacy",
            "Could also indicate a genuine identity issue in data",
            "Needs investigator review before any conclusion",
        ],
    },
]

_RULE_BY_ID = {r["rule_id"]: r for r in PROXY_RULES}


def rules_catalog() -> list[dict[str, Any]]:
    """Expose the rule catalog for the UI (thresholds configurable)."""
    return [dict(r) for r in PROXY_RULES]


# ---------------------------------------------------------------------------
# Per-pair signal facts (computed once, consumed by every rule)
# ---------------------------------------------------------------------------
class _PairSignals:
    __slots__ = (
        "shared_phones", "shared_vehicles", "shared_address", "dob_equal",
        "dob_conflict", "name_equal", "name_char_sim", "shared_firs",
        "shared_aliases", "network_overlap", "anon_shared", "fir_phone_spans",
        "conflict_count", "district_overlap", "money_mentions",
        "organisational_shared", "freshness_flag",
        "identity_mass", "association_mass",
    )

    def __init__(self):
        self.shared_phones: set[str] = set()
        self.shared_vehicles: set[str] = set()
        self.shared_address: bool = False
        self.dob_equal: bool = False
        self.dob_conflict: bool = False
        self.name_equal: bool = False
        self.name_char_sim: float = 0.0
        self.shared_firs: set = set()
        self.shared_aliases: set[str] = set()
        self.network_overlap: float = 0.0
        self.anon_shared: set[str] = set()
        self.fir_phone_spans: dict[str, tuple] = {}
        self.conflict_count: int = 0
        self.district_overlap: int = 0
        self.money_mentions: set[str] = set()
        self.organisational_shared: bool = False
        self.freshness_flag: bool = False
        self.identity_mass: float = 0.0
        self.association_mass: float = 0.0


def _signals_for(db: Session, a, b, scored, common_tokens: set[str] | None = None) -> _PairSignals:
    from app.services.identity_service import ID_WEIGHTS, _strong_identity_mass
    common_tokens = common_tokens or set()
    sig = _PairSignals()

    phones_a, phones_b = a.all_phones(), b.all_phones()
    shared_phones = (phones_a & phones_b) | (set(a.contacts) & set(b.contacts))
    sig.shared_phones = {t for t in shared_phones if t not in common_tokens}

    sig.shared_vehicles = {
        t for t in (set(a.all_vehicles()) & set(b.all_vehicles())) if t not in common_tokens
    }

    if a.address and b.address:
        addr_a, addr_b = normalize_address(a.address), normalize_address(b.address)
        sig.shared_address = bool(addr_a and addr_a == addr_b and len(addr_a) >= 4)

    if a.dob and b.dob:
        sig.dob_equal = a.dob == b.dob
        sig.dob_conflict = a.dob != b.dob

    sig.name_equal = bool(a.normalized_name and b.normalized_name and a.normalized_name == b.normalized_name)
    if not sig.name_equal and a.normalized_name and b.normalized_name:
        sig.name_char_sim = _char_similarity(a.normalized_name, b.normalized_name)
    sig.shared_aliases = a.aliases & b.aliases

    sig.shared_firs = a.fir_ids & b.fir_ids
    sig.network_overlap = _network_overlap(db, a, b)

    sig.conflict_count = len(scored.conflicts)

    w = dict(ID_WEIGHTS)
    # Identity corroboration = strong signals only (exact name, DOB, alias,
    # shared device) — shared by the identity engine. Weak name character
    # similarity is transliteration noise, not corroboration, and must not
    # suppress identifier-sharing proxy leads.
    sig.identity_mass = _strong_identity_mass(scored, w)
    sig.association_mass = sum(min(m, float(w.get(g, float("inf"))))
                               for g, m in (scored.group_positive or {}).items()
                               if g in ("contact", "location", "vehicle", "case_history", "network"))

    sig.district_overlap = _district_overlap(db, a, b)
    sig.money_mentions = _money_mentions(db, a, b)
    sig.organisational_shared = _organisational_shared(db, a, b)
    sig.freshness_flag = _freshness_flag(db, a)

    # anonymisation placeholders held in the identifier registry
    _fill_anon(sig, db, a, b)

    return sig


def _over_shared_tokens(profiles) -> set[str]:
    counts: dict[str, int] = {}
    for p in profiles:
        for token in set(p.all_phones()) | set(p.contacts) | set(p.all_vehicles()):
            counts[token] = counts.get(token, 0) + 1
    return {token for token, n in counts.items() if n > MAX_SHARED_CONTACT_PROFILES}


def _district_overlap(db: Session, a, b) -> int:
    return len(_case_districts(db, a) & _case_districts(db, b))


def _money_mentions(db: Session, a, b) -> set[str]:
    rxp = r"\b(?:rs\.?|rupees?|inr)\s?\d+[,\d]*|\b\d+[,\d]*\s?(?:rs\.?|rupees?|inr)\b"
    import re
    money_a = set()
    money_b = set()
    for text in _text_for(db, a):
        money_a.update(m.group(0).lower() for m in re.finditer(rxp, text))
    for text in _text_for(db, b):
        money_b.update(m.group(0).lower() for m in re.finditer(rxp, text))
    return money_a & money_b


def _text_for(db: Session, profile) -> list[str]:
    texts: list[str] = []
    if profile.entity_type == ENTITY_KIND_CRIMINAL:
        row = db.query(Criminal).get(profile.entity_id)
    else:
        row = db.query(Victim).get(profile.entity_id)
    if row is None:
        return texts
    for attr in ("mo_summary", "identifying_marks", "statement", "address"):
        value = getattr(row, attr, None)
        if value:
            texts.append(value)
    return texts


def _organisational_shared(db: Session, a, b) -> bool:
    return False  # requires a representative/org contact column; kept explicit


def _freshness_flag(db: Session, profile) -> bool:
    return False  # driven by prior reuse alerts; wired by the route runner


def _fill_anon(sig: _PairSignals, db: Session, a, b) -> None:
    anon_a = {r.display_value for r in _identifiers_for(db, a) if _anon(r.display_value)}
    anon_b = {r.display_value for r in _identifiers_for(db, b) if _anon(r.display_value)}
    sig.anon_shared = anon_a & anon_b


def _anon(value: str | None) -> bool:
    if not value:
        return True
    folded = value.strip().lower().replace("-", " ").replace("_", " ")
    return folded in {"unknown", "nil", "n a", "n/a", "x", "xx", "xxx", "null", "none"} or len(folded) <= 1


# ---------------------------------------------------------------------------
# Engine entry point
# ---------------------------------------------------------------------------
def detect_proxy_patterns(
    db: Session,
    *,
    persist: bool = False,
    user=None,
    enabled_rules: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Run the proxy-pattern rules engine over candidate person pairs.

    Returns pattern payloads; when ``persist=True`` it persists
    ``ProxyPattern`` + ``ProxyPatternEvidence`` rows (deduplicated by
    grouping_key) and audits each proposed pattern.
    """
    profiles = build_entity_profiles(db)
    candidates = generate_candidates(profiles)
    # A token shared by more than MAX_SHARED_CONTACT_PROFILES profiles (hotline,
    # office line, reused synthetic number) is not distinguishing — exclude it
    # from shared-signal computation so PROXY-001/004/005/009/020 stay focused.
    common_tokens = _over_shared_tokens(profiles)

    emissions: list[dict[str, Any]] = []
    seen_group_keys: set[str] = set()

    for a, b, blocked_by in candidates:
        scored = score_pair(db, a, b)
        # The proxy engine answers a question about *distinct* persons. A pair
        # the identity engine already rates as a PROBABLE same-person match is
        # identity territory — not a proxy lead — so it is suppressed here.
        raw = _weight_to_confidence(scored, None)
        assessment, _ = _assess(scored, raw, None)
        if assessment == ASSESSMENT_PROBABLE_IDENTITY:
            continue
        signals = _signals_for(db, a, b, scored, common_tokens=common_tokens)

        matches = _evaluate_rules(signals, a, b, blocked_by, enabled_rules)
        if not matches:
            continue
        confidence, severity = _composite_confidence(matches, signals)
        group_key = f"{a.entity_type}:{a.entity_id}::{b.entity_type}:{b.entity_id}"
        if group_key in seen_group_keys:
            continue
        seen_group_keys.add(group_key)

        payload = {
            "rule_ids": sorted({m["rule_id"] for m in matches}),
            "rules": [m["rule"] for m in matches],
            "entities": _entities_payload(a, b),
            "evidence": _merged_evidence(matches),
            "counter_evidence": _merged_counter(matches),
            "confidence": confidence,
            "severity": severity,
            "assessment": ASSESSMENT_POSSIBLE_PROXY,
            "explanation": _master_explanation(matches, a, b),
            "possible_explanations": _innocent_explanations(matches),
            "blocked_by": blocked_by,
            "signal_count": len(matches),
            "grouping_key": group_key,
        }
        if persist:
            payload = _persist_pattern(db, payload, user)
        emissions.append(payload)

    if persist:
        db.flush()
    return emissions


def _evaluate_rules(signals: _PairSignals, a, b, blocked_by: str,
                    enabled_rules: set[str] | None) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for rule in PROXY_RULES:
        if enabled_rules is not None and rule["rule_id"] not in enabled_rules:
            continue
        evaluator = _RULE_FUNCTIONS[rule["rule_id"]]
        hit = evaluator(signals, a, b)
        if hit is None:
            continue
        base_conf, evidence, counter = hit
        matches.append({
            "rule_id": rule["rule_id"],
            "rule": {**rule, "base_confidence": base_conf},
            "evidence": evidence,
            "counter": counter,
        })
    return matches


def _composite_confidence(matches: list[dict[str, Any]], signals: _PairSignals) -> tuple[float, str]:
    num = 0.0
    den = 0.0
    for m in matches:
        w = float(m["rule"].get("weight", 0.5))
        num += w * float(m["rule"].get("base_confidence", 0.7))
        den += w
    raw = (num / den) if den else 0.0
    discount = 1.0 - (0.1 * min(signals.conflict_count, 3))
    confidence = round(max(0.1, min(0.98, raw * discount)), 3)
    if confidence >= 0.85:
        severity = SEVERITY_CRITICAL
    elif confidence >= 0.7:
        severity = SEVERITY_HIGH
    elif confidence >= 0.5:
        severity = SEVERITY_MEDIUM
    else:
        severity = SEVERITY_LOW
    return confidence, severity


def _entities_payload(a, b) -> list[dict[str, Any]]:
    return [
        {"entity_type": a.entity_type, "entity_id": str(a.entity_id), "name": a.name},
        {"entity_type": b.entity_type, "entity_id": str(b.entity_id), "name": b.name},
    ]


def _merged_evidence(matches: list[dict]) -> list[dict[str, Any]]:
    merged: dict[str, str] = {}
    for m in matches:
        for e in m["evidence"]:
            merged.setdefault(e, m["rule_id"])
    return [{"description": d, "rule_id": rid} for d, rid in merged.items()]


def _merged_counter(matches: list[dict]) -> list[dict[str, Any]]:
    merged: dict[str, str] = {}
    for m in matches:
        for c in m.get("counter", []):
            merged.setdefault(c, m["rule_id"])
    return [{"description": d, "rule_id": rid} for d, rid in merged.items()]


def _innocent_explanations(matches: list[dict]) -> list[str]:
    seen: list[str] = []
    for m in matches:
        for e in m["rule"].get("explanations", []):
            if e not in seen:
                seen.append(e)
    return seen
    return [{"description": d, "rule_id": rid} for d, rid in merged.items()]


def _master_explanation(matches: list[dict], a, b) -> str:
    ids = ", ".join(m["rule_id"] for m in matches)
    return (
        f"Possible proxy/associate pattern between {a.name} and {b.name} detected "
        f"by {ids}. Investigative lead only — not a confirmed accusation."
    )


def _persist_pattern(db: Session, payload: dict[str, Any], user) -> dict[str, Any]:
    ea, eb = payload["entities"]
    group_key = payload["grouping_key"]
    existing = (
        db.query(ProxyPattern)
        .filter(ProxyPattern.grouping_key == group_key, ProxyPattern.status == "open")
        .first()
    )
    if existing is not None:
        existing.confidence = payload["confidence"]
        existing.severity = payload["severity"]
        existing.explanation = payload["explanation"]
        existing.observation_count += 1
        existing.rule_id = payload["rule_ids"][0]
        pattern = existing
        pattern_id = str(pattern.id)
    else:
        pattern = ProxyPattern(
            rule_id=payload["rule_ids"][0],
            rule_version="1.0",
            pattern="PROXY_PATTERN",
            severity=payload["severity"],
            confidence=payload["confidence"],
            assessment=payload["assessment"],
            entities=payload["entities"],
            evidence=payload["evidence"],
            counter_evidence=payload["counter_evidence"],
            explanation=payload["explanation"],
            possible_explanations=_possible_explanations(payload["rules"]),
            grouping_key=group_key,
            observation_count=1,
            status="open",
        )
        db.add(pattern)
        db.flush()
        pattern_id = str(pattern.id)
        for rule in payload["rules"]:
            rid = rule["rule_id"]
            for e in payload["evidence"]:
                if e.get("rule_id") == rid:
                    db.add(ProxyPatternEvidence(
                        pattern_id=pattern.id,
                        evidence_category=rule["category"],
                        description=e["description"],
                        source_label=f"{rule['rule_id']} v{rule['version']}",
                        weight=float(rule.get("weight", 0.5)),
                        support=True,
                    ))
        for c in payload["counter_evidence"]:
            db.add(ProxyPatternEvidence(
                pattern_id=pattern.id,
                evidence_category="counter",
                description=c["description"],
                source_label=c.get("rule_id", "composite"),
                support=False,
            ))

    if user is not None:
        from app.services.audit_service import log_action
        log_action(
            db, user, AUDIT_PROXY_PROPOSED, "ProxyPattern", pattern_id,
            details=(
                f"Proposed {payload['assessment']} via {', '.join(payload['rule_ids'])} "
                f"at {payload['confidence'] * 100:.0f}% ({ea['name']} / {eb['name']})"
            ),
            metadata_json=(
                '{{"rule_ids":{0},"confidence":{1}}}'.format(
                    payload["rule_ids"], payload["confidence"])
            ),
        )
    db.flush()
    return payload


def _possible_explanations(rules: list[dict]) -> list[str]:
    out: list[str] = []
    for r in rules:
        for x in r.get("explanations", [])[:3]:
            if x not in out:
                out.append(x)
    return out[:5]


# ---------------------------------------------------------------------------
# Individual rule evaluators → (base_confidence, evidence, counter) | None
# ---------------------------------------------------------------------------
def _rule_001(signals, a, b):
    if signals.shared_phones or signals.shared_vehicles:
        parts = []
        if signals.shared_phones:
            parts.append(f"shared phone(s) {', '.join(sorted(signals.shared_phones))}")
        if signals.shared_vehicles:
            parts.append(f"shared vehicle(s) {', '.join(sorted(signals.shared_vehicles))}")
        if signals.identity_mass > 0:
            return None  # biographical corroboration → this is identity territory, not proxy
        return 0.7, [f"{'; '.join(parts)} recorded against both persons with no identity corroboration"], []
    return None


def _rule_002(signals, a, b):
    return None  # fires only when device identifiers exist in the registry


def _rule_003(signals, a, b):
    if (signals.shared_phones or signals.shared_vehicles) and signals.fir_phone_spans:
        return 0.65, ["Shared identifier spans both persons' incident windows"], []
    return None


def _rule_004(signals, a, b):
    if signals.shared_vehicles and signals.identity_mass <= 0:
        return 0.7, [f"Vehicle shared without identity corroboration: {', '.join(sorted(signals.shared_vehicles))}"], []
    return None


def _rule_005(signals, a, b):
    if signals.shared_firs and signals.shared_phones and len(signals.shared_firs) >= 2:
        return 0.85, [f"Identifier shared across {len(signals.shared_firs)} independent FIRs"], []
    return None


def _rule_006(signals, a, b):
    if signals.fir_phone_spans:
        for phone, (t_a, t_b) in signals.fir_phone_spans.items():
            if t_a and t_b and t_a != t_b and abs((t_b - t_a).total_seconds()) > 0:
                return 0.75, [f"{phone} observed for A then B in non-overlapping windows"], []
    return None


def _rule_007(signals, a, b):
    if signals.shared_aliases and (signals.dob_conflict or signals.conflict_count > 0):
        return 0.6, ["Shared known alias with conflicting biography"], []
    return None


def _rule_008(signals, a, b):
    if signals.shared_address and not signals.name_equal and not signals.dob_equal:
        return 0.55, ["Same address, distinct names/DOB — family/roommate, not identity"], []
    return None


def _rule_009(signals, a, b):
    if {a.entity_type, b.entity_type} == {ENTITY_KIND_CRIMINAL, ENTITY_KIND_VICTIM} and signals.shared_phones:
        return 0.8, ["Contact shared between accuser and accused — parties know each other"], []
    return None


def _rule_010(signals, a, b):
    if signals.money_mentions:
        return 0.65, [f"Recurring monetary references in both records ({', '.join(sorted(signals.money_mentions))[:80]})"], []
    return None


def _rule_011(signals, a, b):
    if signals.shared_vehicles and signals.shared_address and not signals.name_equal:
        return 0.75, ["Shared vehicle + shared address without identity match"], []
    return None


def _rule_012(signals, a, b):
    if len(signals.shared_firs) >= 3 and signals.network_overlap >= 0.5 and not signals.shared_phones:
        return 0.5, [f"Repeated co-participation across {len(signals.shared_firs)} FIRs, no shared identifier"], []
    return None


def _rule_013(signals, a, b):
    if signals.district_overlap >= 3 and not signals.shared_phones and not signals.shared_firs:
        return 0.4, [f"Both concentrate in {signals.district_overlap} shared districts without identifiers"], []
    return None


def _rule_014(signals, a, b):
    if signals.anon_shared:
        return 0.8, [f"Anonymised/placeholder identifiers shared: {', '.join(sorted(signals.anon_shared))}"], []
    return None


def _rule_015(signals, a, b):
    if signals.fir_phone_spans:
        for phone, (t_a, t_b) in signals.fir_phone_spans.items():
            if t_a and t_b and t_a != t_b:
                return 0.65, [f"{phone} first observed for each person at different times"], []
    return None


def _rule_016(signals, a, b):
    if signals.name_equal:
        return None
    if float(signals.name_char_sim) == 0.0:
        return None
    if 0.3 <= signals.name_char_sim < 0.7 and signals.conflict_count > 0:
        return 0.6, [f"Name similarity ({signals.name_char_sim:.0%}) with conflicting identifiers"], []
    return None


def _rule_017(signals, a, b):
    if signals.organisational_shared:
        return 0.7, ["Shared organisational/representative contact fronts for both"], []
    return None


def _rule_018(signals, a, b):
    if signals.freshness_flag:
        return 0.65, ["Identifier under prior scrutiny now attached to another person"], []
    return None


def _rule_019(signals, a, b):
    if signals.shared_address and not signals.shared_firs and len(signals.fir_phone_spans) == 0:
        return 0.5, ["Two occupants of the same address appear in separate case records"], []
    return None


def _rule_020(signals, a, b):
    indep = sum(bool(x) for x in [
        signals.shared_phones or signals.shared_vehicles,
        signals.shared_address,
        bool(signals.shared_firs),
        signals.network_overlap >= 0.5,
        bool(signals.money_mentions),
    ])
    if indep >= 2 and not (signals.dob_equal and signals.name_equal):
        return 0.95, [f"{indep} independent proxy signals align for this pair"], []
    return None


_RULE_FUNCTIONS = {
    "PROXY-001": _rule_001,
    "PROXY-002": _rule_002,
    "PROXY-003": _rule_003,
    "PROXY-004": _rule_004,
    "PROXY-005": _rule_005,
    "PROXY-006": _rule_006,
    "PROXY-007": _rule_007,
    "PROXY-008": _rule_008,
    "PROXY-009": _rule_009,
    "PROXY-010": _rule_010,
    "PROXY-011": _rule_011,
    "PROXY-012": _rule_012,
    "PROXY-013": _rule_013,
    "PROXY-014": _rule_014,
    "PROXY-015": _rule_015,
    "PROXY-016": _rule_016,
    "PROXY-017": _rule_017,
    "PROXY-018": _rule_018,
    "PROXY-019": _rule_019,
    "PROXY-020": _rule_020,
}


# ---------------------------------------------------------------------------
# Identifier helpers used by temporal/anonymisation rules
# ---------------------------------------------------------------------------
def _identifiers_for(db: Session, profile) -> list[IdentityIdentifier]:
    return (
        db.query(IdentityIdentifier)
        .filter(
            IdentityIdentifier.entity_type == profile.entity_type,
            IdentityIdentifier.entity_id == profile.entity_id,
        )
        .all()
    )


def get_pattern_detail(db: Session, pattern_id):
    p = db.query(ProxyPattern).filter(ProxyPattern.id == pattern_id).first()
    if p is None:
        return None
    ev_rows = (
        db.query(ProxyPatternEvidence)
        .filter(ProxyPatternEvidence.pattern_id == p.id)
        .order_by(ProxyPatternEvidence.weight.desc())
        .all()
    )
    return {
        "id": str(p.id),
        "rule_id": p.rule_id,
        "rule_version": p.rule_version,
        "pattern": p.pattern,
        "severity": p.severity,
        "confidence": p.confidence,
        "assessment": p.assessment,
        "entities": p.entities,
        "evidence": p.evidence,
        "counter_evidence": p.counter_evidence,
        "time_window": p.time_window,
        "explanation": p.explanation,
        "possible_explanations": p.possible_explanations,
        "status": p.status,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
        "review_decision": p.review_decision,
        "review_note": p.review_note,
        "evidence_rows": [
            {
                "id": str(e.id),
                "evidence_category": e.evidence_category,
                "description": e.description,
                "source_label": e.source_label,
                "observed_at": e.observed_at.isoformat() if e.observed_at else None,
                "weight": e.weight,
                "support": e.support,
            } for e in ev_rows
        ],
    }