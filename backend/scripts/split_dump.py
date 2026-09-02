"""
Split saksha_full_dump.sql into 4 files grouped by dependency order.
Usage: python scripts/split_dump.py
Output: backups/saksha_dump_part1.sql ... backups/saksha_dump_part4.sql
"""
import re, os

DUMP = os.path.join(os.path.dirname(__file__), '..', 'backups', 'saksha_full_dump.sql')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'backups')

content = open(DUMP, encoding='utf-8').read()

# Find positions of each table block
matches = list(re.finditer(r'DROP TABLE IF EXISTS public\."(\w+)"', content))
assert matches, "No tables found in dump"

# Build list of (table_name, start_pos)
table_positions = [(m.group(1), m.start()) for m in matches]

# Extract header (everything before first DROP TABLE)
header = content[:table_positions[0][1]]
header += "\n"

# Extract each table block (from its DROP TABLE to the next one)
blocks = {}
for i, (name, start) in enumerate(table_positions):
    end = table_positions[i + 1][1] if i + 1 < len(table_positions) else len(content)
    block = content[start:end]
    # Remove trailing "-- End of dump" if present
    block = re.sub(r'\s*-- End of dump\s*$', '', block)
    blocks[name] = block

# Dependency-ordered groups of ~11-12 tables each
# Group 1: foundation tables (no or minimal deps)
group1 = [
    'alembic_version', 'roles', 'users', 'locations',
    'crime_categories', 'mo_tags', 'officers', 'victims',
    'criminals', 'firs', 'crime_cases'
]
# Group 2: link/junction tables and evidence
group2 = [
    'fir_criminal_links', 'fir_victim_links', 'case_mo_tags',
    'criminal_mo_tags', 'evidence', 'chain_of_custody',
    'evidence_ai_summary', 'evidence_assignments',
    'evidence_metadata', 'evidence_timeline', 'audit_logs'
]
# Group 3: chat, reports, notifications, investigation
group3 = [
    'chat_conversations', 'chat_messages', 'reports',
    'report_versions', 'report_evidence_links', 'report_source_links',
    'notifications', 'investigation_notes', 'interventions',
    'intelligence_report_runs', 'role_permissions'
]
# Group 4: remaining tables
group4 = [
    'identity_aliases', 'identity_conflicts', 'identity_evidence',
    'identity_identifiers', 'identity_relationships',
    'import_jobs', 'import_staging_records', 'integrity_alerts',
    'proxy_patterns', 'proxy_pattern_evidence',
    'revoked_tokens', 'socioeconomic_indicators',
    'system_settings', 'locations'  # locations already in group1, skip dupes
]
# Remove duplicates keeping order
seen = set(group1 + group2 + group3)
group4 = [t for t in group4 if t not in seen]
# Add any tables not yet assigned
all_assigned = set(group1 + group2 + group3 + group4)
remaining = [name for name, _ in table_positions if name not in all_assigned]
group4 += remaining

groups = [group1, group2, group3, group4]

footer = "\n-- End of dump\n"

for part_num, group in enumerate(groups, 1):
    out_path = os.path.join(OUT_DIR, f'saksha_dump_part{part_num}.sql')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"-- Saksha Database Dump - Part {part_num}/4\n")
        f.write(f"-- Tables: {', '.join(group)}\n")
        if part_num == 1:
            # Write full header only in part 1
            f.write(header)
        else:
            f.write("SET client_encoding = 'UTF8';\n")
            f.write("SET standard_conforming_strings = on;\n\n")
        for table in group:
            if table in blocks:
                f.write(blocks[table])
                f.write('\n')
            else:
                print(f"  WARNING: table '{table}' not found in dump, skipping")
        f.write(footer)
    size_kb = os.path.getsize(out_path) / 1024
    print(f"Part {part_num}: {out_path} ({size_kb:.1f} KB, {len(group)} tables)")

print("\nDone. Import order: part1 -> part2 -> part3 -> part4")
