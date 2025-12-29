"""Secrets management helpers.

Secrets are loaded from ``config/secrets.yml`` when present and can be
overridden via environment variables. Environment variables take priority,
and missing secrets trigger a fail-fast error for the affected device.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

logger = logging.getLogger(__name__)

ENV_PREFIX = "NETCONFIGBACKUP_SECRET_"
DEFAULT_SECRETS_PATH = Path("config/secrets.yml")


class SecretsConfigError(ValueError):
    """Raised when the secrets file is missing required structure."""


class SecretNotFoundError(KeyError):
    """Raised when a password cannot be resolved for ``secret_ref``.

    This exception is used to stop processing for the current device when
    credentials are missing. Callers should handle it as a fail-fast signal.
    """


@dataclass(slots=True)
class SecretEntry:
    """Credentials required to connect to a device."""

    password: str
    enable_password: str | None = None


@dataclass(slots=True)
class Secrets:
    """Container for device secrets."""

    entries: Mapping[str, SecretEntry]
    source_path: Path
    missing_source: bool = False

    def get(self, secret_ref: str) -> SecretEntry | None:
        """Return the full secret entry if present."""

        return self.entries.get(secret_ref)


def _normalize_secret_ref(secret_ref: str) -> str:
    """Convert secret references to ``UPPER_SNAKE_CASE`` for env lookup."""

    normalized = re.sub(r"[^A-Z0-9]+", "_", secret_ref.upper())
    return normalized.strip("_")


def _load_file_secrets(path: Path) -> Secrets:
    """Load secrets from a YAML file if it exists.

    The expected structure matches ``config/secrets.yml.example``.
    """

    try:
        with path.open("r", encoding="utf-8") as handle:
            raw_data = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:  # pragma: no cover - defensive
        raise SecretsConfigError(f"Unable to read secrets file: {path}") from exc

    if not isinstance(raw_data, Mapping):
        raise SecretsConfigError("Top-level secrets.yml structure must be a mapping.")

    raw_secrets = raw_data.get("secrets")
    if raw_secrets is None:
        raise SecretsConfigError("Field 'secrets' is required in secrets.yml.")
    if not isinstance(raw_secrets, Mapping):
        raise SecretsConfigError("Field 'secrets' must be a mapping of secret refs.")

    entries: dict[str, SecretEntry] = {}
    for ref, entry in raw_secrets.items():
        if not isinstance(entry, Mapping):
            raise SecretsConfigError(f"Secret '{ref}' must be a mapping.")

        password = entry.get("password")
        if password is None:
            raise SecretsConfigError(f"Secret '{ref}' is missing required field 'password'.")
        if not isinstance(password, str):
            raise SecretsConfigError(f"Secret '{ref}' field 'password' must be a string.")

        enable_password = entry.get("enable_password")
        if enable_password is not None and not isinstance(enable_password, str):
            raise SecretsConfigError(
                f"Secret '{ref}' field 'enable_password' must be a string when provided."
            )

        entries[str(ref)] = SecretEntry(password=password, enable_password=enable_password)

    return Secrets(entries=entries, source_path=path)


def _env_password(secret_ref: str) -> str | None:
    """Return an env-sourced password for the given secret ref if set."""

    env_key = f"{ENV_PREFIX}{_normalize_secret_ref(secret_ref)}"
    value = os.getenv(env_key)
    if value is not None:
        return value
    return None


def load_secrets(path: Path = DEFAULT_SECRETS_PATH, logger: logging.Logger | None = None) -> Secrets:
    """Load secrets from the provided path."""

    logger = logger or logging.getLogger(__name__)
    if not path.exists():
        logger.error("Secrets file not found at %s", path, extra={"device": "-"})
        return Secrets(entries={}, source_path=path, missing_source=True)

    secrets = _load_file_secrets(path)
    logger.debug("Secrets file loaded path=%s entries=%d", path, len(secrets.entries))
    return secrets


def resolve_device_secrets(secret_ref: str, secrets: Secrets | None = None) -> SecretEntry:
    """Resolve credentials for a device's secret reference.

    Resolution order:
    1. Environment variable ``NETCONFIGBACKUP_SECRET_<SECRET_REF>`` (password only)
    2. ``config/secrets.yml`` (if present)
    """

    secrets = secrets or load_secrets()

    env_value = _env_password(secret_ref)
    if env_value is not None:
        entry = secrets.get(secret_ref)
        return SecretEntry(password=env_value, enable_password=entry.enable_password if entry else None)

    entry = secrets.get(secret_ref)
    if entry is not None:
        return entry

    raise SecretNotFoundError(f"Secret '{secret_ref}' not found.")


def get_password(secret_ref: str, secrets: Secrets | None = None) -> str:
    """Compatibility wrapper returning only the password value."""

    entry = resolve_device_secrets(secret_ref, secrets)
    return entry.password
