-- ============================================================
-- SAKSHA DATABASE — Complete Schema + Seed Data
-- For import into a new Supabase PostgreSQL project
-- Run this in: Supabase Dashboard > SQL Editor
-- ============================================================
BEGIN;

-- Drop existing public schema
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO anon;
GRANT ALL ON SCHEMA public TO authenticated;
GRANT ALL ON SCHEMA public TO service_role;

-- ============================================================
-- ROLES
-- ============================================================
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_roles_name ON roles(name);

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    role_id UUID NOT NULL REFERENCES roles(id),
    district VARCHAR(100),
    station VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- ============================================================
-- OFFICERS
-- ============================================================
CREATE TABLE officers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_user_id UUID,
    user_id UUID UNIQUE REFERENCES users(id),
    badge_number VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    rank VARCHAR(100),
    station VARCHAR(100) NOT NULL,
    district VARCHAR(100),
    designation VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(255) UNIQUE,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_officers_badge ON officers(badge_number);
CREATE INDEX idx_officers_station ON officers(station);
CREATE INDEX idx_officers_district ON officers(district);

-- ============================================================
-- LOCATIONS
-- ============================================================
CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address VARCHAR(500),
    district VARCHAR(100) NOT NULL,
    station VARCHAR(100),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    pincode VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_locations_district ON locations(district);
CREATE INDEX idx_locations_station ON locations(station);

-- ============================================================
-- CRIME CATEGORIES
-- ============================================================
CREATE TABLE crime_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) UNIQUE NOT NULL,
    section_code VARCHAR(50),
    severity VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_crime_categories_name ON crime_categories(name);

-- ============================================================
-- CRIME CASES
-- ============================================================
CREATE TABLE crime_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_number VARCHAR(50) UNIQUE NOT NULL,
    category_id UUID NOT NULL REFERENCES crime_categories(id),
    location_id UUID NOT NULL REFERENCES locations(id),
    occurred_at TIMESTAMPTZ NOT NULL,
    reported_at TIMESTAMPTZ DEFAULT now(),
    description TEXT,
    mo_tags VARCHAR(500),
    status VARCHAR(30) DEFAULT 'open',
    priority VARCHAR(30) DEFAULT 'medium',
    progress INTEGER DEFAULT 10,
    assigned_officer_id UUID REFERENCES officers(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_crime_cases_case_number ON crime_cases(case_number);
CREATE INDEX idx_crime_cases_occurred_at ON crime_cases(occurred_at);
CREATE INDEX idx_crime_cases_status ON crime_cases(status);

-- ============================================================
-- CRIMINALS
-- ============================================================
CREATE TABLE criminals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(255) NOT NULL,
    aliases VARCHAR(500),
    date_of_birth DATE,
    gender VARCHAR(20),
    address VARCHAR(500),
    identifying_marks TEXT,
    mo_summary TEXT,
    status VARCHAR(30) DEFAULT 'at_large',
    neo4j_node_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_criminals_full_name ON criminals(full_name);
CREATE INDEX idx_criminals_neo4j ON criminals(neo4j_node_id);

-- ============================================================
-- VICTIMS
-- ============================================================
CREATE TABLE victims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(255) NOT NULL,
    contact_number VARCHAR(20),
    address VARCHAR(500),
    gender VARCHAR(20),
    age INTEGER,
    statement TEXT,
    neo4j_node_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_victims_full_name ON victims(full_name);
CREATE INDEX idx_victims_neo4j ON victims(neo4j_node_id);

-- ============================================================
-- FIRs
-- ============================================================
CREATE TABLE firs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fir_number VARCHAR(50) UNIQUE NOT NULL,
    crime_case_id UUID NOT NULL REFERENCES crime_cases(id),
    investigating_officer_id UUID REFERENCES officers(id),
    complainant_name VARCHAR(255) NOT NULL,
    complainant_contact VARCHAR(20),
    sections VARCHAR(255),
    filed_at TIMESTAMPTZ DEFAULT now(),
    status VARCHAR(30) DEFAULT 'registered',
    narrative TEXT,
    attachments TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_firs_fir_number ON firs(fir_number);
CREATE INDEX idx_firs_status ON firs(status);

-- ============================================================
-- FIR-CRIMINAL LINKS
-- ============================================================
CREATE TABLE fir_criminal_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fir_id UUID NOT NULL REFERENCES firs(id),
    criminal_id UUID NOT NULL REFERENCES criminals(id),
    role VARCHAR(50)
);

