"""Configuration helpers for NetConfigBackup."""

from __future__ import annotations

from dataclasses import dataclass
import logging
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


def _validate_platform(value: Any, context: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DevicesConfigError(f"{context}: platform must be a string when provided.")

    allowed = {"ios", "iosxe", "nxos"}
    if value not in allowed:
        raise DevicesConfigError(f"{context}: invalid platform '{value}'. Allowed: ios, iosxe, nxos.")
    return value


def _parse_cisco_device(raw_device: Mapping[str, Any], context: str) -> Device:
    name = _require_string(raw_device, "name", context)
    ip = _require_string(raw_device, "ip", f"{context} '{name}'")
    username = _require_string(raw_device, "username", f"{context} '{name}'")
    secret_ref = _require_string(raw_device, "secrets_ref", f"{context} '{name}'")
    port = _validate_port(raw_device.get("ssh_port"), f"{context} '{name}' ssh_port")
    platform = _validate_platform(raw_device.get("platform"), f"{context} '{name}'")
    model = raw_device.get("model")
    if model is not None and not isinstance(model, str):
        raise DevicesConfigError(f"{context} '{name}': model must be a string when provided.")

    for forbidden in ("password", "enable_password"):
        if forbidden in raw_device:
            raise DevicesConfigError(
                f"{context} '{name}': field '{forbidden}' is not allowed in devices.yml. "
                "Store secrets in config/secrets.yml."
            )

    return Device(
        name=name,
        vendor="cisco",
        model=model,
        host=ip,
        port=port,
        username=username,
        platform=platform,
        auth=DeviceAuth(secret_ref=secret_ref),
        backup=DeviceBackup(type="running-config"),
    )


def _parse_mikrotik_device(raw_device: Mapping[str, Any], context: str) -> Device:
    name = _require_string(raw_device, "name", context)
    model = _require_string(raw_device, "model", context)
    host = _require_string(raw_device, "host", f"{context} '{name}'")
    username = _require_string(raw_device, "username", f"{context} '{name}'")
    port = _validate_port(raw_device.get("port"), f"{context} '{name}'")

    auth_raw = raw_device.get("auth")
    if not isinstance(auth_raw, Mapping):
        raise DevicesConfigError(f"{context} '{name}': auth must be a mapping.")
    secret_ref = _require_string(auth_raw, "secret_ref", f"{context} '{name}' auth")
    if "password" in raw_device or "password" in auth_raw:
        raise DevicesConfigError(
            f"{context} '{name}': password must not be stored in devices.yml. Use config/secrets.yml."
        )

    backup_raw = raw_device.get("backup")
    if not isinstance(backup_raw, Mapping):
        raise DevicesConfigError(f"{context} '{name}': backup must be a mapping.")
    backup_type = _require_string(backup_raw, "type", f"{context} '{name}' backup")
    backup_type = _validate_backup_type("mikrotik", backup_type, f"{context} '{name}'")

    return Device(
        name=name,
        vendor="mikrotik",
        model=model,
        host=host,
        port=port,
        username=username,
        auth=DeviceAuth(secret_ref=secret_ref),
        backup=DeviceBackup(type=backup_type),
    )


def load_devices(path: Path, logger: logging.Logger | None = None) -> list[Device]:
    """Load and validate devices.yml according to the project schema."""

    logger = logger or logging.getLogger(__name__)

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
    seen_names: set[str] = set()

    for index, raw_device in enumerate(raw_devices, start=1):
        context = f"device #{index}"
        if not isinstance(raw_device, dict):
            logger.error("%s: each device must be a mapping.", context, extra={"device": "-"})
            continue

        provisional_name = raw_device.get("name") or "-"
        log_extra = {"device": provisional_name}
        try:
            vendor_value = _validate_vendor(_require_string(raw_device, "vendor", context), context)
            if vendor_value == "cisco":
                device = _parse_cisco_device(raw_device, context)
            else:
                device = _parse_mikrotik_device(raw_device, context)
        except DevicesConfigError as exc:
            logger.error("%s", exc, extra=log_extra)
            continue

        if device.name in seen_names:
            logger.error(
                "%s '%s': device name must be unique. Duplicate ignored.",
                context,
                device.name,
                extra=log_extra,
            )
            continue

        seen_names.add(device.name)
        devices.append(device)

        if device.vendor == "cisco":
            logger.info(
                "device=%s vendor=cisco loaded from devices.yml", device.name, extra={"device": device.name}
            )
            logger.debug(
                "device=%s ip=%s port=%s username=%s platform=%s",
                device.name,
                device.host,
                device.port,
                device.username,
                device.platform or "-",
                extra={"device": device.name},
            )

    return devices
