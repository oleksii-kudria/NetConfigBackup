"""Backup helpers for Cisco devices."""

from __future__ import annotations

from pathlib import Path

from app.cisco.client import CiscoClient
from app.core.storage import write_backup


def backup_device(client: CiscoClient, output_path: Path) -> Path:
    """Perform a backup for a Cisco device and save it to disk."""

    content = client.fetch_running_config()
    return write_backup(output_path, content)
