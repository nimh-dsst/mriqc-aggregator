from __future__ import annotations

from mriqc_aggregator.cache import TimedCache


def test_timed_cache_reuses_entries_until_expiry() -> None:
    now = 100.0

    def clock() -> float:
        return now

    cache: TimedCache[str] = TimedCache(ttl_seconds=5, clock=clock)
    calls = {"count": 0}

    def build_value() -> str:
        calls["count"] += 1
        return f"value-{calls['count']}"

    cache_hit, value = cache.get_or_set(("metrics", "bold"), build_value)
    assert cache_hit is False
    assert value == "value-1"

    cache_hit, value = cache.get_or_set(("metrics", "bold"), build_value)
    assert cache_hit is True
    assert value == "value-1"
    assert calls["count"] == 1

    now += 6

    cache_hit, value = cache.get_or_set(("metrics", "bold"), build_value)
    assert cache_hit is False
    assert value == "value-2"
    assert calls["count"] == 2
