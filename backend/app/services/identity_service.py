"""
Identity Resolution / Proxy Relationship Engine (issue #225).

Core responsibilities:
  * Normalize + hash identifiers (names, phones, addresses, vehicles, emails).
  * Candidate generation via blocking (never O(N^2) full comparison).
  * Explainable, weighted, cost-sensitive confidence scoring across inert
    evidence groups (biographical / contact / location / device / vehicle /
    case-history / network).
  * Counter-evidence support (conflicting DOB / address reduce confidence).
  * Alias evolution, temporal identifier reuse, and identity-conflict detection.
  * Data-integrity dashboard summary.

Design principles (issue #225):
  1. An engine distinguishes CONFIRMED / PROBABLE / POSSIBLE relationships.
     Nothing is auto-confirmed. Language is always cautious.
  2. Do NOT merge on a single shared attribute.
  3. Evidence is grouped and weighted (weights configurable), never simple
     additive scoring across linearly-correlated signals.
  4. Sensitive identifiers are stored hashed + masked in the identity layer to
     avoid PII duplication. Original values remain only in the source tables.
"""
from __future__ import annotations

import hashlib
import re
import uuid
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models.criminal import Criminal
from app.models.identity import (
    ASSESSMENT_IDENTITY_CONFLICT,
    ASSESSMENT_POSSIBLE_ASSOCIATED,
    ASSESSMENT_POSSIBLE_IDENTITY,
    ASSESSMENT_POSSIBLE_PROXY,
    ASSESSMENT_PROBABLE_IDENTITY,
    ASSESSMENT_REQUIRES_REVIEW,
    ENTITY_KIND_CRIMINAL,
    ENTITY_KIND_VICTIM,
    EVIDENCE_GROUP_BIOGRAPHICAL,
    EVIDENCE_GROUP_CASE_HISTORY,
    EVIDENCE_GROUP_CONTACT,
    EVIDENCE_GROUP_DEVICE,
    EVIDENCE_GROUP_LOCATION,
    EVIDENCE_GROUP_NETWORK,
    EVIDENCE_GROUP_VEHICLE,
    ALERT_ALIAS,
    ALERT_CONFLICT,
    ALERT_DUPLICATE,
    ALERT_DUPLICATE_RECORD,
    ALERT_IDENTIFIER_REUSE,
    ALERT_PROXY,
    AUDIT_ALIAS_DETECTED,
    AUDIT_CONFLICT_DETECTED,
    AUDIT_IDENTIFIER_REUSE,
    AUDIT_MATCH_PROPOSED,
    REL_ALIAS_OF,
    REL_ASSOCIATED_WITH,
    REL_CONFLICTING_IDENTITY,
    REL_POSSIBLE_PROXY,
    REL_SAME_PERSON_POSSIBLE,
    REL_SAME_PERSON_PROBABLE,
    RELATIONSHIP_TYPES,
    REL_STATUS_OPEN,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_CRITICAL,
    IdentityAlias,
    IdentityConflict,
    IdentityEvidence,
    IdentityIdentifier,
    IdentityRelationship,
    IntegrityAlert,
    REL_SHARES_PHONE,
)
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.victim import Victim

# ---------------------------------------------------------------------------
# Default, configurable weight groups (issue #225 section 3/4)
# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS = {
    EVIDENCE_GROUP_BIOGRAPHICAL: 25,
    EVIDENCE_GROUP_CONTACT: 20,
    EVIDENCE_GROUP_LOCATION: 15,
    EVIDENCE_GROUP_VEHICLE: 10,
    EVIDENCE_GROUP_CASE_HISTORY: 15,
    EVIDENCE_GROUP_NETWORK: 15,
}

# Weights are configurable at the module level (env override-friendly) rather
# than hard-coded on individual endpoints.
ID_WEIGHTS: dict[str, int] = dict(DEFAULT_WEIGHTS)

# Thresholds below which a pair is not surfaced as a candidate relationship.
MIN_CANDIDATE_CONFIDENCE = 20.0

# A contact token shared by more profiles than this is treated as a
# non-distinguishing identifier (hotlines, office lines, reused numbers) and is
# excluded from contact blocking to avoid O(n^2) noise cliques (issue #225).
MAX_SHARED_CONTACT_PROFILES = 8
PROBABLE_THRESHOLD = 60.0
POSSIBLE_THRESHOLD = 35.0

# Evidence groups that can support an identity (same-person) claim: only
# biographical attributes and a personally-held device. Shared phones, addresses
# and vehicles are *link* evidence (families/roommates/proxies share them) and
# therefore belong to the association set — issue #225 section 7.
IDENTITY_EVIDENCE_GROUPS = {
    EVIDENCE_GROUP_BIOGRAPHICAL,
    EVIDENCE_GROUP_DEVICE,
}
# Evidence groups that indicate association / co-participation / proxying.
ASSOCIATION_EVIDENCE_GROUPS = {
    EVIDENCE_GROUP_CONTACT,
    EVIDENCE_GROUP_LOCATION,
    EVIDENCE_GROUP_VEHICLE,
    EVIDENCE_GROUP_CASE_HISTORY,
    EVIDENCE_GROUP_NETWORK,
}

# Identifiers that are too generic / high-collision to be treated as strong
# identity signals on their own.
TOPUID_LOCATION_KEYWORDS = {"police station", "police", "court", "hospital", "station"}
ADDRESS_HINT_WORDS = {"street", "road", "road", "nagar", "extension", "layout", "cross", "main", "circle"}

# Patterns reused across the engine (kept here so tests can share them).
PHONE_RE = re.compile(r"(\+?91[-\s]?)?([6-9]\d{4}[-\s]?\d{5})")
VEHICLE_RE = re.compile(r"KA[-\s]?\d{1,2}[-\s]?[A-Z]{1,3}[-\s]?\d{3,4}")


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------
def _fold(value: str | None) -> str:
    if not value:
        return ""
    return unicodedata.normalize("NFKD", str(value)).casefold().strip()


def normalize_name(value: str | None) -> str:
    """Normalize a person's name: casefold, strip honors and extra spaces."""
    if not value:
        return ""
    text = _fold(value)
    text = re.sub(r"\b(?:mr|mrs|ms|dr|sri|smt|shri|shrimati|kum|joiner)\b\.?\s*", " ", text)
    # alpha-only tokens (drop stray punctuation/numbers embedded in names)
    tokens = [t for t in re.split(r"[\s.,/&()-]+", text) if t and t.isalpha()]
    return " ".join(sorted(set(tokens)))


def normalize_phone(value: str | None) -> str:
    """Return a canonical 10-digit phone or empty string."""
    if not value:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if digits.startswith("91"):
        digits = digits[2:]
    if digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits.startswith(("6", "7", "8", "9")):
        return digits
    return ""


def normalize_address(value: str | None) -> str:
    if not value:
        return ""
    text = _fold(value)
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [t for t in text.split() if t not in ADDRESS_HINT_WORDS]
    return " ".join(sorted(set(tokens)))


def normalize_vehicle(value: str | None) -> str:
    if not value:
        return ""
    m = VEHICLE_RE.search(value)
    if not m:
        return _fold(value)
    return re.sub(r"[\s-]", "", m.group(0).upper())


def normalize_email(value: str | None) -> str:
    if not value:
        return ""
    return _fold(value).split("@")[0]


# ---------------------------------------------------------------------------
# Identifier hashing
# ---------------------------------------------------------------------------
def hash_identifier(kind: str, value: str) -> str:
    """SHA-256 hash of (kind, normalized value) for equality, no raw PII."""
    normalized = value.strip().lower()
    return hashlib.sha256(f"{kind}:{normalized}".encode("utf-8")).hexdigest()


