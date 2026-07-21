-- SQL Script for creating Officer and Evidence module tables in Supabase

-- Add new roles if they don't exist in roles table
-- INSERT INTO roles (id, name, description, created_at) VALUES 
-- (gen_random_uuid(), 'inspector', 'Inspector Role', now()),
-- (gen_random_uuid(), 'forensic', 'Forensic Role', now()),
-- (gen_random_uuid(), 'viewer', 'Viewer Role', now())
-- ON CONFLICT DO NOTHING;

-- Modify existing officers table if it exists, or create new
CREATE TABLE IF NOT EXISTS officers (
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Note: In a real migration you would ALTER TABLE officers ADD COLUMN ...

-- Modify evidence table
CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES crime_cases(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    evidence_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'Pending',
    created_by VARCHAR(255),
    assigned_to UUID REFERENCES users(id),
    storage_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID NOT NULL UNIQUE REFERENCES evidence(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    filesize INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    uploaded_by VARCHAR(255),
    extracted_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    performed_by VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    assigned_by UUID NOT NULL REFERENCES users(id),
    assigned_to UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'Assigned',
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accepted_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chain_of_custody (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    from_user UUID REFERENCES users(id),
    to_user UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    remarks TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_ai_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    model VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_evidence_case_id ON evidence(case_id);
CREATE INDEX IF NOT EXISTS idx_evidence_metadata_evidence_id ON evidence_metadata(evidence_id);
CREATE INDEX IF NOT EXISTS idx_evidence_timeline_evidence_id ON evidence_timeline(evidence_id);
CREATE INDEX IF NOT EXISTS idx_evidence_assignments_evidence_id ON evidence_assignments(evidence_id);
CREATE INDEX IF NOT EXISTS idx_evidence_assignments_assigned_to ON evidence_assignments(assigned_to);
CREATE INDEX IF NOT EXISTS idx_chain_of_custody_evidence_id ON chain_of_custody(evidence_id);
CREATE INDEX IF NOT EXISTS idx_evidence_ai_summary_evidence_id ON evidence_ai_summary(evidence_id);
