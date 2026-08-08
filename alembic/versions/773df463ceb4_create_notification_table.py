"""create notification table

Revision ID: 773df463ceb4
Revises: cdd4a066ea21
Create Date: 2026-08-08 22:46:05.965260

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '773df463ceb4'
down_revision: Union[str, Sequence[str], None] = 'cdd4a066ea21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    notification_reference_type = sa.Enum(
        "MEDICINE_SCHEDULE",
        "CONTROL_SCHEDULE",
        "COMPLAINT",
        "REFILL",
        "VIDEO_VERIFICATION",
        name="notificationreferencetype",
    )

    notification_reference_type.create(
        op.get_bind(),
        checkfirst=True,
    )

    op.add_column(
        "notifications",
        sa.Column(
            "reference_type",
            notification_reference_type,
            nullable=True,
        ),
    )

    op.add_column(
        "notifications",
        sa.Column(
            "reference_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.drop_column(
        "notifications",
        "related_id",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.add_column(
        "notifications",
        sa.Column(
            "related_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.drop_column(
        "notifications",
        "reference_id",
    )

    op.drop_column(
        "notifications",
        "reference_type",
    )

    notification_reference_type = sa.Enum(
        "MEDICINE_SCHEDULE",
        "CONTROL_SCHEDULE",
        "COMPLAINT",
        "REFILL",
        "VIDEO_VERIFICATION",
        name="notificationreferencetype",
    )

    notification_reference_type.drop(
        op.get_bind(),
        checkfirst=True,
    )