"""add is_active to medicine_schedule

Revision ID: 0f7972211206
Revises: 89c8a430db09
Create Date: 2026-07-31 19:23:47.076201

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f7972211206'
down_revision: Union[str, Sequence[str], None] = '89c8a430db09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():

    op.add_column(
        "medicine_schedules",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade():

    op.drop_column(
        "medicine_schedules",
        "is_active",
    )
