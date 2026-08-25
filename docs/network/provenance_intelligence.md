# SAKSHA Network Intelligence: Provenance, Grounding & Evidence Verification Model

## 1. Overview & Core Mission

SAKSHA's Network Intelligence engine provides high-dimensional graph correlation and relational linkage analysis across criminal records, suspects, crime cases (FIRs), investigating officers, and incident jurisdictions.

To uphold strict evidentiary standards, **no relationship is ever fabricated or hallucinated**. Every node, relationship, and graph edge carries an immutable provenance metadata footprint, distinguishing direct database records from analytical inferences and demo training datasets.

---

## 2. Provenance Taxonomy

Every graph relationship (`NetworkEdge`) conforms to the following four-tier provenance model:

```
                      ┌───────────────────────────────────────┐
                      │          Source Data Origin           │
                      └──────────────────┬────────────────────┘
                                         │
       ┌───────────────────┬─────────────┴────────────┬────────────────────┐
       ▼                   ▼                          ▼                    ▼
┌──────────────┐   ┌────────────────┐         ┌───────────────┐     ┌─────────────┐
│DIRECT_DATABASE│  │ANALYTICAL_LEAD │         │   DEMO_SEED   │     │    MIXED    │
│  (Verified)  │   │  (Potential)   │         │ (Demo Origin) │     │(Live + Seed)│
└──────────────┘   └────────────────┘         └───────────────┘     └─────────────┘
```

| Source Code | Verification Status | Meaning & Legal Evidentiary Standing |
| :--- | :--- | :--- |
| `DIRECT_DATABASE` | `VERIFIED` | Explicitly recorded in database tables (e.g. Person accused in FIR, Officer assigned to case, Location of FIR). Direct database fact. |
| `ANALYTICAL_INFERENCE` | `POTENTIAL` | Multi-record deduction (e.g. Co-accused in shared FIR, repeat incident overlap). Marked as an **Investigative Lead**, not legal proof. |
| `DEMO_SEED` | `DEMO` | Seeded record originating from bundled training/demonstration fixtures (`seed_db.py`). |
| `MIXED` | `DEMO` | Relationship connecting a live operational record with a seed/demo record. |
| `UNKNOWN` | `UNVERIFIED` | Unresolvable lineage. Never silently upgraded to verified status. |

---

## 3. Relationship Types & Evidence Grounding

| Relationship Type | Source | Grounding Evidence Records |
| :--- | :--- | :--- |
| `PERSON_CASE` | `DIRECT_DATABASE` | FIR accused charge record (`FIRCriminalLink`), including sections and filing timestamp. |
| `PERSON_LOCATION` | `DIRECT_DATABASE` | Jurisdictional incident location of FIRs where the suspect is formally listed. |
| `CASE_LOCATION` | `DIRECT_DATABASE` | Primary station and district jurisdiction of the crime case. |
| `PERSON_INVESTIGATION`| `DIRECT_DATABASE` | Investigating Officer formal assignment in FIR record. |
| `PERSON_VICTIM` | `DIRECT_DATABASE` | Complainant/victim identity in formal FIR record (`FIRVictimLink`). |
| `SHARED_CASE` | `ANALYTICAL_INFERENCE` | List of all shared FIR numbers and charge sheets where entities are named together. |
| `GANG_ASSOCIATION` | `ANALYTICAL_INFERENCE` | Shared gang syndicate affiliation recorded across database profiles. |

---

## 4. Calculated Confidence Methodology

Confidence is never static or fabricated. It is calculated directly from corroborating evidence density:

1. **Direct Database Facts**: `1.0` (`100%`, `HIGH` confidence).
2. **Multi-Incident Co-Accused (2+ FIRs)**: 
   $$\text{Confidence} = \min(0.95, 0.70 + 0.08 \times N_{\text{shared FIRs}})$$
   Categorized as `HIGH` confidence.
3. **Single Incident Co-Accused (1 FIR)**: `0.70` (`70%`, `MEDIUM` confidence).
4. **Shared Modus Operandi / Location without direct shared FIR**: `0.50` (`50%`, `LOW` confidence).
5. **Unknown lineage**: `None` / `UNKNOWN`.

---

## 5. Mandatory Operational Lead Disclaimer

Whenever an edge has provenance `ANALYTICAL_INFERENCE` or verification status `POTENTIAL`, the engine attaches the mandatory advisory:

> **Analytical Lead Advisory**:
> *"Analytical relationship identified from available records. This does not establish a confirmed association."*

---

## 6. REST API Contract & Filtering

### `GET /api/v2/network/graph`
**Query Parameters**:
- `category_filter` *(optional)*: `suspect`, `offender`, `location`, `victim`, `case`, `officer`
- `min_risk` *(optional)*: Float `0.0` to `100.0`
- `provenance_filter` *(optional)*: `DIRECT_DATABASE`, `ANALYTICAL_INFERENCE`, `DEMO_SEED`, `MIXED`, `VERIFIED`, `POTENTIAL`
- `exclude_demo` *(optional)*: `true` / `false` (removes all demo-derived records for pure live intelligence)

**Response Schema (`NetworkGraphResponse`)**:
```json
{
  "nodes": [...],
  "edges": [
    {
      "source": "criminal-c001",
      "target": "criminal-c002",
      "relationship": "Co-accused in 2 FIRs",
      "relationship_type": "SHARED_CASE",
      "provenance": "ANALYTICAL_INFERENCE",
      "verification_status": "POTENTIAL",
      "confidence": 0.86,
      "confidence_level": "HIGH",
      "evidence": [
        {
          "record_type": "fir_co_accused",
          "record_number": "FIR-2026-102",
          "sections": "379, 457 IPC",
          "factors": ["Co-accused in formal FIR charge", "Shared FIR #FIR-2026-102"]
        }
      ],
      "is_demo_derived": false,
      "operational_warning": "Analytical relationship identified from available records. This does not establish a confirmed association."
    }
  ],
  "total_nodes": 24,
  "total_edges": 38,
  "is_neo4j_backed": false,
  "provenance_summary": {
    "total_nodes": 24,
    "total_edges": 38,
    "verified_relationships": 26,
    "analytical_relationships": 12,
    "potential_relationships": 12,
    "demo_relationships": 0,
    "mixed_relationships": 0,
    "unknown_relationships": 0
  }
}
```
