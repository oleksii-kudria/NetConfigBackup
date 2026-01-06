"""Diff helpers shared across vendors."""

from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(slots=True)
class DiffOutcome:
    """Result of comparing two backup files."""

    previous_path: Path | None
    normalized_hash: str | None
    config_changed: bool | None
    added: int = 0
    removed: int = 0
    diff_text: str | None = None


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _count_added_removed(diff_lines: list[str]) -> tuple[int, int]:
    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    return added, removed


def _generate_diff(prev: str, curr: str, from_label: str, to_label: str) -> tuple[str, int, int]:
    diff_lines = list(
        difflib.unified_diff(prev.splitlines(), curr.splitlines(), fromfile=from_label, tofile=to_label, lineterm="")
    )
    added, removed = _count_added_removed(diff_lines)
    diff_text = "\n".join(diff_lines)
    if diff_text:
        diff_text += "\n"
    return diff_text, added, removed


def _select_previous_file(current_backup: Path, glob_pattern: str) -> Path | None:
    if not current_backup.exists():
        return None

    backups = sorted((path for path in current_backup.parent.glob(glob_pattern) if path.is_file()), key=lambda p: p.stat().st_mtime)
    for index, path in enumerate(backups):
        if path.resolve() == current_backup.resolve():
            return backups[index - 1] if index > 0 else None

    return backups[-2] if len(backups) > 1 else None


def evaluate_change(
    current_backup: Path,
    glob_pattern: str,
    normalizer: Callable[[str], str],
) -> DiffOutcome:
    """Compare current backup against previous one using the provided normalizer."""

    previous_backup = _select_previous_file(current_backup, glob_pattern)
    curr_text = normalizer(current_backup.read_text(encoding="utf-8"))
    normalized_hash = _hash_text(curr_text)

    if previous_backup is None:
        return DiffOutcome(previous_path=None, normalized_hash=normalized_hash, config_changed=None)

    prev_text = normalizer(previous_backup.read_text(encoding="utf-8"))
    prev_hash = _hash_text(prev_text)

    if prev_hash == normalized_hash:
        return DiffOutcome(previous_path=previous_backup, normalized_hash=normalized_hash, config_changed=False)

    diff_text, added, removed = _generate_diff(prev_text, curr_text, previous_backup.name, current_backup.name)
    return DiffOutcome(
        previous_path=previous_backup,
        normalized_hash=normalized_hash,
        config_changed=True,
        added=added,
        removed=removed,
        diff_text=diff_text,
    )
