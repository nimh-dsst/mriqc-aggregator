from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import httpx


MAX_RESULTS_CAP = 50
DEFAULT_BASE_URL = "https://mriqc.nimh.nih.gov/api/v1"
DEFAULT_MANIFEST_PROJECTION = {
    "_id": 1,
    "_created": 1,
    "bids_meta": 1,
    "provenance.md5sum": 1,
    "provenance.version": 1,
}


class MRIQCAPIError(RuntimeError):
    """Raised when the MRIQC API responds unexpectedly."""


@dataclass(frozen=True)
class APIPageResponse:
    modality: str
    page: int
    response_text: str
    payload: dict[str, Any]
    elapsed_seconds: float


class MRIQCWebAPIClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 30.0,
        user_agent: str = "mriqc-aggregator/0.1.0",
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout_seconds,
            headers={"User-Agent": user_agent},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "MRIQCWebAPIClient":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()

    def fetch_page(
        self,
        modality: str,
        page: int,
        *,
        max_results: int = MAX_RESULTS_CAP,
        projection: dict[str, Any] | None = None,
    ) -> APIPageResponse:
        params: dict[str, Any] = {
            "page": page,
            "max_results": min(max_results, MAX_RESULTS_CAP),
        }
        if projection:
            params["projection"] = json.dumps(
                projection,
                sort_keys=True,
                separators=(",", ":"),
            )

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            started = time.perf_counter()
            try:
                response = self._client.get(f"/{modality}", params=params)
                response.raise_for_status()
                payload = response.json()
                elapsed = time.perf_counter() - started
                return APIPageResponse(
                    modality=modality,
                    page=page,
                    response_text=response.text,
                    payload=payload,
                    elapsed_seconds=elapsed,
                )
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                time.sleep(0.5 * attempt)

        raise MRIQCAPIError(
            f"Failed to fetch {modality} page {page}: {last_error}"
        ) from last_error


def page_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("_items", [])
    if not isinstance(items, list):
        raise MRIQCAPIError("API payload did not contain a list of _items")
    return items
