"""Data models for device inventory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


DeviceVendor = Literal["cisco", "mikrotik"]


@dataclass(slots=True)
class Device:
    """Representation of a network device."""

    name: str
    host: str
    vendor: DeviceVendor
    port: int = 22
    backup_path: Path | None = None
