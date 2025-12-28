"""Backup helpers for Cisco devices."""

from __future__ import annotations

import logging
from pathlib import Path

from app.cisco.client import CiscoClient
from app.core.storage import write_backup


def backup_device(
    client: CiscoClient, output_path: Path, logger: logging.Logger | None = None, log_extra: dict | None = None
) -> Path:
    """Perform a backup for a Cisco device and save it to disk."""

    log_extra = log_extra or {}
    if logger:
        logger.debug("executing command='show running-config'", extra=log_extra)
    content = client.fetch_running_config()
    if logger:
        logger.debug("export received bytes=%d", len(content.encode("utf-8")), extra=log_extra)
        logger.debug("saving backup to %s", output_path, extra=log_extra)
    return write_backup(output_path, content)
