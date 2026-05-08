from mriqc_aggregator.database import create_database_engine, default_database_url
from mriqc_aggregator.migration import run_migrations


if __name__ == "__main__":
    url = default_database_url()
    print(f"Running migrations at {url}")
    engine = create_database_engine(url)
    try:
        with engine.begin() as connection:
            run_migrations(connection)
    finally:
        engine.dispose()
