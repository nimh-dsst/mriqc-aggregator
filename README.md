# mriqc-aggregator

Reusable Python tooling for pulling representative MRIQC Web API samples into a local raw data cache.

## Layout

- `mriqc_aggregator/`: reusable package code
- `scripts/`: thin entrypoint wrappers around package workflows
- `docs/`: project documentation
- `docs/temp/`: ignored scratch space
- `data/`: ignored local data outputs

## Quickstart

```bash
pixi run pull-sample -- --pages-per-modality 64
```

That command will:

1. Discover a usable page frontier for `T1w`, `T2w`, and `bold`
2. Build a wide archive-spanning page plan
3. Download exact raw API page payloads into `data/runs/<run-id>/raw/`
4. Write derived item/page manifests and a summary for inspection

See [docs/representative-sampling.md](/Users/johnlee/code/mriqc-aggregator/docs/representative-sampling.md) for details.