-- ============================================================
-- FIR-VICTIM LINKS
-- ============================================================
CREATE TABLE fir_victim_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fir_id UUID NOT NULL REFERENCES firs(id),
    victim_id UUID NOT NULL REFERENCES victims(id)
);

-- ============================================================
-- EVIDENCE
-- ============================================================
CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES crime_cases(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    evidence_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'Pending',
    created_by VARCHAR(255),
    assigned_to UUID REFERENCES users(id),
    storage_path VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- EVIDENCE METADATA
-- ============================================================
CREATE TABLE evidence_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID UNIQUE NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    filesize INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    uploaded_by VARCHAR(255),
    storage_url VARCHAR(1000),
    extracted_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- EVIDENCE TIMELINE
-- ============================================================
CREATE TABLE evidence_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    performed_by VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- EVIDENCE ASSIGNMENTS
-- ============================================================
CREATE TABLE evidence_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    assigned_by UUID NOT NULL REFERENCES users(id),
    assigned_to UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'Assigned',
    assigned_at TIMESTAMPTZ DEFAULT now(),
    accepted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- EVIDENCE AI SUMMARY
-- ============================================================
CREATE TABLE evidence_ai_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    model VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- CHAIN OF CUSTODY
-- ============================================================
CREATE TABLE chain_of_custody (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    from_user UUID REFERENCES users(id),
    to_user UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    remarks TEXT,
    timestamp TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- AUDIT LOGS
-- ============================================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(100),
    details VARCHAR(1000),
    ip_address VARCHAR(50),
    timestamp TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    sender_id UUID REFERENCES users(id),
    subject VARCHAR(500) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'system_notification',
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    status VARCHAR(20) NOT NULL DEFAULT 'unread',
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    related_case_number VARCHAR(50),
    related_fir_number VARCHAR(50),
    is_read BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    is_broadcast BOOLEAN DEFAULT FALSE,
    parent_id UUID,
    attachment_url VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT now(),
    read_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ
);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_sender_id ON notifications(sender_id);
CREATE INDEX idx_notifications_type ON notifications(notification_type);
CREATE INDEX idx_notifications_category ON notifications(category);
CREATE INDEX idx_notifications_priority ON notifications(priority);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_case ON notifications(related_case_number);
CREATE INDEX idx_notifications_read ON notifications(is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at);

-- ============================================================
-- REPORTS
-- ============================================================
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template VARCHAR(100) NOT NULL,
    requested_by_id UUID NOT NULL REFERENCES users(id),
    district VARCHAR(100),
    date_from TIMESTAMPTZ,
    date_to TIMESTAMPTZ,
    format VARCHAR(10) DEFAULT 'pdf',
    status VARCHAR(20) DEFAULT 'queued',
    file_url VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_reports_status ON reports(status);

-- ============================================================
-- INVESTIGATION NOTES
-- ============================================================
CREATE TABLE investigation_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES crime_cases(id) ON DELETE CASCADE,
    officer_id UUID REFERENCES officers(id) ON DELETE SET NULL,
    officer_name VARCHAR(255) NOT NULL,
    officer_badge VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_investigation_notes_case ON investigation_notes(case_id);

-- ============================================================
-- SYSTEM SETTINGS
-- ============================================================
CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- ROLE PERMISSIONS
-- ============================================================
CREATE TABLE role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id),
    permission VARCHAR(100) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- SEED DATA — Fixed UUIDs for referential integrity
-- ============================================================

-- ROLES
INSERT INTO roles (id, name, description) VALUES
('a0000000-0000-0000-0000-000000000001', 'admin', 'admin role'),
('a0000000-0000-0000-0000-000000000002', 'crime_analyst', 'crime_analyst role'),
('a0000000-0000-0000-0000-000000000003', 'investigator', 'investigator role'),
('a0000000-0000-0000-0000-000000000004', 'policymaker', 'policymaker role');