def mask_display(kind: str, value: str | None) -> str | None:
    """Mask a raw identifier for display without returning full PII."""
    if not value:
        return None
    if kind == "phone":
        digits = re.sub(r"\D", "", str(value))
        if len(digits) >= 10:
            return f"{digits[:5] if len(digits) > 10 else '***'}{'*' * (len(digits[-5:]) - 4)}{digits[-3:]}" if False else _mask_last4(value)
        return "***"
    if kind == "email":
        local, _, domain = str(value).partition("@")
        if domain:
            return f"{local[:1]}***@{domain}"
        return "***"
    if kind == "vehicle":
        return str(value)
    if kind == "address":
        return str(value)[:70]
    return str(value)


def _mask_last4(value: str) -> str:
    s = str(value)
    if len(s) <= 4:
        return "*" * len(s)
    return f"{s[:2].ljust(2, '*')}***{s[-4:]}".replace("*", "*")


# ---------------------------------------------------------------------------
# Entity profile extraction
# ---------------------------------------------------------------------------
def _entity_label(entity_type: str, obj: Any) -> str:
    if entity_type == ENTITY_KIND_CRIMINAL:
        return str(getattr(obj, "full_name", ""))
    if entity_type == ENTITY_KIND_VICTIM:
        return str(getattr(obj, "full_name", ""))
    return str(getattr(obj, "name", ""))


def _entity_dob(entity_type: str, obj: Any):
    return getattr(obj, "date_of_birth", None) or getattr(obj, "dob", None)


def _entity_address(entity_type: str, obj: Any) -> str | None:
    return getattr(obj, "address", None)


def _entity_contact(entity_type: str, obj: Any) -> str | None:
    contact = getattr(obj, "contact_number", None)
    if contact:
        return contact
    for attr in ("phone", "phoneno", "mobile", "phone_number"):
        val = getattr(obj, attr, None)
        if val:
            return val
    return None


def _entity_fir_ids(db: Session, entity_type: str, entity_id) -> set[uuid.UUID]:
    if entity_type == ENTITY_KIND_CRIMINAL:
        links = db.query(FIRCriminalLink).filter(FIRCriminalLink.criminal_id == entity_id).all()
        return {lk.fir_id for lk in links}
    links = db.query(FIRVictimLink).filter(FIRVictimLink.victim_id == entity_id).all()
    return {lk.fir_id for lk in links}


def _entity_fir_dates(db: Session, fir_ids) -> list[datetime]:
    if not fir_ids:
        return []
    firs = db.query(FIR).filter(FIR.id.in_(fir_ids)).all()
    return [f.filed_at for f in firs if f.filed_at]


class EntityProfile:
    def __init__(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        name: str,
        normalized_name: str,
        dob,
        address: str | None,
        contact: str | None,
        fir_ids: set[uuid.UUID],
        aliases: set[str],
        display_names: list[str],
        contacts: list[str] | None = None,
        identifier_types: set[str] | None = None,
        identifier_displays: dict[str, list[str]] | None = None,
        phone_hashes: set[str] | None = None,
    ):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.name = name
        self.normalized_name = normalized_name
        self.dob = dob
        self.address = address
        self.contact = contact
        self.fir_ids = fir_ids
        self.aliases = aliases  # normalized aliases
        self.display_names = display_names
        self.contacts = contacts or []  # additional contacts from identifier registry
        self.identifier_types = identifier_types or set()
        self.identifier_displays = identifier_displays or {}
        self.phone_hashes = phone_hashes or set()

    def all_phones(self) -> set[str]:
        raw = list(self.contacts)
        if self.contact:
            raw.append(self.contact)
        return {p for p in (normalize_phone(x) for x in raw) if p}

    def all_vehicles(self) -> list[str]:
        return [v for d in self.identifier_displays.get("vehicle", []) for v in [d] if normalize_vehicle(v)]


def _load_identifiers(db: Session) -> dict[tuple[str, str], list[IdentityIdentifier]]:
    """Group identity identifiers by (entity_type, entity_id)."""
    grouped: dict[tuple[str, str], list[IdentityIdentifier]] = defaultdict(list)
    for rec in db.query(IdentityIdentifier).all():
        grouped[(rec.entity_type, str(rec.entity_id))].append(rec)
    return grouped


def build_entity_profiles(db: Session) -> list[EntityProfile]:
    """Extract compact, PII-light profiles for every resolvable person record.

    Only normalized + hashed/display-masked values are kept here; this is used
    purely for candidate generation and scoring — source records are untouched.
    """
    profiles: list[EntityProfile] = []
    ident_by_entity = _load_identifiers(db)

    def _identifiers(entity_type: str, entity_id) -> tuple[set[str], dict[str, list[str]], list[str], set[str]]:
        recs = ident_by_entity.get((entity_type, str(entity_id)), [])
        types: set[str] = set()
        displays: dict[str, list[str]] = defaultdict(list)
        contacts: list[str] = []
        phone_hashes: set[str] = set()
        for rec in recs:
            types.add(rec.identifier_type)
            if rec.display_value:
                displays[rec.identifier_type].append(rec.display_value)
            if rec.identifier_type == "phone":
                if rec.value_hash:
                    phone_hashes.add(rec.value_hash)
                if rec.display_value:
                    contacts.append(rec.display_value)
        return types, dict(displays), contacts, phone_hashes

    criminals = db.query(Criminal).all()
    for c in criminals:
        aliases = _parse_aliases(c.aliases)
        fir_ids = {lk.fir_id for lk in c.fir_links}
        types, displays, contacts, phone_hashes = _identifiers(ENTITY_KIND_CRIMINAL, c.id)
        profiles.append(EntityProfile(
            entity_type=ENTITY_KIND_CRIMINAL,
            entity_id=c.id,
            name=c.full_name,
            normalized_name=normalize_name(c.full_name),
            dob=c.date_of_birth,
            address=c.address,
            contact=None,
            fir_ids=fir_ids,
            aliases=aliases,
            display_names=[c.full_name, *_parse_aliases(c.aliases)],
            contacts=contacts,
            identifier_types=types,
            identifier_displays=displays,
            phone_hashes=phone_hashes,
        ))

    victims = db.query(Victim).all()
    for v in victims:
        fir_ids = {lk.fir_id for lk in v.fir_links}
        aliases = set()
        types, displays, contacts, phone_hashes = _identifiers(ENTITY_KIND_VICTIM, v.id)
        profiles.append(EntityProfile(
            entity_type=ENTITY_KIND_VICTIM,
            entity_id=v.id,
            name=v.full_name,
            normalized_name=normalize_name(v.full_name),
            dob=None,
            address=v.address,
            contact=v.contact_number,
            fir_ids=fir_ids,
            aliases=aliases,
            display_names=[v.full_name],
            contacts=contacts,
            identifier_types=types,
            identifier_displays=displays,
            phone_hashes=phone_hashes,
        ))

    return profiles


def _parse_aliases(aliases: str | None) -> set[str]:
    if not aliases:
        return set()
    return {normalize_name(a) for a in str(aliases).split(",") if normalize_name(a)}


