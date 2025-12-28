"""Diff and normalization utilities for MikroTik exports."""

from __future__ import annotations

import difflib
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(slots=True)
class DiffResult:
    """Outcome of comparing two MikroTik exports."""

    first_backup: bool
    config_changed: bool
    added: int = 0
    removed: int = 0
    diff_text: str | None = None
    previous_path: Path | None = None


def normalize_export(text: str) -> str:
    """Normalize MikroTik export text to reduce noise before comparison."""

    normalized_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        line = _WHITESPACE_RE.sub(" ", line)
        normalized_lines.append(line)

    normalized_lines.sort()
    return "\n".join(normalized_lines)


def calculate_hash(text: str) -> str:
    """Return a SHA256 hash for the provided text."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_diff(prev: str, curr: str, from_label: str = "previous", to_label: str = "current") -> tuple[str, int, int]:
    """Generate a unified diff along with added/removed line counts."""

    prev_lines = prev.splitlines()
    curr_lines = curr.splitlines()

    diff_lines = list(
        difflib.unified_diff(prev_lines, curr_lines, fromfile=from_label, tofile=to_label, lineterm="")
    )

    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

    diff_text = "\n".join(diff_lines)
    if diff_text:
        diff_text += "\n"

    return diff_text, added, removed


def find_previous_export(current_export: Path) -> Path | None:
    """Locate the previous export file in the same directory, if any."""

    if not current_export.exists():
        return None

    exports = sorted(
        (path for path in current_export.parent.glob("*_export.rsc") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
    )

    for index, path in enumerate(exports):
        if path.resolve() == current_export.resolve():
            return exports[index - 1] if index > 0 else None

    return exports[-2] if len(exports) > 1 else None


def evaluate_config_change(current_export: Path) -> DiffResult:
    """Compare the current export with the previous one and return the outcome."""

    previous_export = find_previous_export(current_export)
    if previous_export is None:
        return DiffResult(first_backup=True, config_changed=False)

    prev_text = normalize_export(previous_export.read_text(encoding="utf-8"))
    curr_text = normalize_export(current_export.read_text(encoding="utf-8"))

    prev_hash = calculate_hash(prev_text)
    curr_hash = calculate_hash(curr_text)

    if prev_hash == curr_hash:
        return DiffResult(first_backup=False, config_changed=False, previous_path=previous_export)

    diff_text, added, removed = generate_diff(prev_text, curr_text, previous_export.name, current_export.name)

    return DiffResult(
        first_backup=False,
        config_changed=True,
        added=added,
        removed=removed,
        diff_text=diff_text,
        previous_path=previous_export,
    )
