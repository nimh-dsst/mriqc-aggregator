from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class RunLayout:
    root: Path
    frontier_dir: Path
    plans_dir: Path
    manifest_dir: Path
    raw_dir: Path
    summary_path: Path
    config_path: Path


def make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_run_layout(output_root: Path, run_id: str) -> RunLayout:
    root = output_root / "runs" / run_id
    frontier_dir = root / "frontier"
    plans_dir = root / "plans"
    manifest_dir = root / "manifest"
    raw_dir = root / "raw"
    for path in (frontier_dir, plans_dir, manifest_dir, raw_dir):
        path.mkdir(parents=True, exist_ok=True)
    return RunLayout(
        root=root,
        frontier_dir=frontier_dir,
        plans_dir=plans_dir,
        manifest_dir=manifest_dir,
        raw_dir=raw_dir,
        summary_path=root / "summary.json",
        config_path=root / "config.json",
    )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
