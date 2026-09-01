"""add_vot_retry_and_needs_review

Revision ID: 610e1948d18c
Revises: 8922b488e989
Create Date: 2026-09-01 23:32:11.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '610e1948d18c'
down_revision: Union[str, Sequence[str], None] = '8922b488e989'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('daily_medications', sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('daily_medications', sa.Column('failure_reason', sa.String(length=100), nullable=True))
    op.add_column('daily_medications', sa.Column('max_drinking_stage', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('daily_medications', 'max_drinking_stage')
    op.drop_column('daily_medications', 'failure_reason')
    op.drop_column('daily_medications', 'attempt_count')
