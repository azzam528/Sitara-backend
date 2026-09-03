"""add_needs_review_to_dailymedicationstatus_enum

Revision ID: 622ee0d9e156
Revises: 610e1948d18c
Create Date: 2026-09-02 08:55:50.557200

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '622ee0d9e156'
down_revision: Union[str, Sequence[str], None] = '610e1948d18c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE dailymedicationstatus ADD VALUE IF NOT EXISTS 'needs_review'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an ENUM type directly without rebuilding the type.
    # Leaving as safe no-op.
    pass
