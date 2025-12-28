"""Backup helpers for MikroTik devices."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.storage import write_backup
from app.mikrotik.client import MikroTikClient
from app.mikrotik.diff import DiffResult, evaluate_config_change


def fetch_export(device: Any, password: str, logger: logging.Logger) -> str:
    """Fetch export configuration text for a MikroTik device."""

    log_extra = {"device": getattr(device, "name", "-")}
    client = MikroTikClient(
        host=device.host, username=device.username, password=password, port=device.port
    )
    return client.fetch_export(logger, log_extra)


def backup_device(client: MikroTikClient, output_path: Path) -> Path:
    """Perform a backup for a MikroTik device and save it to disk."""

    content = client.fetch_export(logging.getLogger(__name__), {"device": "-"})
    return write_backup(output_path, content)


def perform_system_backup(
    device: Any, password: str, timestamp: str, backup_dir: Path, logger: logging.Logger
) -> Path:
    """Create and download a binary system backup for a MikroTik device."""

    log_extra = {"device": getattr(device, "name", "-")}
    client = MikroTikClient(
        host=device.host, username=device.username, password=password, port=device.port
    )
    device_name = getattr(device, "name", "")
    if " " in device_name:
        raise ValueError("Device name cannot contain spaces for system backup filename")

    backup_name = f"{device_name}_{timestamp}"
    backup_filename = f"{backup_name}.backup"
    destination = backup_dir / "mikrotik" / device_name / backup_filename
    log_extra = {**log_extra, "filename": backup_filename}
    logger.info("creating system-backup device=%s filename=%s", device_name, backup_filename, extra=log_extra)
    return client.fetch_system_backup(backup_name, destination, logger, log_extra)


def log_mikrotik_diff(current_export: Path, logger: logging.Logger, log_extra: dict[str, str]) -> None:
    """Log MikroTik diff status for the latest export and persist diff when needed."""

    result: DiffResult = evaluate_config_change(current_export)

    if result.first_backup:
        logger.info("first_backup=true", extra=log_extra)
        return

    logger.info("config_changed=%s", result.config_changed, extra=log_extra)

    if not result.config_changed:
        return

    logger.debug("diff added=%d removed=%d", result.added, result.removed, extra=log_extra)

    diff_path = current_export.with_suffix(".diff")
    diff_path.write_text(result.diff_text or "", encoding="utf-8")
    logger.info("diff_saved=%s", diff_path, extra=log_extra)