# ---------------------------------------------------------------------------
# Candidate generation / blocking
# ---------------------------------------------------------------------------
def generate_candidates(profiles: list[EntityProfile]) -> list[tuple[EntityProfile, EntityProfile, str]]:
    """Return unordered (a, b, blocking_key) candidate pairs.

    Blocking keys (issue #225 section 20):
      * Normalized-name equality or alias overlap.
      * Shared contact hash.
      * Shared identity-alias (from IdentityAlias table).
      * Shared FIR / case relationship.
    Each candidate appears at most once per blocking key per pair. Pairs with
    the *exact same* entity id are never emitted.
    """
    pairs: dict[tuple[str, str], tuple[str, EntityProfile, EntityProfile]] = {}

    # 1. Name / alias blocking
    by_name: dict[str, list[EntityProfile]] = defaultdict(list)
    for p in profiles:
        key = p.normalized_name
        if key:
            by_name[key].append(p)
        for a in p.aliases:
            if a:
                by_name[a].append(p)
    for bucket in by_name.values():
        _emit_all_pairs(bucket, "normalized_name", pairs)

    # 2. Contact hash blocking. A contact token appearing on more than
    #    MAX_SHARED_CONTACT_PROFILES profiles (hotlines, shared office lines,
    #    reused synthetic numbers) is not a distinguishing identifier — using it
    #    for blocking produces O(n^2) noise cliques, so it is skipped.
    by_contact: dict[str, list[EntityProfile]] = defaultdict(list)
    for p in profiles:
        phone_keys = p.phone_hashes or {hash_identifier("phone", ph) for ph in p.all_phones()}
        for phone in phone_keys:
            by_contact[phone].append(p)
    for bucket in by_contact.values():
        if len(bucket) > MAX_SHARED_CONTACT_PROFILES:
            continue
        _emit_all_pairs(bucket, "shared_contact", pairs)

    # 3. FIR co-occurrence blocking (multiple people on same FIR)
    by_fir: dict[uuid.UUID, list[EntityProfile]] = defaultdict(list)
    for p in profiles:
        for fid in p.fir_ids:
            by_fir[fid].append(p)
    for bucket in by_fir.values():
        _emit_all_pairs(bucket, "shared_fir", pairs)

    return [(a, b, key) for key, a, b in pairs.values()]


def _emit_all_pairs(
    bucket: list[EntityProfile],
    key: str,
    pairs: dict[tuple[str, str], tuple[str, EntityProfile, EntityProfile]],
) -> None:
    unique = {id(p): p for p in bucket}
    items = list(unique.values())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if a.entity_id == b.entity_id and a.entity_type == b.entity_type:
                continue
            pair_key = _pair_key(a, b)
            # Prefer a more specific blocking key if already present.
            existing = pairs.get(pair_key)
            if existing is None or _block_priority(key) < _block_priority(existing[0]):
                pairs[pair_key] = (key, a, b)


_BLOCK_PRIORITY = {"normalized_name": 1, "shared_contact": 2, "shared_fir": 3}


def _block_priority(key: str) -> int:
    return _BLOCK_PRIORITY.get(key, 4)


def _pair_key(a: EntityProfile, b: EntityProfile) -> tuple:
    """Ordered, hashable pair key for a candidate pair (type, id, type, id)."""
    ta, tb = a.entity_type, b.entity_type
    if (ta, str(a.entity_id)) <= (tb, str(b.entity_id)):
        return (ta, str(a.entity_id), tb, str(b.entity_id))
    return (tb, str(b.entity_id), ta, str(a.entity_id))


# ---------------------------------------------------------------------------
# Evidence scoring
# ---------------------------------------------------------------------------
class _Scored:
    """Accumulates positive (per-group, capped) and counter evidence mass.

    ``group_positive`` tracks the summed raw positive contribution per evidence
    group so score normalization can cap each group at its configured maximum —
    never treating linearly-correlated signals within one group as independent
    proof (issue #225 section 12).
    """

    def __init__(self):
        self.group_positive: dict[str, float] = defaultdict(float)
        self.counter_mass: float = 0.0
        self.breakdown: list[dict[str, Any]] = []
        self.evidence: list[IdentityEvidence] = []
        self.counter_evidence: list[IdentityEvidence] = []
        self.conflicts: list[dict[str, Any]] = []


def _add_signal(
    scored: _Scored,
    db: Session,
    relationship_id: uuid.UUID | None,
    group: str,
    signal_type: str,
    weight: float,
    confidence: float,
    description: str,
    *,
    is_counter: bool = False,
    severity: str | None = None,
    source_type: str | None = None,
    source_label: str | None = None,
    observed_at: datetime | None = None,
    time_range: str | None = None,
) -> None:
    """Record a single (positive or counter) evidence signal with its weight."""
    if not is_counter:
        scored.group_positive[group] += max(0.0, weight)
    else:
        scored.counter_mass += abs(weight)
    item = {
        "group": group,
        "signal": signal_type,
        "weight": round(weight, 2),
        "confidence": round(confidence, 2),
        "counter": is_counter,
        "description": description,
        "source": source_label,
        "severity": severity,
    }
    (scored.counter_evidence if is_counter else scored.breakdown).append(item)
    if relationship_id is not None:
        scored.evidence.append(IdentityEvidence(
            relationship_id=relationship_id,
            evidence_group=group,
            signal_type=signal_type,
            weight_delta=round(-abs(weight) if is_counter else weight, 2),
            confidence=confidence,
            severity=severity,
            source_type=source_type,
            source_label=source_label,
            description=description,
            observed_at=observed_at,
            time_range=time_range,
            is_counter_evidence=is_counter,
        ))


