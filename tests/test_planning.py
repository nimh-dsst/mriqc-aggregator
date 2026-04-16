from mriqc_aggregator.planning import (
    FrontierEstimate,
    ProbeResult,
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
