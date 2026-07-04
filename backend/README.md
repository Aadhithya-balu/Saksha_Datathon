# SAKSHA Backend

Core backend for the SAKSHA Crime Intelligence Platform — FastAPI + PostgreSQL + Neo4j, with JWT auth, RBAC, full CRUD, and the API contracts the AI/ML and frontend teams build against.

**Status:** scaffolded, tested, and verified importable. 59 routes registered across 41 unique paths, all confirmed via `pytest` (5/5 passing) and OpenAPI schema generation.

---

## Folder structure

```
backend/
├── app/
│   ├── api/            # versioned router aggregator (v1.py)
│   ├── auth/           # JWT dependency + RBAC role checks
│   ├── core/           # config, logging, security (hashing/JWT), exceptions
│   ├── database/       # Postgres session + Neo4j driver + init/seed scripts
│   ├── models/         # SQLAlchemy ORM models (11 tables)
│   ├── schemas/        # Pydantic request/response schemas
│   ├── services/       # business logic (generic CRUD, auth, audit, crime)
│   ├── routes/         # one router per module (auth, crimes, firs, ...)
│   └── main.py         # FastAPI app, middleware, health checks
├── neo4j/
│   ├── schema.cypher            # constraints, indexes, sample graph
│   └── queries_reference.cypher # ego-network, shortest path, Louvain, etc.
├── tests/               # pytest suite (isolated in-memory SQLite per test)
├── requirements.txt
├── docker-compose.yml    # backend + postgres + neo4j, one command
├── Dockerfile
└── .env.example
```

---

## Quick start (local, no Docker)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DATABASE_URL, NEO4J_URI/USER/PASSWORD, JWT_SECRET_KEY

# create tables
python -m app.database.init_db

# seed roles + a default admin user (admin / ChangeMe123!)
python -m app.database.seed_db

# run
uvicorn app.main:app --reload
```

Visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health check:** http://localhost:8000/health

## Quick start (Docker — recommended for the team)

```bash
cp .env.example .env   # edit values
docker compose up --build
```

This brings up the backend, PostgreSQL, and Neo4j (with the Graph Data Science plugin enabled) together. Then run the init/seed scripts inside the backend container once:

```bash
docker compose exec backend python -m app.database.init_db
docker compose exec backend python -m app.database.seed_db
```

Load the Neo4j sample graph:

```bash
docker compose exec neo4j cypher-shell -u neo4j -p <password> -f /neo4j/schema.cypher
```
(mount `./neo4j` into the neo4j container, or paste the file contents into the Neo4j Browser at http://localhost:7474)

---

## Auth & RBAC

- JWT access tokens (60 min default) + refresh tokens (7 days default), both configurable in `.env`.
- Roles: `admin`, `crime_analyst`, `investigator`, `policymaker` — seeded automatically by `seed_db.py`.
- Protect any route with:
  ```python
  from app.auth.rbac import require_roles, ROLE_ADMIN
  @router.post("/x", dependencies=[Depends(require_roles(ROLE_ADMIN))])
  ```
- Every `POST`/`PUT`/`DELETE` on Crime, FIR, Criminal, Victim, Officer, Location, User writes an `AuditLog` row automatically via `app/services/audit_service.py`.

## Database

- **PostgreSQL**: 11 tables (Users, Roles, CrimeCases, FIRs [+ link tables for criminals/victims], Criminals, Victims, Officers, Evidence, CrimeCategories, Locations, Reports, AuditLogs), all UUID primary keys, indexed foreign keys, `created_at`/`updated_at` timestamps on every table.
- For the datathon timeline, `init_db.py` uses `Base.metadata.create_all()` for speed. **Before production**, switch to Alembic migrations:
  ```bash
  alembic init migrations
  alembic revision --autogenerate -m "initial schema"
  alembic upgrade head
  ```
- **Neo4j**: graph schema in `neo4j/schema.cypher` — 8 node types, 8 relationship types, with a small sample graph pre-loaded so frontend/AI teams have real-shaped data to build against immediately.

## Handoff to the AI/ML team

`app/routes/ai_support.py` defines the exact contract (`/api/v1/ai/chat/query`, `/predictions/risk-scores`, `/predictions/anomalies`, `/hotspots`, `/network/person/{id}`) your teammates' models plug into. Each currently returns a clearly-marked stub. To wire in a real model:

1. Put the model/pipeline logic in a new `app/services/<name>_ai_service.py`.
2. Import and call it from the matching function in `ai_support.py`, replacing the stub return.
3. Keep the response shape (the Pydantic model / dict keys) unchanged — the frontend is already built against it.

## Testing

```bash
pytest tests/ -v
```

5 tests currently cover: root/health endpoints, login success, login with wrong password (401), and unauthenticated access to a protected route (401). Each test gets a fresh in-memory SQLite database — extend `tests/` following the same `client`/`db_session` fixture pattern as you add modules.

## Known environment note

`passlib==1.7.4` requires `bcrypt==4.0.1` pinned exactly — newer `bcrypt` releases removed an attribute passlib's version-detection relies on. This is already pinned in `requirements.txt`; don't `pip install -U bcrypt` without testing.
