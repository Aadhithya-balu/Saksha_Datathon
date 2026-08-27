"""Single source of truth for the SAKSHA -> Catalyst Data Store migration.

Column encoding keys:
    "uuid"             -> Catalyst "Var Char" (50)  (logical PK / FK, stored as lowercase text)
    "varchar:<n>"      -> Catalyst "Var Char" (<n>)  when n <= 255 else Catalyst "Text"
    "text"             -> Catalyst "Text"   (max 10,000 chars, per Zoho docs)
    "json"             -> Catalyst "Text"   (JSON-encoded string; Catalyst DS has no JSON type)
    "datetime"         -> Catalyst "DateTime" (YYYY-MM-DD HH:MM:SS, UTC)
    "date"             -> Catalyst "Date"    (YYYY-MM-DD)
    "int"              -> Catalyst "Int"     (4-byte)
    "double"           -> Catalyst "Double"
    "bool"             -> Catalyst "Boolean"

Flags:
    unique   -> set IsUnique = true in the console
    mandatory-> set IsMandatory = true in the console
    note     -> human guidance for the console operator

Provenance triplet (dataset_provenance, source_file, source_row_ref) is appended
programmatically to every table (see PROVENANCE_COLUMNS) so the DEMO/SEED status
and lineage of each migrated record survives the move.
"""

# ---------------------------------------------------------------------------
# Columns appended to every table to preserve the upstream lineage.
# ---------------------------------------------------------------------------
PROVENANCE_COLUMNS = [
    ("dataset_provenance", "varchar:20", {
        "note": "Source data class: 'demo' for the seed bundle, 'live' or 'migrated' otherwise (Issue #164)."}),
    ("source_file", "varchar:500", {
        "note": "Origin file, e.g. saksha_full_setup.sql (migration aid)."}),
    ("source_row_ref", "varchar:100", {
        "note": "Origin row reference (usally the seed INSERT row number)."}),
]

# column defaults applied for seeded rows when the INSERT omits them
TIMESTAMP_FILLERS = ("created_at", "updated_at", "timestamp")

# Deterministic-UUID generation for pure join tables whose seed omits `id`
# (so the preserved logical `id` is unique and reproducible).
LINK_TABLES_WITH_SYNTH_ID = ("fir_criminal_links", "fir_victim_links")

