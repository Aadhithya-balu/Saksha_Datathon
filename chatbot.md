# Saksha AI Chatbot Architecture Redesign

## Current State Summary

The existing chatbot has critical gaps:
- **No LLM** -- answers are raw prompt template strings, never sent to an LLM
- **Hash-based vector store** -- SHA-256 slot hashing (exact word overlap only, no semantic understanding)
- **3 analytics documents only** -- the route handler builds just 3 docs (dashboard summary, districts, categories), ignoring the richer 150+ doc `rag_service.py`
- **No intent routing** -- trivial keyword matching (4 categories)
- **No entity extraction** -- token splitting
- **No conversation memory** -- `session_id` accepted but never used
- **No backend service integration** -- no Neo4j graph queries, no ML predictions, no FIR/criminal/evidence lookups
- **Dead code** -- `chat_service.py` (with NDJSON streaming) is never called from any route
- **Streaming not consumed** -- frontend calls `/query` (synchronous), ignores NDJSON

---

## Proposed Architecture

```
User Query
    |
React AIChat (streaming NDJSON consumer)
    |
FastAPI POST /api/v1/ai/chat
    |
+-----------------------------------+
|       AI Orchestrator             |
|  (orchestrator.py)                |
|                                   |
|  1. Intent Router                 |
|     (intent_router.py)            |
|                                   |
|  2. Entity Extractor              |
|     (entity_extractor.py)         |
|                                   |
|  3. Query Planner                 |
|     (query_planner.py)            |
|                                   |
|  4. Backend Fetcher               |
|     (backend_fetcher.py)          |
|     +--------+--------+--------+ |
|     |Postgres| Neo4j  |ML Svc  | |
|     +--------+--------+--------+ |
|                                   |
|  5. Context Builder               |
|     (context_builder.py)          |
|                                   |
|  6. LLM Generator                 |
|     (llm_generator.py)            |
|                                   |
|  7. Response Validator            |
|     (response_validator.py)       |
+-----------------------------------+
    |
Streaming NDJSON -> React UI
```

---

## File Plan (13 new files, 5 modified files)

### New Backend Files

| # | File | Purpose |
|---|---|---|
| 1 | `backend/app/ai/chat/__init__.py` | Package init |
| 2 | `backend/app/ai/chat/intent_router.py` | Rule-based intent detection (12 intents) |
| 3 | `backend/app/ai/chat/entity_extractor.py` | Regex + heuristic entity extraction |
| 4 | `backend/app/ai/chat/query_planner.py` | Decides which backend services to call |
| 5 | `backend/app/ai/chat/backend_fetcher.py` | Executes backend calls (Postgres, Neo4j, ML) |
| 6 | `backend/app/ai/chat/context_builder.py` | Merges retrieved data into structured LLM context |
| 7 | `backend/app/ai/chat/llm_generator.py` | Calls Gemini API with context + streams response |
| 8 | `backend/app/ai/chat/response_validator.py` | Validates no hallucination in output |
| 9 | `backend/app/ai/chat/orchestrator.py` | Main orchestrator tying all components together |
| 10 | `backend/app/ai/chat/memory.py` | In-memory session conversation history |

### Modified Files

| # | File | Change |
|---|---|---|
| 11 | `backend/app/routes/ai_chat.py` | Replace `_assistant_response` with orchestrator, add streaming |
| 12 | `backend/app/core/config.py` | Add `GEMINI_API_KEY` / `OPENAI_API_KEY` settings |
| 13 | `backend/requirements.txt` | Add `google-generativeai` or use raw HTTP (httpx already present) |
| 14 | `datathon/src/services/api.ts` | Add streaming chat function + types |
| 15 | `datathon/src/pages/AIChat.tsx` | Consume NDJSON streaming, show intent/entity badges |

---

## Component Details

### 1. Intent Router (`intent_router.py`)

**Strategy**: Rule-based keyword + pattern matching (no external model dependency). Uses weighted keyword sets, regex patterns, and phrase detection.

