from mriqc_aggregator.planning import (
    FrontierEstimate,
    ProbeResult,
    desired_pages_per_modality,
    evenly_spaced_pages,
    plan_pages,
)


def test_evenly_spaced_pages_includes_bounds() -> None:
    assert evenly_spaced_pages(1, 100, 5) == [1, 26, 51, 75, 100]


def test_plan_pages_keeps_probe_and_tail_pages() -> None:
    frontier = FrontierEstimate(
        modality="T1w",
        lower_bound_page=64,
        successful_probes=[
            ProbeResult(
                page=1,
                item_count=50,
                first_created=None,
                last_created=None,
                elapsed_seconds=0.1,
                had_next=True,
            ),
            ProbeResult(
                page=2,
                item_count=50,
                first_created=None,
                last_created=None,
                elapsed_seconds=0.1,
                had_next=True,
            ),
            ProbeResult(
                page=64,
                item_count=50,
                first_created=None,
                last_created=None,
                elapsed_seconds=0.1,
                had_next=True,
            ),
        ],
        failed_probe_page=128,
        failed_probe_reason="slow",
    )

    pages = plan_pages(frontier, desired_count=6)
    by_page = {entry.page: entry for entry in pages}

    assert 1 in by_page
    assert 2 in by_page
    assert 64 in by_page
    assert "probe" in by_page[64].reasons
    assert "tail" in by_page[64].reasons


def test_explicit_page_requests_are_not_silently_capped_by_default() -> None:
    desired = desired_pages_per_modality(
        modalities=("T1w", "T2w", "bold"),
        page_bytes_by_modality={"T1w": 100, "T2w": 100, "bold": 100},
        pages_per_modality=1536,
        target_total_gb=None,
        max_pages_per_modality=None,
    )

    assert desired == {"T1w": 1536, "T2w": 1536, "bold": 1536}


def test_budgeted_page_requests_still_use_default_safety_cap() -> None:
    desired = desired_pages_per_modality(
        modalities=("T1w", "T2w", "bold"),
        page_bytes_by_modality={"T1w": 1, "T2w": 1, "bold": 1},
        pages_per_modality=None,
        target_total_gb=1.0,
        max_pages_per_modality=None,
    )

    assert desired == {"T1w": 128, "T2w": 128, "bold": 128}
