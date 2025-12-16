"""Storage helpers for writing backups to disk."""

from __future__ import annotations

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Ensure the target directory exists and return it."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def write_backup(path: Path, content: str) -> Path:
    """Write backup content to a file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
