# Backend

## Goal

Provide a thin PostgreSQL-backed API for the future dashboard without
introducing normalization yet.

The backend currently serves:

- dataset overview counts by modality
- representative row counts for `raw`, `exact`, and `series` views
- missingness summaries
- top categorical distributions
- duplicate histograms and sample duplicate groups
- key-frequency summaries for `*_extra` JSON columns

## Commands

Apply the latest schema and index definitions:

```bash
pixi run db-init
```

Write a point-in-time database profile snapshot into `docs/temp/`:

```bash
pixi run db-profile
```

Start the FastAPI app for local frontend work:

```bash
pixi run api-dev
```

Open the generated API docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Main Endpoints

- `GET /api/v1/health`
- `GET /api/v1/modalities`
- `GET /api/v1/overview`
- `GET /api/v1/modalities/{modality}/profile`
- `GET /api/v1/modalities/{modality}/missingness`
- `GET /api/v1/modalities/{modality}/distributions/{field_name}`
- `GET /api/v1/modalities/{modality}/extras/{column_name}`
- `GET /api/v1/modalities/{modality}/duplicates/{kind}`

## Query Parameters

Most read endpoints support:

- `view=raw|exact|series`
- repeated `manufacturers=...`
- repeated `mriqc_versions=...`
- repeated `task_ids=...`
- `source_created_from=...`
- `source_created_to=...`

The current `exact` and `series` views are representative-row views, not
canonicalized tables. They choose one row per dedupe key by ordering on
`source_created_at DESC, id DESC`.

## Notes

- The API reads directly from the raw observation tables: `t1w`, `t2w`, and `bold`.
- Duplicate summaries are always computed from raw filtered rows so the dashboard
  can show actual duplication pressure.
- `db-init` now creates missing indexes on existing tables as well as on fresh
  schemas.
