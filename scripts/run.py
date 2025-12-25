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
from app.core.storage import ensure_directory  # noqa: E402
from app.mikrotik.backup import backup_device as backup_mikrotik  # noqa: E402
from app.mikrotik.client import MikroTikClient  # noqa: E402


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
        default=ROOT_DIR / "backups",
        help="Directory where backup files will be written",
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

    ensure_directory(Path(args.backup_dir))
    logger.info("Starting backup for %d device(s).", len(devices))

    for device in devices:
        _process_device_backup(device, Path(args.backup_dir), logger)

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
            client = MikroTikClient(host=device.host, username=device.username, password=password)
            output_path = _device_output_path(backup_dir, device, "export")
            backup_path = backup_mikrotik(client, output_path)
    except Exception:
        logger.exception("Backup failed for device.", extra={"device": device.name})
        return

    logger.info("Backup completed successfully at %s", backup_path, extra={"device": device.name})


def _device_output_path(base_dir: Path, device: Device, suffix: str) -> Path:
    """Create a deterministic backup path for a device."""

    return base_dir / device.name / f"{suffix}.txt"


if __name__ == "__main__":
    raise SystemExit(main())
