"""Align schema with observed MRIQC dump edge cases.

Revision ID: 20260507_0001
Revises:
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op
from sqlalchemy.engine import Connection


revision = "20260507_0001"
down_revision = None
branch_labels = None
depends_on = None


TABLES = ("t1w", "t2w", "bold")
STRUCTURAL_TABLES = ("t1w", "t2w")
BIDS_FLOAT_COLUMNS = (
    "accel_num_reference_lines",
    "acceleration_factor_pe",
    "echo_train_length",
    "flip_angle",
    "number_of_averages",
    "number_shots",
    "percent_phase_field_of_view",
    "percent_sampling",
    "pixel_bandwidth",
    "total_scan_time_sec",
)
VOLUME_DISCARD_COLUMNS = (
    "number_of_volumes_discarded_by_scanner",
    "number_of_volumes_discarded_by_user",
)
STRUCTURAL_NULLABLE_COLUMNS = ("qi_1", "tpm_overlap_gm", "tpm_overlap_wm")
BOLD_NULLABLE_COLUMNS = ("aqi", "gsr_x", "gsr_y")


def _quote(connection: Connection, identifier: str) -> str:
    return connection.dialect.identifier_preparer.quote(identifier)


def _drop_canonical_views(connection: Connection) -> None:
    for table_name in TABLES:
        for view_name in ("exact", "series"):
            relation_name = _quote(connection, f"{table_name}_{view_name}")
            op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {relation_name}")


def _alter_type(
    connection: Connection,
    table_name: str,
    column_name: str,
    sql_type: str,
) -> None:
    table_identifier = _quote(connection, table_name)
    column_identifier = _quote(connection, column_name)
    op.execute(
        f"ALTER TABLE {table_identifier} "
        f"ALTER COLUMN {column_identifier} TYPE {sql_type} "
        f"USING {column_identifier}::{sql_type}"
    )


def _drop_not_null(
    connection: Connection,
    table_name: str,
    column_name: str,
) -> None:
    op.execute(
        f"ALTER TABLE {_quote(connection, table_name)} "
        f"ALTER COLUMN {_quote(connection, column_name)} DROP NOT NULL"
    )


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        return

    _drop_canonical_views(connection)

    for table_name in TABLES:
        _alter_type(connection, table_name, "subject_id", "varchar(128)")
        _alter_type(connection, table_name, "session_id", "varchar(128)")
        _alter_type(connection, table_name, "imaging_frequency", "bigint")
        for column_name in BIDS_FLOAT_COLUMNS:
            _alter_type(connection, table_name, column_name, "double precision")
        for column_name in VOLUME_DISCARD_COLUMNS:
            _alter_type(connection, table_name, column_name, "integer")

    for table_name in STRUCTURAL_TABLES:
        for column_name in STRUCTURAL_NULLABLE_COLUMNS:
            _drop_not_null(connection, table_name, column_name)

    for column_name in BOLD_NULLABLE_COLUMNS:
        _drop_not_null(connection, "bold", column_name)


def downgrade() -> None:
    pass
