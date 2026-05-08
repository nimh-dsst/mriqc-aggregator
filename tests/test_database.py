from sqlalchemy import inspect, text

from mriqc_aggregator.canonical_views import ensure_canonical_views
from mriqc_aggregator.database import create_database_engine, create_database_schema


CANONICAL_MATVIEWS = (
    "bold_exact",
    "bold_series",
    "t1w_exact",
    "t1w_series",
    "t2w_exact",
    "t2w_series",
)
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
    assert set(inspector.get_table_names()) == {
        "alembic_version",
        "bold",
        "t1w",
        "t2w",
    }
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

    assert set(CANONICAL_MATVIEWS).issubset(relation_names)


def test_create_database_schema_migrates_legacy_schema_edge_columns(
    postgres_database_url: str,
) -> None:
    create_database_schema(postgres_database_url)

    engine = create_database_engine(postgres_database_url)
    with engine.begin() as connection:
        _drop_canonical_matviews(connection)
        for table_name in ("t1w", "t2w", "bold"):
            connection.execute(
                text(
                    f"ALTER TABLE {table_name} ALTER COLUMN subject_id TYPE varchar(64)"
                )
            )
            connection.execute(
                text(
                    f"ALTER TABLE {table_name} ALTER COLUMN session_id TYPE varchar(64)"
                )
            )
            connection.execute(
                text(
                    f"ALTER TABLE {table_name} "
                    "ALTER COLUMN imaging_frequency TYPE integer "
                    "USING imaging_frequency::integer"
                )
            )
            for column_name in BIDS_FLOAT_COLUMNS:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ALTER COLUMN {column_name} TYPE integer "
                        f"USING {column_name}::integer"
                    )
                )
            for column_name in VOLUME_DISCARD_COLUMNS:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ALTER COLUMN {column_name} TYPE double precision "
                        f"USING {column_name}::double precision"
                    )
                )

        for table_name in ("t1w", "t2w"):
            for column_name in ("qi_1", "tpm_overlap_gm", "tpm_overlap_wm"):
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ALTER COLUMN {column_name} SET NOT NULL"
                    )
                )
        for column_name in ("aqi", "gsr_x", "gsr_y"):
            connection.execute(
                text(f"ALTER TABLE bold ALTER COLUMN {column_name} SET NOT NULL")
            )

        ensure_canonical_views(connection)
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))

    create_database_schema(postgres_database_url)

    with engine.connect() as connection:
        columns = {
            (row.table_name, row.column_name): row
            for row in connection.execute(
                text(
                    "SELECT table_name, column_name, data_type, is_nullable, "
                    "character_maximum_length "
                    "FROM information_schema.columns "
                    "WHERE table_name IN ('t1w', 't2w', 'bold')"
                )
            )
        }
        matviews = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT matviewname "
                    "FROM pg_matviews "
                    "WHERE schemaname = current_schema()"
                )
            )
        }
        alembic_version = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
    engine.dispose()

    for table_name in ("t1w", "t2w", "bold"):
        assert columns[(table_name, "subject_id")].character_maximum_length == 128
        assert columns[(table_name, "session_id")].character_maximum_length == 128
        assert columns[(table_name, "imaging_frequency")].data_type == "bigint"
        for column_name in BIDS_FLOAT_COLUMNS:
            assert columns[(table_name, column_name)].data_type == "double precision"
        for column_name in VOLUME_DISCARD_COLUMNS:
            assert columns[(table_name, column_name)].data_type == "integer"

    for table_name in ("t1w", "t2w"):
        for column_name in ("qi_1", "tpm_overlap_gm", "tpm_overlap_wm"):
            assert columns[(table_name, column_name)].is_nullable == "YES"
    for column_name in ("aqi", "gsr_x", "gsr_y"):
        assert columns[("bold", column_name)].is_nullable == "YES"

    assert alembic_version == "20260507_0001"
    assert set(CANONICAL_MATVIEWS).issubset(matviews)


def _drop_canonical_matviews(connection) -> None:
    for relation_name in CANONICAL_MATVIEWS:
        connection.execute(text(f"DROP MATERIALIZED VIEW IF EXISTS {relation_name}"))
