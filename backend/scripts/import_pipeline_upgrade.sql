-- ===========================================================================
-- Saksha — Issue 5 (P1): ingestion pipeline upgrade
--
-- `Base.metadata.create_all()` creates NEW tables but cannot ALTER existing
-- ones. Run this script ONCE against an existing Supabase/PostgreSQL database
-- to add the staging table and provenance columns used by the ingestion
-- pipeline. Fresh deployments get everything automatically via create_all().
--
-- Safe to re-run: uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1. Row-level staging area (import_staging_records)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS import_staging_records (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id                 UUID NOT NULL REFERENCES import_jobs(id) ON DELETE CASCADE,
    row_number             INTEGER NOT NULL,
    source_row_ref         VARCHAR(100),
    raw_data               TEXT,          -- verbatim mapped source values
    mapped_data            TEXT,          -- validated/normalized Saksha values
    validation_status      VARCHAR(20)  NOT NULL DEFAULT 'pending', -- valid|invalid|warning
    validation_errors      TEXT,          -- JSON [{code, field, message}]
    validation_warnings    TEXT,          -- JSON [{code, field, message}]
    duplicate_status       VARCHAR(30)  NOT NULL DEFAULT 'unique',
    duplicate_of           TEXT,          -- JSON refs
    reconciliation_status  VARCHAR(30)  NOT NULL DEFAULT 'pending',
    reconciliation_details TEXT,          -- JSON incl. field conflicts
    trust_level            VARCHAR(30)  NOT NULL DEFAULT 'rejected',
    promoted               BOOLEAN      NOT NULL DEFAULT FALSE,
    promoted_record_id     UUID,
    promoted_at            TIMESTAMPTZ,
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_import_staging_records_job_id        ON import_staging_records(job_id);
CREATE INDEX IF NOT EXISTS ix_staging_job_row                      ON import_staging_records(job_id, row_number);
CREATE INDEX IF NOT EXISTS ix_import_staging_records_promoted_record_id ON import_staging_records(promoted_record_id);
CREATE INDEX IF NOT EXISTS ix_import_staging_records_validation_status  ON import_staging_records(validation_status);
CREATE INDEX IF NOT EXISTS ix_import_staging_records_reconciliation_status ON import_staging_records(reconciliation_status);
CREATE INDEX IF NOT EXISTS ix_import_staging_records_duplicate_status   ON import_staging_records(duplicate_status);

-- ---------------------------------------------------------------------------
-- 2. Import job: pipeline lifecycle + quality metrics + grading
-- ---------------------------------------------------------------------------
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS source_system              VARCHAR(100) NOT NULL DEFAULT 'manual_upload';
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS valid_rows                 INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS invalid_rows               INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS warning_rows               INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS exact_duplicate_rows       INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS potential_duplicate_rows   INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS conflict_rows              INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS new_record_rows            INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS matched_record_rows        INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS updated_record_rows        INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS rejected_rows              INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS review_rows                INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS error_count                INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS promoted_rows              INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS quality_grade              VARCHAR(10);           -- A/B/C/D/REJECTED
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS processing_started_at      TIMESTAMPTZ;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS processing_completed_at    TIMESTAMPTZ;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS promoted_at                TIMESTAMPTZ;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS rolled_back_at             TIMESTAMPTZ;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS promoted_by_id             UUID REFERENCES users(id) ON DELETE SET NULL;

-- ---------------------------------------------------------------------------
-- 3. Provenance columns on promotable production records (issue 5 §4/§26).
--    Existing rows keep dataset_provenance='live'; only records promoted by
--    the pipeline are written as 'migrated' with their lineage filled in.
-- ---------------------------------------------------------------------------
ALTER TABLE crime_cases ADD COLUMN IF NOT EXISTS dataset_provenance    VARCHAR(20) NOT NULL DEFAULT 'live';
ALTER TABLE crime_cases ADD COLUMN IF NOT EXISTS source_import_job_id  UUID REFERENCES import_jobs(id) ON DELETE SET NULL;
ALTER TABLE crime_cases ADD COLUMN IF NOT EXISTS source_file           VARCHAR(500);
ALTER TABLE crime_cases ADD COLUMN IF NOT EXISTS source_row_ref        VARCHAR(100);

ALTER TABLE criminals  ADD COLUMN IF NOT EXISTS dataset_provenance    VARCHAR(20) NOT NULL DEFAULT 'live';
ALTER TABLE criminals  ADD COLUMN IF NOT EXISTS source_import_job_id  UUID REFERENCES import_jobs(id) ON DELETE SET NULL;
ALTER TABLE criminals  ADD COLUMN IF NOT EXISTS source_file           VARCHAR(500);
ALTER TABLE criminals  ADD COLUMN IF NOT EXISTS source_row_ref        VARCHAR(100);

ALTER TABLE victims    ADD COLUMN IF NOT EXISTS dataset_provenance    VARCHAR(20) NOT NULL DEFAULT 'live';
ALTER TABLE victims    ADD COLUMN IF NOT EXISTS source_import_job_id  UUID REFERENCES import_jobs(id) ON DELETE SET NULL;
ALTER TABLE victims    ADD COLUMN IF NOT EXISTS source_file           VARCHAR(500);
ALTER TABLE victims    ADD COLUMN IF NOT EXISTS source_row_ref        VARCHAR(100);

CREATE INDEX IF NOT EXISTS ix_crime_cases_dataset_provenance   ON crime_cases(dataset_provenance);
CREATE INDEX IF NOT EXISTS ix_crime_cases_source_import_job_id ON crime_cases(source_import_job_id);
CREATE INDEX IF NOT EXISTS ix_criminals_dataset_provenance     ON criminals(dataset_provenance);
CREATE INDEX IF NOT EXISTS ix_criminals_source_import_job_id   ON criminals(source_import_job_id);
CREATE INDEX IF NOT EXISTS ix_victims_dataset_provenance       ON victims(dataset_provenance);
CREATE INDEX IF NOT EXISTS ix_victims_source_import_job_id     ON victims(source_import_job_id);