-- PASSWORD HASHES (SHA-256 salt-based via security.hash_password)
-- admin: 564738, SCRB-7740: 123456, IO-3921: 456789, SP-0088: 987654
INSERT INTO users (id, username, email, full_name, hashed_password, is_active, role_id, district, station) VALUES
('b0000000-0000-0000-0000-000000000001', 'admin', 'admin@saksha.local', 'Platform Administrator', 'sha256$826b1ece4b4fc23b1beb9253266f7f4e$0ed4b9dd7cb98842efd506ab042fe26a5319d3cc1065dd36f3c13a7c0f789bca', TRUE, 'a0000000-0000-0000-0000-000000000001', 'State HQ', 'KSP HQ'),
('b0000000-0000-0000-0000-000000000002', 'SCRB-7740', 'scrb-7740@saksha.local', 'DCP Rajesh Kumar', 'sha256$ae618a1ff52d38bf6d109cc71495bad0$0e75ac02d2d8174217a9055272369cd5aef660231582e85388723cd3b816a0e1', TRUE, 'a0000000-0000-0000-0000-000000000002', 'Bengaluru Urban', 'SCRB HQ'),
('b0000000-0000-0000-0000-000000000003', 'IO-3921', 'io-3921@saksha.local', 'Inspector Meera Sen', 'sha256$360a587e137e92dbc7043661f63b2528$9e48cf9bca45d94a55495f53c18fd0ae35717975ab476663da13e6202a445ff7', TRUE, 'a0000000-0000-0000-0000-000000000003', 'Mysuru', 'Devaraja Police Station'),
('b0000000-0000-0000-0000-000000000004', 'SP-0088', 'sp-0088@saksha.local', 'SP Anil Kumble', 'sha256$62d62cb07eaed56d1ba2d32d25809ded$2cc7aa6eec58744c4e6148dce2885bb68b3a1a7ad8cef1423591084b33404068', TRUE, 'a0000000-0000-0000-0000-000000000004', 'State HQ', 'KSP HQ');

-- OFFICERS
INSERT INTO officers (id, user_id, badge_number, name, rank, station, district) VALUES
('c0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000003', 'IO-3921', 'Inspector Meera Sen', 'Inspector', 'Devaraja Police Station', 'Mysuru'),
('c0000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000004', 'SP-0088', 'SP Anil Kumble', 'Superintendent of Police', 'KSP HQ', 'State HQ');

-- CRIME CATEGORIES
INSERT INTO crime_categories (id, name, section_code, severity) VALUES
('d0000000-0000-0000-0000-000000000001', 'Cyber Crime & Online Fraud', 'IPC 420 / IT Act 66D', 'high'),
('d0000000-0000-0000-0000-000000000002', 'Theft & Burglaries', 'IPC 379/457', 'medium'),
('d0000000-0000-0000-0000-000000000003', 'Narcotics Smuggling Services', 'NDPS 21/22', 'high'),
('d0000000-0000-0000-0000-000000000004', 'Smuggling & Excise Violations', 'Excise Act', 'medium'),
('d0000000-0000-0000-0000-000000000005', 'Assault', 'IPC 323/324', 'medium'),
('d0000000-0000-0000-0000-000000000006', 'Illegal Mining Violations', 'MMDR Act', 'high'),
('d0000000-0000-0000-0000-000000000007', 'Domestic Violence', 'DV Act', 'medium'),
('d0000000-0000-0000-0000-000000000008', 'Property Disputes', 'IPC 447/506', 'low');

-- LOCATIONS
INSERT INTO locations (id, address, district, station, latitude, longitude, pincode) VALUES
('e0000000-0000-0000-0000-000000000001', 'Whitefield Cyber Cell Beat', 'Bengaluru Urban', 'Whitefield Police Station', 12.9698, 77.7500, '560066'),
('e0000000-0000-0000-0000-000000000002', 'KR Puram Transit Corridor', 'Bengaluru Urban', 'KR Puram Police Station', 13.0056, 77.6880, '560036'),
('e0000000-0000-0000-0000-000000000003', 'Devaraja Market Zone', 'Mysuru', 'Devaraja Police Station', 12.2958, 76.6394, '570001'),
('e0000000-0000-0000-0000-000000000004', 'Harbor Gate A', 'Mangaluru', 'Pandeshwar Police Station', 12.9050, 74.8350, '575001'),
('e0000000-0000-0000-0000-000000000005', 'Khade Bazar Checkpoint', 'Belagavi', 'Khade Bazar Station', 15.8497, 74.4977, '590001'),
('e0000000-0000-0000-0000-000000000006', 'Ballari Mines Sector B', 'Ballari', 'Rural Police Station', 15.1394, 76.9214, '583101'),
('e0000000-0000-0000-0000-000000000007', 'Chowk Survey Layout', 'Kalaburagi', 'Chowk Police Station', 17.3297, 76.8343, '585101'),
('e0000000-0000-0000-0000-000000000008', 'Hassan City East', 'Hassan', 'City Police Station', 13.0641, 76.1030, '573201'),
('e0000000-0000-0000-0000-000000000009', 'Tumkuru Industrial Road', 'Tumkuru', 'Town Police Station', 13.3379, 77.1173, '572101'),
('e0000000-0000-0000-0000-000000000010', 'Dharwad Market Yard', 'Dharwad', 'Suburban Police Station', 15.4589, 75.0078, '580001');

