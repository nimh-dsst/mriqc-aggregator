from sqlalchemy import BigInteger, Float, Integer, create_engine, inspect

from mriqc_aggregator.models import Base, BoldRecord, T1wRecord, T2wRecord


def test_sqlalchemy_models_create_tables() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {"bold", "t1w", "t2w"}
    engine.dispose()


def test_structural_models_expose_core_columns() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    t1w_columns = {
        column["name"] for column in inspector.get_columns(T1wRecord.__tablename__)
    }
    t2w_columns = {
        column["name"] for column in inspector.get_columns(T2wRecord.__tablename__)
    }
    bold_columns = {
        column["name"] for column in inspector.get_columns(BoldRecord.__tablename__)
    }

    shared = {
        "source_api_id",
        "source_md5sum",
        "subject_id",
        "session_id",
        "run_id",
        "acq_id",
        "manufacturer",
        "manufacturers_model_name",
        "magnetic_field_strength",
        "dedupe_exact_key",
        "dedupe_series_key",
        "dedupe_status",
        "canonical_source_api_id",
    }
    assert shared <= t1w_columns
    assert shared <= t2w_columns
    assert shared <= bold_columns

    assert "inversion_time" in t1w_columns
    assert "task_name" in bold_columns
    assert "rating_label" in bold_columns
    engine.dispose()


def test_dump_overflow_prone_string_columns_allow_host_dump_values() -> None:
    assert T1wRecord.__table__.c.patient_position.type.length == 128
    assert T2wRecord.__table__.c.patient_position.type.length == 128
    assert BoldRecord.__table__.c.gradient_set_type.type.length == 128


def test_schema_matches_observed_dump_edge_cases() -> None:
    for model in (T1wRecord, T2wRecord, BoldRecord):
        assert model.__table__.c.subject_id.type.length == 128
        assert model.__table__.c.session_id.type.length == 128
        assert isinstance(model.__table__.c.imaging_frequency.type, BigInteger)

        for column_name in (
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
        ):
            assert isinstance(model.__table__.c[column_name].type, Float)

        for column_name in (
            "number_of_volumes_discarded_by_scanner",
            "number_of_volumes_discarded_by_user",
        ):
            assert isinstance(model.__table__.c[column_name].type, Integer)

    for model in (T1wRecord, T2wRecord):
        assert model.__table__.c.qi_1.nullable
        assert model.__table__.c.tpm_overlap_gm.nullable
        assert model.__table__.c.tpm_overlap_wm.nullable

    assert BoldRecord.__table__.c.aqi.nullable
    assert BoldRecord.__table__.c.gsr_x.nullable
    assert BoldRecord.__table__.c.gsr_y.nullable
