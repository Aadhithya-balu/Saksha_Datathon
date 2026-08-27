# Verification plan — SAKSHA on Catalyst Data Store

## 1. Idempotent row counts

Confirm every migrated table holds the expected number of rows. These queries use ZCQL (DML/read-only — matching Catalyst Cloud Scale's supported operations):

- `SELECT COUNT(*) FROM crime_cases`  →  **11**
- `SELECT COUNT(*) FROM crime_categories`  →  **8**
- `SELECT COUNT(*) FROM criminals`  →  **5**
- `SELECT COUNT(*) FROM evidence`  →  **11**
- `SELECT COUNT(*) FROM fir_criminal_links`  →  **9**
- `SELECT COUNT(*) FROM fir_victim_links`  →  **7**
- `SELECT COUNT(*) FROM firs`  →  **11**
- `SELECT COUNT(*) FROM locations`  →  **10**
- `SELECT COUNT(*) FROM notifications`  →  **12**
- `SELECT COUNT(*) FROM officers`  →  **2**
- `SELECT COUNT(*) FROM roles`  →  **4**
- `SELECT COUNT(*) FROM users`  →  **4**
- `SELECT COUNT(*) FROM victims`  →  **5**

## 2. Referential integrity

### FIRs point at existing cases
```sql
SELECT COUNT(*) FROM firs f LEFT JOIN crime_cases c ON f.crime_case_id = c.id WHERE c.id IS NULL
```
→ `0`

### Cases point at existing categories and locations
```sql
SELECT COUNT(*) FROM crime_cases cc LEFT JOIN crime_categories k ON cc.category_id = k.id
LEFT JOIN locations l ON cc.location_id = l.id
WHERE k.id IS NULL OR l.id IS NULL
```
→ `0`

### FBI links resolve to FIRs, criminals and victims
```sql
SELECT COUNT(*) FROM fir_criminal_links x LEFT JOIN firs f ON x.fir_id = f.id
LEFT JOIN criminals c ON x.criminal_id = c.id WHERE f.id IS NULL OR c.id IS NULL
```
→ `0`  (run the equivalent for `fir_victim_links` against `victims` too)

## 3. Business analytics still hold

### District ranking by open cases (severity-weighted view)
```sql
SELECT l.district, COUNT(*) AS cases FROM crime_cases cc
JOIN locations l ON cc.location_id = l.id GROUP BY l.district ORDER BY cases DESC
```
→ Bengaluru Urban 2, Mysuru 2, then 1 each for Mangaluru, Belagavi, Ballari, Kalaburagi, Hassan, Tumkuru, Dharwad.

### Repeat-offender detection (criminals named in ≥2 FIRs)
```sql
SELECT criminal_id, COUNT(DISTINCT fir_id) AS n FROM fir_criminal_links GROUP BY criminal_id HAVING COUNT(DISTINCT fir_id) >= 2
```
→ Ramu Swamy only.

### Search plumbing still returns offenders/cases/FIRs
```sql
SELECT * FROM criminals WHERE full_name LIKE '%Ibrahim%';
SELECT * FROM crime_cases WHERE case_number = 'CR-2026-BNG-001';
SELECT * FROM firs WHERE fir_number = 'FIR-789/MYS/2026';
```
→ 1 row each.

## 4. Provenance preserved (DEMO/SEED status)
```sql
SELECT dataset_provenance, COUNT(*) FROM crime_cases GROUP BY dataset_provenance;
```
→ `demo  11` (and the same across every migrated table that carries the triplet).

## 5. App-level spot checks (after the backend is pointed at Catalyst)
- Criminal search (offenders page) returns the 5 seeded criminals.
- Case/FIR lists render with correct linked entities.
- Network graph builds from `crime_cases`, `firs`, `fir_criminal_links`, `fir_victim_links`.
- Hotspots page renders (driven by `locations.latitude/longitude` + `crime_cases`).
- Predictions page loads (risk/forecast models read the same tables).
- AI Chat persists conversations into `chat_conversations`/`chat_messages`.
- Reports export works (`reports` insert on generate).
- Auth: `admin` / `564738` and `SCRB-7740` / `123456` log in (hashed_password preserved).
- Evidence file/image workflows: `evidence_metadata.storage_url` / `filepath` point to the migrated bucket paths (note: uploads themselves must be re-synced to Stratus).