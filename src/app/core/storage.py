"""Storage helpers for writing backups to disk."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FALLBACK_BACKUP_DIR = PROJECT_ROOT / "backup"
DEFAULT_LOCAL_CONFIG = PROJECT_ROOT / "config" / "local.yml"


def _format_metadata(metadata: Mapping[str, Any]) -> str:
    if not metadata:
        return ""

    lines = ["# backup_metadata"]
    for key, value in metadata.items():
        lines.append(f"# {key}: {value}")
    lines.append("")
    return "\n".join(lines)


def ensure_directory(path: Path) -> Path:
    """Ensure the target directory exists and return it."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def write_backup(path: Path, content: str) -> Path:
    """Write backup content to a file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def save_backup_text(
    backup_dir: Path,
    vendor: str,
    device_name: str,
    filename: str,
    content: str,
    logger: logging.Logger,
    metadata: Mapping[str, Any] | None = None,
) -> Path:
    """Persist backup content to a structured path and return the saved file path."""

    target_dir = backup_dir / vendor / device_name
    ensure_directory(target_dir)

    backup_path = target_dir / filename
    meta_header = _format_metadata(metadata or {})
    backup_path.write_text(meta_header + content, encoding="utf-8")
    logger.info("saved path=%s", backup_path, extra={"device": device_name})
    return backup_path


def load_local_config(
    config_path: str | Path | None = None, logger: logging.Logger | None = None
) -> Mapping[str, Any] | None:
    """Load local.yml if it exists and return the mapping."""

    config_file = Path(config_path) if config_path else DEFAULT_LOCAL_CONFIG
    if not config_file.is_absolute():
        config_file = PROJECT_ROOT / config_file

    if logger:
        logger.debug("loading local config from %s", config_file)

    if not config_file.exists():
        if logger:
            logger.debug("local config not found at %s", config_file)
        return None

    try:
        with config_file.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        if logger:
            logger.warning("unable to read local config file=%s reason=\"%s\"", config_file, exc)
        return None

    return data if isinstance(data, Mapping) else None


def _probe_directory(path: Path) -> tuple[bool, str | None]:
    """Try to create and write to the directory, returning success and reason."""

    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".write-test"
        with test_file.open("w", encoding="utf-8") as handle:
            handle.write("probe")
        test_file.unlink(missing_ok=True)
        return True, None
    except OSError as exc:
        return False, str(exc)


def _extract_local_backup_dir(local_cfg: Mapping[str, Any] | None) -> Path | None:
    """Return backup.directory from local.yml mapping when present."""

    if not isinstance(local_cfg, Mapping):
        return None

    backup_section = local_cfg.get("backup")
    if not isinstance(backup_section, Mapping):
        return None

    directory_value = backup_section.get("directory")
    if not directory_value:
        return None

    candidate = Path(directory_value).expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate


def resolve_backup_dir(
    cli_backup_dir: str | Path | None, local_cfg: Mapping[str, Any] | None, logger: logging.Logger
) -> Path:
    """Determine the backup directory with priority: CLI > local.yml > fallback."""

    candidates: list[tuple[str, Path]] = []

    if cli_backup_dir:
        candidates.append(("cli", Path(cli_backup_dir).expanduser()))

    local_candidate = _extract_local_backup_dir(local_cfg)
    if local_candidate:
        candidates.append(("local_yml", local_candidate))

    for source, candidate in candidates:
        ok, reason = _probe_directory(candidate)
        if ok:
            logger.info("backup_dir source=%s path=%s", source, candidate)
            return candidate

        logger.warning(
            'backup_dir source=%s path=%s fallback=%s reason="%s"',
            source,
            candidate,
            FALLBACK_BACKUP_DIR,
            reason or "unavailable",
        )

    ok, fallback_reason = _probe_directory(FALLBACK_BACKUP_DIR)
    if not ok:
        logger.error(
            'backup_dir fallback=%s reason="%s"', FALLBACK_BACKUP_DIR, fallback_reason or "unavailable"
        )
        raise OSError(f"Unable to use fallback backup directory: {FALLBACK_BACKUP_DIR}")

    if not candidates:
        logger.info(
            'backup_dir source=fallback path=%s reason="%s"', FALLBACK_BACKUP_DIR, "not provided"
        )
    else:
        logger.info("backup_dir source=fallback path=%s", FALLBACK_BACKUP_DIR)

    return FALLBACK_BACKUP_DIR
