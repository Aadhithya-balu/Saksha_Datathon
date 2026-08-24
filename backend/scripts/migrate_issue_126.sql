-- ============================================================
-- Migration: Issue #126 — Temporary Local Files / Storage Strategy
-- Run this in: Supabase Dashboard > SQL Editor
-- Safe to run multiple times (all statements are idempotent).
-- ============================================================

-- 1. Add storage_url to evidence_metadata
--    Stores the cloud storage URL when a file is uploaded to
--    Supabase Storage (or any future object store). NULL means
--    the file is on local server storage (dev / no-bucket mode).
ALTER TABLE evidence_metadata
    ADD COLUMN IF NOT EXISTS storage_url VARCHAR(1000);

-- 2. Update evidence.storage_path for any existing rows that
--    already have a metadata record with a storage_url so the
--    two columns stay in sync.
UPDATE evidence e
SET    storage_path = m.storage_url
FROM   evidence_metadata m
WHERE  m.evidence_id = e.id
  AND  m.storage_url IS NOT NULL
  AND  (e.storage_path IS NULL OR e.storage_path NOT LIKE 'http%');

-- Done.
-- After running this script the backend will:
--   • Store new uploads in Supabase Storage when SUPABASE_URL +
--     SUPABASE_ANON_KEY + SUPABASE_STORAGE_BUCKET are configured.
--   • Fall back to local backend/uploads/ when those vars are absent
--     (free-tier / local dev — files survive as long as the container
--     volume is persistent).
--   • Serve downloads via HTTP redirect to the cloud URL when
--     storage_url is set, or via local FileResponse otherwise.