def score_pair(
    db: Session,
    a: EntityProfile,
    b: EntityProfile,
    weights: dict[str, int] | None = None,
    relationship_id: uuid.UUID | None = None,
) -> _Scored:
    """Score a candidate pair using grouped, weighted, counter-evidence-aware logic."""
    w = weights or ID_WEIGHTS
    scored = _Scored()
    group_used: set[str] = set()

    # --- Biographical (name / DOB / initials / transliteration) ---
    bio_mat = 0.0
    sig_added = False
    if a.normalized_name and b.normalized_name and a.normalized_name == b.normalized_name:
        bio_mat = 1.0
        _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_BIOGRAPHICAL, "normalized_name_exact",
                    w[EVIDENCE_GROUP_BIOGRAPHICAL] * 0.6, 0.9,
                    "Normalized name exact match", source_label="name")
        sig_added = True
    elif a.normalized_name and b.normalized_name:
        a_tokens = set(a.normalized_name.split())
        b_tokens = set(b.normalized_name.split())
        inter = a_tokens & b_tokens
        union = a_tokens | b_tokens
        if inter and union:
            jacc = len(inter) / len(union)
            if a_tokens - b_tokens or b_tokens - a_tokens:
                # Partial-name score: shared tokens but not identical
                bio_mat = max(0.35, jacc)
                _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_BIOGRAPHICAL, "name_initial_overlap",
                            w[EVIDENCE_GROUP_BIOGRAPHICAL] * 0.5 * bio_mat, round(bio_mat, 2),
                            f"Partial name overlap ({round(jacc, 2)})", source_label="name")
                sig_added = True
        elif not inter:
            # Different tokens — fall back to a weak character-level similarity so
            # transliteration / common-name variants still register *weakly*.
            char_sim = _char_similarity(a.normalized_name, b.normalized_name)
            if char_sim >= 0.5:
                bio_mat = char_sim
                _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_BIOGRAPHICAL, "name_phonetic_similarity",
                            w[EVIDENCE_GROUP_BIOGRAPHICAL] * 0.4 * char_sim, round(char_sim, 2),
                            f"Name character similarity ({round(char_sim, 2)})", source_label="name")
                sig_added = True
    # alias overlap contributes within biographical
    alias_overlap = (a.aliases & b.aliases) or (a.display_names and a.display_names[0] and
                                                b.display_names and b.display_names[0] and
                                                normalize_name(a.display_names[0]) in b.display_names)
    if alias_overlap and not sig_added:
        bio_mat = max(bio_mat, 0.5)
        _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_BIOGRAPHICAL, "alias_overlap",
                    w[EVIDENCE_GROUP_BIOGRAPHICAL] * 0.5, 0.6,
                    "Shared known alias", source_label="alias")
        sig_added = True

    if a.dob and b.dob:
        if a.dob == b.dob:
            dob_w = w[EVIDENCE_GROUP_BIOGRAPHICAL] * 0.45 if bio_mat > 0 else w[EVIDENCE_GROUP_BIOGRAPHICAL] * 0.6
            _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_BIOGRAPHICAL, "dob_match",
                        dob_w, 0.95,
                        "Date of birth exact match", source_label="dob")
        elif a.dob != b.dob:
            _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_BIOGRAPHICAL, "dob_conflict",
                        w[EVIDENCE_GROUP_BIOGRAPHICAL] * 0.35, -0.9,
                        f"Conflicting date of birth ({a.dob} vs {b.dob})",
                        is_counter=True, severity="HIGH")
            scored.conflicts.append({"attribute": "dob",
                                     "value_a": str(a.dob), "value_b": str(b.dob),
                                     "severity": SEVERITY_HIGH})
            group_used.add(EVIDENCE_GROUP_BIOGRAPHICAL)

    # --- Contact consistency ---
    shared_phones = a.phone_hashes & b.phone_hashes
    if shared_phones:
        _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_CONTACT, "shared_phone",
                    w[EVIDENCE_GROUP_CONTACT] * 0.9, 0.9,
                    "Shared phone identifier (PII-masked)",
                    source_label="phone")

    # --- Location consistency ---
    a_addr = normalize_address(a.address)
    b_addr = normalize_address(b.address)
    if a_addr and b_addr and a_addr == b_addr and len(a_addr) >= 4:
        _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_LOCATION, "shared_address",
                    w[EVIDENCE_GROUP_LOCATION] * 0.9, 0.85,
                    f"Shared address ({mask_display('address', a.address)})",
                    source_label="address")
    elif a.address and b.address and len(_fold(a.address)) > 0 and len(_fold(b.address)) > 0:
        a_tokens = set(normalize_address(a.address).split())
        b_tokens = set(normalize_address(b.address).split())
        inter = a_tokens & b_tokens
        if inter and (len(inter) / max(len(a_tokens | b_tokens), 1)) > 0.5:
            _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_LOCATION, "address_overlap",
                        w[EVIDENCE_GROUP_LOCATION] * 0.5, 0.5,
                        "Partial address overlap", source_label="address")
        else:
            _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_LOCATION, "address_conflict",
                        w[EVIDENCE_GROUP_LOCATION] * 0.25, -0.7,
                        "Different residential addresses",
                        is_counter=True, severity="MEDIUM")
            scored.conflicts.append({"attribute": "address",
                                     "value_a": str(a.address), "value_b": str(b.address),
                                     "severity": SEVERITY_MEDIUM})

    # --- Vehicle consistency ---
    a_vehicles = [normalize_vehicle(v) for v in _entity_vehicles(a)]
    b_vehicles = [normalize_vehicle(v) for v in _entity_vehicles(b)]
    shared_vehicle = set(a_vehicles) & set(b_vehicles)
    for v in shared_vehicle:
        if v:
            _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_VEHICLE, "shared_vehicle",
                        w[EVIDENCE_GROUP_VEHICLE] * 0.8, 0.75,
                        f"Shared vehicle ({v})", source_label="vehicle")

    # --- Case relationship ---
    shared_firs = a.fir_ids & b.fir_ids
    if shared_firs:
        # Group 1: same FIR/case/incident — single evidence cluster, bounded.
        _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_CASE_HISTORY, "shared_fir",
                    w[EVIDENCE_GROUP_CASE_HISTORY] * 0.7 * (1.0 if len(shared_firs) >= 1 else 0.5),
                    0.7,
                    f"{len(shared_firs)} shared FIR(s)", source_label="FIR")
    elif a.fir_ids and b.fir_ids:
        # Same-incident-location / same-associates via common co-appearance scoring.
        a_cases, b_cases = _case_districts(db, a), _case_districts(db, b)
        case_overlap = a_cases & b_cases
        if case_overlap:
            _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_CASE_HISTORY, "related_case",
                        w[EVIDENCE_GROUP_CASE_HISTORY] * 0.35, 0.5,
                        f"{len(case_overlap)} common case location(s)", source_label="case")

    # --- Network / associate evidence ---
    net_score = _network_overlap(db, a, b)
    if net_score > 0:
        _add_signal(scored, db, relationship_id, EVIDENCE_GROUP_NETWORK, "shared_associates",
                    w[EVIDENCE_GROUP_NETWORK] * 0.6 * net_score, net_score,
                    f"{net_score:.0%} shared associate/co-occurrence overlap", source_label="network")

    return scored


def _char_similarity(a: str, b: str) -> float:
    """Weak character-level similarity for transliteration / name variants.

    Uses bigram set Jaccard so common diacritic/letter-order permutations still
    register a modest signal while unrelated names produce near-zero scores.
    """
    def _bigrams(s: str) -> set[str]:
        s = re.sub(r"[^a-z0-9]", "", s.lower())
        return {s[i:i + 2] for i in range(max(len(s) - 1, 1))} or {s}
    big_a, big_b = _bigrams(a), _bigrams(b)
    if not big_a or not big_b:
        return 0.0
    inter = big_a & big_b
    union = big_a | big_b
    if not union:
        return 0.0
    return round(min(1.0, len(inter) / len(union)), 3)


def _entity_vehicles(profile: EntityProfile) -> list[str]:
    """Vehicles attributed to an entity under the identity identifier registry.

    Returns only explicitly-typed identifier records (never free-text scraping)
    so the engine stays deterministic and does not over-claim from narrative text.
    """
    if not profile.identifier_types or "vehicle" not in profile.identifier_types:
        return []
    return [d for d in profile.identifier_displays.get("vehicle", []) if d]


def _case_districts(db: Session, p: EntityProfile) -> set[str]:
    if not p.fir_ids:
        return set()
    cache = db.info.setdefault("identity_case_districts", {})
    cache_key = (p.entity_type, str(p.entity_id))
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    firs = db.query(FIR).filter(FIR.id.in_(p.fir_ids)).all()
    loc_ids = {f.crime_case.location_id for f in firs if f.crime_case and f.crime_case.location_id}
    from app.models.location import Location
    if not loc_ids:
        cache[cache_key] = set()
        return cache[cache_key]
    locs = db.query(Location).filter(Location.id.in_(loc_ids)).all()
    districts = {l.district for l in locs if l.district}
    cache[cache_key] = districts
    return districts


def _network_overlap(db: Session, a: EntityProfile, b: EntityProfile) -> float:
    """Fraction of a's immediate network (co-participants) shared with b's."""
    a_shared_ids = _co_participants(db, a) 
    b_shared_ids = _co_participants(db, b)
    inter = a_shared_ids & b_shared_ids
    union = a_shared_ids | b_shared_ids
    if not union:
        return 0.0
    return round(len(inter) / len(union), 3)


def _co_participants(db: Session, p: EntityProfile) -> set[str]:
    """Set of other FIR participants (criminals+victims) sharing any of p's FIRs."""
    cache = db.info.setdefault("identity_co_participants", {})
    cache_key = (p.entity_type, str(p.entity_id))
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    result: set[str] = set()
    if p.fir_ids:
        fids = list(p.fir_ids)
        # Batch per-profile (rather than per-FIR) so the identity scan stays fast
        # on remote databases. Select only the foreign-key values needed for
        # overlap scoring — avoids hydrating legacy link rows with unused columns
        # and keeps the scan compatible with older deployments of these tables.
        criminal_ids = db.query(FIRCriminalLink.criminal_id).filter(
            FIRCriminalLink.fir_id.in_(fids)
        ).all()
        for (criminal_id,) in criminal_ids:
            if (criminal_id, ENTITY_KIND_CRIMINAL) != (p.entity_id, p.entity_type):
                result.add((ENTITY_KIND_CRIMINAL, str(criminal_id)))
        victim_ids = db.query(FIRVictimLink.victim_id).filter(
            FIRVictimLink.fir_id.in_(fids)
        ).all()
        for (victim_id,) in victim_ids:
            if (victim_id, ENTITY_KIND_VICTIM) != (p.entity_id, p.entity_type):
                result.add((ENTITY_KIND_VICTIM, str(victim_id)))
    participants = {f"{t}:{i}" for t, i in result}
    cache[cache_key] = participants
    return participants


