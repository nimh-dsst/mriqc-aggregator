# Production Operations

## Host Layout

The production host keeps code and persistent data separate:

- `/opt/mriqc-aggregator`: current deployed bundle used by `mriqc-aggregator.service`
- `/data/postgres`: PostgreSQL data directory
- `/data/dump`: host-side MRIQC dump files used for backfills
- `/data/nginx/certs`: TLS certificate material served by nginx

`/opt/mriqc-aggregator` is treated as a deploy artifact, not a long-lived git
checkout. The persistent EBS volume is mounted at `/data`, so routine redeploys
must preserve `/data` but can replace `/opt/mriqc-aggregator`.

## Safe Redeploy

Redeploy by shipping a clean repository bundle to the host, swapping the app
directory, and restarting the systemd-managed compose stack.

1. Build a bundle from the branch or ref you want to deploy.
2. Copy it to the host.
3. Preserve the existing `/opt/mriqc-aggregator/.env`.
4. Move the current `/opt/mriqc-aggregator` aside to a timestamped backup.
5. Replace it with the new bundle.
6. Restart `mriqc-aggregator.service`.
7. Verify container health and row counts.

The important rule is simple: preserve `/data`, and do not use `tofu destroy`
when the PostgreSQL contents matter.

Useful verification commands on the host:

```bash
systemctl status --no-pager mriqc-aggregator.service
docker ps --format 'table {{.Names}}\t{{.Status}}'
curl -fsS https://mriqcdb-aggregator.site/api/v1/health
docker exec mriqc-aggregator-postgres-1 \
  psql -U mriqc -d mriqc_aggregator -At -F ',' \
  -c "select 'bold', count(*) from bold union all select 't1w', count(*) from t1w union all select 't2w', count(*) from t2w order by 1;"
```

## Performance Notes

The dashboard now serves `exact` and `series` from PostgreSQL materialized
views instead of recomputing representative rows on every request.

### What Helps Now

- The frontend now splits the dashboard shell, upload tooling, and chart code
  into separate chunks instead of shipping one large JavaScript bundle.
- The frontend memoizes identical API requests in memory and deduplicates
  in-flight fetches.
- The frontend exposes manufacturer, MRIQC version, task, and date filters so
  the dashboard can narrow the reference set before computing charts.
- Histogram cards default to a clipped display range (`p01`–`p99`) so extreme
  outliers do not flatten the plot.
- The API adds a per-worker timed response cache for read endpoints and returns
  `Cache-Control` plus `X-MRIQC-Cache` headers.
- Histogram/statistics queries now compute aggregates in PostgreSQL instead of
  pulling every value into Python first.
- `exact` and `series` now read from materialized canonical views (`*_exact`,
  `*_series`) that are refreshed after loader runs.

### What Still Costs Time

Cold histogram and summary requests on the large canonical views can still take
noticeable time, especially when the dashboard asks for several metrics at
once or when filters still leave a very large `bold` subset in play.

In practice this means:

- the first request to a cold worker is the slowest
- repeated requests with the same parameters should be much faster
- restarting the API clears the in-process cache

### Refresh Canonical Views

Canonical materialized views are refreshed automatically by `load-raw-run` and
`load-dump`. If you bulk edit the database in some other way, refresh them
explicitly:

```bash
pixi run python -m mriqc_aggregator.cli refresh-canonical-views --modalities bold T1w T2w
```

### How To Warm The Cache

If you want the main dashboard view to be ready immediately after a deploy,
prime the common responses once from the host after the canonical views are in
sync:

```bash
curl -fsS https://mriqcdb-aggregator.site/api/v1/modalities >/dev/null
curl -fsS 'https://mriqcdb-aggregator.site/api/v1/modalities/bold/metrics?view=series' >/dev/null
curl -fsS 'https://mriqcdb-aggregator.site/api/v1/modalities/bold/metrics/tsnr?view=series&bins=24' >/dev/null
```

## Next Steps If This Is Still Too Slow

The next material performance step is not more request caching. The likely next
layer is precomputed aggregate serving data on top of the canonical views:

- precomputed summary tables or materialized views for the dashboard endpoints
- dedicated aggregate tables for common filter combinations
- request bundling for multi-metric dashboard loads when the selected metric
  count is high
