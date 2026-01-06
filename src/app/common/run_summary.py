"""Helpers for building and persisting machine-readable run summaries."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class TaskResultData:
    """Summary of a single task execution."""

    performed: bool
    saved_path: str | None = None
    size_bytes: int | None = None
    config_changed: bool | None = None
    lines_added: int | None = None
    lines_removed: int | None = None
    diff_path: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "performed": self.performed,
            "saved_path": self.saved_path,
            "size_bytes": self.size_bytes,
            "config_changed": self.config_changed,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "diff_path": self.diff_path,
            "error": self.error,
        }


@dataclass(slots=True)
class DeviceResultData:
    """Summary of a device run."""

    name: str
    vendor: str
    status: str
    tasks: dict[str, TaskResultData] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "vendor": self.vendor,
            "status": self.status,
            "error": self.error,
            "tasks": {name: task.to_dict() for name, task in self.tasks.items()},
        }


class RunSummaryBuilder:
    """Accumulate per-run data and store it as JSON."""

    def __init__(
        self,
        *,
        run_id: str,
        timestamp: str,
        dry_run: bool,
        selected_features: Iterable[str] | None = None,
    ) -> None:
        self.run_id = run_id
        self.timestamp = timestamp
        self.dry_run = dry_run
        self.selected_features = list(selected_features or [])
        self.devices_total = 0
        self.devices_processed = 0
        self.devices_success = 0
        self.devices_failed = 0
        self.backups_created = 0
        self.configs_changed = 0
        self._devices: list[DeviceResultData] = []

    def set_devices_total(self, total: int) -> None:
        self.devices_total = max(0, total)

    def set_selected_features(self, features: Iterable[str]) -> None:
        self.selected_features = list(features)

    def add_device(self, device: DeviceResultData) -> None:
        self._devices.append(device)

        if device.status != "skipped":
            self.devices_processed += 1
            if device.status == "success":
                self.devices_success += 1
            elif device.status == "failed":
                self.devices_failed += 1

        for task in device.tasks.values():
            if task.performed and task.saved_path:
                self.backups_created += 1
            if task.config_changed is True:
                self.configs_changed += 1

    def build(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "dry_run": self.dry_run,
            "selected_features": self.selected_features,
            "totals": {
                "devices_total": self.devices_total,
                "devices_processed": self.devices_processed,
                "devices_success": self.devices_success,
                "devices_failed": self.devices_failed,
                "backups_created": self.backups_created,
                "configs_changed": self.configs_changed,
            },
            "devices": [device.to_dict() for device in self._devices],
        }

    def save(self, backup_dir: Path, logger) -> Path:
        summary_dir = backup_dir / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)

        target = summary_dir / f"run_{self.run_id}.json"
        target.write_text(json.dumps(self.build(), indent=2, ensure_ascii=False), encoding="utf-8")

        logger.info("run_summary_json_saved path=%s", target)
        return target