-- CRIMINALS
INSERT INTO criminals (id, full_name, aliases, date_of_birth, gender, identifying_marks, mo_summary, status) VALUES
('f0000000-0000-0000-0000-000000000001', 'Ramu Swamy', 'Kodaikanal Ramu', '1982-04-12', 'Male', 'Scar near left eyebrow', 'Night residential lock-break burglaries using scooter reconnaissance', 'at_large'),
('f0000000-0000-0000-0000-000000000002', 'Vikram Yadav', 'Vicky', '1990-11-07', 'Male', 'Spectacles, gold ring', 'Money mule coordinator for app-based cyber extortion', 'at_large'),
('f0000000-0000-0000-0000-000000000003', 'Sayed Ibrahim', 'Sayed', '1985-02-22', 'Male', 'Tattoo on right wrist', 'Port logistics support for synthetic drug consignments', 'at_large'),
('f0000000-0000-0000-0000-000000000004', 'Karthik Gowda', 'Gowda', '1988-08-03', 'Male', 'Thick moustache', 'Forgery and property document intimidation', 'arrested'),
('f0000000-0000-0000-0000-000000000005', 'Mohsin Pasha', 'Pasha', '1987-01-19', 'Male', 'Burn mark on forearm', 'Illegal mineral transport and forged transit slips', 'at_large');

-- VICTIMS
INSERT INTO victims (id, full_name, contact_number, address, gender, age, statement) VALUES
('f1000000-0000-0000-0000-000000000001', 'K. S. Narayanan', '+91 98800 00001', 'Bengaluru Urban', 'Male', 52, 'Reported biometric face ID bypass and loan extortion.'),
('f1000000-0000-0000-0000-000000000002', 'Dr. Vinay Murthy', '+91 98800 00002', 'Mysuru', 'Male', 46, 'Reported night burglary and missing jewellery.'),
('f1000000-0000-0000-0000-000000000003', 'Asha Rao', '+91 98800 00003', 'Mangaluru', 'Female', 33, 'Witnessed cargo handoff near harbor gate.'),
('f1000000-0000-0000-0000-000000000004', 'Prakash Jain', '+91 98800 00004', 'Belagavi', 'Male', 41, 'Reported forged excise transport documents.'),
('f1000000-0000-0000-0000-000000000005', 'Latha Hegde', '+91 98800 00005', 'Hassan', 'Female', 29, 'Filed domestic violence complaint with medical evidence.');

