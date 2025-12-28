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
