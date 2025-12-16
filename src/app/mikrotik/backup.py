"""Backup helpers for MikroTik devices."""

from __future__ import annotations

from pathlib import Path

from app.core.storage import write_backup
from app.mikrotik.client import MikroTikClient


def backup_device(client: MikroTikClient, output_path: Path) -> Path:
    """Perform a backup for a MikroTik device and save it to disk."""

    content = client.fetch_running_config()
    return write_backup(output_path, content)
