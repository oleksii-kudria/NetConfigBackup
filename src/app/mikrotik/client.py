"""MikroTik client placeholder."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MikroTikClient:
    """Client stub for MikroTik devices."""

    host: str
    username: str
    password: str

    def fetch_running_config(self) -> str:
        """Placeholder for retrieving the running configuration."""

        return "/interface print\n# MikroTik configuration placeholder\n"
