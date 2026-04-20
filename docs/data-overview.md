# Data Overview

This note captures a quick live-dataset sanity check performed against the
production database on `2026-04-20`.

## Scope

The immediate goal was to understand whether the spacing distributions shown in
the dashboard looked plausible, and whether the current API surface is rich
enough for users to reach similar conclusions without direct database access.

## Method

The check used both the API and direct PostgreSQL queries on the production
host.

- API checks were used to verify that filter semantics behaved correctly.
- Direct SQL was used for grouped spacing-pattern counts and outlier examples,
  because the current API does not yet expose the joint distributions, cohort
  summaries, or record-level slices needed for deeper inspection.

## High-Level Result

The center of the voxel-spacing distributions looks reasonable for a mixed MRIQC
reference dataset. The tails are real and include several plausible thick-slice
or low-resolution acquisition families, plus a smaller set of suspicious
records that are likely scouts, localizers, or otherwise not ideal reference
scans.

This looks more like heterogeneous source data than a global parsing failure.

## Typical Voxel Spacing Expectations

Reasonable modality-specific expectations for reference MRIQC data are roughly:

- `T1w`: `0.7-1.2 mm` isotropic for modern 3D anatomical scans.
- `T2w`: either `0.7-1.2 mm` isotropic for 3D scans, or about
  `0.4-0.8 mm` in-plane with `2-5 mm` slice thickness for 2D scans.
- `bold`: usually `2-4 mm` in-plane and `2-5 mm` through-plane.

That means very small in-plane values, very large through-plane values, or
highly anisotropic `T1w` records deserve review rather than silent acceptance.

## Live Distribution Summary

Series-view spacing quantiles from production:

| Modality | Metric | Min | P05 | Median | P95 | Max |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `T1w` | `spacing_x` | 0.142 | 0.800 | 1.000 | 1.200 | 44.399 |
| `T1w` | `spacing_y` | 0.213 | 0.800 | 1.000 | 1.055 | 8.000 |
| `T1w` | `spacing_z` | 0.142 | 0.800 | 1.000 | 1.102 | 12.000 |
| `T2w` | `spacing_x` | 0.094 | 0.491 | 1.000 | 1.100 | 8.000 |
| `T2w` | `spacing_y` | 0.094 | 0.500 | 1.000 | 1.198 | 8.000 |
| `T2w` | `spacing_z` | 0.156 | 0.500 | 1.000 | 3.000 | 9.520 |
| `bold` | `spacing_x` | 0.145 | 2.000 | 2.500 | 3.750 | 5.469 |
| `bold` | `spacing_y` | 0.300 | 2.000 | 2.500 | 3.750 | 5.469 |
| `bold` | `spacing_z` | 0.150 | 2.000 | 2.700 | 4.440 | 14.000 |

The medians and central bands are broadly believable.

## Common Spacing Families

The most common spacing triples are recognizable acquisition families rather
than random noise.

### `T1w`

Most common series-view spacing triples:

- `1.0 x 1.0 x 1.0`: `319,180`
- `0.8 x 0.8 x 0.8`: `52,337`
- `1.2 x 1.0 x 1.0`: `22,470`
- `1.2 x 1.055 x 1.055`: `18,631`

### `T2w`

Most common series-view spacing triples:

- `1.0 x 1.0 x 1.0`: `76,963`
- `0.8 x 0.8 x 0.8`: `18,177`
- `0.859 x 0.859 x 3.0`: `2,167`
- `1.0 x 1.0 x 4.0`: `1,615`
- `0.449 x 0.449 x 5.0`: `693`

These T2w tails are consistent with a mix of 3D isotropic and 2D thick-slice
protocols.

### `bold`

Most common series-view spacing triples:

- `2.0 x 2.0 x 2.0`: `69,272`
- `3.0 x 3.0 x 3.0`: `46,948`
- `2.4 x 2.4 x 2.4`: `39,011`
- `3.4375 x 3.4375 x 4.0`: `13,263`
- `4.0 x 4.0 x 4.0`: `5,473`

