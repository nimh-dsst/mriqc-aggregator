from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Iterable

from .api import (
    DEFAULT_MANIFEST_PROJECTION,
    MRIQCAPIError,
    MRIQCWebAPIClient,
    page_items,
)


@dataclass(frozen=True)
class ProbeResult:
    page: int
    item_count: int
    first_created: str | None
    last_created: str | None
    elapsed_seconds: float
    had_next: bool


@dataclass(frozen=True)
class FrontierEstimate:
    modality: str
    lower_bound_page: int
    successful_probes: list[ProbeResult]
    failed_probe_page: int | None
    failed_probe_reason: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "modality": self.modality,
            "lower_bound_page": self.lower_bound_page,
            "successful_probes": [asdict(probe) for probe in self.successful_probes],
            "failed_probe_page": self.failed_probe_page,
            "failed_probe_reason": self.failed_probe_reason,
        }


@dataclass(frozen=True)
class PagePlanEntry:
    page: int
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {"page": self.page, "reasons": list(self.reasons)}


def discover_frontier(
    client: MRIQCWebAPIClient,
    modality: str,
    *,
    max_probe_rounds: int = 12,
    slow_probe_seconds: float = 6.0,
) -> FrontierEstimate:
    successful: list[ProbeResult] = []
    failed_probe_page: int | None = None
    failed_reason: str | None = None
    page = 1

    for _ in range(max_probe_rounds):
        try:
            response = client.fetch_page(
                modality,
                page,
                projection=DEFAULT_MANIFEST_PROJECTION,
            )
        except MRIQCAPIError as exc:
            failed_probe_page = page
            failed_reason = str(exc)
            break

        items = page_items(response.payload)
        if not items:
            failed_probe_page = page
            failed_reason = "empty page"
            break

        successful.append(
            ProbeResult(
                page=page,
                item_count=len(items),
                first_created=items[0].get("_created"),
                last_created=items[-1].get("_created"),
                elapsed_seconds=response.elapsed_seconds,
                had_next="next" in response.payload.get("_links", {}),
            )
        )

        if "next" not in response.payload.get("_links", {}):
            break
        if response.elapsed_seconds >= slow_probe_seconds and page > 1:
            break

        page *= 2

    lower_bound = successful[-1].page if successful else 1
    return FrontierEstimate(
        modality=modality,
        lower_bound_page=lower_bound,
        successful_probes=successful,
        failed_probe_page=failed_probe_page,
        failed_probe_reason=failed_reason,
    )


def estimate_average_page_bytes(
    client: MRIQCWebAPIClient,
    modality: str,
    frontier: FrontierEstimate,
) -> int:
    calibration_pages = sorted(
        {
            1,
            max(1, frontier.lower_bound_page // 2),
            frontier.lower_bound_page,
        }
    )
    sizes: list[int] = []
    for page in calibration_pages:
        response = client.fetch_page(modality, page)
        sizes.append(len(response.response_text.encode("utf-8")))
    return int(sum(sizes) / len(sizes))


def desired_pages_per_modality(
    *,
    modalities: Iterable[str],
    page_bytes_by_modality: dict[str, int],
    pages_per_modality: int | None,
    target_total_gb: float | None,
    max_pages_per_modality: int,
) -> dict[str, int]:
    modality_list = list(modalities)
    if pages_per_modality is not None:
        return {
            modality: min(pages_per_modality, max_pages_per_modality)
            for modality in modality_list
        }

    if target_total_gb is None:
        target_total_gb = 0.25

    total_bytes = int(target_total_gb * (1024**3))
    budget_per_modality = max(total_bytes // max(len(modality_list), 1), 1)
    desired: dict[str, int] = {}
    for modality in modality_list:
        avg_page_bytes = max(page_bytes_by_modality[modality], 1)
        desired[modality] = max(
            1,
            min(budget_per_modality // avg_page_bytes, max_pages_per_modality),
        )
    return desired


def evenly_spaced_pages(start: int, stop: int, count: int) -> list[int]:
    if count <= 0 or stop < start:
        return []
    if count == 1:
        return [start]
    if stop == start:
        return [start]

    span = stop - start
    return sorted(
        {start + round((span * index) / (count - 1)) for index in range(count)}
    )


def plan_pages(
    frontier: FrontierEstimate,
    *,
    desired_count: int,
    extra_early_pages: int = 5,
    extra_tail_pages: int = 3,
) -> list[PagePlanEntry]:
    reason_map: dict[int, set[str]] = defaultdict(set)

    for page in range(1, min(extra_early_pages, frontier.lower_bound_page) + 1):
        reason_map[page].add("early")

    for probe in frontier.successful_probes:
        reason_map[probe.page].add("probe")

    tail_start = max(1, frontier.lower_bound_page - extra_tail_pages + 1)
    for page in range(tail_start, frontier.lower_bound_page + 1):
        reason_map[page].add("tail")

    for page in evenly_spaced_pages(1, frontier.lower_bound_page, desired_count):
        reason_map[page].add("linear")

    return [
        PagePlanEntry(page=page, reasons=tuple(sorted(reasons)))
        for page, reasons in sorted(reason_map.items())
    ]
