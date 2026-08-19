"""add face embeddings and face verifications tables

Revision ID: f1b8a9c2d3e4
Revises: e5884254e230
Create Date: 2026-08-20 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1b8a9c2d3e4'
down_revision: Union[str, Sequence[str], None] = 'e5884254e230'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create face_embeddings table
    op.create_table(
        'face_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('embedding', sa.Text(), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_face_embeddings_patient_id'), 'face_embeddings', ['patient_id'], unique=False)

    # 2. Create face_verifications table
    op.create_table(
        'face_verifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('medicine_schedule_id', sa.Integer(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'VERIFIED', 'FAILED', name='faceverificationstatus'),
            nullable=False,
            server_default='PENDING'
        ),
        sa.Column('captured_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['medicine_schedule_id'], ['medicine_schedules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_face_verifications_patient_id'), 'face_verifications', ['patient_id'], unique=False)
    op.create_index(op.f('ix_face_verifications_medicine_schedule_id'), 'face_verifications', ['medicine_schedule_id'], unique=False)

    # 3. Add face_verification_id to video_verifications table
    op.add_column('video_verifications', sa.Column('face_verification_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_video_verifications_face_verification_id',
        'video_verifications',
        'face_verifications',
        ['face_verification_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_video_verifications_face_verification_id'), 'video_verifications', ['face_verification_id'], unique=False)


def downgrade() -> None:
    # 1. Remove face_verification_id from video_verifications table
    op.drop_index(op.f('ix_video_verifications_face_verification_id'), table_name='video_verifications')
    op.drop_constraint('fk_video_verifications_face_verification_id', 'video_verifications', type_='foreignkey')
    op.drop_column('video_verifications', 'face_verification_id')

    # 2. Drop face_verifications table
    op.drop_index(op.f('ix_face_verifications_medicine_schedule_id'), table_name='face_verifications')
    op.drop_index(op.f('ix_face_verifications_patient_id'), table_name='face_verifications')
    op.drop_table('face_verifications')
    
    # Drop enum if on postgresql
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        sa.Enum(name='faceverificationstatus').drop(bind, checkfirst=True)

    # 3. Drop face_embeddings table
    op.drop_index(op.f('ix_face_embeddings_patient_id'), table_name='face_embeddings')
    op.drop_table('face_embeddings')