-- CRIME CASES
INSERT INTO crime_cases (id, case_number, category_id, location_id, occurred_at, description, mo_tags, status, priority, progress, assigned_officer_id) VALUES
('aa000000-0000-0000-0000-000000000001', 'CR-2026-BNG-001', 'd0000000-0000-0000-0000-000000000001', 'e0000000-0000-0000-0000-000000000001', now() - interval '3 days', 'Cyber Crime & Online Fraud reported at Whitefield Cyber Cell Beat', 'forged biometric login, micro-lending extortion', 'open', 'high', 45, 'c0000000-0000-0000-0000-000000000001'),
('aa000000-0000-0000-0000-000000000002', 'CR-2026-BNG-002', 'd0000000-0000-0000-0000-000000000001', 'e0000000-0000-0000-0000-000000000002', now() - interval '8 days', 'Cyber Crime & Online Fraud reported at KR Puram Transit Corridor', 'wallet mule routing, call spoofing', 'open', 'medium', 25, 'c0000000-0000-0000-0000-000000000001'),
('aa000000-0000-0000-0000-000000000003', 'CR-2026-MYS-001', 'd0000000-0000-0000-0000-000000000002', 'e0000000-0000-0000-0000-000000000003', now() - interval '6 days', 'Theft & Burglaries reported at Devaraja Market Zone', 'late night lock break, scooter reconnaissance', 'open', 'high', 60, 'c0000000-0000-0000-0000-000000000001'),
('aa000000-0000-0000-0000-000000000004', 'CR-2026-MYS-002', 'd0000000-0000-0000-0000-000000000002', 'e0000000-0000-0000-0000-000000000003', now() - interval '18 days', 'Theft & Burglaries reported at Devaraja Market Zone', 'repeat balcony entry, jewellery targeting', 'closed', 'medium', 100, 'c0000000-0000-0000-0000-000000000001'),
('aa000000-0000-0000-0000-000000000005', 'CR-2026-MNG-001', 'd0000000-0000-0000-0000-000000000003', 'e0000000-0000-0000-0000-000000000004', now() - interval '4 days', 'Narcotics Smuggling Services reported at Harbor Gate A', 'synthetic MDMA harbor handoff', 'open', 'critical', 15, 'c0000000-0000-0000-0000-000000000001'),
('aa000000-0000-0000-0000-000000000006', 'CR-2026-BLG-001', 'd0000000-0000-0000-0000-000000000004', 'e0000000-0000-0000-0000-000000000005', now() - interval '10 days', 'Smuggling & Excise Violations reported at Khade Bazar Checkpoint', 'forged inter-state clearance slips', 'open', 'low', 40, 'c0000000-0000-0000-0000-000000000001'),
('aa000000-0000-0000-0000-000000000007', 'CR-2026-BLR-001', 'd0000000-0000-0000-0000-000000000006', 'e0000000-0000-0000-0000-000000000006', now() - interval '13 days', 'Illegal Mining Violations reported at Ballari Mines Sector B', 'night mineral transport convoy', 'open', 'high', 80, 'c0000000-0000-0000-0000-000000000001'),
('aa000000-0000-0000-0000-000000000008', 'CR-2026-KLB-001', 'd0000000-0000-0000-0000-000000000008', 'e0000000-0000-0000-0000-000000000007', now() - interval '15 days', 'Property Disputes reported at Chowk Survey Layout', 'survey intimidation, prior offender density', 'closed', 'low', 100, 'c0000000-0000-0000-0000-000000000001'),
('aa000000-0000-0000-0000-000000000009', 'CR-2026-HSN-001', 'd0000000-0000-0000-0000-000000000007', 'e0000000-0000-0000-0000-000000000008', now() - interval '23 days', 'Domestic Violence reported at Hassan City East', 'repeat household assault complaint', 'open', 'medium', 30, 'c0000000-0000-0000-0000-000000000001'),
('aa000000-0000-0000-0000-000000000010', 'CR-2026-TMK-001', 'd0000000-0000-0000-0000-000000000005', 'e0000000-0000-0000-0000-000000000009', now() - interval '31 days', 'Assault reported at Tumkuru Industrial Road', 'industrial road altercation', 'closed', 'medium', 100, 'c0000000-0000-0000-0000-000000000001'),
('aa000000-0000-0000-0000-000000000011', 'CR-2026-DWD-001', 'd0000000-0000-0000-0000-000000000002', 'e0000000-0000-0000-0000-000000000010', now() - interval '35 days', 'Theft & Burglaries reported at Dharwad Market Yard', 'market yard attempted theft', 'closed', 'low', 100, 'c0000000-0000-0000-0000-000000000001');

