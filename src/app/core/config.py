"""Configuration helpers for NetConfigBackup."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any, Mapping

import yaml

from app.core.models import Device, DeviceAuth, DeviceBackup, DeviceBackupType, DeviceVendor

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


def _validate_forbidden_keys(raw_device: Mapping[str, Any], context: str) -> None:
    forbidden_keys = {
        "host",
        "ssh_port",
        "secrets_ref",
        "auth",
        "backup",
        "platform",
        "password",
        "enable_password",
    }
    for key in forbidden_keys:
        if key in raw_device:
            raise DevicesConfigError(
                f"{context}: field '{key}' is not allowed in devices.yml. "
                "Use the unified schema and store secrets in config/secrets.yml."
            )


def _parse_device(raw_device: Mapping[str, Any], context: str) -> Device:
    _validate_forbidden_keys(raw_device, context)

    allowed_keys = {"name", "vendor", "model", "ip", "port", "username", "secret_ref"}
    unexpected_keys = set(raw_device) - allowed_keys
    if unexpected_keys:
        raise DevicesConfigError(
            f"{context}: unexpected field(s) {sorted(unexpected_keys)}. "
            "Allowed fields: name, vendor, model, ip, port, username, secret_ref."
        )

    name = _require_string(raw_device, "name", context)
    vendor = _validate_vendor(_require_string(raw_device, "vendor", context), context)
    ip = _require_string(raw_device, "ip", f"{context} '{name}'")
    username = _require_string(raw_device, "username", f"{context} '{name}'")
    secret_ref = _require_string(raw_device, "secret_ref", f"{context} '{name}'")
    port = _validate_port(raw_device.get("port"), f"{context} '{name}' port")
    model_raw = raw_device.get("model")
    if model_raw is not None and not isinstance(model_raw, str):
        raise DevicesConfigError(f"{context} '{name}': model must be a string when provided.")

    backup_type: DeviceBackupType = "running-config" if vendor == "cisco" else "export"

    return Device(
        name=name,
        vendor=vendor,
        model=model_raw,
        host=ip,
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
            device = _parse_device(raw_device, context)
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

        logger.info(
            "device=%s vendor=%s loaded from devices.yml", device.name, device.vendor, extra={"device": device.name}
        )
        logger.debug(
            "device=%s ip=%s port=%s username=%s secret_ref=%s model=%s",
            device.name,
            device.host,
            device.port,
            device.username,
            device.auth.secret_ref,
            device.model if device.model is not None and device.model != "" else "-",
            extra={"device": device.name},
        )

    return devices
