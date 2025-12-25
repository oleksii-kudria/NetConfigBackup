"""Data models for device inventory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


DeviceVendor = Literal["cisco", "mikrotik"]
DeviceBackupType = Literal["running-config", "export"]


@dataclass(slots=True)
class DeviceAuth:
    """Authentication reference for a device."""

    secret_ref: str


@dataclass(slots=True)
class DeviceBackup:
    """Backup strategy for a device."""

    type: DeviceBackupType


@dataclass(slots=True)
class Device:
    """Representation of a network device."""

    name: str
    vendor: DeviceVendor
    model: str
    host: str
    username: str
    auth: DeviceAuth
    backup: DeviceBackup
    port: int = 22
    backup_path: Path | None = None
