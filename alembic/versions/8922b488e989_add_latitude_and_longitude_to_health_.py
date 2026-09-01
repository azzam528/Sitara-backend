"""Add latitude and longitude to health_facilities

Revision ID: 8922b488e989
Revises: b9e4c2d8a107
Create Date: 2026-09-01 22:02:23.447278

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8922b488e989'
down_revision: Union[str, Sequence[str], None] = 'b9e4c2d8a107'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "health_facilities",
        sa.Column("latitude", sa.Float(), nullable=True),
    )
    op.add_column(
        "health_facilities",
        sa.Column("longitude", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("health_facilities", "longitude")
    op.drop_column("health_facilities", "latitude")
    # ### end Alembic commands ###
