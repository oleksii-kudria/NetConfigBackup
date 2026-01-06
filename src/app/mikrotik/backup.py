"""Backup helpers for MikroTik devices."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.logging import sanitize_log_extra
from app.core.storage import write_backup
from app.mikrotik.client import MikroTikClient
from app.common.diff import DiffOutcome, evaluate_change
from app.core.normalize import normalize_mikrotik_export


def fetch_export(device: Any, password: str, logger: logging.Logger) -> str:
    """Fetch export configuration text for a MikroTik device."""

    log_extra = sanitize_log_extra({"device": getattr(device, "name", "-")})
    client = MikroTikClient(
        host=device.host, username=device.username, password=password, port=device.port
    )
    return client.fetch_export(logger, log_extra)


def backup_device(client: MikroTikClient, output_path: Path) -> Path:
    """Perform a backup for a MikroTik device and save it to disk."""

    content = client.fetch_export(logging.getLogger(__name__), sanitize_log_extra({"device": "-"}))
    return write_backup(output_path, content)


def perform_system_backup(
    device: Any, password: str, timestamp: str, backup_dir: Path, logger: logging.Logger
) -> Path:
    """Create and download a binary system backup for a MikroTik device."""

    log_extra = sanitize_log_extra({"device": getattr(device, "name", "-")})
    client = MikroTikClient(
        host=device.host, username=device.username, password=password, port=device.port
    )
    device_name = getattr(device, "name", "")
    if " " in device_name:
        raise ValueError("Device name cannot contain spaces for system backup filename")

    backup_dir_device = backup_dir / "mikrotik" / device_name
    remote_filename = f"{device_name}.backup"
    destination = backup_dir_device / remote_filename
    log_extra = sanitize_log_extra({**log_extra, "remote_file": remote_filename})
    logger.info("creating system-backup device=%s remote_file=%s", device_name, remote_filename, extra=log_extra)

    downloaded_size = client.fetch_system_backup(device_name, destination, logger, log_extra)

    if not destination.exists():
        raise FileNotFoundError(f"Downloaded system-backup not found: {destination}")

    local_size = destination.stat().st_size
    if local_size <= 0:
        raise ValueError(f"Downloaded system-backup has zero size: {destination}")

    timestamped_name = f"{device_name}_{timestamp}.backup"
    timestamped_path = backup_dir_device / timestamped_name
    destination.rename(timestamped_path)

    log_extra = sanitize_log_extra({**log_extra, "local_file": timestamped_name})
    logger.info(
        "system-backup downloaded local_file=%s size=%d",
        timestamped_name,
        downloaded_size,
        extra=log_extra,
    )
    logger.info("remote system-backup file kept on device file=%s", remote_filename, extra=log_extra)
    return timestamped_path


def log_mikrotik_diff(current_export: Path, logger: logging.Logger, log_extra: dict[str, str]) -> None:
    """Log MikroTik diff status for the latest export and persist diff when needed."""

    log_extra = sanitize_log_extra(log_extra)
    result: DiffOutcome = evaluate_change(current_export, "*_export.rsc", normalize_mikrotik_export)

    logger.info(
        "device=%s diff baseline=%s current=%s",
        log_extra.get("device", "-"),
        result.previous_path.name if result.previous_path else "-",
        current_export.name,
        extra=log_extra,
    )

    logger.debug("device=%s normalized_hash=%s", log_extra.get("device", "-"), result.normalized_hash, extra=log_extra)

    changed_value = "null" if result.config_changed is None else str(result.config_changed).lower()
    logger.info("device=%s config_changed=%s", log_extra.get("device", "-"), changed_value, extra=log_extra)

    if not result.config_changed:
        return

    diff_path = current_export.with_suffix(".diff")
    diff_path.write_text(result.diff_text or "", encoding="utf-8")
    logger.info(
        "device=%s change_summary added=%d removed=%d diff_file=%s",
        log_extra.get("device", "-"),
        result.added,
        result.removed,
        diff_path,
        extra=log_extra,
    )
