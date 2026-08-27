# Catalyst Data Store — manual column spec

Columns are listed in the same order as the CSV header in `data/<table>.csv`. Create **only** these columns — Catalyst auto-adds `ROWID`, `CREATORID`, `CREATEDTIME`, `MODIFIEDTIME`, which must be left untouched.

Recommended console settings per column: `IsUnique` for the logical PK and any `unique`-flagged columns; `IsMandatory` where flagged; enable `Search Index` on the logical PK and lookup columns (case_number, username, badge_number, fir_number) 
so the app/ queries stay fast.

## `roles`  — seed rows to import: 4

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK (UUID from Postgres). |
| 2 | `name` | Var Char(50) | Y | Y | RBAC role name. |
| 3 | `description` | Var Char(255) |  |  |  |
| 4 | `created_at` | DateTime |  |  |  |
| 5 | `updated_at` | DateTime |  |  |  |
| 6 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 7 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 8 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `users`  — seed rows to import: 4

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `username` | Var Char(100) | Y | Y |  |
| 3 | `email` | Var Char(255) | Y | Y |  |
| 4 | `full_name` | Var Char(255) |  | Y |  |
| 5 | `hashed_password` | Text(10000) |  | Y | Var Char>255 -> Text in Catalyst. |
| 6 | `is_active` | Boolean |  |  |  |
| 7 | `failed_login_attempts` | Int |  |  | Account-lockout counter (ORM default 0). |
| 8 | `locked_until` | DateTime |  |  |  |
| 9 | `role_id` | Var Char(50) |  | Y | FK -> roles.id (stored as plain Var Char, joined by value). |
| 10 | `district` | Var Char(100) |  |  |  |
| 11 | `station` | Var Char(100) |  |  |  |
| 12 | `created_at` | DateTime |  |  |  |
| 13 | `updated_at` | DateTime |  |  |  |
| 14 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 15 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 16 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `officers`  — seed rows to import: 2

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `supabase_user_id` | Var Char(50) |  |  | Legacy Supabase user reference (nullable after migration). |
| 3 | `user_id` | Var Char(50) | Y |  | FK -> users.id. |
| 4 | `badge_number` | Var Char(50) | Y | Y |  |
| 5 | `name` | Var Char(255) |  | Y |  |
| 6 | `rank` | Var Char(100) |  |  |  |
| 7 | `station` | Var Char(100) |  | Y |  |
| 8 | `district` | Var Char(100) |  |  |  |
| 9 | `designation` | Var Char(100) |  |  |  |
| 10 | `phone` | Var Char(20) |  |  |  |
| 11 | `email` | Var Char(255) | Y |  |  |
| 12 | `status` | Var Char(50) |  |  |  |
| 13 | `image_url` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 14 | `created_at` | DateTime |  |  |  |
| 15 | `updated_at` | DateTime |  |  |  |
| 16 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 17 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 18 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `locations`  — seed rows to import: 10

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `address` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 3 | `district` | Var Char(100) |  | Y |  |
| 4 | `station` | Var Char(100) |  |  |  |
| 5 | `latitude` | Double |  | Y |  |
| 6 | `longitude` | Double |  | Y |  |
| 7 | `pincode` | Var Char(10) |  |  |  |
| 8 | `created_at` | DateTime |  |  |  |
| 9 | `updated_at` | DateTime |  |  |  |
| 10 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 11 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 12 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `crime_categories`  — seed rows to import: 8

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `name` | Var Char(150) | Y | Y |  |
| 3 | `section_code` | Var Char(50) |  |  |  |
| 4 | `severity` | Var Char(20) |  |  |  |
| 5 | `created_at` | DateTime |  |  |  |
| 6 | `updated_at` | DateTime |  |  |  |
| 7 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 8 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 9 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `crime_cases`  — seed rows to import: 11

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `case_number` | Var Char(50) | Y | Y |  |
| 3 | `category_id` | Var Char(50) |  | Y | FK -> crime_categories.id. |
| 4 | `location_id` | Var Char(50) |  | Y | FK -> locations.id. |
| 5 | `occurred_at` | DateTime |  | Y |  |
| 6 | `reported_at` | DateTime |  |  |  |
| 7 | `description` | Text(10000) |  |  |  |
| 8 | `mo_tags` | Text(10000) |  |  | Denormalized legacy tag string. |
| 9 | `status` | Var Char(30) |  |  |  |
| 10 | `priority` | Var Char(30) |  |  |  |
| 11 | `progress` | Int |  |  |  |
| 12 | `assigned_officer_id` | Var Char(50) |  |  | FK -> officers.id (nullable). |
| 13 | `created_at` | DateTime |  |  |  |
| 14 | `updated_at` | DateTime |  |  |  |
| 15 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 16 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 17 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `criminals`  — seed rows to import: 5

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `full_name` | Var Char(255) |  | Y |  |
| 3 | `aliases` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 4 | `date_of_birth` | Date |  |  |  |
| 5 | `gender` | Var Char(20) |  |  |  |
| 6 | `address` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 7 | `identifying_marks` | Text(10000) |  |  |  |
| 8 | `mo_summary` | Text(10000) |  |  |  |
| 9 | `status` | Var Char(30) |  |  |  |
| 10 | `gang_affiliation` | Var Char(255) |  |  |  |
| 11 | `neo4j_node_id` | Var Char(100) |  |  |  |
| 12 | `image_url` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 13 | `created_at` | DateTime |  |  |  |
| 14 | `updated_at` | DateTime |  |  |  |
| 15 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 16 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 17 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `victims`  — seed rows to import: 5

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `full_name` | Var Char(255) |  | Y |  |
| 3 | `contact_number` | Var Char(20) |  |  |  |
| 4 | `address` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 5 | `gender` | Var Char(20) |  |  |  |
| 6 | `age` | Int |  |  |  |
| 7 | `statement` | Text(10000) |  |  |  |
| 8 | `neo4j_node_id` | Var Char(100) |  |  |  |
| 9 | `image_url` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 10 | `created_at` | DateTime |  |  |  |
| 11 | `updated_at` | DateTime |  |  |  |
| 12 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 13 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 14 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `firs`  — seed rows to import: 11

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `fir_number` | Var Char(50) | Y | Y |  |
| 3 | `crime_case_id` | Var Char(50) |  | Y | FK -> crime_cases.id. |
| 4 | `investigating_officer_id` | Var Char(50) |  |  | FK -> officers.id (nullable). |
| 5 | `complainant_name` | Var Char(255) |  | Y |  |
| 6 | `complainant_contact` | Var Char(20) |  |  |  |
| 7 | `sections` | Var Char(255) |  |  |  |
| 8 | `filed_at` | DateTime |  |  |  |
| 9 | `status` | Var Char(30) |  |  |  |
| 10 | `narrative` | Text(10000) |  |  |  |
| 11 | `attachments` | Text(10000) |  |  | JSON-encoded attachment array (Text in Catalyst). |
| 12 | `created_at` | DateTime |  |  |  |
| 13 | `updated_at` | DateTime |  |  |  |
| 14 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 15 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 16 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `fir_criminal_links`  — seed rows to import: 9

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK (deterministic UUID synthesised at CSV build). |
| 2 | `fir_id` | Var Char(50) |  | Y | FK -> firs.id. |
| 3 | `criminal_id` | Var Char(50) |  | Y | FK -> criminals.id. |
| 4 | `role` | Var Char(50) |  |  |  |
| 5 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 6 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 7 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `fir_victim_links`  — seed rows to import: 7

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK (deterministic UUID synthesised at CSV build). |
| 2 | `fir_id` | Var Char(50) |  | Y | FK -> firs.id. |
| 3 | `victim_id` | Var Char(50) |  | Y | FK -> victims.id. |
| 4 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 5 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 6 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `evidence`  — seed rows to import: 11

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `case_id` | Var Char(50) |  | Y | FK -> crime_cases.id. |
| 3 | `title` | Var Char(255) |  | Y |  |
| 4 | `description` | Text(10000) |  |  |  |
| 5 | `evidence_type` | Var Char(50) |  | Y |  |
| 6 | `status` | Var Char(50) |  |  |  |
| 7 | `created_by` | Var Char(255) |  |  |  |
| 8 | `assigned_to` | Var Char(50) |  |  | FK -> users.id (nullable). |
| 9 | `storage_path` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 10 | `created_at` | DateTime |  |  |  |
| 11 | `updated_at` | DateTime |  |  |  |
| 12 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 13 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 14 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `evidence_metadata`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `evidence_id` | Var Char(50) | Y | Y | FK -> evidence.id. |
| 3 | `filename` | Var Char(255) |  | Y |  |
| 4 | `filepath` | Text(10000) |  | Y | Var Char>255 -> Text in Catalyst. |
| 5 | `filesize` | Int |  | Y |  |
| 6 | `mime_type` | Var Char(100) |  | Y |  |
| 7 | `uploaded_by` | Var Char(255) |  |  |  |
| 8 | `storage_url` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 9 | `extracted_data` | Text(10000) |  |  | JSON -> Text (JSON-encoded string) in Catalyst. |
| 10 | `created_at` | DateTime |  |  |  |
| 11 | `updated_at` | DateTime |  |  |  |
| 12 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 13 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 14 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `evidence_timeline`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `evidence_id` | Var Char(50) |  | Y | FK -> evidence.id. |
| 3 | `action` | Var Char(100) |  | Y |  |
| 4 | `performed_by` | Var Char(255) |  | Y |  |
| 5 | `role` | Var Char(100) |  | Y |  |
| 6 | `description` | Text(10000) |  |  |  |
| 7 | `created_at` | DateTime |  |  |  |
| 8 | `updated_at` | DateTime |  |  |  |
| 9 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 10 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 11 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `evidence_assignments`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `evidence_id` | Var Char(50) |  | Y | FK -> evidence.id. |
| 3 | `assigned_by` | Var Char(50) |  | Y | FK -> users.id. |
| 4 | `assigned_to` | Var Char(50) |  | Y | FK -> users.id. |
| 5 | `status` | Var Char(50) |  |  |  |
| 6 | `assigned_at` | DateTime |  |  |  |
| 7 | `accepted_at` | DateTime |  |  |  |
| 8 | `completed_at` | DateTime |  |  |  |
| 9 | `created_at` | DateTime |  |  |  |
| 10 | `updated_at` | DateTime |  |  |  |
| 11 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 12 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 13 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `evidence_ai_summary`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `evidence_id` | Var Char(50) |  | Y | FK -> evidence.id. |
| 3 | `summary` | Text(10000) |  | Y |  |
| 4 | `model` | Var Char(100) |  | Y |  |
| 5 | `created_at` | DateTime |  |  |  |
| 6 | `updated_at` | DateTime |  |  |  |
| 7 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 8 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 9 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `chain_of_custody`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `evidence_id` | Var Char(50) |  | Y | FK -> evidence.id. |
| 3 | `from_user` | Var Char(50) |  |  | FK -> users.id (nullable). |
| 4 | `to_user` | Var Char(50) |  |  | FK -> users.id (nullable). |
| 5 | `action` | Var Char(100) |  | Y |  |
| 6 | `location` | Var Char(255) |  |  |  |
| 7 | `remarks` | Text(10000) |  |  |  |
| 8 | `timestamp` | DateTime |  |  |  |
| 9 | `created_at` | DateTime |  |  |  |
| 10 | `updated_at` | DateTime |  |  |  |
| 11 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 12 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 13 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `audit_logs`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `user_id` | Var Char(50) |  | Y | FK -> users.id. |
| 3 | `action` | Var Char(50) |  | Y |  |
| 4 | `resource_type` | Var Char(100) |  | Y |  |
| 5 | `resource_id` | Var Char(100) |  |  |  |
| 6 | `details` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 7 | `ip_address` | Var Char(50) |  |  |  |
| 8 | `timestamp` | DateTime |  |  |  |
| 9 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 10 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 11 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `notifications`  — seed rows to import: 12

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `user_id` | Var Char(50) |  |  | FK -> users.id (nullable: broadcast/system feeds). |
| 3 | `sender_id` | Var Char(50) |  |  | FK -> users.id (nullable). |
| 4 | `subject` | Text(10000) |  | Y | Var Char>255 -> Text in Catalyst. |
| 5 | `notification_type` | Var Char(50) |  | Y |  |
| 6 | `category` | Var Char(50) |  | Y |  |
| 7 | `title` | Var Char(255) |  | Y |  |
| 8 | `message` | Text(10000) |  | Y |  |
| 9 | `severity` | Var Char(20) |  | Y |  |
| 10 | `priority` | Var Char(20) |  | Y |  |
| 11 | `status` | Var Char(20) |  | Y |  |
| 12 | `resource_type` | Var Char(50) |  |  |  |
| 13 | `resource_id` | Var Char(100) |  |  |  |
| 14 | `related_case_number` | Var Char(50) |  |  |  |
| 15 | `related_fir_number` | Var Char(50) |  |  |  |
| 16 | `is_read` | Boolean |  |  |  |
| 17 | `is_dismissed` | Boolean |  |  |  |
| 18 | `is_broadcast` | Boolean |  |  |  |
| 19 | `parent_id` | Var Char(50) |  |  | Self FK -> notifications.id (nullable). |
| 20 | `attachment_url` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 21 | `created_at` | DateTime |  |  |  |
| 22 | `read_at` | DateTime |  |  |  |
| 23 | `acknowledged_at` | DateTime |  |  |  |
| 24 | `resolved_at` | DateTime |  |  |  |
| 25 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 26 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 27 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `reports`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `template` | Var Char(100) |  | Y |  |
| 3 | `requested_by_id` | Var Char(50) |  | Y | FK -> users.id. |
| 4 | `district` | Var Char(100) |  |  |  |
| 5 | `date_from` | DateTime |  |  |  |
| 6 | `date_to` | DateTime |  |  |  |
| 7 | `format` | Var Char(10) |  |  |  |
| 8 | `status` | Var Char(20) |  |  |  |
| 9 | `file_url` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 10 | `created_at` | DateTime |  |  |  |
| 11 | `updated_at` | DateTime |  |  |  |
| 12 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 13 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 14 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `investigation_notes`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `case_id` | Var Char(50) |  | Y | FK -> crime_cases.id. |
| 3 | `officer_id` | Var Char(50) |  |  | FK -> officers.id (nullable). |
| 4 | `officer_name` | Var Char(255) |  | Y |  |
| 5 | `officer_badge` | Var Char(50) |  | Y |  |
| 6 | `content` | Text(10000) |  | Y |  |
| 7 | `created_at` | DateTime |  |  |  |
| 8 | `updated_at` | DateTime |  |  |  |
| 9 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 10 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 11 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `mo_tags`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `name` | Var Char(120) | Y | Y |  |
| 3 | `created_at` | DateTime |  |  |  |
| 4 | `updated_at` | DateTime |  |  |  |
| 5 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 6 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 7 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `case_mo_tags`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `case_id` | Var Char(50) |  | Y | Composite logical PK with mo_tag_id; FK -> crime_cases.id. |
| 2 | `mo_tag_id` | Var Char(50) |  | Y | Composite logical PK; FK -> mo_tags.id. |
| 3 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 4 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 5 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `criminal_mo_tags`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `criminal_id` | Var Char(50) |  | Y | Composite logical PK with mo_tag_id; FK -> criminals.id. |
| 2 | `mo_tag_id` | Var Char(50) |  | Y | Composite logical PK; FK -> mo_tags.id. |
| 3 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 4 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 5 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `chat_conversations`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `user_id` | Var Char(50) |  | Y | FK -> users.id. |
| 3 | `title` | Var Char(200) |  | Y |  |
| 4 | `is_temporary` | Boolean |  |  |  |
| 5 | `message_count` | Int |  |  |  |
| 6 | `last_message_at` | DateTime |  |  |  |
| 7 | `created_at` | DateTime |  |  |  |
| 8 | `updated_at` | DateTime |  |  |  |
| 9 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 10 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 11 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `chat_messages`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `conversation_id` | Var Char(50) |  | Y | FK -> chat_conversations.id. |
| 3 | `role` | Var Char(16) |  | Y |  |
| 4 | `content` | Text(10000) |  | Y |  |
| 5 | `classification` | Var Char(50) |  |  |  |
| 6 | `sources_json` | Text(10000) |  |  | JSON -> Text in Catalyst. |
| 7 | `citations_json` | Text(10000) |  |  | JSON -> Text in Catalyst. |
| 8 | `seq` | Int |  |  |  |
| 9 | `created_at` | DateTime |  |  |  |
| 10 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 11 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 12 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `import_jobs`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `entity_type` | Var Char(50) |  | Y |  |
| 3 | `source_format` | Var Char(10) |  | Y |  |
| 4 | `mapping_profile` | Var Char(50) |  | Y |  |
| 5 | `source_system` | Var Char(100) |  | Y |  |
| 6 | `filename` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 7 | `status` | Var Char(30) |  |  |  |
| 8 | `total_rows` | Int |  |  |  |
| 9 | `imported_rows` | Int |  |  |  |
| 10 | `failed_rows` | Int |  |  |  |
| 11 | `valid_rows` | Int |  |  |  |
| 12 | `invalid_rows` | Int |  |  |  |
| 13 | `warning_rows` | Int |  |  |  |
| 14 | `exact_duplicate_rows` | Int |  |  |  |
| 15 | `potential_duplicate_rows` | Int |  |  |  |
| 16 | `conflict_rows` | Int |  |  |  |
| 17 | `new_record_rows` | Int |  |  |  |
| 18 | `matched_record_rows` | Int |  |  |  |
| 19 | `updated_record_rows` | Int |  |  |  |
| 20 | `rejected_rows` | Int |  |  |  |
| 21 | `review_rows` | Int |  |  |  |
| 22 | `error_count` | Int |  |  |  |
| 23 | `promoted_rows` | Int |  |  |  |
| 24 | `quality_grade` | Var Char(10) |  |  |  |
| 25 | `processing_started_at` | DateTime |  |  |  |
| 26 | `processing_completed_at` | DateTime |  |  |  |
| 27 | `promoted_at` | DateTime |  |  |  |
| 28 | `rolled_back_at` | DateTime |  |  |  |
| 29 | `validation_report` | Text(10000) |  |  | JSON-encoded validation report. |
| 30 | `created_by_id` | Var Char(50) |  |  | FK -> users.id (nullable). |
| 31 | `promoted_by_id` | Var Char(50) |  |  | FK -> users.id (nullable). |
| 32 | `created_at` | DateTime |  |  |  |
| 33 | `updated_at` | DateTime |  |  |  |
| 34 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 35 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 36 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `import_staging_records`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `job_id` | Var Char(50) |  | Y | FK -> import_jobs.id. |
| 3 | `row_number` | Int |  | Y |  |
| 4 | `source_row_ref` | Var Char(100) |  |  |  |
| 5 | `raw_data` | Text(10000) |  |  | JSON-encoded source values. |
| 6 | `mapped_data` | Text(10000) |  |  | JSON-encoded normalized values. |
| 7 | `validation_status` | Var Char(20) |  | Y |  |
| 8 | `validation_errors` | Text(10000) |  |  |  |
| 9 | `validation_warnings` | Text(10000) |  |  |  |
| 10 | `duplicate_status` | Var Char(30) |  | Y |  |
| 11 | `duplicate_of` | Text(10000) |  |  |  |
| 12 | `reconciliation_status` | Var Char(30) |  | Y |  |
| 13 | `reconciliation_details` | Text(10000) |  |  |  |
| 14 | `trust_level` | Var Char(30) |  | Y |  |
| 15 | `promoted` | Boolean |  |  |  |
| 16 | `promoted_record_id` | Var Char(50) |  |  |  |
| 17 | `promoted_at` | DateTime |  |  |  |
| 18 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 19 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |

