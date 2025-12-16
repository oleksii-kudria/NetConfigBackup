"""Cisco client placeholder."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CiscoClient:
    """Client stub for Cisco devices."""

    host: str
    username: str
    password: str

    def fetch_running_config(self) -> str:
        """Placeholder for retrieving the running configuration."""

        return "! Cisco running-config placeholder\n"
