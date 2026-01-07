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
    current_path: Path | None
    normalized_hash: str | None
    config_changed: bool | None
    baseline_sha256: str | None = None
    current_sha256: str | None = None
    baseline_size_bytes: int | None = None
    current_size_bytes: int | None = None
    baseline_lines: int | None = None
    current_lines: int | None = None
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

    current_backup = current_backup.resolve()
    previous_backup = _select_previous_file(current_backup, glob_pattern)

    curr_text = normalizer(current_backup.read_text(encoding="utf-8"))
    current_hash = _hash_text(curr_text)
    current_lines = len(curr_text.splitlines())
    current_size = current_backup.stat().st_size if current_backup.exists() else None

    if previous_backup is None:
        return DiffOutcome(
            previous_path=None,
            current_path=current_backup,
            normalized_hash=current_hash,
            config_changed=None,
            current_sha256=current_hash,
            current_size_bytes=current_size,
            current_lines=current_lines,
        )

    previous_backup = previous_backup.resolve()
    prev_text = normalizer(previous_backup.read_text(encoding="utf-8"))
    prev_hash = _hash_text(prev_text)
    baseline_lines = len(prev_text.splitlines())
    baseline_size = previous_backup.stat().st_size if previous_backup.exists() else None

    if prev_hash == current_hash:
        return DiffOutcome(
            previous_path=previous_backup,
            current_path=current_backup,
            normalized_hash=current_hash,
            config_changed=False,
            baseline_sha256=prev_hash,
            current_sha256=current_hash,
            baseline_size_bytes=baseline_size,
            current_size_bytes=current_size,
            baseline_lines=baseline_lines,
            current_lines=current_lines,
        )

    diff_text, added, removed = _generate_diff(prev_text, curr_text, str(previous_backup), str(current_backup))
    return DiffOutcome(
        previous_path=previous_backup,
        current_path=current_backup,
        normalized_hash=current_hash,
        config_changed=True,
        baseline_sha256=prev_hash,
        current_sha256=current_hash,
        baseline_size_bytes=baseline_size,
        current_size_bytes=current_size,
        baseline_lines=baseline_lines,
        current_lines=current_lines,
        added=added,
        removed=removed,
        diff_text=diff_text,
    )
