from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Hashable
from threading import Lock
from time import monotonic
from typing import Generic, TypeVar

T = TypeVar("T")


class TimedCache(Generic[T]):
    def __init__(
        self,
        *,
        ttl_seconds: float,
        max_entries: int = 256,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[Hashable, tuple[float, T]] = OrderedDict()
        self._lock = Lock()

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def get_or_set(
        self,
        key: Hashable,
        factory: Callable[[], T],
    ) -> tuple[bool, T]:
        cached_value = self._get(key)
        if cached_value is not None:
            return True, cached_value

        value = factory()
        self._set(key, value)
        return False, value

    def _get(self, key: Hashable) -> T | None:
        now = self._clock()
        with self._lock:
            self._purge_expired(now)
            cached = self._entries.get(key)
            if cached is None:
                return None
            self._entries.move_to_end(key)
            return cached[1]

    def _set(self, key: Hashable, value: T) -> None:
        expires_at = self._clock() + self._ttl_seconds
        with self._lock:
            self._entries[key] = (expires_at, value)
            self._entries.move_to_end(key)
            self._purge_expired(self._clock())
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def _purge_expired(self, now: float) -> None:
        expired_keys = [
            key for key, (expires_at, _value) in self._entries.items() if expires_at <= now
        ]
        for key in expired_keys:
            self._entries.pop(key, None)
