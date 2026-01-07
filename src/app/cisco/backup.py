"""Backup helpers for Cisco devices."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from app.core.logging import sanitize_log_extra
from app.cisco.client import CiscoClient
from app.core.storage import ensure_directory
from app.common.diff import DiffOutcome, evaluate_change
from app.core.normalize import normalize_cisco_running_config


def backup_device(
    client: CiscoClient,
    backup_dir: Path,
    logger: logging.Logger | None = None,
    log_extra: dict | None = None,
) -> tuple[Path, DiffOutcome, Path | None]:
    """Perform a backup for a Cisco device and save it to disk."""

    resolved_logger = logger or logging.getLogger(__name__)
    sanitized_extra = sanitize_log_extra(log_extra)
    log_extra = {"device": client.name, **sanitized_extra}

    resolved_logger.info("device=%s fetching running-config", client.name, extra=log_extra)
    try:
        content = client.fetch_running_config(resolved_logger, log_extra)
    except Exception:
        resolved_logger.error("device=%s running-config retrieval failed", client.name, extra=log_extra)
        raise

    if not _is_valid_running_config(content):
        resolved_logger.error("device=%s running-config sanity-check failed", client.name, extra=log_extra)
        raise ValueError("Invalid running-config output.")

    resolved_logger.info("device=%s running-config retrieved", client.name, extra=log_extra)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    target_dir = ensure_directory(backup_dir / "cisco" / client.name)
    backup_path = target_dir / f"{timestamp}_running-config.txt"

    if backup_path.exists():
        resolved_logger.error("device=%s running-config retrieval failed", client.name, extra=log_extra)
        raise FileExistsError(f"Backup file already exists: {backup_path}")

    backup_path.write_text(content, encoding="utf-8")
    size = backup_path.stat().st_size if backup_path.exists() else 0

    if size <= 0:
        resolved_logger.error("device=%s running-config retrieval failed", client.name, extra=log_extra)
        raise ValueError("Backup file is empty after write.")

    resolved_logger.info(
        "device=%s running-config saved path=%s size=%d", client.name, backup_path, size, extra=log_extra
    )
    diff_outcome, diff_path = _log_cisco_diff(backup_path, resolved_logger, log_extra)
    return backup_path, diff_outcome, diff_path


def _is_valid_running_config(content: str) -> bool:
    if not content or not content.strip():
        return False

    lowered = content.lower()
    return any(marker in lowered for marker in ("version", "hostname", "!"))


def _log_cisco_diff(
    current_backup: Path, logger: logging.Logger, log_extra: dict[str, str]
) -> tuple[DiffOutcome, Path | None]:
    """Log diff status for Cisco running-config backups."""

    result: DiffOutcome = evaluate_change(current_backup, "*_running-config.txt", normalize_cisco_running_config)
    device_name = log_extra.get("device", "-")
    current_path = result.current_path or current_backup.resolve()

    if device_name not in ("", "-") and current_path.parent.name != device_name:
        logger.error(
            "device=%s device_path_mismatch expected=%s actual=%s current_path=%s",
            device_name,
            device_name,
            current_path.parent.name,
            current_path,
            extra=log_extra,
        )
        raise ValueError(f"Device path mismatch for {device_name}: {current_path}")

    logger.info(
        "device=%s diff baseline_path=%s current_path=%s",
        device_name,
        str(result.previous_path) if result.previous_path else "-",
        current_path,
        extra=log_extra,
    )

    logger.debug(
        "device=%s baseline_size_bytes=%s current_size_bytes=%s baseline_sha256=%s current_sha256=%s baseline_lines=%s current_lines=%s",
        device_name,
        result.baseline_size_bytes if result.baseline_size_bytes is not None else 0,
        result.current_size_bytes if result.current_size_bytes is not None else 0,
        result.baseline_sha256 or "-",
        result.current_sha256 or "-",
        result.baseline_lines if result.baseline_lines is not None else 0,
        result.current_lines if result.current_lines is not None else 0,
        extra=log_extra,
    )
    logger.debug("device=%s normalized_hash=%s", device_name, result.normalized_hash, extra=log_extra)

    changed_value = "null" if result.config_changed is None else str(result.config_changed).lower()
    logger.info("device=%s config_changed=%s", device_name, changed_value, extra=log_extra)

    if not result.config_changed:
        return result, None

    diff_path = current_path.with_suffix(".diff")
    diff_path.write_text(result.diff_text or "", encoding="utf-8")
    logger.info(
        "device=%s change_summary added=%d removed=%d diff_file=%s",
        device_name,
        result.added,
        result.removed,
        diff_path,
        extra=log_extra,
    )
    return result, diff_path