# ---------------------------------------------------------------------------
# Table -> [(column, pg_key, {flags})]
# ---------------------------------------------------------------------------
TABLES = {
    "roles": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK (UUID from Postgres)."}),
        ("name", "varchar:50", {"unique": True, "mandatory": True, "note": "RBAC role name."}),
        ("description", "varchar:255", {}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "users": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("username", "varchar:100", {"unique": True, "mandatory": True}),
        ("email", "varchar:255", {"unique": True, "mandatory": True}),
        ("full_name", "varchar:255", {"mandatory": True}),
        ("hashed_password", "varchar:400", {"mandatory": True, "note": "Var Char>255 -> Text in Catalyst."}),
        ("is_active", "bool", {}),
        ("failed_login_attempts", "int", {"note": "Account-lockout counter (ORM default 0)."}),
        ("locked_until", "datetime", {}),
        ("role_id", "uuid", {"mandatory": True, "note": "FK -> roles.id (stored as plain Var Char, joined by value)."}),
        ("district", "varchar:100", {}),
        ("station", "varchar:100", {}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "officers": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("supabase_user_id", "uuid", {"note": "Legacy Supabase user reference (nullable after migration)."}),
        ("user_id", "uuid", {"unique": True, "note": "FK -> users.id."}),
        ("badge_number", "varchar:50", {"unique": True, "mandatory": True}),
        ("name", "varchar:255", {"mandatory": True}),
        ("rank", "varchar:100", {}),
        ("station", "varchar:100", {"mandatory": True}),
        ("district", "varchar:100", {}),
        ("designation", "varchar:100", {}),
        ("phone", "varchar:20", {}),
        ("email", "varchar:255", {"unique": True}),
        ("status", "varchar:50", {}),
        ("image_url", "varchar:1000", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "locations": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("address", "varchar:500", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("district", "varchar:100", {"mandatory": True}),
        ("station", "varchar:100", {}),
        ("latitude", "double", {"mandatory": True}),
        ("longitude", "double", {"mandatory": True}),
        ("pincode", "varchar:10", {}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "crime_categories": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("name", "varchar:150", {"unique": True, "mandatory": True}),
        ("section_code", "varchar:50", {}),
        ("severity", "varchar:20", {}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "crime_cases": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("case_number", "varchar:50", {"unique": True, "mandatory": True}),
        ("category_id", "uuid", {"mandatory": True, "note": "FK -> crime_categories.id."}),
        ("location_id", "uuid", {"mandatory": True, "note": "FK -> locations.id."}),
        ("occurred_at", "datetime", {"mandatory": True}),
        ("reported_at", "datetime", {}),
        ("description", "text", {}),
        ("mo_tags", "varchar:500", {"note": "Denormalized legacy tag string."}),
        ("status", "varchar:30", {}),
        ("priority", "varchar:30", {}),
        ("progress", "int", {}),
        ("assigned_officer_id", "uuid", {"note": "FK -> officers.id (nullable)."}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "criminals": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("full_name", "varchar:255", {"mandatory": True}),
        ("aliases", "varchar:500", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("date_of_birth", "date", {}),
        ("gender", "varchar:20", {}),
        ("address", "varchar:500", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("identifying_marks", "text", {}),
        ("mo_summary", "text", {}),
        ("status", "varchar:30", {}),
        ("gang_affiliation", "varchar:255", {}),
        ("neo4j_node_id", "varchar:100", {}),
        ("image_url", "varchar:1000", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "victims": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("full_name", "varchar:255", {"mandatory": True}),
        ("contact_number", "varchar:20", {}),
        ("address", "varchar:500", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("gender", "varchar:20", {}),
        ("age", "int", {}),
        ("statement", "text", {}),
        ("neo4j_node_id", "varchar:100", {}),
        ("image_url", "varchar:1000", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "firs": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("fir_number", "varchar:50", {"unique": True, "mandatory": True}),
        ("crime_case_id", "uuid", {"mandatory": True, "note": "FK -> crime_cases.id."}),
        ("investigating_officer_id", "uuid", {"note": "FK -> officers.id (nullable)."}),
        ("complainant_name", "varchar:255", {"mandatory": True}),
        ("complainant_contact", "varchar:20", {}),
        ("sections", "varchar:255", {}),
        ("filed_at", "datetime", {}),
        ("status", "varchar:30", {}),
        ("narrative", "text", {}),
        ("attachments", "text", {"note": "JSON-encoded attachment array (Text in Catalyst)."}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "fir_criminal_links": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK (deterministic UUID synthesised at CSV build)."}),
        ("fir_id", "uuid", {"mandatory": True, "note": "FK -> firs.id."}),
        ("criminal_id", "uuid", {"mandatory": True, "note": "FK -> criminals.id."}),
        ("role", "varchar:50", {}),
    ],
    "fir_victim_links": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK (deterministic UUID synthesised at CSV build)."}),
        ("fir_id", "uuid", {"mandatory": True, "note": "FK -> firs.id."}),
        ("victim_id", "uuid", {"mandatory": True, "note": "FK -> victims.id."}),
    ],
    "evidence": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("case_id", "uuid", {"mandatory": True, "note": "FK -> crime_cases.id."}),
        ("title", "varchar:255", {"mandatory": True}),
        ("description", "text", {}),
        ("evidence_type", "varchar:50", {"mandatory": True}),
        ("status", "varchar:50", {}),
        ("created_by", "varchar:255", {}),
        ("assigned_to", "uuid", {"note": "FK -> users.id (nullable)."}),
        ("storage_path", "varchar:500", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "evidence_metadata": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("evidence_id", "uuid", {"unique": True, "mandatory": True, "note": "FK -> evidence.id."}),
        ("filename", "varchar:255", {"mandatory": True}),
        ("filepath", "varchar:500", {"mandatory": True, "note": "Var Char>255 -> Text in Catalyst."}),
        ("filesize", "int", {"mandatory": True}),
        ("mime_type", "varchar:100", {"mandatory": True}),
        ("uploaded_by", "varchar:255", {}),
        ("storage_url", "varchar:1000", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("extracted_data", "json", {"note": "JSON -> Text (JSON-encoded string) in Catalyst."}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "evidence_timeline": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("evidence_id", "uuid", {"mandatory": True, "note": "FK -> evidence.id."}),
        ("action", "varchar:100", {"mandatory": True}),
        ("performed_by", "varchar:255", {"mandatory": True}),
        ("role", "varchar:100", {"mandatory": True}),
        ("description", "text", {}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "evidence_assignments": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("evidence_id", "uuid", {"mandatory": True, "note": "FK -> evidence.id."}),
        ("assigned_by", "uuid", {"mandatory": True, "note": "FK -> users.id."}),
        ("assigned_to", "uuid", {"mandatory": True, "note": "FK -> users.id."}),
        ("status", "varchar:50", {}),
        ("assigned_at", "datetime", {}),
        ("accepted_at", "datetime", {}),
        ("completed_at", "datetime", {}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "evidence_ai_summary": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("evidence_id", "uuid", {"mandatory": True, "note": "FK -> evidence.id."}),
        ("summary", "text", {"mandatory": True}),
        ("model", "varchar:100", {"mandatory": True}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "chain_of_custody": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("evidence_id", "uuid", {"mandatory": True, "note": "FK -> evidence.id."}),
        ("from_user", "uuid", {"note": "FK -> users.id (nullable)."}),
        ("to_user", "uuid", {"note": "FK -> users.id (nullable)."}),
        ("action", "varchar:100", {"mandatory": True}),
        ("location", "varchar:255", {}),
        ("remarks", "text", {}),
        ("timestamp", "datetime", {}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "audit_logs": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("user_id", "uuid", {"mandatory": True, "note": "FK -> users.id."}),
        ("action", "varchar:50", {"mandatory": True}),
        ("resource_type", "varchar:100", {"mandatory": True}),
        ("resource_id", "varchar:100", {}),
        ("details", "varchar:1000", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("ip_address", "varchar:50", {}),
        ("timestamp", "datetime", {}),
    ],
    "notifications": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("user_id", "uuid", {"note": "FK -> users.id (nullable: broadcast/system feeds)."}),
        ("sender_id", "uuid", {"note": "FK -> users.id (nullable)."}),
        ("subject", "varchar:500", {"mandatory": True, "note": "Var Char>255 -> Text in Catalyst."}),
        ("notification_type", "varchar:50", {"mandatory": True}),
        ("category", "varchar:50", {"mandatory": True}),
        ("title", "varchar:255", {"mandatory": True}),
        ("message", "text", {"mandatory": True}),
        ("severity", "varchar:20", {"mandatory": True}),
        ("priority", "varchar:20", {"mandatory": True}),
        ("status", "varchar:20", {"mandatory": True}),
        ("resource_type", "varchar:50", {}),
        ("resource_id", "varchar:100", {}),
        ("related_case_number", "varchar:50", {}),
        ("related_fir_number", "varchar:50", {}),
        ("is_read", "bool", {}),
        ("is_dismissed", "bool", {}),
        ("is_broadcast", "bool", {}),
        ("parent_id", "uuid", {"note": "Self FK -> notifications.id (nullable)."}),
        ("attachment_url", "varchar:500", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("created_at", "datetime", {}),
        ("read_at", "datetime", {}),
        ("acknowledged_at", "datetime", {}),
        ("resolved_at", "datetime", {}),
    ],
    "reports": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("template", "varchar:100", {"mandatory": True}),
        ("requested_by_id", "uuid", {"mandatory": True, "note": "FK -> users.id."}),
        ("district", "varchar:100", {}),
        ("date_from", "datetime", {}),
        ("date_to", "datetime", {}),
        ("format", "varchar:10", {}),
        ("status", "varchar:20", {}),
        ("file_url", "varchar:500", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "investigation_notes": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("case_id", "uuid", {"mandatory": True, "note": "FK -> crime_cases.id."}),
        ("officer_id", "uuid", {"note": "FK -> officers.id (nullable)."}),
        ("officer_name", "varchar:255", {"mandatory": True}),
        ("officer_badge", "varchar:50", {"mandatory": True}),
        ("content", "text", {"mandatory": True}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "mo_tags": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("name", "varchar:120", {"unique": True, "mandatory": True}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "case_mo_tags": [
        ("case_id", "uuid", {"mandatory": True, "note": "Composite logical PK with mo_tag_id; FK -> crime_cases.id."}),
        ("mo_tag_id", "uuid", {"mandatory": True, "note": "Composite logical PK; FK -> mo_tags.id."}),
    ],
    "criminal_mo_tags": [
        ("criminal_id", "uuid", {"mandatory": True, "note": "Composite logical PK with mo_tag_id; FK -> criminals.id."}),
        ("mo_tag_id", "uuid", {"mandatory": True, "note": "Composite logical PK; FK -> mo_tags.id."}),
    ],
    "chat_conversations": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("user_id", "uuid", {"mandatory": True, "note": "FK -> users.id."}),
        ("title", "varchar:200", {"mandatory": True}),
        ("is_temporary", "bool", {}),
        ("message_count", "int", {}),
        ("last_message_at", "datetime", {}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "chat_messages": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("conversation_id", "uuid", {"mandatory": True, "note": "FK -> chat_conversations.id."}),
        ("role", "varchar:16", {"mandatory": True}),
        ("content", "text", {"mandatory": True}),
        ("classification", "varchar:50", {}),
        ("sources_json", "json", {"note": "JSON -> Text in Catalyst."}),
        ("citations_json", "json", {"note": "JSON -> Text in Catalyst."}),
        ("seq", "int", {}),
        ("created_at", "datetime", {}),
    ],
    "import_jobs": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("entity_type", "varchar:50", {"mandatory": True}),
        ("source_format", "varchar:10", {"mandatory": True}),
        ("mapping_profile", "varchar:50", {"mandatory": True}),
        ("source_system", "varchar:100", {"mandatory": True}),
        ("filename", "varchar:500", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("status", "varchar:30", {}),
        ("total_rows", "int", {}),
        ("imported_rows", "int", {}),
        ("failed_rows", "int", {}),
        ("valid_rows", "int", {}),
        ("invalid_rows", "int", {}),
        ("warning_rows", "int", {}),
        ("exact_duplicate_rows", "int", {}),
        ("potential_duplicate_rows", "int", {}),
        ("conflict_rows", "int", {}),
        ("new_record_rows", "int", {}),
        ("matched_record_rows", "int", {}),
        ("updated_record_rows", "int", {}),
        ("rejected_rows", "int", {}),
        ("review_rows", "int", {}),
        ("error_count", "int", {}),
        ("promoted_rows", "int", {}),
        ("quality_grade", "varchar:10", {}),
        ("processing_started_at", "datetime", {}),
        ("processing_completed_at", "datetime", {}),
        ("promoted_at", "datetime", {}),
        ("rolled_back_at", "datetime", {}),
        ("validation_report", "text", {"note": "JSON-encoded validation report."}),
        ("created_by_id", "uuid", {"note": "FK -> users.id (nullable)."}),
        ("promoted_by_id", "uuid", {"note": "FK -> users.id (nullable)."}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "import_staging_records": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("job_id", "uuid", {"mandatory": True, "note": "FK -> import_jobs.id."}),
        ("row_number", "int", {"mandatory": True}),
        ("source_row_ref", "varchar:100", {}),
        ("raw_data", "text", {"note": "JSON-encoded source values."}),
        ("mapped_data", "text", {"note": "JSON-encoded normalized values."}),
        ("validation_status", "varchar:20", {"mandatory": True}),
        ("validation_errors", "text", {}),
        ("validation_warnings", "text", {}),
        ("duplicate_status", "varchar:30", {"mandatory": True}),
        ("duplicate_of", "text", {}),
        ("reconciliation_status", "varchar:30", {"mandatory": True}),
        ("reconciliation_details", "text", {}),
        ("trust_level", "varchar:30", {"mandatory": True}),
        ("promoted", "bool", {}),
        ("promoted_record_id", "uuid", {}),
        ("promoted_at", "datetime", {}),
    ],
    "interventions": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("district", "varchar:100", {"mandatory": True}),
        ("intervention_type", "varchar:50", {"mandatory": True}),
        ("title", "varchar:255", {"mandatory": True}),
        ("description", "text", {}),
        ("started_at", "datetime", {"mandatory": True}),
        ("ended_at", "datetime", {}),
        ("status", "varchar:20", {}),
        ("created_by_id", "uuid", {"note": "FK -> users.id (nullable)."}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "revoked_tokens": [
        ("jti", "varchar:64", {"unique": True, "mandatory": True, "note": "Natural logical PK (JWT id), not a UUID."}),
        ("revoked_at", "datetime", {}),
        ("expires_at", "datetime", {"mandatory": True}),
    ],
    # --- Legacy admin tables present in saksha_full_setup.sql but WITHOUT ORM
    # models (not created by SQLAlchemy create_all). Included so a live DB that
    # was provisioned from the uploaded SQL can also be fully migrated.
    "system_settings": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("key", "varchar:100", {"unique": True, "mandatory": True}),
        ("value", "text", {}),
        ("description", "varchar:500", {"note": "Var Char>255 -> Text in Catalyst."}),
        ("created_at", "datetime", {}),
        ("updated_at", "datetime", {}),
    ],
    "role_permissions": [
        ("id", "uuid", {"unique": True, "mandatory": True, "note": "Logical PK."}),
        ("role_id", "uuid", {"mandatory": True, "note": "FK -> roles.id."}),
        ("permission", "varchar:100", {"mandatory": True}),
        ("resource", "varchar:100", {"mandatory": True}),
        ("created_at", "datetime", {}),
    ],
}

# Order to emit (and therefore to create columns) in the console.
TABLE_ORDER = [
    "roles", "users", "officers", "locations", "crime_categories",
    "crime_cases", "criminals", "victims", "firs",
    "fir_criminal_links", "fir_victim_links", "evidence",
    "evidence_metadata", "evidence_timeline", "evidence_assignments",
    "evidence_ai_summary", "chain_of_custody", "audit_logs",
    "notifications", "reports", "investigation_notes",
    "mo_tags", "case_mo_tags", "criminal_mo_tags",
    "chat_conversations", "chat_messages", "import_jobs",
    "import_staging_records", "interventions", "revoked_tokens",
    "system_settings", "role_permissions",
]


def catalyst_type(pg_key: str) -> tuple[str, int | None]:
    """Return (data_type, max_length) for Catalyst, or 0/None where N/A."""
    if pg_key == "uuid":
        return "Var Char", 50
    if pg_key.startswith("varchar:"):
        n = int(pg_key.split(":", 1)[1])
        return ("Var Char", n) if n <= 255 else ("Text", 10000)
    if pg_key == "text":
        return "Text", 10000
    if pg_key == "json":
        return "Text", 10000
    if pg_key == "datetime":
        return "DateTime", None
    if pg_key == "date":
        return "Date", None
    if pg_key == "int":
        return "Int", None
    if pg_key == "double":
        return "Double", None
    if pg_key == "bool":
        return "Boolean", None
    raise ValueError(f"Unknown pg type key: {pg_key}")


def full_columns(table: str) -> list[tuple[str, str, dict]]:
    """Registry columns + provenance triplet, in emission order."""
    cols = list(TABLES[table])
    for cname, k, f in PROVENANCE_COLUMNS:
        if cname not in [c[0] for c in cols]:
            cols.append((cname, k, dict(f)))
    return cols


def expected_seed_counts() -> dict[str, int]:
    """Rows produced from the seed bundle per table (excluding header-only)."""
    return {
        "roles": 4, "users": 4, "officers": 2, "crime_categories": 8,
        "locations": 10, "criminals": 5, "victims": 5, "crime_cases": 11,
        "firs": 11, "fir_criminal_links": 9, "fir_victim_links": 7,
        "evidence": 11, "notifications": 12,
    }