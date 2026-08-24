"""Semantic modus-operandi (MO) search and NER extraction over case narratives.

Closes gap M6: MO handling was previously substring ILIKE matching, so
similar-meaning text never matched. This module builds lightweight *semantic*
embeddings with scikit-learn (already a project dependency — no new deps):

- TF-IDF over word 1-2 grams plus sublinear tf (robust free-text handling),
- Latent Semantic Analysis via ``TruncatedSVD`` projecting into a dense
  latent space where paraphrases land close together,
- cosine-similarity kNN retrieval over criminals, cases, and FIR narratives.

Also provides a rule-based NER extractor for investigative entities
(vehicle plates, phones, weapons, places, dates/times, money) over free text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.fir import FIR

# ---------------------------------------------------------------------------
# Corpus assembly
# ---------------------------------------------------------------------------

@dataclass
class SemanticDocument:
    doc_id: str
    kind: str            # criminal / crime_case / fir
    title: str
    text: str
    meta: dict[str, Any] = field(default_factory=dict)


def build_corpus(db: Session) -> list[SemanticDocument]:
    docs: list[SemanticDocument] = []
    for criminal in db.query(Criminal).all():
        text = " ".join(filter(None, [criminal.mo_summary, criminal.aliases]))
        if text.strip():
            docs.append(SemanticDocument(
                doc_id=f"criminal-{criminal.id}", kind="criminal", title=criminal.full_name,
                text=text, meta={"status": criminal.status},
            ))
    for case in db.query(CrimeCase).all():
        text = " ".join(filter(None, [case.description, case.mo_tags]))
        if text.strip():
            docs.append(SemanticDocument(
                doc_id=f"crime_case-{case.id}", kind="crime_case", title=case.case_number,
                text=text, meta={"status": case.status},
            ))
    for fir in db.query(FIR).all():
        if (fir.narrative or "").strip() or (fir.sections or "").strip():
            docs.append(SemanticDocument(
                doc_id=f"fir-{fir.id}", kind="fir", title=fir.fir_number,
                text=" ".join(filter(None, [fir.narrative, fir.sections])),
                meta={"status": fir.status},
            ))
    return docs


# ---------------------------------------------------------------------------
# Embeddings (TF-IDF -> LSA) with cached fitted transformers
# ---------------------------------------------------------------------------

@dataclass
class SemanticIndex:
    documents: list[SemanticDocument]
    vectorizer: Any
    svd: Any | None
    matrix: Any                 # L2-normalized document vectors (cosine-ready)
    n_components: int


def _sklearn_modules():
    try:
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.preprocessing import normalize
    except ImportError:  # pragma: no cover - sklearn is a project dependency
        return None
    return TruncatedSVD, TfidfVectorizer, normalize


def build_semantic_index(documents: list[SemanticDocument]) -> SemanticIndex | None:
    modules = _sklearn_modules()
    if modules is None or not documents:
        return None
    TruncatedSVD, TfidfVectorizer, _normalize = modules

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    tfidf_matrix = vectorizer.fit_transform([doc.text for doc in documents])

    n_components = max(2, min(64, len(documents) - 1, tfidf_matrix.shape[1]))
    if n_components < tfidf_matrix.shape[1]:
        svd = TruncatedSVD(n_components=n_components, random_state=42)
        reduced = svd.fit_transform(tfidf_matrix)
    else:
        svd = None
        reduced = tfidf_matrix.toarray()

    from sklearn.preprocessing import normalize
    normalized = normalize(reduced)
    return SemanticIndex(
        documents=documents, vectorizer=vectorizer, svd=svd,
        matrix=normalized, n_components=int(n_components),
    )


_INDEX_CACHE: dict[str, tuple[int, SemanticIndex | None]] = {}


def get_or_build_index(db: Session) -> SemanticIndex | None:
    """Cached index keyed by corpus size so it rebuilds as records are added."""
    documents = build_corpus(db)
    cached = _INDEX_CACHE.get("mo_semantic")
    if cached and cached[0] == len(documents):
        return cached[1]
    index = build_semantic_index(documents)
    _INDEX_CACHE["mo_semantic"] = (len(documents), index)
    return index


def invalidate_semantic_index() -> None:
    """Force a rebuild on next use (call after bulk imports/updates)."""
    _INDEX_CACHE.pop("mo_semantic", None)


def semantic_search(index: SemanticIndex, query: str, top_k: int = 10) -> list[dict[str, Any]]:
    """kNN cosine search of an already-fitted index; query is transformed, never re-fit."""
    from sklearn.preprocessing import normalize

    query_tfidf = index.vectorizer.transform([query])
    query_reduced = index.svd.transform(query_tfidf) if index.svd is not None else query_tfidf.toarray()
    query_norm = normalize(query_reduced)

    scores = (index.matrix @ query_norm.T).ravel()
    order = scores.argsort()[::-1][:top_k]

    results = []
    for position in order:
        score = float(scores[position])
        if score <= 0:
            continue
        doc = index.documents[int(position)]
        results.append({
            "doc_id": doc.doc_id,
            "kind": doc.kind,
            "title": doc.title,
            "similarity": round(score, 4),
            "excerpt": doc.text[:220],
            "meta": doc.meta,
        })
    return results


def search_similar_mo(
    db: Session,
    query: str,
    top_k: int = 10,
    kinds: list[str] | None = None,
) -> dict[str, Any]:
    """Public API: semantic similarity search over MO summaries and narratives.

    Falls back to substring matching when scikit-learn is unavailable so the
    endpoint never hard-fails.
    """
    documents = build_corpus(db)
    if kinds:
        wanted = set(kinds)
        documents = [d for d in documents if d.kind in wanted]
        # Kind-restricted queries always build a fresh, small index (cheap).
        index = build_semantic_index(documents)
    else:
        index = get_or_build_index(db)

    matches: list[dict[str, Any]]
    method = "substring_fallback"
    if index is not None:
        matches = semantic_search(index, query, top_k=top_k)
        method = (
            f"tfidf_word_1_2gram+lsa_svd_{index.n_components}c cosine"
            if index.svd is not None else "tfidf_word_1_2gram cosine"
        )
    else:
        needle = query.lower()
        matches = [
            {"doc_id": d.doc_id, "kind": d.kind, "title": d.title, "similarity": None,
             "excerpt": d.text[:220], "meta": d.meta}
            for d in documents if needle in d.text.lower()
        ][:top_k]

    return {
        "query": query,
        "corpus_size": len(documents),
        "embedding_method": method,
        "results": matches,
    }


# ---------------------------------------------------------------------------
# Rule-based NER extraction over free-text narratives
# ---------------------------------------------------------------------------

_VEHICLE_PLATE = re.compile(r"\bKA[-\s]?\d{1,2}[-\s]?[A-Z]{1,3}[-\s]?\d{3,4}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)")
_MONEY = re.compile(r"Rs\.?\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:lakh|crore|crores|lakhs))?|\b\d[\d,]+\s?(?:rupees|rs)\b", re.IGNORECASE)
_DATE = re.compile(
    r"\b(?:\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{4})?)\b",
    re.IGNORECASE,
)
_TIME = re.compile(r"\b(?:[01]?\d|2[0-3])[:.][0-5]\d\s?(?:am|pm|AM|PM)?\b")
_WEAPON_KEYWORDS = [
    "knife", "pistol", "revolver", "gun", "firearm", "country-made pistol", "machete",
    "sword", "stick", "rod", "iron rod", "blade", "rifle", "ammunition", "explosive",
]
_DRUG_KEYWORDS = ["ganja", "mdMA", "md", "heroin", "opium", "cocaine", "narcotic", "peddling"]
_DISTRICT_HINTS = [
    "Bengaluru", "Bangalore", "Mysuru", "Mangaluru", "Belagavi", "Ballari", "Kalaburagi",
    "Hassan", "Tumkuru", "Dharwad", "Whitefield", "KR Puram", "Hubli",
]
_PERSON_TITLE = re.compile(r"\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Sri\.?|Smt\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})")


def extract_entities(text: str) -> dict[str, Any]:
    """Rule-based named-entity extraction tuned for Indian police narratives."""
    entities: dict[str, list[str]] = {
        "vehicle_plates": sorted({m.group(0).upper().replace(" ", "-") for m in _VEHICLE_PLATE.finditer(text)}),
        "phone_numbers": sorted({m.group(0).replace("-", "").replace(" ", "") for m in _PHONE.finditer(text)}),
        "money_amounts": sorted({m.group(0).strip() for m in _MONEY.finditer(text)}),
        "dates": sorted({m.group(0) for m in _DATE.finditer(text)}),
        "times": sorted({m.group(0).replace(".", ":") for m in _TIME.finditer(text)}),
        "weapons": sorted({w for w in _WEAPON_KEYWORDS if w in text.lower()}),
        "controlled_substances": sorted({d for d in _DRUG_KEYWORDS if d.lower() in text.lower()}),
        "places": sorted({p for p in _DISTRICT_HINTS if p.lower() in text.lower()}),
        "person_names": [],
    }
    seen_names: set[str] = set()
    for match in _PERSON_TITLE.finditer(text):
        name = match.group(1).strip()
        if name not in seen_names:
            seen_names.add(name)
            entities["person_names"].append(name)
    total = sum(len(v) for v in entities.values())
    return {
        "entities": entities,
        "entity_count": total,
        "method": "rule_based_regex+gazetteer (no external NLP model required)",
        "note": "Person names are extracted via honorific patterns; add spaCy NER later for deeper coverage.",
    }


def extract_case_entities(db: Session, case_id: str) -> dict[str, Any] | None:
    """Extract entities from a case's description/MO tags and its linked FIR narratives."""
    import uuid as uuid_mod

    try:
        case_uuid = uuid_mod.UUID(case_id)
    except ValueError:
        return None
    case = db.query(CrimeCase).filter(CrimeCase.id == case_uuid).first()
    if case is None:
        return None

    combined_text = " \n".join(filter(None, [case.description, case.mo_tags]))
    for fir in case.firs:
        combined_text += "\n" + (fir.narrative or "")
    extraction = extract_entities(combined_text)
    return {
        "case_id": str(case.id),
        "case_number": case.case_number,
        **extraction,
    }
