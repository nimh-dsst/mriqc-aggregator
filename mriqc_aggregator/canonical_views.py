from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import column, table
from sqlalchemy.engine import Connection, Engine

from .models import BoldRecord, T1wRecord, T2wRecord


CANONICAL_VIEW_KEY_COLUMNS = {
    "exact": "dedupe_exact_key",
    "series": "dedupe_series_key",
}

CANONICAL_VIEW_FILTER_COLUMNS = {
    "t1w": ("source_created_at", "manufacturer", "mriqc_version"),
    "t2w": ("source_created_at", "manufacturer", "mriqc_version"),
    "bold": ("source_created_at", "manufacturer", "mriqc_version", "task_id"),
}

MODEL_BY_MODALITY = {
    "T1w": T1wRecord,
    "T2w": T2wRecord,
    "bold": BoldRecord,
}


def supports_canonical_views(bind: Engine | Connection) -> bool:
    return bind.dialect.name == "postgresql"


def canonical_view_name(
    model: type[T1wRecord] | type[T2wRecord] | type[BoldRecord],
    view_name: str,
) -> str:
    return f"{model.__table__.name}_{view_name}"


def canonical_view_table(
    model: type[T1wRecord] | type[T2wRecord] | type[BoldRecord],
    view_name: str,
) -> Any:
    return table(
        canonical_view_name(model, view_name),
        *[
            column(source_column.name, type_=source_column.type)
            for source_column in model.__table__.columns
        ],
    )


def ensure_canonical_views(connection: Connection) -> None:
    if not supports_canonical_views(connection):
        return

    for model in MODEL_BY_MODALITY.values():
        for view_name in CANONICAL_VIEW_KEY_COLUMNS:
            if not _relation_exists(connection, canonical_view_name(model, view_name)):
                _create_canonical_view(connection, model, view_name)
            _ensure_canonical_view_indexes(connection, model, view_name)


def refresh_canonical_views(
    *,
    url: str | None = None,
    engine: Engine | None = None,
    modalities: Iterable[str] | None = None,
) -> None:
    active_engine = engine
    should_dispose = False
    if active_engine is None:
        from .database import create_database_engine

        active_engine = create_database_engine(url=url)
        should_dispose = True

    try:
        if not supports_canonical_views(active_engine):
            return
        selected_modalities = tuple(modalities or MODEL_BY_MODALITY)
        with active_engine.begin() as connection:
            ensure_canonical_views(connection)
            for modality in selected_modalities:
                model = MODEL_BY_MODALITY[modality]
                for view_name in CANONICAL_VIEW_KEY_COLUMNS:
                    connection.exec_driver_sql(
                        f"REFRESH MATERIALIZED VIEW "
                        f"{_quote_identifier(connection, canonical_view_name(model, view_name))}"
                    )
    finally:
        if should_dispose and active_engine is not None:
            active_engine.dispose()


def _quote_identifier(connection: Connection, identifier: str) -> str:
    return connection.dialect.identifier_preparer.quote(identifier)


def _quote_table_name(
    connection: Connection,
    model: type[T1wRecord] | type[T2wRecord] | type[BoldRecord],
) -> str:
    table_name = model.__table__.name
    schema = model.__table__.schema
    if schema:
        return (
            f"{_quote_identifier(connection, schema)}."
            f"{_quote_identifier(connection, table_name)}"
        )
    return _quote_identifier(connection, table_name)


def _relation_exists(connection: Connection, relation_name: str) -> bool:
    return (
        connection.exec_driver_sql("SELECT to_regclass(%s)", (relation_name,)).scalar()
        is not None
    )


def _create_canonical_view(
    connection: Connection,
    model: type[T1wRecord] | type[T2wRecord] | type[BoldRecord],
    view_name: str,
) -> None:
    key_column_name = CANONICAL_VIEW_KEY_COLUMNS[view_name]
    quoted_view_name = _quote_identifier(
        connection, canonical_view_name(model, view_name)
    )
    quoted_table_name = _quote_table_name(connection, model)
    quoted_columns = ", ".join(
        _quote_identifier(connection, column.name) for column in model.__table__.columns
    )
    quoted_key = _quote_identifier(connection, key_column_name)
    quoted_source_id = _quote_identifier(connection, "source_api_id")
    quoted_source_created_at = _quote_identifier(connection, "source_created_at")
    quoted_id = _quote_identifier(connection, "id")
    connection.exec_driver_sql(
        f"CREATE MATERIALIZED VIEW {quoted_view_name} AS "
        f"WITH ranked AS ("
        f"  SELECT {quoted_columns}, "
        f"  row_number() OVER ("
        f"    PARTITION BY COALESCE({quoted_key}, {quoted_source_id}) "
        f"    ORDER BY {quoted_source_created_at} DESC NULLS LAST, {quoted_id} DESC"
        f"  ) AS row_number "
        f"  FROM {quoted_table_name}"
        f") "
        f"SELECT {quoted_columns} FROM ranked WHERE row_number = 1"
    )


def _ensure_canonical_view_indexes(
    connection: Connection,
    model: type[T1wRecord] | type[T2wRecord] | type[BoldRecord],
    view_name: str,
) -> None:
    relation_name = canonical_view_name(model, view_name)
    quoted_relation_name = _quote_identifier(connection, relation_name)
    index_columns = (
        "source_api_id",
        *CANONICAL_VIEW_FILTER_COLUMNS[model.__table__.name],
    )
    for column_name in index_columns:
        index_name = f"ix_{relation_name}_{column_name}"
        connection.exec_driver_sql(
            f"CREATE INDEX IF NOT EXISTS {_quote_identifier(connection, index_name)} "
            f"ON {quoted_relation_name} ({_quote_identifier(connection, column_name)})"
        )

    unique_index_name = f"ux_{relation_name}_source_api_id"
    connection.exec_driver_sql(
        f"CREATE UNIQUE INDEX IF NOT EXISTS {_quote_identifier(connection, unique_index_name)} "
        f"ON {quoted_relation_name} ({_quote_identifier(connection, 'source_api_id')})"
    )