-- FIRs
INSERT INTO firs (id, fir_number, crime_case_id, investigating_officer_id, complainant_name, complainant_contact, sections, status, narrative) VALUES
('bb000000-0000-0000-0000-000000000001', 'FIR-045/BNG/2026', 'aa000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', 'K. S. Narayanan', '+91 98800 00001', 'IPC 420, IT Act 66D', 'registered', 'Backend-seeded FIR for CR-2026-BNG-001'),
('bb000000-0000-0000-0000-000000000002', 'FIR-052/BNG/2026', 'aa000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000001', 'K. S. Narayanan', '+91 98800 00001', 'IPC 419, IT Act 66C', 'registered', 'Backend-seeded FIR for CR-2026-BNG-002'),
('bb000000-0000-0000-0000-000000000003', 'FIR-789/MYS/2026', 'aa000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000000001', 'Dr. Vinay Murthy', '+91 98800 00002', 'IPC 379, 457', 'registered', 'Backend-seeded FIR for CR-2026-MYS-001'),
('bb000000-0000-0000-0000-000000000004', 'FIR-790/MYS/2026', 'aa000000-0000-0000-0000-000000000004', 'c0000000-0000-0000-0000-000000000001', 'Dr. Vinay Murthy', '+91 98800 00002', 'IPC 380', 'closed', 'Backend-seeded FIR for CR-2026-MYS-002'),
('bb000000-0000-0000-0000-000000000005', 'FIR-331/MNG/2026', 'aa000000-0000-0000-0000-000000000005', 'c0000000-0000-0000-0000-000000000001', 'Asha Rao', '+91 98800 00003', 'NDPS 21, 22', 'registered', 'Backend-seeded FIR for CR-2026-MNG-001'),
('bb000000-0000-0000-0000-000000000006', 'FIR-204/BLG/2026', 'aa000000-0000-0000-0000-000000000006', 'c0000000-0000-0000-0000-000000000001', 'Prakash Jain', '+91 98800 00004', 'Excise Act 32', 'registered', 'Backend-seeded FIR for CR-2026-BLG-001'),
('bb000000-0000-0000-0000-000000000007', 'FIR-611/BLR/2026', 'aa000000-0000-0000-0000-000000000007', 'c0000000-0000-0000-0000-000000000001', 'State Complainant', NULL, 'MMDR Act 21', 'registered', 'Backend-seeded FIR for CR-2026-BLR-001'),
('bb000000-0000-0000-0000-000000000008', 'FIR-122/KLB/2026', 'aa000000-0000-0000-0000-000000000008', 'c0000000-0000-0000-0000-000000000001', 'State Complainant', NULL, 'IPC 447, 506', 'closed', 'Backend-seeded FIR for CR-2026-KLB-001'),
('bb000000-0000-0000-0000-000000000009', 'FIR-208/HSN/2026', 'aa000000-0000-0000-0000-000000000009', 'c0000000-0000-0000-0000-000000000001', 'Latha Hegde', '+91 98800 00005', 'DV Act', 'registered', 'Backend-seeded FIR for CR-2026-HSN-001'),
('bb000000-0000-0000-0000-000000000010', 'FIR-144/TMK/2026', 'aa000000-0000-0000-0000-000000000010', 'c0000000-0000-0000-0000-000000000001', 'State Complainant', NULL, 'IPC 323', 'closed', 'Backend-seeded FIR for CR-2026-TMK-001'),
('bb000000-0000-0000-0000-000000000011', 'FIR-177/DWD/2026', 'aa000000-0000-0000-0000-000000000011', 'c0000000-0000-0000-0000-000000000001', 'State Complainant', NULL, 'IPC 379', 'closed', 'Backend-seeded FIR for CR-2026-DWD-001');

-- FIR-CRIMINAL LINKS
INSERT INTO fir_criminal_links (fir_id, criminal_id, role) VALUES
('bb000000-0000-0000-0000-000000000002', 'f0000000-0000-0000-0000-000000000002', 'accused'),
('bb000000-0000-0000-0000-000000000003', 'f0000000-0000-0000-0000-000000000001', 'accused'),
('bb000000-0000-0000-0000-000000000003', 'f0000000-0000-0000-0000-000000000004', 'accused'),
('bb000000-0000-0000-0000-000000000004', 'f0000000-0000-0000-0000-000000000001', 'accused'),
('bb000000-0000-0000-0000-000000000005', 'f0000000-0000-0000-0000-000000000003', 'accused'),
('bb000000-0000-0000-0000-000000000006', 'f0000000-0000-0000-0000-000000000004', 'accused'),
('bb000000-0000-0000-0000-000000000007', 'f0000000-0000-0000-0000-000000000005', 'accused'),
('bb000000-0000-0000-0000-000000000008', 'f0000000-0000-0000-0000-000000000004', 'accused'),
('bb000000-0000-0000-0000-000000000011', 'f0000000-0000-0000-0000-000000000001', 'accused');