```python
class Intent(Enum):
    FIR_LOOKUP = "fir_lookup"
    CASE_DETAILS = "case_details"
    CRIMINAL_HISTORY = "criminal_history"
    OFFICER_INFO = "officer_info"
    CRIME_STATISTICS = "crime_statistics"
    HOTSPOT_ANALYSIS = "hotspot_analysis"
    CRIMINAL_NETWORK = "criminal_network"
    SIMILAR_CASES = "similar_cases"
    PREDICTIONS = "predictions"
    NOTIFICATIONS = "notifications"
    DASHBOARD_ANALYTICS = "dashboard_analytics"
    GENERAL = "general"
```

Detection approach:
- Each intent has a keyword set + optional regex patterns
- Score accumulated per intent; highest score wins
- Threshold check to reject ambiguous queries
- Multi-intent detection for compound queries (e.g., "show FIR 104 and who is connected to the accused" -> FIR_LOOKUP + CRIMINAL_NETWORK)

### 2. Entity Extractor (`entity_extractor.py`)

Extracts structured entities using regex patterns:

| Entity | Pattern Example |
|---|---|
| Case ID | `CR-2026-\d+`, UUID pattern |
| FIR Number | `FIR\s*\d+/\d+`, `\d{4}/\d+` |
| Person Name | Capitalized multi-word phrases after keywords ("of", "named", "accused") |
| District | Match against known Karnataka districts list |
| Police Station | Match against known stations list |
| Crime Category | Match against 8 seeded categories |
| Date | `DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD` |
| Vehicle Number | `KA-\d{2}-[A-Z]-\d{4}` pattern |
| Phone Number | `+91 \d{5}-\d{5}`, `10-digit` patterns |

### 3. Query Planner (`query_planner.py`)

Given intent + entities, produces a `QueryPlan`:

```python
@dataclass
class QueryPlan:
    intents: list[Intent]
    entities: dict[str, Any]
    backend_calls: list[BackendCall]
    parallel: bool  # True if calls are independent
    merge_strategy: str  # "concatenate" | "interleave" | "priority"

class BackendCall:
    service: str  # "postgres" | "neo4j" | "ml" | "analytics"
    method: str   # "get_fir_by_number" | "get_criminal_network" | etc.
    params: dict
    priority: int  # Lower = higher priority
```

Example intent-to-service mappings:

| Intent | Backend Calls |
|---|---|
| `FIR_LOOKUP` | PostgreSQL: `get_fir_by_number()` or `search_firs()` |
| `CASE_DETAILS` | PostgreSQL: `get_case_by_number()` or `search_cases()` |
| `CRIMINAL_HISTORY` | PostgreSQL: `get_criminal_by_name()` + Neo4j: `get_criminal_associations()` |
| `CRIME_STATISTICS` | PostgreSQL: `dashboard_summary()` + `category_breakdown()` + `district_comparison()` |
| `HOTSPOT_ANALYSIS` | ML: `hotspot_predict()` + PostgreSQL: `hotspots()` |
| `CRIMINAL_NETWORK` | Neo4j: `get_person_network()` + PostgreSQL fallback |
| `PREDICTIONS` | ML: `risk_predict()` or `forecast()` |
| `DASHBOARD_ANALYTICS` | PostgreSQL: `dashboard_summary()` + `trends()` + `categories()` |

### 4. Backend Fetcher (`backend_fetcher.py`)

Executes the query plan by calling existing services directly (not HTTP):

- **PostgreSQL**: Uses SQLAlchemy `db` session to query models directly via existing service functions
- **Neo4j**: Uses `network_service.py` functions + `neo4j/client.py` Cypher queries
- **ML Services**: Calls existing inference functions (`hotspot.py`, `risk.py`, `criminal.py`)
- **Analytics**: Uses `analytics_service.py` functions

All calls wrapped in try/except with graceful fallback. Returns structured `BackendResult` objects.

### 5. Context Builder (`context_builder.py`)

Merges all `BackendResult` objects into a single structured context string for the LLM:

```
## Retrieved Backend Data

### FIR Records
- FIR 2026/104: Complainant K. S. Narayanan, Sections 420/468 IPC, Status: Open
  Accused: Vikram Yadav, Narrative: [summary]

### Criminal Network
- Vikram Yadav KNOWS Sayed Ibrahim (Hawala Transfer Link)
- Vikram Yadav ASSOCIATED_WITH Coastal Narcotics Transit Ring

### Crime Statistics
- Total crimes: 11, Open cases: 6, Resolution rate: 45%

### Predictions
- Bengaluru Urban risk score: 78/100 (HIGH)
```

