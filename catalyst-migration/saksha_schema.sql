-- ============================================================
-- SAKSHA -> CATALYST DATA STORE MIGRATION SPEC
-- Style: PostgreSQL DDL mirroring schema_registry.py.
-- NOTE: The Data Store API/SDK/CLI cannot create this schema.
--       Tables + columns must be created in the Catalyst
--       console (Data Store > Create a new Table / +New Column).
-- ============================================================

-- roles
CREATE TABLE roles (
    id                           Var Char(50)       UNIQUE NOT NULL,
    name                         Var Char(50)       UNIQUE NOT NULL,
    description                  Var Char(255)     ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- users
CREATE TABLE users (
    id                           Var Char(50)       UNIQUE NOT NULL,
    username                     Var Char(100)      UNIQUE NOT NULL,
    email                        Var Char(255)      UNIQUE NOT NULL,
    full_name                    Var Char(255)      NOT NULL,
    hashed_password              Text(10000)        NOT NULL,
    is_active                    Boolean           ,
    failed_login_attempts        Int               ,
    locked_until                 DateTime          ,
    role_id                      Var Char(50)       NOT NULL,
    district                     Var Char(100)     ,
    station                      Var Char(100)     ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- officers
CREATE TABLE officers (
    id                           Var Char(50)       UNIQUE NOT NULL,
    supabase_user_id             Var Char(50)      ,
    user_id                      Var Char(50)       UNIQUE,
    badge_number                 Var Char(50)       UNIQUE NOT NULL,
    name                         Var Char(255)      NOT NULL,
    rank                         Var Char(100)     ,
    station                      Var Char(100)      NOT NULL,
    district                     Var Char(100)     ,
    designation                  Var Char(100)     ,
    phone                        Var Char(20)      ,
    email                        Var Char(255)      UNIQUE,
    status                       Var Char(50)      ,
    image_url                    Text(10000)       ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- locations
CREATE TABLE locations (
    id                           Var Char(50)       UNIQUE NOT NULL,
    address                      Text(10000)       ,
    district                     Var Char(100)      NOT NULL,
    station                      Var Char(100)     ,
    latitude                     Double             NOT NULL,
    longitude                    Double             NOT NULL,
    pincode                      Var Char(10)      ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- crime_categories
CREATE TABLE crime_categories (
    id                           Var Char(50)       UNIQUE NOT NULL,
    name                         Var Char(150)      UNIQUE NOT NULL,
    section_code                 Var Char(50)      ,
    severity                     Var Char(20)      ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- crime_cases
CREATE TABLE crime_cases (
    id                           Var Char(50)       UNIQUE NOT NULL,
    case_number                  Var Char(50)       UNIQUE NOT NULL,
    category_id                  Var Char(50)       NOT NULL,
    location_id                  Var Char(50)       NOT NULL,
    occurred_at                  DateTime           NOT NULL,
    reported_at                  DateTime          ,
    description                  Text(10000)       ,
    mo_tags                      Text(10000)       ,
    status                       Var Char(30)      ,
    priority                     Var Char(30)      ,
    progress                     Int               ,
    assigned_officer_id          Var Char(50)      ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- criminals
CREATE TABLE criminals (
    id                           Var Char(50)       UNIQUE NOT NULL,
    full_name                    Var Char(255)      NOT NULL,
    aliases                      Text(10000)       ,
    date_of_birth                Date              ,
    gender                       Var Char(20)      ,
    address                      Text(10000)       ,
    identifying_marks            Text(10000)       ,
    mo_summary                   Text(10000)       ,
    status                       Var Char(30)      ,
    gang_affiliation             Var Char(255)     ,
    neo4j_node_id                Var Char(100)     ,
    image_url                    Text(10000)       ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- victims
CREATE TABLE victims (
    id                           Var Char(50)       UNIQUE NOT NULL,
    full_name                    Var Char(255)      NOT NULL,
    contact_number               Var Char(20)      ,
    address                      Text(10000)       ,
    gender                       Var Char(20)      ,
    age                          Int               ,
    statement                    Text(10000)       ,
    neo4j_node_id                Var Char(100)     ,
    image_url                    Text(10000)       ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- firs
CREATE TABLE firs (
    id                           Var Char(50)       UNIQUE NOT NULL,
    fir_number                   Var Char(50)       UNIQUE NOT NULL,
    crime_case_id                Var Char(50)       NOT NULL,
    investigating_officer_id     Var Char(50)      ,
    complainant_name             Var Char(255)      NOT NULL,
    complainant_contact          Var Char(20)      ,
    sections                     Var Char(255)     ,
    filed_at                     DateTime          ,
    status                       Var Char(30)      ,
    narrative                    Text(10000)       ,
    attachments                  Text(10000)       ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- fir_criminal_links
CREATE TABLE fir_criminal_links (
    id                           Var Char(50)       UNIQUE NOT NULL,
    fir_id                       Var Char(50)       NOT NULL,
    criminal_id                  Var Char(50)       NOT NULL,
    role                         Var Char(50)      ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- fir_victim_links
CREATE TABLE fir_victim_links (
    id                           Var Char(50)       UNIQUE NOT NULL,
    fir_id                       Var Char(50)       NOT NULL,
    victim_id                    Var Char(50)       NOT NULL,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- evidence
CREATE TABLE evidence (
    id                           Var Char(50)       UNIQUE NOT NULL,
    case_id                      Var Char(50)       NOT NULL,
    title                        Var Char(255)      NOT NULL,
    description                  Text(10000)       ,
    evidence_type                Var Char(50)       NOT NULL,
    status                       Var Char(50)      ,
    created_by                   Var Char(255)     ,
    assigned_to                  Var Char(50)      ,
    storage_path                 Text(10000)       ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- evidence_metadata
CREATE TABLE evidence_metadata (
    id                           Var Char(50)       UNIQUE NOT NULL,
    evidence_id                  Var Char(50)       UNIQUE NOT NULL,
    filename                     Var Char(255)      NOT NULL,
    filepath                     Text(10000)        NOT NULL,
    filesize                     Int                NOT NULL,
    mime_type                    Var Char(100)      NOT NULL,
    uploaded_by                  Var Char(255)     ,
    storage_url                  Text(10000)       ,
    extracted_data               Text(10000)       ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- evidence_timeline
CREATE TABLE evidence_timeline (
    id                           Var Char(50)       UNIQUE NOT NULL,
    evidence_id                  Var Char(50)       NOT NULL,
    action                       Var Char(100)      NOT NULL,
    performed_by                 Var Char(255)      NOT NULL,
    role                         Var Char(100)      NOT NULL,
    description                  Text(10000)       ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- evidence_assignments
CREATE TABLE evidence_assignments (
    id                           Var Char(50)       UNIQUE NOT NULL,
    evidence_id                  Var Char(50)       NOT NULL,
    assigned_by                  Var Char(50)       NOT NULL,
    assigned_to                  Var Char(50)       NOT NULL,
    status                       Var Char(50)      ,
    assigned_at                  DateTime          ,
    accepted_at                  DateTime          ,
    completed_at                 DateTime          ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- evidence_ai_summary
CREATE TABLE evidence_ai_summary (
    id                           Var Char(50)       UNIQUE NOT NULL,
    evidence_id                  Var Char(50)       NOT NULL,
    summary                      Text(10000)        NOT NULL,
    model                        Var Char(100)      NOT NULL,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- chain_of_custody
CREATE TABLE chain_of_custody (
    id                           Var Char(50)       UNIQUE NOT NULL,
    evidence_id                  Var Char(50)       NOT NULL,
    from_user                    Var Char(50)      ,
    to_user                      Var Char(50)      ,
    action                       Var Char(100)      NOT NULL,
    location                     Var Char(255)     ,
    remarks                      Text(10000)       ,
    timestamp                    DateTime          ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- audit_logs
CREATE TABLE audit_logs (
    id                           Var Char(50)       UNIQUE NOT NULL,
    user_id                      Var Char(50)       NOT NULL,
    action                       Var Char(50)       NOT NULL,
    resource_type                Var Char(100)      NOT NULL,
    resource_id                  Var Char(100)     ,
    details                      Text(10000)       ,
    ip_address                   Var Char(50)      ,
    timestamp                    DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- notifications
CREATE TABLE notifications (
    id                           Var Char(50)       UNIQUE NOT NULL,
    user_id                      Var Char(50)      ,
    sender_id                    Var Char(50)      ,
    subject                      Text(10000)        NOT NULL,
    notification_type            Var Char(50)       NOT NULL,
    category                     Var Char(50)       NOT NULL,
    title                        Var Char(255)      NOT NULL,
    message                      Text(10000)        NOT NULL,
    severity                     Var Char(20)       NOT NULL,
    priority                     Var Char(20)       NOT NULL,
    status                       Var Char(20)       NOT NULL,
    resource_type                Var Char(50)      ,
    resource_id                  Var Char(100)     ,
    related_case_number          Var Char(50)      ,
    related_fir_number           Var Char(50)      ,
    is_read                      Boolean           ,
    is_dismissed                 Boolean           ,
    is_broadcast                 Boolean           ,
    parent_id                    Var Char(50)      ,
    attachment_url               Text(10000)       ,
    created_at                   DateTime          ,
    read_at                      DateTime          ,
    acknowledged_at              DateTime          ,
    resolved_at                  DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- reports
CREATE TABLE reports (
    id                           Var Char(50)       UNIQUE NOT NULL,
    template                     Var Char(100)      NOT NULL,
    requested_by_id              Var Char(50)       NOT NULL,
    district                     Var Char(100)     ,
    date_from                    DateTime          ,
    date_to                      DateTime          ,
    format                       Var Char(10)      ,
    status                       Var Char(20)      ,
    file_url                     Text(10000)       ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- investigation_notes
CREATE TABLE investigation_notes (
    id                           Var Char(50)       UNIQUE NOT NULL,
    case_id                      Var Char(50)       NOT NULL,
    officer_id                   Var Char(50)      ,
    officer_name                 Var Char(255)      NOT NULL,
    officer_badge                Var Char(50)       NOT NULL,
    content                      Text(10000)        NOT NULL,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- mo_tags
CREATE TABLE mo_tags (
    id                           Var Char(50)       UNIQUE NOT NULL,
    name                         Var Char(120)      UNIQUE NOT NULL,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- case_mo_tags
CREATE TABLE case_mo_tags (
    case_id                      Var Char(50)       NOT NULL,
    mo_tag_id                    Var Char(50)       NOT NULL,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- criminal_mo_tags
CREATE TABLE criminal_mo_tags (
    criminal_id                  Var Char(50)       NOT NULL,
    mo_tag_id                    Var Char(50)       NOT NULL,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- chat_conversations
CREATE TABLE chat_conversations (
    id                           Var Char(50)       UNIQUE NOT NULL,
    user_id                      Var Char(50)       NOT NULL,
    title                        Var Char(200)      NOT NULL,
    is_temporary                 Boolean           ,
    message_count                Int               ,
    last_message_at              DateTime          ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- chat_messages
CREATE TABLE chat_messages (
    id                           Var Char(50)       UNIQUE NOT NULL,
    conversation_id              Var Char(50)       NOT NULL,
    role                         Var Char(16)       NOT NULL,
    content                      Text(10000)        NOT NULL,
    classification               Var Char(50)      ,
    sources_json                 Text(10000)       ,
    citations_json               Text(10000)       ,
    seq                          Int               ,
    created_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- import_jobs
CREATE TABLE import_jobs (
    id                           Var Char(50)       UNIQUE NOT NULL,
    entity_type                  Var Char(50)       NOT NULL,
    source_format                Var Char(10)       NOT NULL,
    mapping_profile              Var Char(50)       NOT NULL,
    source_system                Var Char(100)      NOT NULL,
    filename                     Text(10000)       ,
    status                       Var Char(30)      ,
    total_rows                   Int               ,
    imported_rows                Int               ,
    failed_rows                  Int               ,
    valid_rows                   Int               ,
    invalid_rows                 Int               ,
    warning_rows                 Int               ,
    exact_duplicate_rows         Int               ,
    potential_duplicate_rows     Int               ,
    conflict_rows                Int               ,
    new_record_rows              Int               ,
    matched_record_rows          Int               ,
    updated_record_rows          Int               ,
    rejected_rows                Int               ,
    review_rows                  Int               ,
    error_count                  Int               ,
    promoted_rows                Int               ,
    quality_grade                Var Char(10)      ,
    processing_started_at        DateTime          ,
    processing_completed_at      DateTime          ,
    promoted_at                  DateTime          ,
    rolled_back_at               DateTime          ,
    validation_report            Text(10000)       ,
    created_by_id                Var Char(50)      ,
    promoted_by_id               Var Char(50)      ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- import_staging_records
CREATE TABLE import_staging_records (
    id                           Var Char(50)       UNIQUE NOT NULL,
    job_id                       Var Char(50)       NOT NULL,
    row_number                   Int                NOT NULL,
    source_row_ref               Var Char(100)     ,
    raw_data                     Text(10000)       ,
    mapped_data                  Text(10000)       ,
    validation_status            Var Char(20)       NOT NULL,
    validation_errors            Text(10000)       ,
    validation_warnings          Text(10000)       ,
    duplicate_status             Var Char(30)       NOT NULL,
    duplicate_of                 Text(10000)       ,
    reconciliation_status        Var Char(30)       NOT NULL,
    reconciliation_details       Text(10000)       ,
    trust_level                  Var Char(30)       NOT NULL,
    promoted                     Boolean           ,
    promoted_record_id           Var Char(50)      ,
    promoted_at                  DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       
);

-- interventions
CREATE TABLE interventions (
    id                           Var Char(50)       UNIQUE NOT NULL,
    district                     Var Char(100)      NOT NULL,
    intervention_type            Var Char(50)       NOT NULL,
    title                        Var Char(255)      NOT NULL,
    description                  Text(10000)       ,
    started_at                   DateTime           NOT NULL,
    ended_at                     DateTime          ,
    status                       Var Char(20)      ,
    created_by_id                Var Char(50)      ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- revoked_tokens
CREATE TABLE revoked_tokens (
    jti                          Var Char(64)       UNIQUE NOT NULL,
    revoked_at                   DateTime          ,
    expires_at                   DateTime           NOT NULL,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- system_settings
CREATE TABLE system_settings (
    id                           Var Char(50)       UNIQUE NOT NULL,
    key                          Var Char(100)      UNIQUE NOT NULL,
    value                        Text(10000)       ,
    description                  Text(10000)       ,
    created_at                   DateTime          ,
    updated_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

-- role_permissions
CREATE TABLE role_permissions (
    id                           Var Char(50)       UNIQUE NOT NULL,
    role_id                      Var Char(50)       NOT NULL,
    permission                   Var Char(100)      NOT NULL,
    resource                     Var Char(100)      NOT NULL,
    created_at                   DateTime          ,
    dataset_provenance           Var Char(20)      ,
    source_file                  Text(10000)       ,
    source_row_ref               Var Char(100)     
);

