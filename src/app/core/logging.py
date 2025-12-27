"""Central logging configuration for NetConfigBackup.

This module reads the optional ``config/local.yml`` file (``logging`` section)
to determine where logs should be written and which verbosity level to use. If
the configured directory is not writable, it falls back to ``./logs`` while
recording a warning. Secrets are scrubbed from log messages and the ``device``
context is always present to satisfy the required format.
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DIRECTORY = Path("/var/log/netconfigbackup")
DEFAULT_FILENAME = "netconfigbackup.log"
DEFAULT_LEVEL = logging.INFO
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "local.yml"
FALLBACK_DIRECTORY = Path("./logs")

LOG_FORMAT = "%(asctime)s | %(levelname)s | device=%(device)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(slots=True)
class LoggingConfig:
    """Configuration values loaded from local.yml or defaults."""

    directory: Path
    filename: str
    level: int


class DeviceContextFilter(logging.Filter):
    """Ensure every record contains a device name."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - logging hook
        if not getattr(record, "device", None):
            record.device = "-"
        return True


class SecretScrubberFilter(logging.Filter):
    """Remove obvious secrets from log messages."""

    SECRET_PATTERN = re.compile(r"(password|secret|token)=([^\s]+)", re.IGNORECASE)

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - logging hook
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            return True

        cleaned = self.SECRET_PATTERN.sub(r"\1=***", message)
        if cleaned != message:
            record.msg = cleaned
            record.args = ()
        return True


def _load_logging_section(config_path: Path) -> Mapping[str, Any]:
    if not config_path.exists():
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError):  # pragma: no cover - defensive
        return {}

    if not isinstance(data, Mapping):
        return {}

    logging_section = data.get("logging", {})
    if not isinstance(logging_section, Mapping):
        return {}

    return logging_section


def _level_from_value(raw_level: Any) -> int:
    if isinstance(raw_level, str):
        level_name = raw_level.upper()
        level = logging.getLevelName(level_name)
        if isinstance(level, int):
            return level
    if isinstance(raw_level, int):
        return raw_level
    return DEFAULT_LEVEL


def _parse_logging_config(config_path: Path) -> tuple[LoggingConfig, bool]:
    section = _load_logging_section(config_path)
    missing_file = not config_path.exists()

    directory_value = section.get("directory") if section else None
    filename_value = section.get("filename") if section else None
    level_value = section.get("level") if section else None

    directory = Path(directory_value).expanduser() if directory_value else DEFAULT_DIRECTORY
    filename = str(filename_value) if filename_value else DEFAULT_FILENAME
    level = _level_from_value(level_value)

    return LoggingConfig(directory=directory, filename=filename, level=level), missing_file


def _resolve_config_path(config_path: str | Path) -> Path:
    candidate = Path(config_path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate


def _ensure_writable_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".write-test"
    with probe.open("a", encoding="utf-8"):
        probe.touch()
    probe.unlink(missing_ok=True)


def _determine_log_directory(target: Path, fallback: Path) -> tuple[Path, bool]:
    for index, candidate in enumerate((target, fallback)):
        try:
            _ensure_writable_directory(candidate)
            return candidate, index == 1
        except OSError:
            continue
    raise OSError("Unable to create a writable logging directory.")


def _build_handlers(log_path: Path) -> list[logging.Handler]:
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    filters: list[logging.Filter] = [DeviceContextFilter(), SecretScrubberFilter()]

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    stream_handler = logging.StreamHandler(sys.stdout)

    for handler in (file_handler, stream_handler):
        handler.setFormatter(formatter)
        for filter_ in filters:
            handler.addFilter(filter_)

    return [file_handler, stream_handler]


def setup_logging(config_path: str | Path = "config/local.yml") -> logging.Logger:
    """Configure application-wide logging.

    Parameters
    ----------
    config_path:
        Optional path to ``local.yml``. Defaults to ``config/local.yml``
        relative to the project root when not provided.
    """

    config_file = _resolve_config_path(config_path) if config_path else DEFAULT_CONFIG_PATH
    config, missing_file = _parse_logging_config(config_file)
    log_directory, used_fallback = _determine_log_directory(config.directory, FALLBACK_DIRECTORY)
    log_path = log_directory / config.filename

    handlers = _build_handlers(log_path)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(config.level)
    for handler in handlers:
        root_logger.addHandler(handler)

    logger = logging.getLogger("netconfigbackup")
    logger.setLevel(config.level)
    logger.propagate = True

    if missing_file:
        logger.info(
            "Logging configuration file '%s' not found. Using defaults (directory=%s, level=%s).",
            config_file,
            config.directory,
            logging.getLevelName(config.level),
        )

    if used_fallback:
        logger.warning(
            "Logging directory '%s' is not writable. Falling back to '%s'.",
            config.directory,
            log_directory,
        )

    logger.info("Logging initialized at %s", log_path)
    return logger
