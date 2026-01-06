#!/usr/bin/env python3
"""Entry point for NetConfigBackup."""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from typing import Mapping
from pathlib import Path
from dataclasses import dataclass

# Ensure src/ is on sys.path for local imports when running as a script
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.cisco.backup import backup_device as backup_cisco  # noqa: E402
from app.cisco.client import CiscoClient  # noqa: E402
from app.core.config import load_devices  # noqa: E402
from app.core.logging import setup_logging  # noqa: E402
from app.core.models import Device  # noqa: E402
from app.core.secrets import Secrets, SecretNotFoundError, load_secrets, resolve_device_secrets  # noqa: E402
from app.core.storage import load_local_config, resolve_backup_dir, save_backup_text  # noqa: E402
from app.mikrotik.backup import fetch_export, log_mikrotik_diff, perform_system_backup  # noqa: E402


@dataclass(frozen=True)
class FeatureSelection:
    default_mode: bool
    mikrotik_export: bool
    mikrotik_system_backup: bool
    cisco_running_config: bool


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    feature_flags_parent = argparse.ArgumentParser(add_help=False)
    feature_flags_parent.add_argument(
        "--mikrotik-system-backup",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Enable MikroTik binary system backup via /system backup save",
    )
    feature_flags_parent.add_argument(
        "--mikrotik-export",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Run only MikroTik /export text backup",
    )
    feature_flags_parent.add_argument(
        "--cisco-running-config",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Run only Cisco show running-config text backup",
    )

    parser = argparse.ArgumentParser(
        description=(
            "Backup utility for Cisco and MikroTik device configurations. "
            "Use this CLI to run configuration backups and manage inventory files."
        ),
        parents=[feature_flags_parent],
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT_DIR / "config" / "devices.yml",
        help="Path to the devices inventory file (YAML)",
    )
    parser.add_argument(
        "--secrets",
        type=Path,
        default=ROOT_DIR / "config" / "secrets.yml",
        help="Path to the secrets file (YAML)",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=None,
        help="Directory where backup files will be written. Overrides config/local.yml.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug-level logging for troubleshooting. Overrides config/local.yml logging.level.",
    )

    subcommands = parser.add_subparsers(dest="command", title="commands")

    backup_parser = subcommands.add_parser(
        "backup",
        help="Run configuration backups for all configured devices",
        parents=[feature_flags_parent],
    )
    backup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be backed up without connecting to devices",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    logger = setup_logging(cli_level=logging.DEBUG if args.debug else None)
    logger.info("NetConfigBackup run started.")

    if args.command is None:
        parser.print_help()
        logger.info("NetConfigBackup run finished.")
        return 0

    if args.command == "backup":
        exit_code = _run_backup(args, logger)
        logger.info("NetConfigBackup run finished.")
        return exit_code

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_backup(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Execute the backup workflow for all configured devices."""

    config_path = Path(args.config)
    logger.debug("loading devices from %s", config_path)
    try:
        devices = load_devices(config_path, logger)
    except Exception:
        logger.exception("Failed to load devices configuration.", extra={"device": "-"})
        return 1

    logger.debug("total devices loaded=%d", len(devices))
    for vendor, count in sorted(Counter(device.vendor for device in devices).items()):
        logger.debug("%s devices selected=%d", vendor, count)

    local_config_path = ROOT_DIR / "config" / "local.yml"
    local_config = load_local_config(local_config_path, logger)
    if local_config is not None:
        logger.debug("local config loaded from %s", local_config_path)

    feature_selection = _resolve_feature_selection(args, local_config, logger)

    _log_selected_features(feature_selection, logger)

    if args.dry_run:
        logger.info("Dry run requested. Devices to process: %s", [d.name for d in devices])
        return 0

    secrets_path = Path(args.secrets)
    logger.debug("loading secrets from %s", secrets_path)
    try:
        secrets = load_secrets(secrets_path, logger)
    except Exception:
        logger.exception("Failed to load secrets configuration.", extra={"device": "-"})
        return 1

    logger.debug(
        "resolving backup directory cli_arg=%s local_yml_present=%s", args.backup_dir, local_config is not None
    )
    backup_dir = resolve_backup_dir(args.backup_dir, local_config, logger)
    logger.info("Starting backup for %d device(s).", len(devices))

    for device in devices:
        _process_device_backup(device, backup_dir, secrets, logger, feature_selection)

    return 0


def _resolve_feature_selection(
    args: argparse.Namespace, local_config: Mapping[str, object] | None, logger: logging.Logger
) -> FeatureSelection:
    """Resolve which backup features are enabled for this run."""

    cli_features = {
        "mikrotik_export": getattr(args, "mikrotik_export", False),
        "mikrotik_system_backup": getattr(args, "mikrotik_system_backup", False),
        "cisco_running_config": getattr(args, "cisco_running_config", False),
    }

    if any(cli_features.values()):
        return FeatureSelection(
            default_mode=False,
            mikrotik_export=cli_features["mikrotik_export"],
            mikrotik_system_backup=cli_features["mikrotik_system_backup"],
            cisco_running_config=cli_features["cisco_running_config"],
        )

    system_backup_enabled = _resolve_mikrotik_system_backup(
        getattr(args, "mikrotik_system_backup", None), local_config, logger
    )

    return FeatureSelection(
        default_mode=True,
        mikrotik_export=True,
        mikrotik_system_backup=system_backup_enabled,
        cisco_running_config=True,
    )


def _log_selected_features(feature_selection: FeatureSelection, logger: logging.Logger) -> None:
    if feature_selection.default_mode:
        logger.info("selected_features=default")
        return

    enabled = _format_features_log(
        mikrotik_export=feature_selection.mikrotik_export,
        mikrotik_system_backup=feature_selection.mikrotik_system_backup,
        cisco_running_config=feature_selection.cisco_running_config,
    )
    logger.info("selected_features=%s", enabled if enabled else "none")


def _format_features_log(
    *, mikrotik_export: bool, mikrotik_system_backup: bool, cisco_running_config: bool
) -> str:
    order = (
        ("mikrotik_export", mikrotik_export),
        ("mikrotik_system_backup", mikrotik_system_backup),
        ("cisco_running_config", cisco_running_config),
    )
    return ",".join(name for name, enabled in order if enabled)


def _process_device_backup(
    device: Device, backup_dir: Path, secrets: Secrets, logger: logging.Logger, feature_selection: FeatureSelection
) -> None:
    """Handle backup for a single device with logging."""

    log_extra = {"device": device.name}
    logger.info("Beginning processing for device.", extra=log_extra)
    logger.debug(
        "preparing backup for device=%s vendor=%s host=%s port=%s",
        device.name,
        device.vendor,
        device.host,
        device.port,
        extra=log_extra,
    )

    device_tasks = _select_device_tasks(device.vendor, feature_selection)
    logger.info(
        "device=%s vendor=%s selected_tasks=%s",
        device.name,
        device.vendor,
        _format_features_log(
            mikrotik_export="mikrotik_export" in device_tasks,
            mikrotik_system_backup="mikrotik_system_backup" in device_tasks,
            cisco_running_config="cisco_running_config" in device_tasks,
        )
        or "none",
        extra=log_extra,
    )

    if not device_tasks:
        logger.info("No selected tasks for device vendor; skipping.", extra=log_extra)
        return

    try:
        secret_entry = resolve_device_secrets(device.auth.secret_ref, secrets)
    except SecretNotFoundError:
        logger.error(
            "device=%s missing secrets for secret_ref=%s",
            device.name,
            device.auth.secret_ref,
            extra=log_extra,
        )
        return

    logger.info("device=%s secret_ref=%s secrets_loaded=true", device.name, device.auth.secret_ref, extra=log_extra)

    completed_paths: list[Path] = []
    try:
        if device.vendor == "cisco" and "cisco_running_config" in device_tasks:
            client = CiscoClient(
                host=device.host,
                name=device.name,
                username=device.username,
                password=secret_entry.password,
                port=device.port,
                enable_password=secret_entry.enable_password,
            )
            completed_paths.append(backup_cisco(client, backup_dir, logger, log_extra))
        elif device.vendor == "mikrotik":
            logger.info(
                "start backup device=%s host=%s", device.name, device.host, extra=log_extra
            )
            completed_paths.extend(
                _backup_mikrotik_device(
                    device,
                    secret_entry.password,
                    backup_dir,
                    logger,
                    run_export="mikrotik_export" in device_tasks,
                    run_system_backup="mikrotik_system_backup" in device_tasks,
                )
            )
        else:
            logger.info("Unknown vendor=%s; skipping.", device.vendor, extra=log_extra)
            return
    except Exception:
        logger.exception("Backup failed for device.", extra=log_extra)
        return

    if completed_paths:
        logger.info(
            "Backup completed successfully tasks=%s paths=%s",
            ",".join(device_tasks),
            [str(path) for path in completed_paths],
            extra=log_extra,
        )
    else:
        logger.info("Backup finished with no generated files.", extra=log_extra)


def _select_device_tasks(vendor: str, feature_selection: FeatureSelection) -> list[str]:
    tasks: list[str] = []
    if vendor == "mikrotik":
        if feature_selection.mikrotik_export:
            tasks.append("mikrotik_export")
        if feature_selection.mikrotik_system_backup:
            tasks.append("mikrotik_system_backup")
    elif vendor == "cisco":
        if feature_selection.cisco_running_config:
            tasks.append("cisco_running_config")
    return tasks


def _backup_mikrotik_device(
    device: Device,
    password: str,
    backup_dir: Path,
    logger: logging.Logger,
    run_export: bool,
    run_system_backup: bool,
) -> list[Path]:
    log_extra = {"device": device.name}
    logger.debug(
        "checking tcp connectivity host=%s port=%s timeout=%s", device.host, device.port, 5, extra=log_extra
    )
    if not _tcp_check(device.host, device.port, timeout=5):
        logger.error(
            "tcp_check fail host=%s port=%s", device.host, device.port, extra=log_extra
        )
        raise ConnectionError(f"TCP check failed for {device.host}:{device.port}")

    logger.info("tcp_check ok host=%s port=%s", device.host, device.port, extra=log_extra)

    timestamp = _timestamp()
    completed: list[Path] = []
    if run_export:
        export_text = fetch_export(device, password, logger)
        logger.debug("export received bytes=%d", len(export_text.encode("utf-8")), extra=log_extra)

        if not export_text.strip():
            raise ValueError("Empty export received from device")

        filename = f"{timestamp}_export.rsc"
        metadata = {
            "device": device.name,
            "vendor": device.vendor,
            "model": device.model or "-",
            "host": device.host,
            "backup_time": timestamp,
        }

        target_path = backup_dir / "mikrotik" / device.name / filename
        logger.debug("saving backup to %s", target_path, extra=log_extra)

        saved_path = save_backup_text(backup_dir, "mikrotik", device.name, filename, export_text, logger, metadata)
        completed.append(saved_path)
        log_mikrotik_diff(saved_path, logger, log_extra)
    else:
        logger.info("MikroTik export skipped", extra=log_extra)

    if run_system_backup:
        try:
            completed.append(perform_system_backup(device, password, timestamp, backup_dir, logger))
        except Exception:
            logger.exception("system-backup failed", extra=log_extra)
    else:
        logger.info("mikrotik system-backup disabled (skipping) device=%s", device.name, extra=log_extra)

    return completed


def _resolve_mikrotik_system_backup(
    cli_flag: bool | None, local_config: Mapping[str, object] | None, logger: logging.Logger
) -> bool:
    """Determine whether MikroTik system backup is enabled.

    Priority: CLI flag > local.yml > default False.
    """

    local_value = _extract_mikrotik_system_backup(local_config)
    if cli_flag is True:
        enabled = True
        source = "cli"
    elif isinstance(local_value, bool):
        enabled = local_value
        source = "local_yml"
    else:
        enabled = False
        source = "default"

    logger.debug(
        "mikrotik system-backup resolved enabled=%s source=%s cli_flag=%s local_yml=%s",
        enabled,
        source,
        cli_flag,
        local_value,
    )
    return enabled


def _extract_mikrotik_system_backup(local_config: Mapping[str, object] | None) -> bool | None:
    if not isinstance(local_config, Mapping):
        return None

    mikrotik_section = local_config.get("mikrotik")
    if not isinstance(mikrotik_section, Mapping):
        return None

    value = mikrotik_section.get("system_backup")
    return value if isinstance(value, bool) else None


def _tcp_check(host: str, port: int, timeout: float = 3.0) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False


def _timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")


if __name__ == "__main__":
    raise SystemExit(main())
