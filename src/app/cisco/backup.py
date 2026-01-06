"""Backup helpers for Cisco devices."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from app.core.logging import sanitize_log_extra
from app.cisco.client import CiscoClient
from app.core.storage import ensure_directory


def backup_device(
    client: CiscoClient,
    backup_dir: Path,
    logger: logging.Logger | None = None,
    log_extra: dict | None = None,
) -> Path:
    """Perform a backup for a Cisco device and save it to disk."""

    resolved_logger = logger or logging.getLogger(__name__)
    sanitized_extra = sanitize_log_extra(log_extra)
    log_extra = {"device": client.name, **sanitized_extra}

    resolved_logger.info("device=%s fetching running-config", client.name, extra=log_extra)
    try:
        content = client.fetch_running_config(resolved_logger, log_extra)
    except Exception:
        resolved_logger.error("device=%s running-config retrieval failed", client.name, extra=log_extra)
        raise

    if not _is_valid_running_config(content):
        resolved_logger.error("device=%s running-config sanity-check failed", client.name, extra=log_extra)
        raise ValueError("Invalid running-config output.")

    resolved_logger.info("device=%s running-config retrieved", client.name, extra=log_extra)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    target_dir = ensure_directory(backup_dir / "cisco" / client.name)
    backup_path = target_dir / f"{timestamp}_running-config.txt"

    if backup_path.exists():
        resolved_logger.error("device=%s running-config retrieval failed", client.name, extra=log_extra)
        raise FileExistsError(f"Backup file already exists: {backup_path}")

    backup_path.write_text(content, encoding="utf-8")
    size = backup_path.stat().st_size if backup_path.exists() else 0

    if size <= 0:
        resolved_logger.error("device=%s running-config retrieval failed", client.name, extra=log_extra)
        raise ValueError("Backup file is empty after write.")

    resolved_logger.info(
        "device=%s running-config saved path=%s size=%d", client.name, backup_path, size, extra=log_extra
    )
    return backup_path


def _is_valid_running_config(content: str) -> bool:
    if not content or not content.strip():
        return False

    lowered = content.lower()
    return any(marker in lowered for marker in ("version", "hostname", "!"))
