"""Modus-operandi normalization, backfill, and recurring-pattern detection.

Issue #144 gaps:

- 132.1 ``sync_mo_tags``          backfills the denormalized legacy fields
                                  (``crime_cases.mo_tags`` CSV string,
                                  ``criminals.mo_summary`` free text) into the
                                  normalized ``mo_tags`` / ``case_mo_tags`` /
                                  ``criminal_mo_tags`` relations. Idempotent.
- 132.2 ``detect_recurring_mo_patterns``
                                  groups cases and criminals whose normalized
                                  MO signatures overlap (Jaccard similarity +
                                  union-find), producing repeat-pattern
                                  intelligence reports.

The lexicon maps free-text MO phrases to a small canonical tag vocabulary so
similarity is computed on comparable units instead of raw strings.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.mo_tag import CaseMOTag, CriminalMOTag, MOTag


# ---------------------------------------------------------------------------
# Canonical MO lexicon (132.1)
# ---------------------------------------------------------------------------

# Canonical tag -> list of case-insensitive regexes matching free-text MO.
MO_LEXICON: dict[str, list[str]] = {
    "night_operation": [r"\blate[\s-]?night\b", r"\bmidnight\b", r"\bnight\s+(?:patrol|transport|operation|residential|mineral)\b", r"\bat night\b"],
    "break_in": [r"\bburglar\w*\b", r"\bbreak[\s-]?in\b", r"\bhousebreak\w*\b", r"\block\s+break\b", r"\bbalcony\s+entry\b", r"\bsmart\s+lock\b"],
    "tool_usage": [r"\bcrowbar\b", r"\bpower\s+tools\b", r"\biron\s+rod\b", r"\bcountry[\s-]made\s+(?:pistol|gun|firearm|rifle)\w*\b", r"\bknives?\b", r"\bmachete\b", r"\bsickle\b"],
    "phishing_portal_fraud": [r"\bphishing\b", r"\bfake\s+(?:banking\s+portal|customer\s+care|merchant|qr|payment\s+portal|fishing\s+license\s+portal|biometric\s+login)\b", r"\bupi\s+fraud\b", r"\bonline\s+ticket\s+booking\s+scam\b"],
    "call_spoofing": [r"\bspoofing\b"],
    "money_mule_routing": [r"\bmule\b", r"\bhawala\b"],
    "crypto_fraud": [r"\bcrypto\w*\b", r"\bbitcoin\b"],
    "extortion": [r"\bextortion\b", r"\bblackmail\b", r"\bmicro-lending\b"],
    "online_marketplace_scam": [r"\bexchange\s+scam\b", r"\be-commerce\b"],
    "drug_courier": [r"\bdrug\s+courier?\b", r"\bcourier\s+via\b", r"\bsupply\s+chain\b", r"\bdistribution\s+network\b", r"\bdelivery\s+via\b"],
    "synthetic_drugs": [r"\bmdma\b", r"\bsynthetic\s+drug\w*\b", r"\becstasy\b", r"\bpharmaceutical\s+drug\b"],
    "cannabis_supply": [r"\bganja\b", r"\bcannabis\b", r"\bmarijuana\b"],
    "illicit_liquor": [r"\billicit\s+(?:liquor|arrac)\w*\b", r"\barrac\w*\b", r"\bdistillery\b"],
    "illegal_mining": [r"\billegal\s+mining\b", r"\bsand\s+mining\b", r"\bmineral\s+transport\b", r"\bgranite\s+quarry\b", r"\biron\s+ore\b", r"\bweighbridge\b", r"\bquarry\b"],
    "timber_smuggling": [r"\btimber\b"],
    "cross_border_smuggling": [r"\bsmuggl\w+\b", r"\bcontraband\b", r"\bharbor\s+handoff\b", r"\bcross-border\b", r"\bvia\s+fishing\s+boats\b"],
    "forged_documents": [r"\bforged?\b", r"\bforgery\b", r"\bfake\s+(?:identity|documents?|manifests?|deed|title|records?|clearance)\b", r"\bforged\s+\w+\b"],
    "witness_intimidation": [r"\bwitness\s+intimidation\b", r"\bintimidation\b"],
    "land_encroachment": [r"\bencroachment\b", r"\btemple\s+land\b", r"\bland\s+dispute\b", r"\bboundary\s+dispute\b", r"\bancestral\s+land\b", r"\bsurvey\b"],
    "repeat_domestic_assault": [r"\brepeat\s+(?:domestic|household)\b", r"\bdowry\s+harassment\b"],
    "road_rage": [r"\broad\s+rage\b"],
    "violent_assault": [r"\bassault\w*\b", r"\baltercation\b", r"\bviolence\b"],
    "jewellery_targeting": [r"\bjewell?ery\b", r"\bgold\s+chain\b"],
    "vehicle_crime": [r"\bhijack\w*\b", r"\bvehicle\s+theft\b", r"\bscooter\s+reconnaissance\b", r"\brobbery\s+attempt\b", r"\bcargo\s+truck\b", r"\bstolen\s+(?:motorcycle|scooter|bike|two[\s-]wheeler|car|vehicle)\b", r"\bgetaway\s+vehicle\b"],
    "reconnaissance": [r"\breconnaissance\b", r"\bscouting\b", r"\bsurveillance\b"],
    "coordinated_group": [r"\bring\b", r"\bnetwork\b", r"\bgang\b", r"\bunit\s+raided\b", r"\bconvoy\b", r"\bmanufacturing\s+unit\b"],
    "dead_drop": [r"\bdead\s+drop\b"],
    "dark_web": [r"\bdark\s+web\b", r"\bdarknet\b"],
    "temple_theft": [r"\btemple\s+hundi\b", r"\btreasury\s+theft\b", r"\bsanctum\b"],
    "gps_evasion": [r"\bgps\s+track\w*\b", r"\btrackers?\s+removed\b"],
}

_COMPILED_LEXICON: dict[str, list[re.Pattern[str]]] = {
    tag: [re.compile(rx, re.IGNORECASE) for rx in patterns]
    for tag, patterns in MO_LEXICON.items()
}

WEAPON_TAG_NAMES = {"tool_usage"}
VEHICLE_TAG_NAMES = {"vehicle_crime", "gps_evasion"}
NIGHT_TAG_NAMES = {"night_operation"}

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def tags_for_text(text: str | None) -> set[str]:
    """Return canonical MO tags whose regexes match *text*."""
    if not text:
        return set()
    return {
        tag
        for tag, patterns in _COMPILED_LEXICON.items()
        if any(pattern.search(text) for pattern in patterns)
    }


def slugify_phrase(phrase: str) -> str | None:
    """Normalize an unmatched free-text phrase into a safe tag name."""
    slug = _SLUG_RE.sub("_", phrase.lower()).strip("_")[:120]
    return slug if len(slug) >= 4 else None


def tags_for_case_text(case: CrimeCase) -> set[str]:
    """Tags derivable from one case: explicit CSV field plus description."""
    tags: set[str] = set()
    if case.mo_tags:
        for phrase in case.mo_tags.split(","):
            phrase = phrase.strip()
            if not phrase:
                continue
            matched = tags_for_text(phrase)
            if matched:
                tags.update(matched)
            else:
                slug = slugify_phrase(phrase)
                if slug:
                    tags.add(slug)
    if not tags:
        tags.update(tags_for_text(case.description))
    return tags


def numeric_mo_features(text: str | None) -> dict[str, float]:
    """Scalar MO indicators for ML feature vectors (issue #144 gap 132.3)."""
    tags = tags_for_text(text)
    return {
        "mo_tag_count": float(len(tags)),
        "mo_night_flag": 1.0 if tags & NIGHT_TAG_NAMES else 0.0,
        "mo_weapon_flag": 1.0 if tags & WEAPON_TAG_NAMES else 0.0,
        "mo_vehicle_flag": 1.0 if tags & VEHICLE_TAG_NAMES else 0.0,
    }


# ---------------------------------------------------------------------------
# Backfill: legacy fields -> normalized relations (132.1)
# ---------------------------------------------------------------------------

def sync_mo_tags(db: Session) -> dict[str, int]:
    """Backfill normalized MO tables from legacy fields. Idempotent.

    Returns a stats dict describing what was created/skipped so callers
    (seed, admin route) can log the outcome.
    """
    stats = {
        "cases_scanned": 0,
        "criminals_scanned": 0,
        "tags_created": 0,
        "case_links_created": 0,
        "criminal_links_created": 0,
        "already_synced": 0,
    }

    tag_cache: dict[str, MOTag] = {tag.name: tag for tag in db.query(MOTag).all()}

    def ensure_tag(name: str) -> MOTag:
        tag = tag_cache.get(name)
        if tag is None:
            tag = MOTag(name=name)
            db.add(tag)
            db.flush()
            tag_cache[name] = tag
            stats["tags_created"] += 1
        return tag

    existing_case_links = {(link.case_id, link.mo_tag_id) for link in db.query(CaseMOTag).all()}
    existing_criminal_links = {(link.criminal_id, link.mo_tag_id) for link in db.query(CriminalMOTag).all()}

    for case in db.query(CrimeCase).all():
        stats["cases_scanned"] += 1
        for name in sorted(tags_for_case_text(case)):
            tag = ensure_tag(name)
            key = (case.id, tag.id)
            if key in existing_case_links:
                stats["already_synced"] += 1
                continue
            db.add(CaseMOTag(case_id=case.id, mo_tag_id=tag.id))
            existing_case_links.add(key)
            stats["case_links_created"] += 1

    for criminal in db.query(Criminal).all():
        stats["criminals_scanned"] += 1
        for name in sorted(tags_for_text(criminal.mo_summary)):
            tag = ensure_tag(name)
            key = (criminal.id, tag.id)
            if key in existing_criminal_links:
                stats["already_synced"] += 1
                continue
            db.add(CriminalMOTag(criminal_id=criminal.id, mo_tag_id=tag.id))
            existing_criminal_links.add(key)
            stats["criminal_links_created"] += 1

    db.commit()
    return stats


def entity_tag_map(db: Session) -> tuple[dict[uuid.UUID, set[str]], dict[uuid.UUID, set[str]]]:
    """Normalized tag sets keyed by case id / criminal id (empty side omitted)."""
    case_tags: dict[uuid.UUID, set[str]] = {}
    for case_id, tag_name in (
        db.query(CaseMOTag.case_id, MOTag.name).join(MOTag, CaseMOTag.mo_tag_id == MOTag.id).all()
    ):
        case_tags.setdefault(case_id, set()).add(tag_name)

    criminal_tags: dict[uuid.UUID, set[str]] = {}
    for criminal_id, tag_name in (
        db.query(CriminalMOTag.criminal_id, MOTag.name)
        .join(MOTag, CriminalMOTag.mo_tag_id == MOTag.id)
        .all()
    ):
        criminal_tags.setdefault(criminal_id, set()).add(tag_name)

    return case_tags, criminal_tags


# ---------------------------------------------------------------------------
# Recurring-MO pattern detection (132.2)
# ---------------------------------------------------------------------------

_JACCARD_THRESHOLD = 0.34
_MIN_SHARED_TAGS = 2
_PEAK_WINDOWS = (
    ("00:00-06:00", range(0, 6)),
    ("06:00-12:00", range(6, 12)),
    ("12:00-18:00", range(12, 18)),
    ("18:00-24:00", range(18, 24)),
)


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[Any, Any] = {}

    def find(self, item: Any) -> Any:
        self.parent.setdefault(item, item)
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != root:  # path compression
            self.parent[item], item = root, self.parent[item]
        return root

    def union(self, a: Any, b: Any) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def groups(self) -> dict[Any, list[Any]]:
        out: dict[Any, list[Any]] = {}
        for item in self.parent:
            out.setdefault(self.find(item), []).append(item)
        return out


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    if not intersection:
        return 0.0
    return intersection / len(a | b)


def _linked(tags_a: set[str], tags_b: set[str]) -> bool:
    shared = tags_a & tags_b
    return len(shared) >= _MIN_SHARED_TAGS or _jaccard(tags_a, tags_b) >= _JACCARD_THRESHOLD


def detect_recurring_mo_patterns(
    db: Session,
    min_support: int = 2,
    max_patterns: int = 10,
) -> dict[str, Any]:
    """Group cases and criminals with overlapping MO signatures (132.2).

    Entities are linked when they share at least two canonical MO tags or a
    Jaccard similarity >= 0.34; connected components (union-find) with at
    least ``min_support`` entities become reported patterns.

    Threat score heuristic (documented for explainability):
        min(100, 18*support + 12*criminal_count + 15*at_large_members
                + 8*len(shared_tags) + 10*violent_flag)
    """
    ensure_synced(db)

    case_tags, criminal_tags = entity_tag_map(db)
    cases = {case.id: case for case in db.query(CrimeCase).all() if case.id in case_tags}
    criminals = {
        criminal.id: criminal for criminal in db.query(Criminal).all() if criminal.id in criminal_tags
    }

    # Entity tuples: (key, kind, label, tags, payload)
    entities: list[tuple[Any, str, str, set[str], dict[str, Any]]] = []
    for case_id, case in cases.items():
        entities.append(
            (
                ("case", case_id),
                "case",
                case.case_number,
                case_tags[case_id],
                {
                    "status": case.status,
                    "district": case.location.district if case.location else None,
                    "category": case.category.name if case.category else None,
                    "occurred_at": case.occurred_at,
                    "narrative": (case.description or case.mo_tags or "").strip(),
                },
            )
        )
    for criminal_id, criminal in criminals.items():
        entities.append(
            (
                ("criminal", criminal_id),
                "criminal",
                criminal.full_name,
                criminal_tags[criminal_id],
                {
                    "status": criminal.status,
                    "gang": criminal.gang_affiliation,
                    "narrative": (criminal.mo_summary or "").strip(),
                },
            )
        )

    uf = _UnionFind()
    keys = [entity[0] for entity in entities]
    tags_by_key = {entity[0]: entity[3] for entity in entities}
    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            if _linked(entities[i][3], entities[j][3]):
                uf.union(keys[i], keys[j])

    by_root: dict[Any, list[int]] = {}
    for idx, entity in enumerate(entities):
        by_root.setdefault(uf.find(entity[0]), []).append(idx)

    patterns = []
    violent_tags = {"violent_assault", "road_rage", "repeat_domestic_assault"}
    for members_idx in by_root.values():
        if len(members_idx) < max(2, min_support):
            continue

        # Deterministic member order: richest MO signature first, then label.
        ordered = sorted(members_idx, key=lambda i: (-len(entities[i][3]), entities[i][2]))
        member_rows = []
        tag_counter: Counter[str] = Counter()
        categories: Counter[str] = Counter()
        districts: Counter[str] = Counter()
        hours: list[int] = []
        occurred: list[datetime] = []
        at_large = 0
        narrative_example = ""

        for idx in ordered:
            key, kind, label, tags, payload = entities[idx]
            member_rows.append({
                "kind": kind,
                "id": str(key[1]),
                "label": label,
                "status": payload.get("status"),
                "district": payload.get("district"),
            })
            tag_counter.update(tags)
            if kind == "case":
                if payload.get("category"):
                    categories[payload["category"]] += 1
                if payload.get("district"):
                    districts[payload["district"]] += 1
                if payload.get("occurred_at"):
                    occurred.append(payload["occurred_at"])
                    hours.append(payload["occurred_at"].hour)
                if payload.get("narrative") and not narrative_example:
                    narrative_example = payload["narrative"][:180]
            elif payload.get("status") == "at_large":
                at_large += 1

        shared_tags = [name for name, _count in tag_counter.most_common()]
        criminal_count = sum(1 for row in member_rows if row["kind"] == "criminal")
        support = len(member_rows)
        hour_counter = Counter(hours)
        block_counts = {label: sum(hour_counter[h] for h in rng) for label, rng in _PEAK_WINDOWS}
        peak_window = max(block_counts, key=block_counts.get) if any(hours) else None
        violent_flag = bool(set(shared_tags) & violent_tags)

        threat_score = int(min(
            100,
            18 * support
            + 12 * criminal_count
            + 15 * at_large
            + 8 * len(shared_tags[:5])
            + (10 if violent_flag else 0),
        ))

        patterns.append({
            "pattern_id": hashlib.sha1(
                "|".join(sorted(row["label"] for row in member_rows)).encode("utf-8")
            ).hexdigest()[:16],
            "support": support,
            "case_count": support - criminal_count,
            "criminal_count": criminal_count,
            "members": member_rows,
            "shared_tags": shared_tags,
            "dominant_category": categories.most_common(1)[0][0] if categories else None,
            "districts": sorted(districts),
            "first_occurred": min(occurred).isoformat() if occurred else None,
            "last_occurred": max(occurred).isoformat() if occurred else None,
            "peak_time_window": peak_window,
            "at_large_members": at_large,
            "threat_score": threat_score,
            "example_narrative": narrative_example,
        })

    patterns.sort(key=lambda p: (-p["threat_score"], -p["support"]))
    return {
        "patterns": patterns[:max_patterns],
        "total_patterns": len(patterns),
        "method": f"jaccard>={_JACCARD_THRESHOLD}_or_shared_tags>={_MIN_SHARED_TAGS}_union_find",
        "min_support": max(2, min_support),
        "entities_analysed": {"cases": len(case_tags), "criminals": len(criminal_tags)},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def shared_mo_tags(db: Session, criminal_a_id: uuid.UUID, criminal_b_id: uuid.UUID) -> list[str]:
    """Canonical MO tags two offenders have in common (used to enrich
    similar-offender matches, gap 132.3)."""
    def tags_for(cid: uuid.UUID) -> set[str]:
        return {
            name
            for name, in (
                db.query(MOTag.name)
                .join(CriminalMOTag, CriminalMOTag.mo_tag_id == MOTag.id)
                .filter(CriminalMOTag.criminal_id == cid)
                .all()
            )
        }

    return sorted(tags_for(criminal_a_id) & tags_for(criminal_b_id))


def mo_signature(db: Session, criminal_id: uuid.UUID) -> list[str]:
    """Canonical tag names for one offender."""
    return [
        name
        for name, in (
            db.query(MOTag.name)
            .join(CriminalMOTag, CriminalMOTag.mo_tag_id == MOTag.id)
            .filter(CriminalMOTag.criminal_id == criminal_id)
            .all()
        )
    ]


def ensure_synced(db: Session) -> None:
    """Lazily backfill normalized tables when still empty.

    Keeps detection working on databases seeded before the normalized
    relations existed. The emptiness check is a cheap indexed count, which
    stays correct across sessions/engines (unlike a process-global flag,
    which goes stale between test databases or worker processes).
    """
    if db.query(MOTag).count() > 0:
        return
    sync_mo_tags(db)