def _strong_identity_mass(scored: _Scored, weights: dict[str, int] | None = None) -> float:
    """Sum of strong biographical/device evidence (weak name similarity excluded).

    Weak transliteration/character-similarity is noise, not identity
    corroboration; only signals at or above half their group maximum count as
    identity evidence so link-sharing alone never inflates identity mass.
    """
    w = weights or ID_WEIGHTS
    total = 0.0
    for item in scored.breakdown:
        if item.get("counter"):
            continue
        if item["group"] not in IDENTITY_EVIDENCE_GROUPS:
            continue
        if item["weight"] >= 0.5 * float(w.get(item["group"], 0.0)):
            total += max(0.0, item["weight"])
    return total


def _assess(scored: _Scored, score: float, weights: dict[str, int] | None) -> tuple[str, str]:
    """Map the weighted score + evidence composition into a cautious verdict.

    Conservative rules (issue #225 sections 6, 7, 18):
      * Repeated strong contradictions kill identity claims entirely.
      * Purely link evidence (shared phone/address/vehicle/case/network) with no
        strong biographical corroboration is always an *association*, never
        identity.
      * A single strong biographical conflict caps identity at "possible".
    """
    high_conflicts = sum(c.get("severity") == SEVERITY_HIGH for c in scored.conflicts)
    score = max(0.0, min(score, 100.0))

    identity_mass = _strong_identity_mass(scored, weights)

    if high_conflicts >= 2:
        # Repeated strong contradictions kill identity claims entirely.
        return ASSESSMENT_POSSIBLE_ASSOCIATED, REL_ASSOCIATED_WITH
    if identity_mass <= 0:
        # Links shared between distinct persons = association / proxy territory.
        return ASSESSMENT_POSSIBLE_ASSOCIATED, REL_ASSOCIATED_WITH
    if high_conflicts == 1:
        # A single strong biographical conflict caps identity at "possible".
        if score >= POSSIBLE_THRESHOLD:
            return ASSESSMENT_POSSIBLE_IDENTITY, REL_SAME_PERSON_POSSIBLE
        return ASSESSMENT_REQUIRES_REVIEW, REL_POSSIBLE_PROXY
    if score >= PROBABLE_THRESHOLD:
        return ASSESSMENT_PROBABLE_IDENTITY, REL_SAME_PERSON_PROBABLE
    if score >= POSSIBLE_THRESHOLD:
        return ASSESSMENT_POSSIBLE_IDENTITY, REL_SAME_PERSON_POSSIBLE
    return ASSESSMENT_REQUIRES_REVIEW, REL_POSSIBLE_PROXY


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _upsert_relationship(
    db: Session,
    a: EntityProfile,
    b: EntityProfile,
    blocked_by: str,
    scored: _Scored,
) -> IdentityRelationship:
    existing = (
        db.query(IdentityRelationship)
        .filter(
            IdentityRelationship.source_entity_type == a.entity_type,
            IdentityRelationship.source_entity_id == a.entity_id,
            IdentityRelationship.target_entity_type == b.entity_type,
            IdentityRelationship.target_entity_id == b.entity_id,
        )
        .first()
    )
    if existing is None:
        existing = (
            db.query(IdentityRelationship)
            .filter(
                IdentityRelationship.source_entity_type == b.entity_type,
                IdentityRelationship.source_entity_id == b.entity_id,
                IdentityRelationship.target_entity_type == a.entity_type,
                IdentityRelationship.target_entity_id == a.entity_id,
            )
            .first()
        )
    if existing is None:
        existing = IdentityRelationship(
            source_entity_type=a.entity_type,
            source_entity_id=a.entity_id,
            target_entity_type=b.entity_type,
            target_entity_id=b.entity_id,
            relationship_type=REL_SAME_PERSON_POSSIBLE,
            assessment=ASSESSMENT_REQUIRES_REVIEW,
            status=REL_STATUS_OPEN,
        )
        db.add(existing)
        db.flush()
    return existing


def _save_evidence(
    db: Session,
    relationship: IdentityRelationship,
    scored: _Scored,
) -> None:
    """Persist (or refresh) identity evidence rows for an existing relationship."""
    existing = {
        (e.signal_type, e.is_counter_evidence): e
        for e in db.query(IdentityEvidence).filter(
            IdentityEvidence.relationship_id == relationship.id
        ).all()
    }

    def _upsert_from(item: dict, counter: bool) -> None:
        key = (item["signal"], counter)
        old = existing.get(key)
        if old is not None:
            old.weight_delta = -abs(item["weight"]) if counter else item["weight"]
            old.confidence = item.get("confidence")
            old.description = item.get("description")
            old.is_counter_evidence = counter
        else:
            db.add(IdentityEvidence(
                relationship_id=relationship.id,
                evidence_group=item["group"],
                signal_type=item["signal"],
                weight_delta=-abs(item["weight"]) if counter else item["weight"],
                confidence=item.get("confidence"),
                severity=item.get("severity"),
                source_type=item.get("source"),
                source_label=item.get("source"),
                description=item.get("description"),
                is_counter_evidence=counter,
            ))

    for item in scored.breakdown:
        _upsert_from(item, counter=False)
    for item in scored.counter_evidence:
        _upsert_from(item, counter=True)
    db.flush()


def _save_conflicts(db: Session, relationship: IdentityRelationship, scored: _Scored) -> None:
    existing = {
        (c.attribute,) for c in db.query(IdentityConflict).filter(
            IdentityConflict.relationship_id == relationship.id
        ).all()
    }
    for conflict in scored.conflicts:
        if (conflict["attribute"],) not in existing:
            db.add(IdentityConflict(
                relationship_id=relationship.id,
                source_entity_type=relationship.source_entity_type,
                source_entity_id=relationship.source_entity_id,
                target_entity_type=relationship.target_entity_type,
                target_entity_id=relationship.target_entity_id,
                attribute=conflict["attribute"],
                value_a=conflict["value_a"],
                value_b=conflict["value_b"],
                severity=conflict["severity"],
                explanation="Conflicting biographical attribute between candidate records.",
            ))
    db.flush()


# ---------------------------------------------------------------------------
# Public orchestration: run full resolution scan
# ---------------------------------------------------------------------------
def _normalize_phone_for_identifier(v: str) -> str:
    return normalize_phone(v)


def _text_identifiers(text: str | None) -> tuple[list[str], list[str]]:
    """Best-effort phones + vehicle plates pulled from free text.

    Uses the identity service's own normalized regex extractors (which tolerate
    spaced digits) and augments from the MO semantic service gazetteer so
    narrative sources (mo_summary, statements, FIR narratives) can contribute
    contact and vehicle identifiers without a model schema change.
    """
    if not text:
        return [], []
    phones: list[str] = []
    plates: list[str] = []
    for m in PHONE_RE.finditer(text):
        norm = normalize_phone(m.group(0))
        if norm:
            phones.append(norm)
    for m in VEHICLE_RE.finditer(text):
        norm = normalize_vehicle(m.group(0))
        if norm:
            plates.append(norm)
    from app.services.mo_semantic_service import extract_entities
    try:
        extracted = extract_entities(text) or {}
    except Exception:
        extracted = {}
    phones += [p for p in (extracted.get("phone_numbers") or []) if normalize_phone(p)]
    plates += [v for v in (extracted.get("vehicle_plates") or []) if normalize_vehicle(v)]
    return list(dict.fromkeys(phones)), list(dict.fromkeys(plates))