-- FIR-VICTIM LINKS
INSERT INTO fir_victim_links (fir_id, victim_id) VALUES
('bb000000-0000-0000-0000-000000000001', 'f1000000-0000-0000-0000-000000000001'),
('bb000000-0000-0000-0000-000000000002', 'f1000000-0000-0000-0000-000000000001'),
('bb000000-0000-0000-0000-000000000003', 'f1000000-0000-0000-0000-000000000002'),
('bb000000-0000-0000-0000-000000000004', 'f1000000-0000-0000-0000-000000000002'),
('bb000000-0000-0000-0000-000000000005', 'f1000000-0000-0000-0000-000000000003'),
('bb000000-0000-0000-0000-000000000006', 'f1000000-0000-0000-0000-000000000004'),
('bb000000-0000-0000-0000-000000000009', 'f1000000-0000-0000-0000-000000000005');

-- EVIDENCE
INSERT INTO evidence (id, case_id, title, evidence_type, description, created_by, status) VALUES
('cc000000-0000-0000-0000-000000000001', 'aa000000-0000-0000-0000-000000000001', 'Evidence for CR-2026-BNG-001', 'digital', 'Primary evidence packet for CR-2026-BNG-001', 'IO-3921', 'Pending'),
('cc000000-0000-0000-0000-000000000002', 'aa000000-0000-0000-0000-000000000002', 'Evidence for CR-2026-BNG-002', 'digital', 'Primary evidence packet for CR-2026-BNG-002', 'IO-3921', 'Pending'),
('cc000000-0000-0000-0000-000000000003', 'aa000000-0000-0000-0000-000000000003', 'Evidence for CR-2026-MYS-001', 'document', 'Primary evidence packet for CR-2026-MYS-001', 'IO-3921', 'Pending'),
('cc000000-0000-0000-0000-000000000004', 'aa000000-0000-0000-0000-000000000004', 'Evidence for CR-2026-MYS-002', 'document', 'Primary evidence packet for CR-2026-MYS-002', 'IO-3921', 'Pending'),
('cc000000-0000-0000-0000-000000000005', 'aa000000-0000-0000-0000-000000000005', 'Evidence for CR-2026-MNG-001', 'digital', 'Primary evidence packet for CR-2026-MNG-001', 'IO-3921', 'Pending'),
('cc000000-0000-0000-0000-000000000006', 'aa000000-0000-0000-0000-000000000006', 'Evidence for CR-2026-BLG-001', 'document', 'Primary evidence packet for CR-2026-BLG-001', 'IO-3921', 'Pending'),
('cc000000-0000-0000-0000-000000000007', 'aa000000-0000-0000-0000-000000000007', 'Evidence for CR-2026-BLR-001', 'document', 'Primary evidence packet for CR-2026-BLR-001', 'IO-3921', 'Pending'),
('cc000000-0000-0000-0000-000000000008', 'aa000000-0000-0000-0000-000000000008', 'Evidence for CR-2026-KLB-001', 'document', 'Primary evidence packet for CR-2026-KLB-001', 'IO-3921', 'Pending'),
('cc000000-0000-0000-0000-000000000009', 'aa000000-0000-0000-0000-000000000009', 'Evidence for CR-2026-HSN-001', 'document', 'Primary evidence packet for CR-2026-HSN-001', 'IO-3921', 'Pending'),
('cc000000-0000-0000-0000-000000000010', 'aa000000-0000-0000-0000-000000000010', 'Evidence for CR-2026-TMK-001', 'document', 'Primary evidence packet for CR-2026-TMK-001', 'IO-3921', 'Pending'),
('cc000000-0000-0000-0000-000000000011', 'aa000000-0000-0000-0000-000000000011', 'Evidence for CR-2026-DWD-001', 'document', 'Primary evidence packet for CR-2026-DWD-001', 'IO-3921', 'Pending');

