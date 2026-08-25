"""partial unique indexes for active username nik mrn

Revision ID: c8f3a91b4e07
Revises: f1b8a9c2d3e4
Create Date: 2026-08-25 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.sql import text


revision: str = "c8f3a91b4e07"
down_revision: Union[str, Sequence[str], None] = "f1b8a9c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PARTIAL_INDEXES = (
    ("uq_users_username_active", "users", ["username"]),
    ("uq_patients_nik_active", "patients", ["nik"]),
    ("uq_patients_mrn_active", "patients", ["medical_record_number"]),
)

GLOBAL_UNIQUES = (
    ("users", ["username"]),
    ("patients", ["nik"]),
    ("patients", ["medical_record_number"]),
)


def _drop_unique_on_columns(table_name: str, column_names: list[str]) -> str:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    wanted = list(column_names)
    partial_names = {item[0] for item in PARTIAL_INDEXES}

    for constraint in inspector.get_unique_constraints(table_name):
        if list(constraint.get("column_names") or []) == wanted:
            name = constraint["name"]
            op.drop_constraint(name, table_name, type_="unique")
            return name

    for index in inspector.get_indexes(table_name):
        if (
            index.get("unique")
            and list(index.get("column_names") or []) == wanted
            and index.get("name") not in partial_names
        ):
            name = index["name"]
            op.drop_index(name, table_name=table_name)
            return name

    raise RuntimeError(
        f"Unique constraint/index on {table_name}.{wanted} was not found. "
        "Inspect the live database before dropping uniqueness."
    )


def upgrade() -> None:
    for table_name, column_names in GLOBAL_UNIQUES:
        _drop_unique_on_columns(table_name, column_names)

    for index_name, table_name, column_names in PARTIAL_INDEXES:
        op.create_index(
            index_name,
            table_name,
            column_names,
            unique=True,
            postgresql_where=sa.text("is_active = true"),
        )


def downgrade() -> None:
    bind = op.get_bind()

    duplicate_checks = (
        (
            "users.username",
            "SELECT username FROM users GROUP BY username HAVING COUNT(*) > 1",
        ),
        (
            "patients.nik",
            "SELECT nik FROM patients GROUP BY nik HAVING COUNT(*) > 1",
        ),
        (
            "patients.medical_record_number",
            "SELECT medical_record_number FROM patients "
            "GROUP BY medical_record_number HAVING COUNT(*) > 1",
        ),
    )

    for label, sql in duplicate_checks:
        duplicates = bind.execute(text(sql)).fetchall()
        if duplicates:
            raise RuntimeError(
                f"Cannot restore global unique on {label}: "
                "duplicate values exist (including archived rows)."
            )

    for index_name, table_name, _column_names in PARTIAL_INDEXES:
        op.drop_index(index_name, table_name=table_name)

    op.create_unique_constraint("users_username_key", "users", ["username"])
    op.create_unique_constraint("patients_nik_key", "patients", ["nik"])
    op.create_unique_constraint(
        "patients_medical_record_number_key",
        "patients",
        ["medical_record_number"],
    )
