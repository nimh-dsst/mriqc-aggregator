from sqlalchemy import inspect, text

from mriqc_aggregator.database import create_database_engine, create_database_schema


def test_create_database_engine_accepts_explicit_url() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    assert str(engine.url) == "sqlite+pysqlite:///:memory:"
    engine.dispose()


def test_create_database_schema_creates_expected_tables(
    postgres_database_url: str,
) -> None:
    create_database_schema(postgres_database_url)

    engine = create_database_engine(postgres_database_url)
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {"bold", "t1w", "t2w"}
    engine.dispose()


def test_create_database_schema_creates_expected_indexes(
    postgres_database_url: str,
) -> None:
    create_database_schema(postgres_database_url)

    engine = create_database_engine(postgres_database_url)
    inspector = inspect(engine)
    bold_indexes = {index["name"] for index in inspector.get_indexes("bold")}
    t1w_indexes = {index["name"] for index in inspector.get_indexes("t1w")}

    assert "ix_bold_source_created_at" in bold_indexes
    assert "ix_bold_task_id" in bold_indexes
    assert "ix_bold_manufacturer" in bold_indexes
    assert "ix_t1w_source_created_at" in t1w_indexes
    assert "ix_t1w_manufacturer" in t1w_indexes
    engine.dispose()


def test_create_database_schema_creates_canonical_materialized_views(
    postgres_database_url: str,
) -> None:
    create_database_schema(postgres_database_url)

    engine = create_database_engine(postgres_database_url)
    with engine.connect() as connection:
        relation_names = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT matviewname "
                    "FROM pg_matviews "
                    "WHERE schemaname = current_schema()"
                )
            )
        }
    engine.dispose()

    assert {
        "bold_exact",
        "bold_series",
        "t1w_exact",
        "t1w_series",
        "t2w_exact",
        "t2w_series",
    }.issubset(relation_names)
