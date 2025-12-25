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
class Secrets:
    """Container for device passwords."""

    passwords: Mapping[str, str]

    def get(self, secret_ref: str) -> str | None:
        """Return the password for ``secret_ref`` if present."""

        return self.passwords.get(secret_ref)


def _normalize_secret_ref(secret_ref: str) -> str:
    """Convert secret references to ``UPPER_SNAKE_CASE`` for env lookup."""

    normalized = re.sub(r"[^A-Z0-9]+", "_", secret_ref.upper())
    return normalized.strip("_")


def _load_file_secrets(path: Path) -> Secrets:
    """Load secrets from a YAML file if it exists.

    The expected structure matches ``config/secrets.yml.example``.
    """

    if not path.exists():
        return Secrets(passwords={})

    try:
        with path.open("r", encoding="utf-8") as handle:
            raw_data = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:  # pragma: no cover - defensive
        raise SecretsConfigError(f"Unable to read secrets file: {path}") from exc

    if not isinstance(raw_data, Mapping):
        raise SecretsConfigError("Top-level secrets.yml structure must be a mapping.")

    raw_secrets = raw_data.get("secrets") or {}
    if not isinstance(raw_secrets, Mapping):
        raise SecretsConfigError("Field 'secrets' must be a mapping of secret refs.")

    passwords: dict[str, str] = {}
    for ref, entry in raw_secrets.items():
        if not isinstance(entry, Mapping):
            raise SecretsConfigError(f"Secret '{ref}' must be a mapping.")

        password = entry.get("password")
        if password is None:
            raise SecretsConfigError(f"Secret '{ref}' is missing required field 'password'.")
        if not isinstance(password, str):
            raise SecretsConfigError(f"Secret '{ref}' field 'password' must be a string.")

        passwords[str(ref)] = password

    return Secrets(passwords=passwords)


FILE_SECRETS = _load_file_secrets(DEFAULT_SECRETS_PATH)


def _env_password(secret_ref: str) -> str | None:
    """Return an env-sourced password for the given secret ref if set."""

    env_key = f"{ENV_PREFIX}{_normalize_secret_ref(secret_ref)}"
    value = os.getenv(env_key)
    if value is not None:
        return value
    return None


def get_password(secret_ref: str) -> str:
    """Resolve the password for a device's secret reference.

    Resolution order:
    1. Environment variable ``NETCONFIGBACKUP_SECRET_<SECRET_REF>``
    2. ``config/secrets.yml`` (if present)

    If the password cannot be found, the function logs an error (without the
    secret value) and raises :class:`SecretNotFoundError` to halt processing for
    the current device.
    """

    env_value = _env_password(secret_ref)
    if env_value is not None:
        return env_value

    password = FILE_SECRETS.get(secret_ref)
    if password is not None:
        return password

    logger.error("Missing secret for reference '%s'.", secret_ref)
    raise SecretNotFoundError(f"Secret '{secret_ref}' not found.")