def sync_identity_identifiers(db: Session) -> int:
    """Populate identity_identifiers with hashed, masked values from source rows.

    Sources:
      * names/aliases from person records
      * phones from victim contact_number, FIR complainant_contact, and free text
      * vehicles from explicit fields when present and free-text plates
    Only normalized, non-empty values are recorded; identifiers are refreshed
    rather than duplicated on subsequent runs.
    """
    written = 0
    criminals = db.query(Criminal).all()
    criminal_ids = {c.id for c in criminals}
    for c in criminals:
        for name in _alias_list(c):
            n = normalize_name(name)
            if not n:
                continue
            _upsert_identifier(db, ENTITY_KIND_CRIMINAL, c.id, "name", hash_identifier("name", n),
                               mask_display("name", name), "alias_profile")
            written += 1
        phones, plates = _text_identifiers(f"{c.mo_summary or ''} | {c.identifying_marks or ''}")
        for phone in phones:
            _upsert_identifier(db, ENTITY_KIND_CRIMINAL, c.id, "phone", hash_identifier("phone", phone),
                               mask_display("phone", phone), "text_extraction")
            written += 1
        for plate in plates:
            _upsert_identifier(db, ENTITY_KIND_CRIMINAL, c.id, "vehicle", hash_identifier("vehicle", plate),
                               plate, "text_extraction")
            written += 1
    victims = db.query(Victim).all()
    victim_ids = {v.id for v in victims}
    for v in victims:
        n = normalize_name(v.full_name)
        if n:
            _upsert_identifier(db, ENTITY_KIND_VICTIM, v.id, "name", hash_identifier("name", n),
                           v.full_name, "registry")
            written += 1
        phone = normalize_phone(v.contact_number)
        if phone:
            _upsert_identifier(db, ENTITY_KIND_VICTIM, v.id, "phone", hash_identifier("phone", phone),
                               mask_display("phone", v.contact_number), "registry")
            written += 1
        phones, plates = _text_identifiers(f"{v.statement or ''} | {v.address or ''}")
        for phone in phones:
            _upsert_identifier(db, ENTITY_KIND_VICTIM, v.id, "phone", hash_identifier("phone", phone),
                               mask_display("phone", phone), "text_extraction")
            written += 1
        for plate in plates:
            _upsert_identifier(db, ENTITY_KIND_VICTIM, v.id, "vehicle", hash_identifier("vehicle", plate),
                               plate, "text_extraction")
            written += 1
    _sync_fir_identifiers(db, criminal_ids, victim_ids)
    db.flush()
    return written


def _sync_fir_identifiers(db: Session, criminal_ids: set, victim_ids: set) -> int:
    """Attach phones/vehicles found in linked FIR narratives/complainant contacts.

    Each FIR is resolved once; its extracted identifiers are attributed to every
    person record linked to that FIR, preserving provenance via source_label.
    """
    written = 0
    firs = db.query(FIR).all()
    fir_links_by_id: dict[str, list[str, object]] = {}
    for link in db.query(FIRCriminalLink).all():
        fir_links_by_id.setdefault(str(link.fir_id), []).append((ENTITY_KIND_CRIMINAL, link.criminal_id))
    for link in db.query(FIRVictimLink).all():
        fir_links_by_id.setdefault(str(link.fir_id), []).append((ENTITY_KIND_VICTIM, link.victim_id))
    for fir in firs:
        phones = [p for p in [normalize_phone(fir.complainant_contact)] if p]
        narrative_phones, plates = _text_identifiers(fir.narrative)
        phones.extend(p for p in narrative_phones if p not in phones)
        linked = fir_links_by_id.get(str(fir.id), [])
        for entity_type, entity_id in linked:
            if entity_type == ENTITY_KIND_CRIMINAL and entity_id not in criminal_ids:
                continue
            if entity_type == ENTITY_KIND_VICTIM and entity_id not in victim_ids:
                continue
            for phone in phones:
                _upsert_identifier(db, entity_type, entity_id, "phone",
                                   hash_identifier("phone", phone), mask_display("phone", phone),
                                   f"fir:{str(fir.id)[:8]}")
                written += 1
            for plate in plates:
                _upsert_identifier(db, entity_type, entity_id, "vehicle",
                                   hash_identifier("vehicle", plate), plate,
                                   f"fir:{str(fir.id)[:8]}")
                written += 1
    return written


def _alias_list(c: Criminal) -> list[str]:
    out = [c.full_name]
    if c.aliases:
        out.extend([a for a in str(c.aliases).split(",") if a.strip()])
    return out


def _upsert_identifier(
    db: Session,
    entity_type: str,
    entity_id,
    id_type: str,
    value_hash: str,
    display: str | None,
    source_label: str,
) -> IdentityIdentifier | None:
    existing = (
        db.query(IdentityIdentifier)
        .filter(
            IdentityIdentifier.entity_type == entity_type,
            IdentityIdentifier.entity_id == entity_id,
            IdentityIdentifier.identifier_type == id_type,
            IdentityIdentifier.value_hash == value_hash,
        )
        .first()
    )
    if existing is not None:
        existing.display_value = display or existing.display_value
        return existing
    rec = IdentityIdentifier(
        entity_type=entity_type,
        entity_id=entity_id,
        identifier_type=id_type,
        value_hash=value_hash,
        display_value=display,
        source_label=source_label,
        observed_at=datetime.now(timezone.utc),
    )
    db.add(rec)
    db.flush()
    return rec


