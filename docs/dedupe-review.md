# Dedupe Review

## Scope

This note reviews the dedupe work currently implemented in `mriqc-aggregator`.
It is not a proposal for a final canonicalization system. The goal is to make
the current strategy explicit, call out what is actually wired today, and list
the main risks that still need decisions or follow-up work.

Relevant implementation files:

- `mriqc_aggregator/parsing.py`
- `mriqc_aggregator/models.py`
- `mriqc_aggregator/loading.py`
- `mriqc_aggregator/profiling.py`
- `mriqc_aggregator/app.py`

Related design notes:

- `docs/schema-design.md`
- `docs/duplicate-handling.md`
- `docs/backend.md`

## Review Summary

The current dedupe work is a solid first-stage read model, not a full
canonicalization system.

What it gets right:

- raw source rows are preserved instead of being destructively merged
- exact duplicates and heuristic series duplicates are separated
- dedupe is exposed consistently through API read views
- duplicate pressure remains observable through dedicated duplicate summaries

What it does not do yet:

- it does not persist a canonical row per duplicate group
- it does not apply a quality-aware or completeness-aware representative policy
- it does not use `dedupe_status` or `canonical_source_api_id` operationally

The main risk is that downstream consumers could mistake `exact` or `series`
views for fully adjudicated canonical data. They are not. They are
representative-row query modes on top of raw tables.

## Current Strategy

### 1. All raw rows are retained

The loader upserts raw observations by `source_api_id`. No duplicate rows are
deleted at ingest time. The source tables remain the system of record.

Current tables:

- `t1w`
- `t2w`
- `bold`

### 2. Two dedupe keys are computed at load time

Each observation stores:

- `dedupe_exact_key`
- `dedupe_series_key`
- `dedupe_status`
- `canonical_source_api_id`

The implemented meaning today is:

- `dedupe_exact_key`: copied from `provenance.md5sum`
- `dedupe_series_key`: SHA-256 of a modality-local normalized identity payload
- `dedupe_status`: always initialized as `pending`
- `canonical_source_api_id`: reserved for future use

### 3. Exact dedupe is payload-based

`exact` dedupe uses `provenance.md5sum` as the grouping key. This is the
highest-confidence signal in the current system because it is intended to
represent repeated payload content rather than a broader acquisition heuristic.

### 4. Series dedupe is modality-local and heuristic

`series` dedupe hashes a subset of modality-specific identity fields.

Structural modalities use:

- subject, session, run, acquisition labels
- scanner identity
- field strength
- echo, repetition, inversion, and flip parameters
- image size and spacing

`bold` uses a similar identity plus task and temporal geometry fields.

This is useful for estimating likely repeated acquisitions, but it is not proof
that two rows refer to the same real-world scan.

### 5. Dedupe is applied at query time

The API exposes three read modes:

- `raw`: all loaded rows
- `exact`: one representative row per `dedupe_exact_key`
- `series`: one representative row per `dedupe_series_key`

Representative selection is currently:

1. newest `source_created_at`
2. highest surrogate `id`

That policy is deterministic, but it is only a recency rule. It is not a
semantic best-row rule.

### 6. Duplicate summaries stay raw

Duplicate summary endpoints do not report representative-row counts. They group
the filtered raw rows so the dashboard can still show actual duplicate pressure.

## What Is Working Well

### Reversible design

The raw facts are preserved. That keeps future policy changes possible and makes
this safer than collapsing rows permanently during ingest.

### Clear separation between exact and heuristic dedupe

The implementation distinguishes high-confidence duplicate detection
(`exact`) from broader acquisition-level approximation (`series`). That is a
sound boundary.

### API-level consistency

The `view` parameter is applied across overview counts, distributions, metric
summaries, missingness, and profile payloads. That makes the read semantics
predictable.

### Good observability of duplicate pressure

The duplicate summary endpoints are useful operationally because they expose
group counts, row counts, histograms, and sampled members from the raw set.

## Outstanding Risks

### 1. Series keys are unstable across semantically equivalent numeric types