### 6. LLM Generator (`llm_generator.py`)

Calls an external LLM API. Supports:

1. **Primary**: Google Gemini API via `httpx` (HTTP calls, no SDK dependency)
2. **Fallback**: OpenAI API via `httpx`
3. **Local fallback**: If no API key configured, falls back to a template-based response generator (improved version of current system that intelligently formats retrieved backend data)

The generator:
- Sends system prompt + context + conversation history + user query
- Supports streaming (yields chunks)
- System prompt enforces: "Answer ONLY using supplied context. Never fabricate."

**Critical design decision**: Since this is a competition project that may not have API keys, the local fallback must produce high-quality responses by intelligently formatting the retrieved backend data into readable answers.

### 7. Response Validator (`response_validator.py`)

Before sending to user:
- Extracts all named entities from the LLM response
- Cross-references against retrieved backend data
- Flags any names, IDs, or statistics not present in the context
- If hallucination detected, either:
  - Strips the hallucinated sentence
  - Appends a disclaimer
  - Falls back to raw data summary

### 8. Orchestrator (`orchestrator.py`)

Ties everything together:

```python
async def process_message(
    message: str,
    session_id: str,
    db: Session,
) -> AsyncIterator[dict]:
    # 1. Load conversation memory
    history = memory.get_history(session_id)

    # 2. Detect intents
    intents = intent_router.detect(message)

    # 3. Extract entities
    entities = entity_extractor.extract(message)

    # 4. Resolve pronouns using history
    entities = resolve_coreference(entities, history)

    # 5. Plan queries
    plan = query_planner.plan(intents, entities)

    # 6. Fetch from backends (parallel where possible)
    results = await backend_fetcher.execute(plan, db)

    # 7. Build context
    context = context_builder.build(results, entities)

    # 8. Generate response via LLM (streaming)
    response_chunks = []
    async for chunk in llm_generator.generate(message, context, history):
        response_chunks.append(chunk)
        yield {"type": "token", "content": chunk}

    # 9. Validate response
    full_response = "".join(response_chunks)
    validated = response_validator.validate(full_response, results)

    # 10. Save to memory
    memory.add(session_id, message, validated)

    # 11. Yield final payload
    yield {"type": "final", "content": {
        "answer": validated,
        "summary": context.summary,
        "entities": list(entities.values()),
        "classification": intents[0].value if intents else "general",
        "sources": [r.source for r in results],
        "citations": [...],
    }}
```

### 9. Conversation Memory (`memory.py`)

Simple in-memory store (dict of session_id -> message list):
- Stores last 20 messages per session
- Provides context for pronoun resolution ("he", "she", "that case")
- TTL-based cleanup (1 hour idle -> evict)
- Never replaces backend retrieval

### 10. Route Changes (`ai_chat.py`)

Replace current `_assistant_response` with:
```python
@router.post("")
async def chat(payload: ChatRequest, db=..., user=...):
    return StreamingResponse(
        orchestrator.process_message(payload.message, payload.session_id, db),
        media_type="application/x-ndjson"
    )
```

Keep `/query` as a non-streaming wrapper that collects all chunks.

### 11. Frontend Changes

**`api.ts`**: Add `chatQueryStream()` that returns an `AsyncGenerator` reading NDJSON.

**`AIChat.tsx`**:
- Consume streaming response, appending tokens as they arrive
- Show intent badge and entity tags below the query
- Show "Querying PostgreSQL..." / "Analyzing network..." status indicators
- Show retrieval source cards with document references

---

## Implementation Order

| Phase | Files | Description | Status |
|---|---|---|---|
| **Phase 1** | `config.py`, `requirements.txt` | Add LLM config settings | COMPLETED |
| **Phase 2** | `intent_router.py`, `entity_extractor.py` | Intent detection + entity extraction | COMPLETED |
| **Phase 3** | `query_planner.py`, `backend_fetcher.py` | Query planning + backend execution | COMPLETED |
| **Phase 4** | `context_builder.py`, `llm_generator.py` | Context building + LLM integration | COMPLETED |
| **Phase 5** | `response_validator.py`, `memory.py` | Validation + conversation memory | COMPLETED |
| **Phase 6** | `orchestrator.py` | Wire everything together | COMPLETED |
| **Phase 7** | `ai_chat.py` (route) | Update routes to use orchestrator | COMPLETED |
| **Phase 8** | `api.ts`, `AIChat.tsx` | Frontend streaming + UI enhancements | COMPLETED |