## `interventions`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `district` | Var Char(100) |  | Y |  |
| 3 | `intervention_type` | Var Char(50) |  | Y |  |
| 4 | `title` | Var Char(255) |  | Y |  |
| 5 | `description` | Text(10000) |  |  |  |
| 6 | `started_at` | DateTime |  | Y |  |
| 7 | `ended_at` | DateTime |  |  |  |
| 8 | `status` | Var Char(20) |  |  |  |
| 9 | `created_by_id` | Var Char(50) |  |  | FK -> users.id (nullable). |
| 10 | `created_at` | DateTime |  |  |  |
| 11 | `updated_at` | DateTime |  |  |  |
| 12 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 13 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 14 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `revoked_tokens`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `jti` | Var Char(64) | Y | Y | Natural logical PK (JWT id), not a UUID. |
| 2 | `revoked_at` | DateTime |  |  |  |
| 3 | `expires_at` | DateTime |  | Y |  |
| 4 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 5 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 6 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `system_settings`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `key` | Var Char(100) | Y | Y |  |
| 3 | `value` | Text(10000) |  |  |  |
| 4 | `description` | Text(10000) |  |  | Var Char>255 -> Text in Catalyst. |
| 5 | `created_at` | DateTime |  |  |  |
| 6 | `updated_at` | DateTime |  |  |  |
| 7 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 8 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 9 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |

## `role_permissions`

| # | Column | Catalyst data type | Unique | Mandatory | Notes |
|---|--------|-------------------|--------|-----------|-------|
| 1 | `id` | Var Char(50) | Y | Y | Logical PK. |
| 2 | `role_id` | Var Char(50) |  | Y | FK -> roles.id. |
| 3 | `permission` | Var Char(100) |  | Y |  |
| 4 | `resource` | Var Char(100) |  | Y |  |
| 5 | `created_at` | DateTime |  |  |  |
| 6 | `dataset_provenance` | Var Char(20) |  |  | Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164). |
| 7 | `source_file` | Text(10000) |  |  | Origin file, e.g. saksha_full_setup.sql (migration aid). |
| 8 | `source_row_ref` | Var Char(100) |  |  | Origin row reference (usally the seed INSERT row number). |