Again, these look like real protocol clusters rather than a unit-conversion
mistake.

## Suspicious Tails

The extreme tail still contains records that should probably not be part of a
default reference cohort.

Examples:

- `T1w` records with `spacing_x` between roughly `22 mm` and `44 mm` while
  `spacing_y/z` stay near `1 mm`.
- `T2w` records like `0.491 x 0.491 x 9.52`.
- `T2w` records like `8 x 8 x 8`.
- `bold` records around `3.75 x 3.75 x 14.0`, especially from `GE SIGNA HDx`.

These may be scouts, localizers, mislabeled series, or otherwise unusual
acquisitions that are poor default references even if they are technically
valid rows.

## Rough Outlier Rates

Using simple modality-specific spacing envelopes:

- `T1w`: about `2-3%` of series rows fall outside a normal structural range.
- `T2w`: about `4-5%` of series rows fall outside a normal T2w range.
- `bold`: about `0.3%` of series rows fall outside a normal BOLD range.

These are not catastrophic rates, but they are large enough to justify
screening or flagging logic in the product.

## Additional Integrity Checks

- No zero or negative spacing values were found in `t1w_series`, `t2w_series`,
  or `bold_series`.
- The previously observed `NaN` histogram issue was a rendering/API handling
  bug, not a broad pattern of invalid numeric values across canonical views.
- `source_created_at` coverage looks plausible:
  - `bold`: `2017-06-06` to `2026-04-15`
  - `T1w`: `2017-06-06` to `2026-03-27`
  - `T2w`: `2018-03-02` to `2026-04-15`

## Dashboard Filter Note

The API correctly honors date filters. For example, filtering `T2w` metrics to
`2026-04-19` returns zero rows. A dashboard screenshot showed full sample counts
with that date range displayed, which indicates a frontend state/rendering bug
rather than a backend filter bug.

## Why Direct SQL Was Still Necessary

The current API is good enough for:

- modality-level metric summaries
- single-field histograms
- simple categorical value distributions

It is not yet good enough for higher-value exploration tasks such as:

- joint acquisition-pattern analysis
- grouped spacing or protocol-family summaries
- outlier cohort extraction
- timeline coverage summaries
- drill-down from an unusual cluster to example records

That is why direct PostgreSQL queries were needed for this check.

## Recommended API Expansion

If the goal is to make the data more useful for others, the next API step
should be broader analytical endpoints rather than a narrow one-off sanity
route.

The most useful additions would be:

1. `protocol` or `acquisition-profile` endpoints
   Group rows by spacing, matrix size, TR/TE, manufacturer, model, task, and
   view so users can see the dominant acquisition families directly.

2. `outlier` endpoints
   Return counts and sample records for rows outside modality-specific ranges,
   for example unusually anisotropic `T1w`, very thick-slice `T2w`, or extreme
   `bold` through-plane spacing.

3. `coverage` endpoints
   Summarize row counts by date, manufacturer, model, MRIQC version, and task so
   users can understand growth, recency, and cohort balance.

4. `facet` endpoints for numeric metrics
   Support grouped summaries such as `spacing_z by manufacturer`,
   `fd_mean by task`, or `cjv by MRIQC version`.

5. record-sample drill-down
   Return a capped list of representative records behind a cohort, cluster, or
   outlier bucket so users can inspect suspicious rows without direct SQL.

6. bundled dashboard endpoints
   Allow the frontend to request several metric cards, shared filter metadata,
   and cohort context in one round trip instead of many independent requests.

## Product Direction

The dashboard would become much more trustworthy and useful if it:

- flags likely non-reference acquisitions by default
- lets users include or exclude those flagged cohorts explicitly
- exposes protocol-family summaries instead of forcing interpretation from raw
  histogram tails alone
- supports grouped exploration without requiring direct database access
