from __future__ import annotations

import os

import uvicorn

from mriqc_aggregator.database import create_database_schema, default_database_url


if __name__ == "__main__":
    create_database_schema(url=default_database_url())
    uvicorn.run(
        "mriqc_aggregator.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("API_PORT", "8000")),
    )
