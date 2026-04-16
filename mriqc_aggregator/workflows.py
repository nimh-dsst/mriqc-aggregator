from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .api import MRIQCAPIError, MRIQCWebAPIClient, page_items
from .planning import (
    FrontierEstimate,
    desired_pages_per_modality,
    discover_frontier,
    estimate_average_page_bytes,
    plan_pages,
)
from .storage import (
    RunLayout,
    append_jsonl,
    build_run_layout,
    make_run_id,
    write_json,
    write_text,
)


MODALITIES = ("T1w", "T2w", "bold")

IMPORTANT_FIELDS = {
    "T1w": (
        "session_id",
        "run_id",
        "acq_id",
        "Manufacturer",
        "ManufacturersModelName",
        "MagneticFieldStrength",
        "EchoTime",
        "InversionTime",
        "RepetitionTime",
    ),
    "T2w": (
        "session_id",
        "run_id",
        "acq_id",
        "Manufacturer",
        "ManufacturersModelName",
        "MagneticFieldStrength",
        "EchoTime",
        "RepetitionTime",
    ),
    "bold": (
        "session_id",
        "run_id",
        "acq_id",
        "task_id",
        "TaskName",
        "Manufacturer",
        "ManufacturersModelName",
        "MagneticFieldStrength",
        "EchoTime",
        "RepetitionTime",
    ),
}


