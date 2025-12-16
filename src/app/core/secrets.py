"""Secrets management helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml


@dataclass(slots=True)
class DeviceCredentials:
    """Credentials for a device."""

    username: str
    password: str


@dataclass(slots=True)
class Secrets:
    """Container for all secrets used by the app."""

    devices: Mapping[str, DeviceCredentials]


def load_secrets(path: Path) -> Secrets:
    """Load secrets from a YAML file.

    This is a thin placeholder to document the expected structure while
    keeping implementation minimal for the project skeleton.
    """

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    devices: dict[str, DeviceCredentials] = {}
    for name, creds in (data.get("devices") or {}).items():
        devices[name] = DeviceCredentials(
            username=str(creds.get("username", "")),
            password=str(creds.get("password", "")),
        )

    return Secrets(devices=devices)
