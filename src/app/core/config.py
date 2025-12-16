"""Configuration helpers for NetConfigBackup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ConfigPaths:
    """Paths used by the application."""

    devices: Path
    secrets: Path
    backups: Path


DEFAULT_CONFIG = ConfigPaths(
    devices=Path("config/devices.yml"),
    secrets=Path("config/secrets.yml"),
    backups=Path("backups"),
)