def _missing_important_fields(modality: str, bids_meta: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in IMPORTANT_FIELDS[modality]:
        value = bids_meta.get(field)
        if value in (None, ""):
            missing.append(field)
    return missing


def _page_summary(
    modality: str,
    page: int,
    reasons: list[str],
    payload: dict[str, Any],
    raw_bytes: int,
) -> dict[str, Any]:
    items = page_items(payload)
    md5_counter = Counter(
        item.get("provenance", {}).get("md5sum")
        for item in items
        if item.get("provenance", {}).get("md5sum")
    )
    subject_counter = Counter(
        item.get("bids_meta", {}).get("subject_id")
        for item in items
        if item.get("bids_meta", {}).get("subject_id")
    )
    missing_counter = Counter()
    for item in items:
        missing_counter.update(
            _missing_important_fields(modality, item.get("bids_meta", {}))
        )

    return {
        "modality": modality,
        "page": page,
        "reasons": reasons,
        "item_count": len(items),
        "first_created": items[0].get("_created") if items else None,
        "last_created": items[-1].get("_created") if items else None,
        "duplicate_md5_groups": sum(1 for count in md5_counter.values() if count > 1),
        "duplicate_subject_groups": sum(
            1 for count in subject_counter.values() if count > 1
        ),
        "missing_important_counts": dict(sorted(missing_counter.items())),
        "raw_bytes": raw_bytes,
    }


def _item_manifest_rows(
    modality: str,
    page: int,
    reasons: list[str],
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(page_items(payload), start=1):
        bids_meta = item.get("bids_meta", {})
        provenance = item.get("provenance", {})
        rows.append(
            {
                "modality": modality,
                "page": page,
                "item_index": index,
                "item_id": item.get("_id"),
                "created": item.get("_created"),
                "reasons": reasons,
                "bids_meta": bids_meta,
                "provenance": provenance,
                "bids_meta_key_count": len(bids_meta),
                "missing_important_fields": _missing_important_fields(
                    modality, bids_meta
                ),
            }
        )
    return rows


def _modality_summary(
    modality: str,
    frontier: FrontierEstimate,
    raw_pages: list[dict[str, Any]],
    item_rows: list[dict[str, Any]],
    error_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    versions = Counter(
        row.get("provenance", {}).get("version")
        for row in item_rows
        if row.get("provenance", {}).get("version")
    )
    manufacturers = Counter(
        row.get("bids_meta", {}).get("Manufacturer")
        for row in item_rows
        if row.get("bids_meta", {}).get("Manufacturer")
    )
    task_ids = Counter(
        row.get("bids_meta", {}).get("task_id")
        for row in item_rows
        if row.get("bids_meta", {}).get("task_id")
    )
    missing_counter = Counter()
    for row in item_rows:
        missing_counter.update(row["missing_important_fields"])

    return {
        "modality": modality,
        "frontier": frontier.to_dict(),
        "page_count": len(raw_pages),
        "item_count": len(item_rows),
        "page_error_count": len(error_rows),
        "page_errors": error_rows[:10],
        "raw_bytes": sum(page["raw_bytes"] for page in raw_pages),
        "top_versions": versions.most_common(10),
        "top_manufacturers": manufacturers.most_common(10),
        "top_task_ids": task_ids.most_common(10),
        "missing_important_counts": dict(sorted(missing_counter.items())),
    }


def pull_representative_sample(
    *,
    output_root: Path,
    modalities: list[str],
    pages_per_modality: int | None,
    target_total_gb: float | None,
    max_pages_per_modality: int | None,
    max_probe_rounds: int,
) -> RunLayout:
    run_id = make_run_id()
    layout = build_run_layout(output_root, run_id)
    write_json(
        layout.config_path,
        {
            "modalities": modalities,
            "pages_per_modality": pages_per_modality,
            "target_total_gb": target_total_gb,
            "max_pages_per_modality": max_pages_per_modality,
            "max_probe_rounds": max_probe_rounds,
        },
    )

    per_modality_summaries: dict[str, dict[str, Any]] = {}
    with MRIQCWebAPIClient() as client:
        frontiers = {
            modality: discover_frontier(
                client,
                modality,
                max_probe_rounds=max_probe_rounds,
            )
            for modality in modalities
        }
        for modality, frontier in frontiers.items():
            write_json(
                layout.frontier_dir / f"{modality}.json",
                frontier.to_dict(),
            )

        avg_page_bytes = {
            modality: estimate_average_page_bytes(client, modality, frontier)
            for modality, frontier in frontiers.items()
        }
        write_json(layout.frontier_dir / "avg-page-bytes.json", avg_page_bytes)

        desired_page_counts = desired_pages_per_modality(
            modalities=modalities,
            page_bytes_by_modality=avg_page_bytes,
            pages_per_modality=pages_per_modality,
            target_total_gb=target_total_gb,
            max_pages_per_modality=max_pages_per_modality,
        )
        write_json(layout.plans_dir / "page-counts.json", desired_page_counts)

        total_raw_bytes = 0
        total_items = 0
        for modality in modalities:
            frontier = frontiers[modality]
            page_plan = plan_pages(
                frontier,
                desired_count=min(
                    desired_page_counts[modality], frontier.lower_bound_page
                ),
            )
            write_json(
                layout.plans_dir / f"{modality}.json",
                [entry.to_dict() for entry in page_plan],
            )

            page_manifest_path = layout.manifest_dir / f"{modality}-pages.jsonl"
            item_manifest_path = layout.manifest_dir / f"{modality}-items.jsonl"
            page_error_path = layout.manifest_dir / f"{modality}-page-errors.jsonl"
            raw_modality_dir = layout.raw_dir / modality
            page_rows: list[dict[str, Any]] = []
            item_rows: list[dict[str, Any]] = []
            error_rows: list[dict[str, Any]] = []

            for entry in page_plan:
                try:
                    response = client.fetch_page(modality, entry.page)
                except MRIQCAPIError as exc:
                    error_row = {
                        "modality": modality,
                        "page": entry.page,
                        "reasons": list(entry.reasons),
                        "error": str(exc),
                    }
                    append_jsonl(page_error_path, [error_row])
                    error_rows.append(error_row)
                    continue

                raw_path = raw_modality_dir / f"page-{entry.page:06d}.json"
                write_text(raw_path, response.response_text)

                page_row = _page_summary(
                    modality,
                    entry.page,
                    list(entry.reasons),
                    response.payload,
                    len(response.response_text.encode("utf-8")),
                )
                item_batch = _item_manifest_rows(
                    modality,
                    entry.page,
                    list(entry.reasons),
                    response.payload,
                )
                append_jsonl(page_manifest_path, [page_row])
                append_jsonl(item_manifest_path, item_batch)
                page_rows.append(page_row)
                item_rows.extend(item_batch)

            per_modality_summaries[modality] = _modality_summary(
                modality,
                frontier,
                page_rows,
                item_rows,
                error_rows,
            )
            total_raw_bytes += per_modality_summaries[modality]["raw_bytes"]
            total_items += per_modality_summaries[modality]["item_count"]

    write_json(
        layout.summary_path,
        {
            "run_id": run_id,
            "modalities": modalities,
            "total_raw_bytes": total_raw_bytes,
            "total_item_count": total_items,
            "modalities_summary": per_modality_summaries,
        },
    )
    return layout
