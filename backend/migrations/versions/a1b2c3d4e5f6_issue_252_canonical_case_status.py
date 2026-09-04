"""issue_252_canonical_case_status — normalize crime_cases.status to canonical values

Revision ID: a1b2c3d4e5f6
Revises: 8e6e75dc04de
Create Date: 2026-07-26 00:00:00.000000

Backward-compatible migration:
  - Existing records with already-canonical statuses are untouched.
  - Legacy status strings are mapped to their canonical equivalents.
  - Records with NULL or unrecognised status receive the safe default 'active'.
  - No data is deleted; no column type changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "8e6e75dc04de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Legacy value  →  canonical value
_MIGRATIONS = [
    ("open",               "active"),
    ("assigned",           "active"),
    ("investigating",      "under_investigation"),
    ("evidence collected", "under_investigation"),
    ("charge sheet filed", "chargesheeted"),
    # "closed", "active", "under_investigation", "arrested",
    # "chargesheeted", "convicted" are already canonical — no-op rows.
]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Map legacy values to canonical equivalents.
    for legacy, canonical in _MIGRATIONS:
        conn.execute(
            sa.text(
                "UPDATE crime_cases SET status = :canonical "
                "WHERE LOWER(status) = :legacy"
            ),
            {"canonical": canonical, "legacy": legacy},
        )

    # 2. Any remaining NULL or unrecognised status → safe default 'active'.
    conn.execute(
        sa.text(
            "UPDATE crime_cases SET status = 'active' "
            "WHERE status IS NULL "
            "   OR status NOT IN ("
            "       'active','under_investigation','arrested',"
            "       'chargesheeted','convicted','closed'"
            "   )"
        )
    )


def downgrade() -> None:
    # Reverse canonical → legacy (best-effort; 'active' maps back to 'open').
    conn = op.get_bind()
    _REVERSE = [
        ("active",             "open"),
        ("under_investigation","investigating"),
        ("chargesheeted",      "charge sheet filed"),
    ]
    for canonical, legacy in _REVERSE:
        conn.execute(
            sa.text(
                "UPDATE crime_cases SET status = :legacy "
                "WHERE status = :canonical"
            ),
            {"legacy": legacy, "canonical": canonical},
        )
