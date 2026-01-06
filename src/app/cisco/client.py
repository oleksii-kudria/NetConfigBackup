"""Cisco SSH client implementation."""

from __future__ import annotations

import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

import paramiko

from app.core.logging import sanitize_log_extra


class CiscoClientError(RuntimeError):
    """Base exception for Cisco client errors."""


class CiscoAuthenticationError(CiscoClientError):
    """Raised when SSH authentication fails."""


class CiscoConnectionError(CiscoClientError):
    """Raised when SSH connection fails."""


def _tcp_check(host: str, port: int, timeout: float) -> bool:
    """Verify TCP reachability for the SSH port."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False


def _extract_prompt(buffer: str) -> str | None:
    """Return the last line ending with '>' or '#' from a buffer."""

    lines = buffer.splitlines()
    for line in reversed(lines):
        stripped = line.strip()
        if stripped.endswith((">", "#")):
            return stripped
    return None


@dataclass(slots=True)
class CiscoSSHSession:
    """Active SSH session with prompt metadata."""

    client: paramiko.SSHClient
    timeout: float
    logger: logging.Logger
    log_extra: dict[str, Any]
    device_name: str
    channel: paramiko.Channel | None = field(init=False, default=None)
    prompt: str | None = field(init=False, default=None)
    prompt_mode: str | None = field(init=False, default=None)

    def initialize_prompt(self) -> None:
        """Open an interactive shell and detect the initial prompt."""

        self.channel = self.client.invoke_shell()
        self.channel.settimeout(self.timeout)

        buffer = self._gather_prompt_buffer()
        prompt = _extract_prompt(buffer)
        if prompt is not None:
            self.prompt = prompt
            if prompt.endswith("#"):
                self.prompt_mode = "privileged"
            elif prompt.endswith(">"):
                self.prompt_mode = "user"
            self.logger.debug(
                "device=%s initial prompt detected prompt=%s",
                self.device_name,
                prompt,
                extra=self.log_extra,
            )

    def _gather_prompt_buffer(self) -> str:
        """Read from the channel until a prompt is likely present."""

        buffer = ""
        deadline = time.monotonic() + self.timeout

        try:
            self.channel.send("\n")
        except Exception:
            return buffer

        while time.monotonic() < deadline:
            if self.channel.recv_ready():
                try:
                    data = self.channel.recv(1024)
                except Exception:
                    break
                buffer += data.decode("utf-8", errors="replace")
                if _extract_prompt(buffer):
                    break
            else:
                time.sleep(0.1)

        return buffer

    def close(self) -> None:
        """Close the SSH session and underlying client."""

        try:
            if self.channel is not None and not self.channel.closed:
                self.channel.close()
        finally:
            self.client.close()
            self.logger.debug("device=%s ssh session closed", self.device_name, extra=self.log_extra)


@dataclass(slots=True)
class CiscoClient:
    """SSH client for Cisco devices."""

    host: str
    username: str
    password: str
    name: str
    enable_password: str | None = None
    port: int = 22
    timeout: float = 5.0
    initial_prompt: str | None = field(init=False, default=None)
    prompt_mode: str | None = field(init=False, default=None)

    def _log_extra(self, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
        base: dict[str, Any] = {"device": self.name}
        if extra:
            base.update(extra)
        return sanitize_log_extra(base)

    def _connect(self, logger: logging.Logger, log_extra: dict[str, Any]) -> CiscoSSHSession:
        logger.info("device=%s checking ssh connectivity", self.name, extra=log_extra)
        if not _tcp_check(self.host, self.port, timeout=self.timeout):
            logger.error(
                "device=%s ssh port unreachable ip=%s port=%s",
                self.name,
                self.host,
                self.port,
                extra=log_extra,
            )
            raise CiscoConnectionError("SSH port unreachable")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(
                self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                look_for_keys=False,
                allow_agent=False,
                timeout=self.timeout,
                banner_timeout=self.timeout,
                auth_timeout=self.timeout,
            )
            logger.info("device=%s ssh connected", self.name, extra=log_extra)
        except paramiko.AuthenticationException as exc:  # pragma: no cover - network dependent
            logger.error("device=%s ssh authentication failed", self.name, extra=log_extra)
            ssh.close()
            raise CiscoAuthenticationError("SSH authentication failed") from exc
        except (paramiko.SSHException, socket.error, TimeoutError) as exc:  # pragma: no cover - network dependent
            logger.error("device=%s ssh connection error", self.name, extra=log_extra)
            ssh.close()
            raise CiscoConnectionError("SSH connection error") from exc

        session = CiscoSSHSession(
            client=ssh,
            timeout=self.timeout,
            logger=logger,
            log_extra=log_extra,
            device_name=self.name,
        )
        session.initialize_prompt()
        self.initial_prompt = session.prompt
        self.prompt_mode = session.prompt_mode
        return session

    def fetch_running_config(
        self, logger: logging.Logger, log_extra: Mapping[str, Any] | None = None
    ) -> str:
        """Establish SSH session and return placeholder configuration text."""

        session: CiscoSSHSession | None = None
        resolved_log_extra = self._log_extra(log_extra)
        try:
            session = self._connect(logger, resolved_log_extra)
            return "! Cisco running-config placeholder\n"
        finally:
            if session is not None:
                session.close()