---

## Key Design Decisions

1. **No external embedding service**: Keep the hash-based vector store as a fallback but route most queries through direct backend service calls instead of vector search
2. **Gemini API via raw HTTP**: Use `httpx` to call Gemini's REST API directly, avoiding SDK dependencies. If no API key is set, use the enhanced template-based fallback
3. **Direct service calls**: The `backend_fetcher` calls Python service functions directly (not HTTP endpoints), since everything runs in the same FastAPI process
4. **Parallel execution**: Use `asyncio.gather()` for independent backend calls (e.g., PostgreSQL + Neo4j for criminal history)
5. **Streaming from start**: Stream intent detection -> entity extraction -> backend fetching status -> LLM tokens -> final response

---

## Non-Negotiable Rules

1. Never answer factual queries without backend retrieval
2. Never fabricate case details, FIRs, officer names, or criminal relationships
3. Always query PostgreSQL for structured data
4. Always query Neo4j for relationship data
5. Always query ML services for predictions and analytics
6. The LLM's responsibility is reasoning, summarization, explanation, and conversational interaction only
7. If no API key is configured, use the enhanced template-based fallback that formats retrieved data into readable answers
8. Every factual statement must originate from retrieved backend data
9. If no data exists, respond with "I couldn't find matching records in the Saksha database."

---

## Existing Code References

### Key files to integrate with:

| File | Functions/Classes |
|---|---|
| `backend/app/services/analytics_service.py` | `dashboard_summary()`, `category_breakdown()`, `district_comparison()`, `hotspots()`, `anomalies()`, `offender_dossiers()` |
| `backend/app/services/crime_service.py` | `list_crimes()`, `get_crime()`, `search_crimes()` |
| `backend/app/services/investigation_service.py` | `get_investigation()`, `get_investigation_timeline()` |
| `backend/app/services/network/network_service.py` | `get_full_network_graph()`, `get_person_network_graph()`, `find_shortest_path()`, `perform_link_analysis()`, `generate_ai_graph_insights()`, `get_organization_gang_networks()` |
| `backend/app/services/neo4j/client.py` | `is_neo4j_available()`, `query_shortest_path_neo4j()`, `sync_postgres_to_neo4j()` |
| `backend/app/services/rag/rag_service.py` | `build_rag_documents()` |
| `backend/app/ai/inference/hotspot.py` | Hotspot prediction model |
| `backend/app/ai/inference/risk.py` | Risk scoring + forecasting |
| `backend/app/ai/inference/criminal.py` | Criminal risk, repeat offender, similar, cluster |
| `backend/app/ai/inference/anomaly.py` | Anomaly detection |
| `backend/app/models/` | All 22 SQLAlchemy ORM models |
| `backend/app/database/postgres.py` | `get_db()` session provider |
| `backend/app/database/neo4j.py` | `get_neo4j_driver()`, `verify_neo4j_connectivity()` |

### Known Karnataka districts (for entity matching):

Bengaluru Urban, Bengaluru Rural, Mysuru, Mangaluru, Belagavi, Ballari, Kalaburagi, Hassan, Tumkuru, Dharwad

### Known police stations (for entity matching):

Whitefield, KR Puram, Devaraja, Mangaluru Harbor, Belagavi City, Ballari, Kalaburagi, Hassan, Tumkuru, Dharwad

### Known crime categories (for entity matching):

Cyber Crime, Theft & Burglaries, Narcotics, Smuggling, Assault, Illegal Mining, Domestic Violence, Property Disputes

### Demo users:

| Username | Password | Role | Full Name |
|---|---|---|---|
| `admin` | `564738` | admin | Admin User |
| `SCRB-7740` | `123456` | crime_analyst | Priya Sharma |
| `IO-3921` | `456789` | investigator | Inspector Ravi Kumar |
| `SP-0088` | `987654` | inspector | Superintendent Arun Mehta |