def run_identity_resolution(
    db: Session,
    *,
    persist: bool = False,
    user=None,
    weights: dict[str, int] | None = None,
    entity_scope: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Run the full identity-resolution scan and (optionally) persist results.

    Returns a summary with scores for testing; when ``persist=True`` it stores
    relationships, evidence, conflicts and integrity alerts and audits each
    proposed match.
    """
    profiles = build_entity_profiles(db)
    if entity_scope is not None:
        profiles = [
            profile for profile in profiles
            if (profile.entity_type, str(profile.entity_id)) in entity_scope
        ]
    candidates = generate_candidates(profiles)

    relationships: list[dict[str, Any]] = []

    for a, b, blocked_by in candidates:
        scored = score_pair(db, a, b, weights=weights)
        raw = _weight_to_confidence(scored, weights)
        score = round(raw, 1)
        if score < MIN_CANDIDATE_CONFIDENCE:
            continue
        # A strong contradiction caps identity claims at "possible" — the score
        # must respect the same ceiling (issue #225). Two+ conflicts already
        # demote the pair to association in _assess.
        high_conflicts = sum(c.get("severity") == SEVERITY_HIGH for c in scored.conflicts)
        if high_conflicts >= 1:
            score = min(score, PROBABLE_THRESHOLD - 5.0)
        assessment, rel_type = _assess(scored, score, weights)
        relationship = None
        if persist:
            relationship = _upsert_relationship(db, a, b, blocked_by, scored)
            # Recompute evidence rows for an accurate, explainable snapshot.
            _save_evidence(db, relationship, scored)
            _save_conflicts(db, relationship, scored)
            relationship.confidence = score
            relationship.assessment = assessment
            relationship.relationship_type = rel_type
            relationship.confidence_breakdown = {
                "score": score,
                "thresholds": {"probable": PROBABLE_THRESHOLD, "possible": POSSIBLE_THRESHOLD},
                "contributing": _confidence_breakdown_payload(scored),
                "weights": weights or ID_WEIGHTS,
                "method": (
                    "weighted, grouped, counter-evidence-aware identity scoring "
                    "(biographical/contact/location/vehicle/case/network)"
                ),
            }
            relationship.evidence_summary = {
                "supporting_count": len(scored.breakdown),
                "counter_count": len(scored.counter_evidence),
                "groups": sorted({e.get("group") for e in scored.breakdown}),
            }
            db.flush()
            if user is not None:
                from app.services.audit_service import log_action
                log_action(
                    db, user, AUDIT_MATCH_PROPOSED, "IdentityRelationship",
                    str(relationship.id),
                    details=(
                        f"Proposed {rel_type} ({assessment}) between "
                        f"{a.name} and {b.name} at {score:.0f}% confidence (blocked by {blocked_by})"
                    ),
                    metadata_json=(
                        f'{{"confidence":{score},"type":"{rel_type}",'
                        f'"source":"{a.entity_type}:{a.entity_id}","target":"{b.entity_type}:{b.entity_id}"}}'
                    ),
                )
            db.flush()
        relationships.append({
            "source_type": a.entity_type,
            "source_id": str(a.entity_id),
            "source_name": a.name,
            "target_type": b.entity_type,
            "target_id": str(b.entity_id),
            "target_name": b.name,
            "blocking_key": blocked_by,
            "confidence": score,
            "assessment": assessment,
            "relationship_type": rel_type,
            "evidence_count": len(scored.breakdown),
            "conflict_count": len(scored.conflicts),
            "breaking": None,
        })

    if persist:
        _set_integrity_alerts(db, relationships)
        db.flush()

    return {
        "profiles_analyzed": len(profiles),
        "candidates_generated": len(candidates),
        "relationships_proposed": len(relationships),
        "results": relationships,
    }


def _weight_to_confidence(scored: _Scored, weights: dict[str, int] | None) -> float:
    """Normalize grouped evidence mass into a 0..100 confidence.

    1. Positive contributions are capped per evidence group (never double-count
       linearly-correlated signals within one group).
    2. Confidence = capped match mass / max achievable mass for the groups that
       fired, minus a bounded penalty proportional to the share of contradicting
       evidence.
    """
    w = weights or ID_WEIGHTS
    max_possible = 0.0
    capped = 0.0
    for group, mass in scored.group_positive.items():
        group_max = float(w.get(group, mass))
        max_possible += group_max
        capped += min(mass, group_max)
    if capped <= 0:
        return 0.0
    base = capped / max_possible * 100.0 if max_possible > 0 else 0.0
    conflict_ratio = scored.counter_mass / (scored.counter_mass + capped)
    confidence = base - conflict_ratio * 25.0
    return max(0.0, min(100.0, confidence))


def _confidence_breakdown_payload(scored: _Scored) -> list[dict[str, Any]]:
    payload = []
    for item in scored.breakdown:
        payload.append({
            "signal": item["signal"],
            "group": item["group"],
            "delta": item["weight"],
            "counter": False,
        })
    for item in scored.counter_evidence:
        payload.append({
            "signal": item["signal"],
            "group": item["group"],
            "delta": item["weight"],
            "counter": True,
        })
    return payload


def _set_integrity_alerts(db: Session, relationships: list[dict[str, Any]]) -> None:
    """Collapse proposed relationships into focused integrity alerts.

    Grouping keys let repeated/expanded evidence collapse into a single alert
    rather than flooding the operator (issue #225 section 14).
    """
    # Clear prior open integrity alerts derived from this scan so refreshed
    # results replace stale ones.
    db.query(IntegrityAlert).filter(IntegrityAlert.status == "open").delete(
        synchronize_session=False)

    for rel in relationships:
        # Alerts are reserved for actionable duplicate-identity and proxy leads;
        # routine co-occurrence associations stay in the review list only.
        if rel["assessment"] not in (
            ASSESSMENT_PROBABLE_IDENTITY,
            ASSESSMENT_POSSIBLE_IDENTITY,
            ASSESSMENT_POSSIBLE_PROXY,
        ):
            continue
        alert_type = ALERT_DUPLICATE
        gkey = f"{alert_type}:{min(rel['source_id'], rel['target_id'])}:{max(rel['source_id'], rel['target_id'])}"
        db.add(IntegrityAlert(
            alert_type=alert_type,
            severity=_severity_for(rel["confidence"]),
            entity_a_type=rel["source_type"],
            entity_a_id=uuid.UUID(rel["source_id"]),
            entity_b_type=rel["target_type"],
            entity_b_id=uuid.UUID(rel["target_id"]),
            confidence=rel["confidence"] / 100.0,
            description=(
                f"{rel['source_name']} ↔ {rel['target_name']}: {rel['assessment']} "
                f"({rel['confidence']:.0f}%), {rel['evidence_count']} evidence signal(s) via "
                f"{rel['blocking_key']}"
            ),
            grouping_key=gkey,
            observation_count=rel["evidence_count"],
            source_summary={"found_by": rel["blocking_key"], "evidence": rel["evidence_count"]},
        ))
    db.flush()


def _severity_for(score: float) -> str:
    if score >= 80:
        return SEVERITY_CRITICAL
    if score >= 60:
        return SEVERITY_HIGH
    if score >= 40:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


# ---------------------------------------------------------------------------
# Person search against identity signals
# ---------------------------------------------------------------------------
def search_identity(db: Session, q: str) -> dict[str, Any]:
    """Search person records by name/alias, returning identity-aware matches."""
    nq = normalize_name(q)
    profiles = build_entity_profiles(db)
    exact: list[dict[str, Any]] = []
    probable: list[dict[str, Any]] = []
    possible: list[dict[str, Any]] = []

    from app.models.criminal import Criminal as _C
    from app.models.victim import Victim as _V
    rows_c = db.query(_C).all()
    rows_v = db.query(_V).all()
    registry = {}
    for r in rows_c:
        registry[(ENTITY_KIND_CRIMINAL, str(r.id))] = r
    for r in rows_v:
        registry[(ENTITY_KIND_VICTIM, str(r.id))] = r

    for p in profiles:
        if not nq or not q.strip():
            continue
        qtokens = set(nq.split())
        name_tokens: set[str] = set()
        for dn in p.display_names:
            name_tokens.update(t for t in normalize_name(dn).split() if t)
        for al in p.aliases:
            name_tokens.update(t for t in al.split() if t)
        if not name_tokens:
            continue
        if p.normalized_name == nq:
            bucket = exact
        elif qtokens.issubset(name_tokens):
            bucket = probable
        elif any(qt in t or t in qt for qt in qtokens for t in name_tokens):
            bucket = possible
        else:
            continue
        row = registry.get((p.entity_type, str(p.entity_id)))
        bucket.append({
            "id": p.entity_id,
            "entity_type": p.entity_type,
            "entity_id": p.entity_id,
            "name": p.name,
            "status": getattr(row, "status", None) if row else None,
            "contacts": sorted(p.all_phones())[:3] or None,
        })

    return {
        "query": q,
        "exact": exact,
        "probable": probable,
        "possible": possible,
        "method": "normalized-name + alias + character-similarity blocking",
    }


# ---------------------------------------------------------------------------
# Identifier-reuse detection
# ---------------------------------------------------------------------------
def detect_identifier_reuse(db: Session) -> list[IntegrityAlert]:
    """Find hash identifiers shared by >1 distinct entity (excluding names).

    Identifier reuse is surfaced as an *alert with possible explanations*, never
    as an automatic accusation. A single shared-phone occurrence stays a LOW
    alert; repeated signals bump it higher.
    """
    from sqlalchemy.sql import func as safunc

    rows = (
        db.query(IdentityIdentifier.identifier_type, IdentityIdentifier.value_hash,
                 safunc.count(safunc.distinct(IdentityIdentifier.entity_id)).label("n"),
                 safunc.min(IdentityIdentifier.observed_at).label("first_seen"),
                 safunc.max(IdentityIdentifier.observed_at).label("last_seen"))
        .filter(IdentityIdentifier.identifier_type != "name")
        .group_by(IdentityIdentifier.identifier_type, IdentityIdentifier.value_hash)
        .having(safunc.count(safunc.distinct(IdentityIdentifier.entity_id)) > 1)
        .all()
    )

    alerts: list[IntegrityAlert] = []
    for id_type, value_hash, n, first_seen, last_seen in rows:
        recs = (
            db.query(IdentityIdentifier)
            .filter(
                IdentityIdentifier.identifier_type == id_type,
                IdentityIdentifier.value_hash == value_hash,
            )
        .all()
        )
        display = recs[0].display_value if recs else None
        entities = {(r.entity_type, str(r.entity_id)) for r in recs}
        severity = SEVERITY_MEDIUM if len(entities) >= 2 else SEVERITY_LOW
        gkey = f"{ALERT_IDENTIFIER_REUSE}:{id_type}:{value_hash}"
        alert = IntegrityAlert(
            alert_type=ALERT_IDENTIFIER_REUSE,
            severity=severity,
            identifier_type=id_type,
            value_hash=value_hash,
            display_value=display,
            confidence=min(0.5 + 0.1 * (len(entities) - 1), 0.9),
            description=(
                f"{id_type} reused by {len(entities)} distinct entities — "
                "possible explanations: shared family number, reassigned number, "
                "data-entry error, proxy/associate use, identifier reuse."
            ),
            grouping_key=gkey,
            observation_count=len(entities),
            source_summary={
                "identifier_type": id_type,
                "entities": [{"entity_type": t, "entity_id": i} for t, i in sorted(entities)],
                "first_seen": first_seen.isoformat() if first_seen else None,
                "last_seen": last_seen.isoformat() if last_seen else None,
            },
        )
        db.add(alert)
        alerts.append(alert)
    db.flush()
    return alerts


# ---------------------------------------------------------------------------
# Data-integrity dashboard
# ---------------------------------------------------------------------------
def integrity_summary(db: Session) -> dict[str, int]:
    """Aggregate counts for the DATA INTEGRITY dashboard."""
    from sqlalchemy.sql import func as safunc
    open_alerts = db.query(IntegrityAlert).filter(IntegrityAlert.status == "open")
    by_type = dict(
        open_alerts.with_entities(
            IntegrityAlert.alert_type, safunc.count(IntegrityAlert.id)
        ).group_by(IntegrityAlert.alert_type).all()
    )
    critical = (
        db.query(IntegrityAlert).filter(
            IntegrityAlert.status == "open",
            IntegrityAlert.severity == SEVERITY_CRITICAL,
        ).count()
    )
    total_open = open_alerts.count()
    total_records = db.query(Criminal).count() + db.query(Victim).count()

    return {
        "records_analyzed": total_records,
        "possible_duplicates": by_type.get(ALERT_DUPLICATE, 0),
        "identity_conflicts": by_type.get(ALERT_CONFLICT, 0),
        "identifier_reuse_alerts": by_type.get(ALERT_IDENTIFIER_REUSE, 0),
        "possible_aliases": by_type.get(ALERT_ALIAS, 0),
        "possible_proxy_relationships": by_type.get(ALERT_PROXY, 0) + by_type.get(ALERT_DUPLICATE_RECORD, 0),
        "critical_reviews": critical,
        "open_reviews": total_open,
    }


# ---------------------------------------------------------------------------
# Exposed small helpers for reuse by the rules engine / routes
# ---------------------------------------------------------------------------
def weight_config(overrides: dict[str, int] | None = None) -> dict[str, int]:
    if not overrides:
        return dict(ID_WEIGHTS)
    merged = dict(ID_WEIGHTS)
    merged.update({k: int(v) for k, v in overrides.items() if k in merged})
    return merged


def build_identity_graph(db: Session, center_type: str | None = None, center_id=None) -> dict[str, Any]:
    """Build the identity graph (entity→identity nodes) for visualization."""
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    rels = (
        db.query(IdentityRelationship)
        .filter(IdentityRelationship.status == REL_STATUS_OPEN)
        .order_by(IdentityRelationship.confidence.desc())
        .all()
    )

    profiles = build_entity_profiles(db)
    by_key = {(p.entity_type, str(p.entity_id)): p for p in profiles}

    def _ensure_node(entity_type: str, entity_id) -> dict:
        key = f"{entity_type}:{entity_id}"
        if key in nodes:
            return nodes[key]
        p = by_key.get((entity_type, str(entity_id)))
        aliases = []
        for a in db.query(IdentityAlias).filter(
                IdentityAlias.entity_type == entity_type,
                IdentityAlias.entity_id == entity_id).all():
            aliases.append(a.alias_name)
        ids = [
            {"type": i.identifier_type, "display": i.display_value}
            for i in db.query(IdentityIdentifier).filter(
                IdentityIdentifier.entity_type == entity_type,
                IdentityIdentifier.entity_id == entity_id,
                IdentityIdentifier.identifier_type != "name",
            ).limit(10).all()
        ]
        node = {
            "id": key,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "name": p.name if p else "unknown",
            "aliases": aliases,
            "identifiers": ids,
        }
        nodes[key] = node
        return node

    rel_count = 0
    for r in rels:
        if rel_count > 200:
            break
        src = _ensure_node(r.source_entity_type, r.source_entity_id)
        tgt = _ensure_node(r.target_entity_type, r.target_entity_id)
        edges.append({
            "source": src["id"],
            "target": tgt["id"],
            "relationship_type": r.relationship_type,
            "relationship_id": str(r.id),
            "confidence": r.confidence,
            "assessment": r.assessment,
            "evidence_count": r.evidence_summary.get("supporting_count", 0) if r.evidence_summary else 0,
            "status": r.status,
        })
        rel_count += 1

    return {"nodes": list(nodes.values()), "edges": edges}


def get_relationship_detail(db: Session, relationship_id: uuid.UUID) -> dict[str, Any] | None:
    rel = db.query(IdentityRelationship).filter(IdentityRelationship.id == relationship_id).first()
    if rel is None:
        return None
    profiles = build_entity_profiles(db)
    by_key = {(p.entity_type, str(p.entity_id)): p for p in profiles}
    source = by_key.get((rel.source_entity_type, str(rel.source_entity_id)))
    target = by_key.get((rel.target_entity_type, str(rel.target_entity_id)))
    evidence = db.query(IdentityEvidence).filter(
        IdentityEvidence.relationship_id == rel.id).order_by(IdentityEvidence.weight_delta.desc()).all()
    conflicts = db.query(IdentityConflict).filter(IdentityConflict.relationship_id == rel.id).all()

    import json
    return json.loads(json.dumps({
        "id": str(rel.id),
        "source_entity_type": rel.source_entity_type,
        "source_entity_id": str(rel.source_entity_id),
        "target_entity_type": rel.target_entity_type,
        "target_entity_id": str(rel.target_entity_id),
        "source": {
            "entity_type": rel.source_entity_type,
            "entity_id": str(rel.source_entity_id),
            "name": source.name if source else None,
        },
        "target": {
            "entity_type": rel.target_entity_type,
            "entity_id": str(rel.target_entity_id),
            "name": target.name if target else None,
        },
        "relationship_type": rel.relationship_type,
        "assessment": rel.assessment,
        "confidence": rel.confidence,
        "confidence_breakdown": rel.confidence_breakdown,
        "evidence_summary": rel.evidence_summary,
        "status": rel.status,
        "valid_from": rel.valid_from.isoformat() if rel.valid_from else None,
        "valid_to": rel.valid_to.isoformat() if rel.valid_to else None,
        "reviewed_at": rel.reviewed_at.isoformat() if rel.reviewed_at else None,
        "review_decision": rel.review_decision,
        "review_note": rel.review_note,
        "evidence": [
            {
                "id": str(e.id),
                "evidence_group": e.evidence_group,
                "signal_type": e.signal_type,
                "weight_delta": e.weight_delta,
                "confidence": e.confidence,
                "severity": e.severity,
                "source_label": e.source_label,
                "description": e.description,
                "observed_at": e.observed_at.isoformat() if e.observed_at else None,
                "time_range": e.time_range,
                "is_counter_evidence": e.is_counter_evidence,
            } for e in evidence
        ],
        "conflicts": [
            {
                "id": str(c.id),
                "attribute": c.attribute,
                "value_a": c.value_a,
                "value_b": c.value_b,
                "severity": c.severity,
                "explanation": c.explanation,
            } for c in conflicts
        ],
    }))