-- NOTIFICATIONS (10 inter-station messages)
INSERT INTO notifications (id, user_id, sender_id, subject, notification_type, category, title, message, priority, severity, status, related_case_number, related_fir_number, is_read, is_broadcast, created_at) VALUES
('dd000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000002', 'Gang activity detected in Whitefield Sector-4', 'intelligence_sharing', 'intelligence_sharing', 'Gang Activity Alert — Whitefield', 'Recent analytics indicate repeated movement of suspects associated with CR-2026-BNG-001. Increase patrol frequency and verify CCTV feeds in Sector-4 between 22:00–04:00.', 'high', 'high', 'unread', 'CR-2026-BNG-001', NULL, FALSE, FALSE, now() - interval '2 hours'),
('dd000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000003', 'Evidence Uploaded for CR-2026-MYS-001', 'case_update', 'evidence_request', 'CCTV Footage & Witness Statements Ready', 'Digital CCTV footage from Devaraja Market Zone and three witness statements have been uploaded for CR-2026-MYS-001.', 'medium', 'medium', 'read', 'CR-2026-MYS-001', 'FIR-789/MYS/2026', TRUE, FALSE, now() - interval '5 hours'),
('dd000000-0000-0000-0000-000000000003', NULL, 'b0000000-0000-0000-0000-000000000004', 'Operation Night Shield — Statewide Directive', 'emergency_broadcast', 'emergency_broadcast', 'Operation Night Shield Activated', 'All officers are instructed to increase highway surveillance from 21:00 to 05:00 effective immediately.', 'critical', 'critical', 'unread', NULL, NULL, FALSE, TRUE, now() - interval '8 hours'),
('dd000000-0000-0000-0000-000000000005', 'b0000000-0000-0000-0000-000000000004', 'b0000000-0000-0000-0000-000000000003', 'Request for Additional Cyber Forensic Personnel', 'case_escalation', 'case_escalation', 'Cyber Forensic Support Required — CR-2026-BNG-001', 'The investigation into CR-2026-BNG-001 requires dedicated cyber forensic support.', 'high', 'high', 'unread', 'CR-2026-BNG-001', 'FIR-045/BNG/2026', FALSE, FALSE, now() - interval '3 hours'),
('dd000000-0000-0000-0000-000000000007', 'b0000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000004', 'Arrest Warrant Approved — Sayed Ibrahim', 'investigation_update', 'investigation_update', 'Arrest Warrant Issued', 'The arrest warrant for Sayed Ibrahim in connection with CR-2026-MNG-001 has been approved.', 'critical', 'critical', 'unread', 'CR-2026-MNG-001', 'FIR-331/MNG/2026', FALSE, FALSE, now() - interval '1 hours'),
('dd000000-0000-0000-0000-000000000008', 'b0000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000003', 'Suspect Movement Tracked — Mysuru Division', 'intelligence_sharing', 'intelligence_sharing', 'Real-Time Suspect Tracking Update', 'Vehicle registration KA-09-M-4412 linked to Vikram Yadav was flagged at KR Puram Transit Corridor.', 'high', 'high', 'read', 'CR-2026-BNG-001', 'FIR-052/BNG/2026', TRUE, FALSE, now() - interval '10 hours'),
('dd000000-0000-0000-0000-000000000009', 'b0000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000002', 'Evidence Chain Verification Required', 'evidence_request', 'evidence_request', 'Chain of Custody Verification — CR-2026-MYS-001', 'Evidence packet for CR-2026-MYS-001 requires chain of custody verification.', 'medium', 'medium', 'unread', 'CR-2026-MYS-001', 'FIR-789/MYS/2026', FALSE, FALSE, now() - interval '4 hours'),
('dd000000-0000-0000-0000-000000000010', NULL, 'b0000000-0000-0000-0000-000000000003', 'Narcotics Seizure Report — Mangaluru Harbor', 'case_update', 'case_update', 'Seizure Report Filed', 'Detailed narcotics seizure report for the Mangaluru Harbor operation has been compiled.', 'high', 'high', 'unread', 'CR-2026-MNG-001', 'FIR-331/MNG/2026', FALSE, TRUE, now() - interval '7 hours'),
('dd000000-0000-0000-0000-000000000011', 'b0000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000004', 'Weekly Intelligence Brief — District Overview', 'intelligence_sharing', 'intelligence_sharing', 'Weekly Intelligence Summary', 'Weekly intelligence brief for all districts is now available.', 'low', 'low', 'read', NULL, NULL, TRUE, FALSE, now() - interval '24 hours'),
('dd000000-0000-0000-0000-000000000012', 'b0000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000001', 'Officer Badge Update', 'administrative', 'administrative', 'Badge Configuration Updated', 'Your officer badge profile has been updated with the latest certification.', 'low', 'low', 'read', NULL, NULL, TRUE, FALSE, now() - interval '48 hours');

COMMIT;
