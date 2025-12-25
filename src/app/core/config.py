"""Configuration helpers for NetConfigBackup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from app.core.models import Device, DeviceAuth, DeviceBackup, DeviceVendor

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


class DevicesConfigError(ValueError):
    """Raised when devices.yml cannot be parsed or validated."""


def _require_string(mapping: Mapping[str, Any], field: str, context: str) -> str:
    value = mapping.get(field)
    if value is None or value == "":
        raise DevicesConfigError(f"{context}: missing required field '{field}'.")
    if not isinstance(value, str):
        raise DevicesConfigError(f"{context}: field '{field}' must be a string.")
    return value


def _validate_vendor(value: str, context: str) -> DeviceVendor:
    if value not in ("cisco", "mikrotik"):
        raise DevicesConfigError(
            f"{context}: invalid vendor '{value}'. Allowed values: cisco, mikrotik."
        )
    return value  # type: ignore[return-value]


def _validate_port(value: Any, context: str) -> int:
    if value is None:
        return 22
    if isinstance(value, bool) or not isinstance(value, int):
        raise DevicesConfigError(f"{context}: port must be an integer.")
    if value <= 0 or value > 65535:
        raise DevicesConfigError(f"{context}: port must be between 1 and 65535.")
    return value


def _validate_backup_type(vendor: DeviceVendor, backup_type: str, context: str) -> str:
    if vendor == "cisco" and backup_type != "running-config":
        raise DevicesConfigError(
            f"{context}: Cisco devices must use backup type 'running-config'."
        )
    if vendor == "mikrotik" and backup_type != "export":
        raise DevicesConfigError(
            f"{context}: MikroTik devices must use backup type 'export'."
        )
    return backup_type


def load_devices(path: Path) -> list[Device]:
    """Load and validate devices.yml according to the project schema."""

    if not path.exists():
        raise FileNotFoundError(f"Devices inventory not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        raw_data = yaml.safe_load(handle) or {}

    if not isinstance(raw_data, dict):
        raise DevicesConfigError("Top-level devices.yml structure must be a mapping.")

    raw_devices = raw_data.get("devices")
    if raw_devices is None:
        raise DevicesConfigError("devices.yml must contain a 'devices' list.")
    if not isinstance(raw_devices, list):
        raise DevicesConfigError("The 'devices' field must be a list of device entries.")

    devices: list[Device] = []
    for index, raw_device in enumerate(raw_devices, start=1):
        context = f"device #{index}"
        if not isinstance(raw_device, dict):
            raise DevicesConfigError(f"{context}: each device must be a mapping.")

        name = _require_string(raw_device, "name", context)
        vendor_value = _validate_vendor(_require_string(raw_device, "vendor", context), context)
        model = _require_string(raw_device, "model", context)
        host = _require_string(raw_device, "host", context)
        username = _require_string(raw_device, "username", context)
        port = _validate_port(raw_device.get("port"), f"{context} '{name}'")

        auth_raw = raw_device.get("auth")
        if not isinstance(auth_raw, dict):
            raise DevicesConfigError(f"{context} '{name}': auth must be a mapping.")
        secret_ref = _require_string(auth_raw, "secret_ref", f"{context} '{name}' auth")

        backup_raw = raw_device.get("backup")
        if not isinstance(backup_raw, dict):
            raise DevicesConfigError(f"{context} '{name}': backup must be a mapping.")
        backup_type = _require_string(
            backup_raw, "type", f"{context} '{name}' backup"
        )
        backup_type = _validate_backup_type(vendor_value, backup_type, f"{context} '{name}'")

        devices.append(
            Device(
                name=name,
                vendor=vendor_value,
                model=model,
                host=host,
                port=port,
                username=username,
                auth=DeviceAuth(secret_ref=secret_ref),
                backup=DeviceBackup(type=backup_type),
            )
        )

    return devices
