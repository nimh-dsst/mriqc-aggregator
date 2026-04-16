# Representative Sampling

## Goal

Pull a reusable, rerunnable, raw sample from `https://mriqc.nimh.nih.gov/api/v1`
for `T1w`, `T2w`, and `bold` without prematurely normalizing the payloads.

## Why Pages Instead Of Records

The live API is an Eve app backed by MongoDB. It exposes page-based list endpoints
and caps `max_results` at `50`. Pulling representative raw pages has two benefits:

1. The saved JSON matches the live API payload exactly.
2. Broad archive coverage is cheap because we can sample page positions instead of
   downloading the entire collection.

## Workflow

1. Probe each modality at exponentially increasing page numbers.
2. Use the highest successful probe as a lower-bound frontier.
3. Build a wide page plan from:
   - early pages
   - probe pages
   - tail pages near the discovered frontier
   - evenly spaced pages across the discovered range
4. Fetch exact raw JSON for every selected page.
5. Derive page-level and item-level manifests from those raw payloads.

## Outputs

Each run is written under `data/runs/<run-id>/`.

- `config.json`: run configuration
- `frontier/`: page frontier estimates and average raw page sizes
- `plans/`: selected pages per modality
- `raw/<modality>/page-*.json`: exact API responses
- `manifest/*-pages.jsonl`: derived page summaries
- `manifest/*-items.jsonl`: derived item summaries
- `summary.json`: run-level totals and modality summaries

## Notes

- The current workflow favors broad archive coverage over exhaustive crawling.
- The derived manifests are for inspection only. The raw source of truth is the
  saved page JSON under `raw/`.
- Explicit `--pages-per-modality` requests are honored as-is unless you also
  set `--max-pages-per-modality`.
- If later work requires denser coverage, rerun with a larger
  `--pages-per-modality` or use the optional `--target-total-gb` budget.
- The current larger exploratory run is `20260416T175935Z`, which pulled
  `231,100` observations and about `676 MB` of raw JSON payload.
