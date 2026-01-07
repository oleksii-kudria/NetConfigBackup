"""Normalization helpers for backup configuration texts."""

from __future__ import annotations

import re


def _normalize_line_endings(text: str) -> str:
    """Convert CRLF/CR line endings to LF for consistent processing."""

    return text.replace("\r\n", "\n").replace("\r", "\n")


def _trim_trailing_blank_lines(lines: list[str]) -> list[str]:
    """Remove trailing empty lines while preserving internal spacing."""

    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def normalize_mikrotik_export(text: str) -> str:
    """Normalize MikroTik export text.

    - unify line endings
    - rstrip each line
    - drop blank lines at the end
    """

    normalized = _normalize_line_endings(text)
    lines = [line.rstrip() for line in normalized.split("\n")]
    trimmed = _trim_trailing_blank_lines(lines)
    return "\n".join(trimmed)


_CISCO_VOLATILE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^!\s+Last configuration change.*", re.IGNORECASE),
    re.compile(r"^!\s+NVRAM config last updated.*", re.IGNORECASE),
    re.compile(r"^!\s+Time:.*", re.IGNORECASE),
    re.compile(r"^!\s+.*uptime is.*", re.IGNORECASE),
    re.compile(r"^Current configuration : \d+ bytes", re.IGNORECASE),
    re.compile(r"^ntp clock-period \d+", re.IGNORECASE),
)


def _is_volatile_cisco_line(line: str) -> bool:
    return any(pattern.match(line) for pattern in _CISCO_VOLATILE_PATTERNS)


def normalize_cisco_running_config(text: str) -> str:
    """Normalize Cisco running-config text.

    Removes volatile metadata lines (timestamps, uptime, size counters) and
    standardizes line endings while keeping configuration commands intact.
    """

    normalized = _normalize_line_endings(text)
    lines = normalized.split("\n")

    filtered: list[str] = []
    for line in lines:
        if _is_volatile_cisco_line(line):
            continue
        filtered.append(line)

    trimmed = _trim_trailing_blank_lines(filtered)
    return "\n".join(trimmed)
