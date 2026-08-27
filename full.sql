-- ============================================================================
--  SAKSHA - Crime Intelligence & Analytical Platform
--  Complete PostgreSQL bundle for Supabase (Postgres 16). Copy-paste target:
--  Supabase Dashboard > SQL Editor, or any Postgres 13+ client.
--
--  CONTENTS
--    1. Schema setup   (idempotent DDL matching backend/app/models/*)
--    2. Seed data      (categories, locations, officers, criminals, victims,
--                      cases, FIRs and link tables - safe to re-run)
--    3. Joins          (Case + FIR + criminal + victim drill-down, search)
--    4. Repeat         offenders (criminals named in multiple FIRs/cases)
--    5. District       crime ranking (volume + severity-weighted score)
--    6. Dashboard      summary (KPIs, trends, category/status breakdown)
--    7. Index / perf   review (missing FK indexes, seq scans, unused/dup
--                      indexes, recommended CREATE INDEX statements)
--
--  Each section is independent - copy a single block. All identifiers are
--  lowercase (Postgres practice). Analytics queries assume the app schema
--  (UUID PKs via gen_random_uuid(), timestamptz, dataset_provenance).
-- ============================================================================



-- ============================================================================
-- 1. SCHEMA SETUP (idempotent)
--    Mirrors the SQLAlchemy ORM in backend/app/models. Runs safely on a DB
--    that already has these tables (CREATE TABLE IF NOT EXISTS is a no-op).
-- ============================================================================

-- 1.1 crime_categories --------------------------------------------------------
create table if not exists crime_categories (
    id           uuid primary key default gen_random_uuid(),
    name         varchar(150) not null,
    section_code varchar(50),
    severity     varchar(20),           -- low | medium | high
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now(),
    constraint uq_crime_categories_name unique (name)
);
create index if not exists ix_crime_categories_name on crime_categories (name);

-- 1.2 locations ---------------------------------------------------------------
create table if not exists locations (
    id                   uuid primary key default gen_random_uuid(),
    address              varchar(500),          -- beat/place name
    district             varchar(100) not null,
    station              varchar(100),          -- police station
    latitude             double precision not null,
    longitude            double precision not null,
    pincode              varchar(10),
    dataset_provenance   varchar(20)  not null default 'live',
    source_import_job_id uuid,
    source_file          varchar(500),
    source_row_ref       varchar(100),
    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now(),
    constraint uq_location_station_address unique (station, address)
);
create index if not exists ix_locations_district on locations (district);
create index if not exists ix_locations_station  on locations (station);

-- 1.3 criminals ---------------------------------------------------------------
create table if not exists criminals (
    id                   uuid primary key default gen_random_uuid(),
    full_name            varchar(255) not null,
    aliases              varchar(500),
    date_of_birth        date,
    gender               varchar(20),
    address              varchar(500),
    identifying_marks    text,
    mo_summary           text,                  -- modus operandi notes
    status               varchar(30)  not null default 'at_large', -- at_large | arrested | convicted | deceased
    gang_affiliation     varchar(255),
    neo4j_node_id        varchar(100),
    image_url            varchar(1000),
    dataset_provenance   varchar(20)  not null default 'live',
    source_import_job_id uuid,
    source_file          varchar(500),
    source_row_ref       varchar(100),
    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now()
);
create index if not exists ix_criminals_full_name on criminals (full_name);
create index if not exists ix_criminals_status    on criminals (status);
create index if not exists ix_criminals_neo4j     on criminals (neo4j_node_id);
create index if not exists ix_criminals_prov      on criminals (dataset_provenance);

-- 1.4 victims -----------------------------------------------------------------
create table if not exists victims (
    id                   uuid primary key default gen_random_uuid(),
    full_name            varchar(255) not null,
    contact_number       varchar(20),
    address              varchar(500),
    gender               varchar(20),
    age                  integer,
    statement            text,
    neo4j_node_id        varchar(100),
    image_url            varchar(1000),
    dataset_provenance   varchar(20)  not null default 'live',
    source_import_job_id uuid,
    source_file          varchar(500),
    source_row_ref       varchar(100),
    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now()
);
create index if not exists ix_victims_full_name on victims (full_name);
create index if not exists ix_victims_neo4j      on victims (neo4j_node_id);

-- 1.5 officers ----------------------------------------------------------------
create table if not exists officers (
    id                   uuid primary key default gen_random_uuid(),
    supabase_user_id     uuid,
    user_id              uuid unique,
    badge_number         varchar(50) not null,
    name                 varchar(255) not null,
    rank                 varchar(100),
    station              varchar(100) not null,
    district             varchar(100),
    designation          varchar(100),
    phone                varchar(20),
    email                varchar(255) unique,
    status               varchar(50)  not null default 'active',
    image_url            varchar(1000),
    dataset_provenance   varchar(20)  not null default 'live',
    source_import_job_id uuid,
    source_file          varchar(500),
    source_row_ref       varchar(100),
    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now(),
    constraint uq_officers_badge_number unique (badge_number)
);
create index if not exists ix_officers_badge    on officers (badge_number);
create index if not exists ix_officers_station  on officers (station);
create index if not exists ix_officers_district on officers (district);

-- 1.6 crime_cases -------------------------------------------------------------
create table if not exists crime_cases (
    id                  uuid primary key default gen_random_uuid(),
    case_number         varchar(50) not null,
    category_id         uuid not null references crime_categories (id) on delete restrict,
    location_id         uuid not null references locations (id) on delete restrict,
    occurred_at         timestamptz not null,
    reported_at         timestamptz not null default now(),
    description         text,
    mo_tags             varchar(500),           -- comma-separated modus operandi tags
    status              varchar(30)  not null default 'open', -- open | investigating | closed
    priority            varchar(30)  not null default 'medium', -- low | medium | high | critical
    progress            integer      not null default 10,
    assigned_officer_id uuid references officers (id) on delete set null,
    dataset_provenance  varchar(20)  not null default 'live',
    source_import_job_id uuid,
    source_file         varchar(500),
    source_row_ref      varchar(100),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    constraint uq_crime_cases_number unique (case_number)
);
create index if not exists ix_crime_cases_number      on crime_cases (case_number);
create index if not exists ix_crime_cases_category    on crime_cases (category_id);
create index if not exists ix_crime_cases_location    on crime_cases (location_id);
create index if not exists ix_crime_cases_occurred_at on crime_cases (occurred_at);
create index if not exists ix_crime_cases_status      on crime_cases (status);
create index if not exists ix_crime_cases_officer     on crime_cases (assigned_officer_id);
create index if not exists ix_crime_cases_created_at  on crime_cases (created_at);

-- 1.7 firs --------------------------------------------------------------------
create table if not exists firs (
    id                       uuid primary key default gen_random_uuid(),
    fir_number               varchar(50) not null,
    crime_case_id            uuid not null references crime_cases (id) on delete cascade,
    investigating_officer_id uuid references officers (id) on delete set null,
    complainant_name         varchar(255) not null,
    complainant_contact      varchar(20),
    sections                 varchar(255),           -- IPC/BNS sections, comma-separated
    filed_at                 timestamptz not null default now(),
    status                   varchar(30)  not null default 'registered', -- registered | investigated | closed
    narrative                text,
    attachments              text,                   -- JSON array
    dataset_provenance       varchar(20)  not null default 'live',
    source_import_job_id     uuid,
    source_file              varchar(500),
    source_row_ref           varchar(100),
    created_at               timestamptz not null default now(),
    updated_at               timestamptz not null default now(),
    constraint uq_firs_number unique (fir_number)
);
create index if not exists ix_firs_number  on firs (fir_number);
create index if not exists ix_firs_case    on firs (crime_case_id);
create index if not exists ix_firs_officer on firs (investigating_officer_id);
create index if not exists ix_firs_status  on firs (status);
create index if not exists ix_firs_filed_at on firs (filed_at);

-- 1.8 fir_criminal_links (FIR <-> Criminal, many-to-many) ---------------------
create table if not exists fir_criminal_links (
    id          uuid primary key default gen_random_uuid(),
    fir_id      uuid not null references firs (id) on delete cascade,
    criminal_id uuid not null references criminals (id) on delete cascade,
    role        varchar(50),                        -- accused | suspect | absconding
    constraint uq_fir_criminal unique (fir_id, criminal_id)
);
create index if not exists ix_fcl_fir_id      on fir_criminal_links (fir_id);
create index if not exists ix_fcl_criminal_id on fir_criminal_links (criminal_id);

-- 1.9 fir_victim_links (FIR <-> Victim, many-to-many) -------------------------
create table if not exists fir_victim_links (
    id        uuid primary key default gen_random_uuid(),
    fir_id    uuid not null references firs (id) on delete cascade,
    victim_id uuid not null references victims (id) on delete cascade,
    constraint uq_fir_victim unique (fir_id, victim_id)
);
create index if not exists ix_fvl_fir_id      on fir_victim_links (fir_id);
create index if not exists ix_fvl_victim_id   on fir_victim_links (victim_id);



-- ============================================================================
-- 2. SEED DATA
--    Categories/locations/officers use ON CONFLICT on natural keys (safe on
--    any DB). Criminals/victims/cases/FIRs/links only seed when the criminals
--    table is empty (idempotent guard).
-- ============================================================================

-- 2.1 Crime categories (8) ----------------------------------------------------
insert into crime_categories (name, section_code, severity) values
    ('Cyber Crime & Online Fraud', 'IPC 420 / IT Act 66D', 'high'),
    ('Theft & Burglaries',          'IPC 379/457',          'medium'),
    ('Narcotics Smuggling Services','NDPS 21/22',           'high'),
    ('Smuggling & Excise Violations','Excise Act',          'medium'),
    ('Assault',                     'IPC 323/324',          'medium'),
    ('Illegal Mining Violations',   'MMDR Act',             'high'),
    ('Domestic Violence',           'DV Act',               'medium'),
    ('Property Disputes',           'IPC 447/506',          'low')
on conflict (name) do nothing;

-- 2.2 Locations (subset across Karnataka districts) ---------------------------
insert into locations (address, district, station, latitude, longitude, pincode) values
    ('Whitefield Cyber Cell Beat', 'Bengaluru Urban',  'Whitefield Police Station',      12.9698, 77.7500, '560066'),
    ('KR Puram Transit Corridor',  'Bengaluru Urban',  'KR Puram Police Station',        13.0056, 77.6880, '560036'),
    ('Koramangala Layout',         'Bengaluru Urban',  'Koramangala Police Station',     12.9352, 77.6245, '560034'),
    ('HSR Layout Beat',            'Bengaluru Urban',  'HSR Layout Police Station',      12.9116, 77.6389, '560102'),
    ('Jayanagar 4th Block',        'Bengaluru Urban',  'Jayanagar Police Station',       12.9260, 77.5830, '560041'),
    ('Khade Bazar Checkpoint',     'Belagavi',         'Khade Bazar Station',            15.8497, 74.4977, '590001'),
    ('Camp Area Patrol',           'Belagavi',         'Camp Police Station',            15.8625, 74.5050, '590006'),
    ('Tilakwadi Beat',             'Belagavi',         'Tilakwadi Police Station',       15.8380, 74.4780, '590009'),
    ('Dharwad Market Yard',        'Dharwad',          'Suburban Police Station',        15.4589, 75.0078, '580001'),
    ('Hubli Traffic Island',       'Dharwad',          'Hubli City Police Station',      15.3647, 75.1240, '580002'),
    ('Chowk Survey Layout',        'Kalaburagi',       'Chowk Police Station',           17.3297, 76.8343, '585101'),
    ('Devaraja Market Zone',       'Mysuru',           'Devaraja Police Station',        12.2958, 76.6394, '570001'),
    ('Mysuru-Mandya Highway',      'Mandya',           'Srirangapatna Police Station',   12.4200, 76.6900, '571402'),
    ('Hassan City East',           'Hassan',           'City Police Station',            13.0641, 76.1030, '573201'),
    ('Tumkuru Industrial Road',    'Tumkuru',          'Town Police Station',            13.3379, 77.1173, '572101'),
    ('Ballari Mines Sector B',     'Ballari',          'Rural Police Station',           15.1394, 76.9214, '583101'),
    ('Harbor Gate A',              'Dakshina Kannada', 'Pandeshwar Police Station',      12.9050, 74.8350, '575001')
on conflict (station, address) do nothing;

-- 2.3 Officers ----------------------------------------------------------------
insert into officers (badge_number, name, rank, station, district, designation, phone, email) values
    ('IO-1247', 'Inspector Virupakshi Hallur', 'Inspector',  'Khade Bazar Station',     'Belagavi',          'SHO', '+91 94480 12001', 'virupakshi.h@ksp.gov.in'),
    ('IO-5501', 'Inspector Manoj Biradar',     'Inspector',  'Hubli City Police Station','Dharwad',          'SHO', '+91 94480 12003', 'manoj.b@ksp.gov.in'),
    ('IO-2267', 'Inspector Kavitha Prasad',    'Inspector',  'Koramangala Police Station','Bengaluru Urban', 'SHO', '+91 94480 12011', 'kavitha.p@ksp.gov.in'),
    ('IO-8823', 'Inspector Mohammed Irfan',    'Inspector',  'City Police Station',     'Hassan',            'SHO', '+91 94480 12017', 'mohammed.i@ksp.gov.in'),
    ('IO-3267', 'Inspector Bharath Gowda',     'Inspector',  'Nazarbad Police Station', 'Mysuru',            'SHO', '+91 94480 12021', 'bharath.g@ksp.gov.in'),
    ('IO-9823', 'Inspector Irfan Hassan',      'Inspector',  'Pandeshwar Police Station','Dakshina Kannada', 'SHO', '+91 94480 12027', 'irfan.h@ksp.gov.in')
on conflict (badge_number) do nothing;

-- 2.4 Linked seed block: criminals, victims, cases, FIRs, links ----------------
do $$
begin
    if not exists (select 1 from criminals limit 1) then

        -- Criminals (5)
        insert into criminals (full_name, aliases, date_of_birth, gender, address, identifying_marks, mo_summary, status, gang_affiliation) values
            ('Ramu Swamy',   'Ramu, Bangarappa',   '1982-04-11', 'Male', 'KR Puram, Bengaluru', 'Scar on left forearm', 'Night break-in specialist; crowbar entry, targets electronics and cash.', 'at_large',  'Market Street Crew'),
            ('Vikram Yadav', 'Vicky, Cyber Vicky', '1995-08-23', 'Male', 'Whitefield, Bengaluru', 'Tattoo on right hand', 'UPI/OTP fraud, mule account routing, call spoofing.',                    'arrested',  'Whitefield Cyber Ring'),
            ('Sayed Ibrahim','Ibba',               '1979-01-30', 'Male', 'Chowk, Kalaburagi',    'Limp in left leg',  'Interstate narcotics courier via bus terminals.',                         'at_large',  'North Corridor Syndicate'),
            ('Karthik Gowda','Gowda',              '1988-12-15', 'Male', 'Belagavi',             'Grey hair patch',   'Forged property deeds, witness intimidation.',                            'convicted', ''),
            ('Mohsin Pasha', 'Mouja',              '1990-06-09', 'Male', 'Mangaluru',            'Beard, mole on cheek', 'Harbor smuggling logistics, forged excise slips.',                      'at_large',  'Coastal Smugglers Circle');

        -- Victims (6)
        insert into victims (full_name, contact_number, address, gender, age, statement) values
            ('K. S. Narayanan', '+91 98800 00001', 'Bengaluru Urban', 'Male',   52, 'Reported biometric face ID bypass and loan extortion.'),
            ('Sunita Devi',     '+91 98800 00006', 'Bengaluru Urban', 'Female', 38, 'Lost savings in online investment scam.'),
            ('Anupama Sharma',  '+91 98800 00030', 'Bengaluru Urban', 'Female', 26, 'Cyber stalking via social media, threats received.'),
            ('Bharat Hegde',    '+91 98800 00017', 'Belagavi',        'Male',   43, 'ATM card cloned, account drained.'),
            ('Prakash Jain',    '+91 98800 00004', 'Belagavi',        'Male',   41, 'Reported forged excise transport documents.'),
            ('Pradeep Naik',    '+91 98800 00013', 'Dharwad',         'Male',   37, 'Shop broken into, cash and electronics stolen.');

        -- Crime cases (6) - Vikram Yadav on 2 cyber cases, Ramu Swamy on 3 theft
        -- cases, so the repeat-offender query (section 4) returns real results.
        insert into crime_cases
            (case_number, category_id, location_id, occurred_at, reported_at, description, mo_tags, status, priority, progress)
        select v.case_number, c.id, l.id, v.occurred_at, v.occurred_at + interval '1 hour',
               v.description, v.mo_tags, v.status, v.priority, v.progress
        from (values
            ('CR-2026-BNG-001'::text, 'Cyber Crime & Online Fraud'::text, 'Whitefield Police Station'::text,
             now() - interval '3 days',  'forged biometric login, micro-lending extortion', 'faceid,upi_fraud,loansharking', 'open', 'high', 45),
            ('CR-2026-BNG-002', 'Cyber Crime & Online Fraud', 'KR Puram Police Station',
             now() - interval '8 days',  'wallet mule routing, call spoofing',             'mule,spoofing,upi_fraud',        'open', 'medium', 25),
            ('CR-2026-BNG-003', 'Theft & Burglaries', 'Koramangala Police Station',
             now() - interval '6 days',  'apartment burglary, smart lock bypass',          'night_breakin,crowbar,electronics','open', 'medium', 40),
            ('CR-2026-BLG-001', 'Smuggling & Excise Violations', 'Khade Bazar Station',
             now() - interval '10 days', 'forged inter-state clearance slips',             'forgery,excise,interstate',      'open', 'low', 40),
            ('CR-2026-BLG-002', 'Theft & Burglaries', 'Camp Police Station',
             now() - interval '15 days', 'night residential break-in, crowbar used',       'night_breakin,crowbar',          'open', 'medium', 25),
            ('CR-2026-DWD-001', 'Theft & Burglaries', 'Suburban Police Station',
             now() - interval '35 days', 'market yard attempted theft',                    'attempted_theft,market',         'closed', 'low', 100)
        ) as v(case_number, category, station, occurred_at, description, mo_tags, status, priority, progress)
        join crime_categories c on c.name = v.category
        join locations l        on l.station = v.station
        on conflict (case_number) do nothing;

        -- FIRs (6) - one per case
        insert into firs (fir_number, crime_case_id, complainant_name, complainant_contact, sections, filed_at, status, narrative)
        select v.fir_number, c.id, v.complainant_name, v.complainant_contact, v.sections,
               c.occurred_at + interval '2 hours', 'registered', v.narrative
        from (values
            ('FIR-045/BNG/2026'::text, 'CR-2026-BNG-001'::text, 'K. S. Narayanan'::text, '+91 98800 00001'::text, 'IPC 420, IT Act 66D'::text, 'Biometric bypass and loan extortion complaint.'),
            ('FIR-052/BNG/2026', 'CR-2026-BNG-002', 'K. S. Narayanan', '+91 98800 00001', 'IPC 419, IT Act 66C', 'Mule account and call spoofing complaint.'),
            ('FIR-053/BNG/2026', 'CR-2026-BNG-003', 'Anupama Sharma',  '+91 98800 00030', 'IPC 380, 457',        'Burglary at apartment, smart lock bypassed.'),
            ('FIR-204/BLG/2026', 'CR-2026-BLG-001', 'Prakash Jain',    '+91 98800 00004', 'Excise Act 32',        'Forged excise transport documents seized.'),
            ('FIR-205/BLG/2026', 'CR-2026-BLG-002', 'Bharat Hegde',    '+91 98800 00017', 'IPC 379, 457',        'Night break-in; cash and electronics stolen.'),
            ('FIR-177/DWD/2026', 'CR-2026-DWD-001', 'Pradeep Naik',    '+91 98800 00013', 'IPC 379',             'Market yard attempted theft.')
        ) as v(fir_number, case_number, complainant_name, complainant_contact, sections, narrative)
        join crime_cases c on c.case_number = v.case_number
        on conflict (fir_number) do nothing;

        -- FIR <-> Criminal links
        insert into fir_criminal_links (fir_id, criminal_id, role)
        select fl.id, cl.id, v.role
        from (values
            ('FIR-045/BNG/2026'::text, 'Vikram Yadav'::text, 'accused'::text),
            ('FIR-052/BNG/2026', 'Vikram Yadav',  'accused'),
            ('FIR-053/BNG/2026', 'Ramu Swamy',    'accused'),
            ('FIR-204/BLG/2026', 'Karthik Gowda', 'accused'),
            ('FIR-205/BLG/2026', 'Ramu Swamy',    'accused'),
            ('FIR-177/DWD/2026', 'Ramu Swamy',    'absconding')
        ) as v(fir_number, criminal_name, role)
        join firs fl      on fl.fir_number = v.fir_number
        join criminals cl on cl.full_name = v.criminal_name
        on conflict (fir_id, criminal_id) do nothing;

        -- FIR <-> Victim links
        insert into fir_victim_links (fir_id, victim_id)
        select fl.id, vl.id
        from (values
            ('FIR-045/BNG/2026'::text, 'K. S. Narayanan'::text),
            ('FIR-052/BNG/2026', 'K. S. Narayanan'),
            ('FIR-053/BNG/2026', 'Anupama Sharma'),
            ('FIR-204/BLG/2026', 'Prakash Jain'),
            ('FIR-205/BLG/2026', 'Bharat Hegde'),
            ('FIR-177/DWD/2026', 'Pradeep Naik')
        ) as v(fir_number, victim_name)
        join firs fl    on fl.fir_number = v.fir_number
        join victims vl on vl.full_name = v.victim_name
        on conflict (fir_id, victim_id) do nothing;

    end if;
end $$;

-- ============================================================================
-- 3. CASE + FIR + CRIMINAL + VICTIM JOINS
-- ============================================================================

-- 3.1 Full case drill-down ----------------------------------------------------
--     One row per case with aggregated criminal / victim name lists.
--     Replace the value in the final execute(...) with any case number.
prepare case_drill_down (text) as
select
    c.case_number,
    cc.name        as category_name,
    cc.section_code,
    cc.severity    as category_severity,
    c.priority, c.status, c.progress,
    l.district, l.station, l.address as beat,
    c.occurred_at, c.reported_at,
    c.description, c.mo_tags,
    o.name as assigned_officer, o.badge_number,
    array_agg(distinct cr.full_name) filter (where cr.id is not null) as criminals,
    array_agg(distinct v.full_name)  filter (where v.id is not null)  as victims,
    count(distinct f.id)                                              as fir_count
from crime_cases c
join crime_categories cc on cc.id = c.category_id
join locations l         on l.id = c.location_id
left join officers o     on o.id = c.assigned_officer_id
left join firs f         on f.crime_case_id = c.id
left join fir_criminal_links fcl on fcl.fir_id = f.id
left join criminals cr   on cr.id = fcl.criminal_id
left join fir_victim_links fvl  on fvl.fir_id = f.id
left join victims v      on v.id = fvl.victim_id
where c.case_number = $1
group by c.id, cc.id, l.id, o.id;

execute case_drill_down ('CR-2026-BNG-001');
deallocate case_drill_down;

-- 3.2 Case search (case number / FIR number / text / MO tag) ------------------
--     ILIKE is fine on small data; use pg_trgm GIN for large volumes.
select
    c.case_number, cc.name as category_name, l.district, l.station,
    c.status, c.priority, c.occurred_at,
    coalesce(string_agg(distinct f.fir_number, ', '), '') as fir_numbers
from crime_cases c
join crime_categories cc on cc.id = c.category_id
join locations l         on l.id = c.location_id
left join firs f         on f.crime_case_id = c.id
where c.case_number ilike '%' || '2026-BNG' || '%'
   or c.mo_tags     ilike '%' || '2026-BNG' || '%'
   or c.description ilike '%' || '2026-BNG' || '%'
group by c.id, cc.id, l.id
order by c.occurred_at desc
limit 25;

-- 3.3 FIR register view --------------------------------------------------------
select
    f.fir_number,
    f.complainant_name, f.complainant_contact,
    f.sections, f.filed_at, f.status,
    c.case_number, cc.name as category_name, l.district, l.station,
    count(distinct fcl.criminal_id) as named_criminals,
    count(distinct fvl.victim_id)   as named_victims
from firs f
join crime_cases c       on c.id = f.crime_case_id
join crime_categories cc on cc.id = c.category_id
join locations l         on l.id = c.location_id
left join fir_criminal_links fcl on fcl.fir_id = f.id
left join fir_victim_links fvl   on fvl.fir_id = f.id
group by f.id, c.id, cc.id, l.id
order by f.filed_at desc;



-- ============================================================================
-- 4. REPEAT OFFENDERS - criminals named in >= 2 FIRs / cases
-- ============================================================================
--     Adjust the >= 2 threshold (HAVING clause) as needed.
select
    cr.id,
    cr.full_name,
    cr.aliases,
    cr.status,
    cr.gang_affiliation,
    count(distinct fcl.fir_id) as fir_count,
    count(distinct c.id)       as case_count,
    count(distinct c.id) filter (where c.status <> 'closed') as open_case_count,
    count(distinct l.district) as district_count,
    count(distinct cc.name)    as category_count,
    max(c.occurred_at)         as latest_occurred_at,
    round(extract(epoch from (now() - max(c.occurred_at))) / 86400) as days_since_last
from criminals cr
join fir_criminal_links fcl on fcl.criminal_id = cr.id
join firs f                 on f.id = fcl.fir_id
join crime_cases c          on c.id = f.crime_case_id
join crime_categories cc    on cc.id = c.category_id
left join locations l       on l.id = c.location_id
group by cr.id
having count(distinct fcl.fir_id) >= 2
order by fir_count desc, days_since_last asc;

-- 4b. Per-district breakdown for a repeat offender -----------------------------
--     Shows which districts a criminal has been active in.
select
    cr.full_name,
    l.district,
    count(distinct c.id)   as cases,
    count(distinct fcl.fir_id) as firs,
    max(c.occurred_at)     as last_seen
from criminals cr
join fir_criminal_links fcl on fcl.criminal_id = cr.id
join firs f                 on f.id = fcl.fir_id
join crime_cases c          on c.id = f.crime_case_id
left join locations l       on l.id = c.location_id
group by cr.full_name, l.district
having count(distinct c.id) >= 2
order by cr.full_name, cases desc;



-- ============================================================================
-- 5. DISTRICT CRIME RANKING
-- ============================================================================

-- 5.1 Severity-weighted ranking ------------------------------------------------
--     score = category.severity weight x case.priority weight per case.
with district_stats as (
    select
        l.district,
        count(*) as total_cases,
        count(*) filter (where c.status = 'open')    as open_cases,
        count(*) filter (where c.status <> 'closed') as active_cases,
        count(*) filter (where c.progress < 50)      as stalled_cases,
        sum(
            (case cc.severity when 'low' then 1 when 'medium' then 2 when 'high' then 3 else 1 end)
            * (case c.priority when 'low' then 1 when 'medium' then 2 when 'high' then 3 when 'critical' then 4 else 2 end)
        ) as weighted_score,
        count(distinct cc.id)  as category_span,
        max(c.occurred_at)     as last_case_at
    from crime_cases c
    join crime_categories cc on cc.id = c.category_id
    join locations l         on l.id = c.location_id
    group by l.district
)
select
    district,
    total_cases,
    open_cases,
    active_cases,
    stalled_cases,
    weighted_score,
    round(weighted_score::numeric / nullif(total_cases, 0), 2) as severity_per_case,
    last_case_at,
    round(extract(epoch from (now() - last_case_at)) / 86400)  as days_since_last_case,
    rank() over (order by weighted_score desc)                 as risk_rank
from district_stats
order by risk_rank;

-- 5.2 Simple volume ranking (no severity weighting) ----------------------------
select
    l.district,
    count(*) as total_cases,
    count(*) filter (where c.status = 'open') as open_cases,
    row_number() over (order by count(*) desc) as vol_rank
from crime_cases c
join locations l on l.id = c.location_id
group by l.district
order by vol_rank;

-- 5.3 Hot stations (resource allocation view) ----------------------------------
select
    l.district, l.station,
    count(*) as cases,
    count(*) filter (where c.status = 'open') as open_cases,
    count(distinct c.category_id) as category_span,
    count(distinct fcl.criminal_id) as unique_criminals
from crime_cases c
join locations l on l.id = c.location_id
left join firs f on f.crime_case_id = c.id
left join fir_criminal_links fcl on fcl.fir_id = f.id
group by l.district, l.station
having count(*) >= 2
order by cases desc, open_cases desc;

-- ============================================================================
-- 6. DASHBOARD SUMMARY
-- ============================================================================

-- 6.1 KPI cards ----------------------------------------------------------------
select
    count(*) as total_cases,
    count(*) filter (where status in ('open', 'investigating')) as active_cases,
    count(*) filter (where status = 'open')                     as open_cases,
    count(*) filter (where status = 'investigating')            as investigating_cases,
    count(*) filter (where status = 'closed')                   as closed_cases,
    round(100.0 * count(*) filter (where status = 'closed') / nullif(count(*), 0), 1) as closure_pct,
    count(*) filter (where occurred_at >= now() - interval '7 days')   as last_7d,
    count(*) filter (where occurred_at >= now() - interval '30 days')  as last_30d,
    count(*) filter (where priority = 'critical')               as critical_cases,
    (select count(*) from firs)                                 as total_firs,
    (select count(*) from criminals)                            as total_criminals
from crime_cases;

-- 6.2 Cases by category with share ----------------------------------------------
select
    cc.name,
    count(*) as case_count,
    round(100.0 * count(*) / sum(count(*)) over (), 2) as share_pct
from crime_cases c
join crime_categories cc on cc.id = c.category_id
group by cc.name
order by case_count desc;

-- 6.3 Monthly trend, last 12 months (zero-filled) -------------------------------
with months as (
    select date_trunc('month', gs) as month
    from generate_series(now() - interval '11 months', now(), interval '1 month') as gs
)
select
    to_char(m.month, 'YYYY-MM') as month,
    count(c.id) as cases,
    count(f.id) as firs_filed
from months m
left join crime_cases c on date_trunc('month', c.occurred_at) = m.month
left join firs f        on date_trunc('month', f.filed_at)    = m.month
                            and f.crime_case_id = c.id
group by m.month
order by m.month;

-- 6.4 Status x priority matrix ---------------------------------------------------
select
    status,
    priority,
    count(*) as cnt
from crime_cases
group by status, priority
order by status, cnt desc;

-- 6.5 Recent cases feed (live wall) ----------------------------------------------
select
    c.case_number,
    cc.name as category,
    l.district, l.station,
    c.status, c.priority, c.progress,
    c.occurred_at,
    c.mo_tags
from crime_cases c
join crime_categories cc on cc.id = c.category_id
join locations l         on l.id = c.location_id
order by c.occurred_at desc
limit 10;

-- 6.6 Offender / victim summary --------------------------------------------------
select
    (select count(*) from criminals) as total_criminals,
    (select count(*) from criminals where status = 'at_large')   as at_large,
    (select count(*) from criminals where status = 'arrested')   as arrested,
    (select count(*) from criminals where status = 'convicted')  as convicted,
    (select count(*) from criminals where gang_affiliation <> '') as gang_members,
    (select count(*) from victims) as total_victims,
    (select count(*) from victims where gender = 'Female') as female_victims,
    (select count(*) from victims where gender = 'Male')   as male_victims;



-- ============================================================================
-- 7. MISSING INDEX / PERFORMANCE REVIEW
--    Run these as the postgres role (Supabase: Database > SQL Editor). The
--    first four are diagnostics; 7.5 is the list of indexes to create.
-- ============================================================================

-- 7.1 Foreign-key columns that have NO index ------------------------------------
--     Every FK column should be indexed for fast JOINs and CASCADE deletes.
select
    c.conrelid::regclass as table_name,
    a.attname            as fk_column,
    c.conname            as constraint_name
from pg_constraint c
join pg_attribute a on a.attrelid = c.conrelid and a.attnum = any(c.conkey)
where c.contype = 'f'
  and not exists (
      select 1 from pg_index i
      where i.indrelid = c.conrelid and a.attnum = any(i.indkey)
  )
order by 1, 2;

-- 7.2 Tables with heavy sequential scans (missing index candidates) -------------
select
    relname as table_name,
    seq_scan,
    seq_tup_read,
    idx_scan,
    round(100.0 * seq_scan / nullif(seq_scan + idx_scan, 0), 1) as seq_scan_pct
from pg_stat_user_tables
where seq_scan + idx_scan > 0
order by seq_scan_pct desc, seq_tup_read desc
limit 20;

-- 7.3 Unused indexes (idx_scan = 0) - candidates for DROP -----------------------
select
    schemaname, tablename, indexname,
    idx_scan, idx_tup_read, idx_tup_fetch
from pg_stat_user_indexes
where idx_scan = 0 and idx_tup_read = 0
  and indexrelid not in (select conindid from pg_constraint where contype = 'p')
order by tablename, indexname;

-- 7.4 Exact duplicate indexes (same column list) ---------------------------------
select
    i1.indrelid::regclass   as table_name,
    i1.indexrelid::regclass as index_1,
    i2.indexrelid::regclass as index_2
from pg_index i1
join pg_index i2
  on i1.indrelid = i2.indrelid
 and i1.indexrelid < i2.indexrelid
 and i1.indkey = i2.indkey
 and i1.indclass = i2.indclass
 and i1.indpred is null and i2.indpred is null
 and i1.indexprs is null and i2.indexprs is null
where i1.indisprimary = false and i2.indisprimary = false
order by 1;

-- 7.5 Recommended index maintenance ---------------------------------------------
--     Idempotent. These target the exact join/filter patterns used by the
--     analytics queries above (sections 3-6). idx_active_cases is a PARTIAL
--     index (only open/investigating rows) - smaller and faster for the live
--     dashboard feed than a full status index.
create index if not exists ix_crime_cases_active
    on crime_cases (occurred_at)
    where status in ('open', 'investigating');

create index if not exists ix_crime_cases_status_priority
    on crime_cases (status, priority);

create index if not exists ix_fcls_criminal_fir
    on fir_criminal_links (criminal_id, fir_id);

create index if not exists ix_fcls_fir_criminal
    on fir_criminal_links (fir_id, criminal_id);

create index if not exists ix_fvls_victim_fir
    on fir_victim_links (victim_id, fir_id);

create index if not exists ix_criminals_gang
    on criminals (gang_affiliation)
    where gang_affiliation <> '';

create index if not exists ix_firs_filed_at_status
    on firs (filed_at, status);

-- 7.6 Optional: statement-level diagnostics -------------------------------------
--     Uncomment to track total time / calls per query statement. Requires
--     superuser once:  create extension if not exists pg_stat_statements;
-- select
--     left(query, 90)          as query,
--     calls,
--     round(total_exec_time / 1000, 1) as total_ms,
--     round(mean_exec_time, 1)         as mean_ms
-- from pg_stat_statements
-- order by total_exec_time desc
-- limit 20;