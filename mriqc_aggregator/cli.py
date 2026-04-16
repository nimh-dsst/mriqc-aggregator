from __future__ import annotations

import argparse
from pathlib import Path

from .workflows import MODALITIES, pull_representative_sample


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mriqc-aggregator",
        description="Pull representative raw samples from the MRIQC Web API.",
    )
    parser.add_argument(
        "command",
        choices=["pull-representative"],
        help="Workflow to run.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data"),
        help="Root directory for ignored local outputs.",
    )
    parser.add_argument(
        "--modalities",
        nargs="+",
        default=list(MODALITIES),
        choices=list(MODALITIES),
        help="Modalities to sample.",
    )
    parser.add_argument(
        "--pages-per-modality",
        type=int,
        default=64,
        help="Number of archive-spanning raw pages to fetch per modality.",
    )
    parser.add_argument(
        "--target-total-gb",
        type=float,
        default=None,
        help="Optional total raw size budget across modalities.",
    )
    parser.add_argument(
        "--max-pages-per-modality",
        type=int,
        default=128,
        help="Hard cap on sampled raw pages per modality.",
    )
    parser.add_argument(
        "--max-probe-rounds",
        type=int,
        default=12,
        help="Maximum exponential page probes per modality.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "pull-representative":
        parser.error(f"Unsupported command: {args.command}")

    layout = pull_representative_sample(
        output_root=args.output_root,
        modalities=args.modalities,
        pages_per_modality=args.pages_per_modality,
        target_total_gb=args.target_total_gb,
        max_pages_per_modality=args.max_pages_per_modality,
        max_probe_rounds=args.max_probe_rounds,
    )
    print(f"Representative sample written to {layout.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