`normalize_identity_value()` normalizes floats, but not integers. That means
numerically equivalent values such as `64` and `64.0` hash differently in the
series identity payload.

Observed example:

- `compute_dedupe_series_key("T1w", {"subject_id": "subj", "size_x": 64})`
- `compute_dedupe_series_key("T1w", {"subject_id": "subj", "size_x": 64.0})`

These produce different hashes today.

Impact:

- under-collapsing likely duplicate acquisitions
- inconsistent series grouping when upstream JSON encodes the same number with
  different numeric types

### 2. The implementation treats md5 as required, not optional

The design notes describe md5 as a strong signal that may be absent or
inconsistent. The code path is stricter:

- `source_md5sum` is non-nullable in the ORM
- required-column validation will reject payloads that do not include it

Impact:

- ingestion fails instead of degrading gracefully when upstream data lack md5
- the current system cannot actually exercise the documented "series works when
  md5 is missing" path

### 3. Representative selection is not quality-aware

The schema design note recommends a richer canonical-pick order, including
newer MRIQC versions and more complete metadata. That logic is not implemented.
The current winner is only "newest created row, then highest id."

Impact:

- a newer but less complete or less desirable row can become the representative
- `exact` and `series` views can drift from what analysts would consider the
  best record in a duplicate group

### 4. Canonical-state fields are present but not operational

`dedupe_status` and `canonical_source_api_id` exist in the schema, but the
loader sets `dedupe_status` to `pending` and the read layer ignores both
columns.

Impact:

- downstream consumers may over-interpret those columns as adjudicated state
- there is no workflow yet for marking canonical, duplicate, or review-needed
  rows

### 5. Series identity can still over-collapse or under-collapse

The current series key intentionally uses a constrained identity tuple. That
keeps the first implementation simple, but it leaves normal heuristic risk.

Under-collapse examples:

- one row is missing `session_id`, `run_id`, `task_id`, or scanner metadata
- equivalent values are encoded with different numeric types
- nominally matching rows differ in one metadata field due to upstream noise

Over-collapse examples:

- two distinct acquisitions share the same subject/session/run/acq/task pattern
- the selected identity fields are too coarse to distinguish repeats

### 6. Dedupe remains a read-time behavior, not a persisted canonical layer

Every deduped view is computed at query time from raw rows. That is safe for a
first iteration, but it leaves some unresolved concerns.

Impact:

- no canonical audit trail beyond the current ranking rule
- policy changes will rewrite history for all downstream views immediately
- consumers cannot join directly against a stable canonical table

### 7. Test coverage is still narrow around dedupe correctness

The current tests verify that:

- dedupe keys are populated
- exact duplicate counts appear in profiles
- the API serves deduped views

Important gaps remain:

- no test for integer-vs-float normalization in series identity fields
- no test for `series` representative selection under collisions
- no test for tie-break behavior beyond the current happy path
- no test for missing-md5 ingestion behavior

## Recommended Next Steps

### Near term

- normalize numeric identity fields in a type-stable way before hashing
- decide whether missing md5 should be accepted or the docs should be tightened
- add tests for series-key normalization and representative-row selection

### Medium term

- decide whether `exact` should remain the default deduped read mode
- implement a deliberate canonical-pick policy if analysts need stable "best
  row" semantics
- either wire `dedupe_status` and `canonical_source_api_id` into a review flow
  or document them as reserved-only fields more aggressively

### Longer term

- decide whether to keep dedupe entirely as a query-time concern
- or introduce a persisted canonical layer once the policy is stable

## Bottom Line

The dedupe effort is in a good place for exploratory analytics and dashboard
work. It gives the project conservative exact dedupe, a usable heuristic series
view, and visibility into duplicate pressure without throwing raw data away.

The main limitation is that the system stops at representative-row selection. It
does not yet provide a durable canonical-record model, and a few edge cases can
still make series dedupe unstable or misleading. The next round of work should
focus on making the series key type-stable, aligning the md5 contract with the
docs, and deciding whether a true canonical selection workflow is needed.
