"""baseline schema — stamps current DB state as Alembic baseline

Revision ID: 8e6e75dc04de
Revises: 
Create Date: 2026-07-25 07:29:47.867408

This is a no-op baseline migration. It marks the existing database schema
(created via SQLAlchemy create_all() + manual ALTER TABLE) as the starting
point. Future ``alembic revision --autogenerate`` commands will only
capture new changes going forward.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8e6e75dc04de'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
