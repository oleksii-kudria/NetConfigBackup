"""Backup helpers for MikroTik devices."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.storage import write_backup
from app.mikrotik.client import MikroTikClient


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
