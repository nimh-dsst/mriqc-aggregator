from pathlib import Path

from sqlalchemy import inspect

from mriqc_aggregator.database import create_database_engine, create_database_schema


def test_create_database_engine_accepts_explicit_url() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    assert str(engine.url) == "sqlite+pysqlite:///:memory:"


def test_create_database_schema_creates_expected_tables() -> None:
    database_path = Path("test-schema.db")
    database_url = f"sqlite+pysqlite:///{database_path}"
    create_database_schema(database_url)

    engine = create_database_engine(database_url)
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {"bold", "t1w", "t2w"}
    database_path.unlink()


def test_create_database_schema_creates_expected_indexes() -> None:
    database_path = Path("test-indexes.db")
    database_url = f"sqlite+pysqlite:///{database_path}"
    create_database_schema(database_url)

    engine = create_database_engine(database_url)
    inspector = inspect(engine)
    bold_indexes = {index["name"] for index in inspector.get_indexes("bold")}
    t1w_indexes = {index["name"] for index in inspector.get_indexes("t1w")}

    assert "ix_bold_source_created_at" in bold_indexes
    assert "ix_bold_task_id" in bold_indexes
    assert "ix_bold_manufacturer" in bold_indexes
    assert "ix_t1w_source_created_at" in t1w_indexes
    assert "ix_t1w_manufacturer" in t1w_indexes

    database_path.unlink()
