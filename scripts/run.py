#!/usr/bin/env python3
"""Entry point for NetConfigBackup."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

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
from app.core.secrets import SecretNotFoundError, get_password  # noqa: E402
from app.core.storage import load_local_config, resolve_backup_dir, save_backup_text  # noqa: E402
from app.mikrotik.backup import fetch_export  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Backup utility for Cisco and MikroTik device configurations. "
            "Use this CLI to run configuration backups and manage inventory files."
        )
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

    subcommands = parser.add_subparsers(dest="command", title="commands")

    backup_parser = subcommands.add_parser(
        "backup", help="Run configuration backups for all configured devices"
    )
    backup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be backed up without connecting to devices",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    logger = setup_logging()
    logger.info("NetConfigBackup run started.")
    parser = build_parser()
    args = parser.parse_args(argv)

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

    try:
        devices = load_devices(Path(args.config))
    except Exception:
        logger.exception("Failed to load devices configuration.", extra={"device": "-"})
        return 1

    if args.dry_run:
        logger.info("Dry run requested. Devices to process: %s", [d.name for d in devices])
        return 0

    local_config = load_local_config(ROOT_DIR / "config" / "local.yml")
    backup_dir = resolve_backup_dir(args.backup_dir, local_config, logger)
    logger.info("Starting backup for %d device(s).", len(devices))

    for device in devices:
        _process_device_backup(device, backup_dir, logger)

    return 0


def _process_device_backup(device: Device, backup_dir: Path, logger: logging.Logger) -> None:
    """Handle backup for a single device with logging."""

    logger.info("Beginning processing for device.", extra={"device": device.name})

    try:
        password = get_password(device.auth.secret_ref)
    except SecretNotFoundError:
        logger.error("Skipping device due to missing secret.", extra={"device": device.name})
        return

    try:
        if device.vendor == "cisco":
            client = CiscoClient(host=device.host, username=device.username, password=password)
            output_path = _device_output_path(backup_dir, device, "running-config")
            backup_path = backup_cisco(client, output_path)
        else:
            logger.info(
                "start backup device=%s host=%s", device.name, device.host, extra={"device": device.name}
            )
            backup_path = _backup_mikrotik_device(device, password, backup_dir, logger)
    except Exception:
        logger.exception("Backup failed for device.", extra={"device": device.name})
        return

    logger.info("Backup completed successfully at %s", backup_path, extra={"device": device.name})


def _device_output_path(base_dir: Path, device: Device, suffix: str) -> Path:
    """Create a deterministic backup path for a device."""

    return base_dir / device.name / f"{suffix}.txt"


def _backup_mikrotik_device(device: Device, password: str, backup_dir: Path, logger: logging.Logger) -> Path:
    log_extra = {"device": device.name}
    if not _tcp_check(device.host, device.port, timeout=5):
        logger.error(
            "tcp_check fail host=%s port=%s", device.host, device.port, extra=log_extra
        )
        raise ConnectionError(f"TCP check failed for {device.host}:{device.port}")

    logger.info("tcp_check ok host=%s port=%s", device.host, device.port, extra=log_extra)

    export_text = fetch_export(device, password, logger)

    if not export_text.strip():
        raise ValueError("Empty export received from device")

    timestamp = _timestamp()
    filename = f"{timestamp}_export.rsc"
    metadata = {
        "device": device.name,
        "vendor": device.vendor,
        "model": device.model,
        "host": device.host,
        "backup_time": timestamp,
    }

    return save_backup_text(backup_dir, "mikrotik", device.name, filename, export_text, logger, metadata)


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
