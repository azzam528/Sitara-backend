"""add daily_medications table

Revision ID: b9e4c2d8a107
Revises: c8f3a91b4e07
Create Date: 2026-08-26 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9e4c2d8a107"
down_revision: Union[str, Sequence[str], None] = "c8f3a91b4e07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    daily_medication_status = sa.Enum(
        "pending",
        "in_progress",
        "verified",
        "missed",
        "rejected",
        name="dailymedicationstatus",
    )
    vot_step = sa.Enum(
        "waiting",
        "face_verified",
        "medicine_detected",
        "medicine_matched",
        "drinking",
        "verified",
        name="votstep",
    )

    op.create_table(
        "daily_medications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("medicine_schedule_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("scheduled_time", sa.Time(), nullable=False),
        sa.Column(
            "status",
            daily_medication_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "vot_step",
            vot_step,
            nullable=False,
            server_default="waiting",
        ),
        sa.Column("face_verification_id", sa.Integer(), nullable=True),
        sa.Column("video_verification_id", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["medicine_schedule_id"],
            ["medicine_schedules.id"],
        ),
        sa.ForeignKeyConstraint(
            ["face_verification_id"],
            ["face_verifications.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["video_verification_id"],
            ["video_verifications.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "medicine_schedule_id",
            "scheduled_date",
            name="uq_daily_medications_schedule_date",
        ),
    )
    op.create_index(
        op.f("ix_daily_medications_medicine_schedule_id"),
        "daily_medications",
        ["medicine_schedule_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_daily_medications_face_verification_id"),
        "daily_medications",
        ["face_verification_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_daily_medications_video_verification_id"),
        "daily_medications",
        ["video_verification_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_daily_medications_video_verification_id"),
        table_name="daily_medications",
    )
    op.drop_index(
        op.f("ix_daily_medications_face_verification_id"),
        table_name="daily_medications",
    )
    op.drop_index(
        op.f("ix_daily_medications_medicine_schedule_id"),
        table_name="daily_medications",
    )
    op.drop_table("daily_medications")

    sa.Enum(name="votstep").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="dailymedicationstatus").drop(op.get_bind(), checkfirst=True)
