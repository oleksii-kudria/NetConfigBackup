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


class CiscoEnableError(CiscoClientError):
    """Raised when privileged EXEC mode cannot be reached."""


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
            self._update_prompt(prompt)
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

    def _ensure_channel(self) -> paramiko.Channel:
        if self.channel is None or self.channel.closed:
            raise CiscoClientError("SSH channel is not available")
        return self.channel

    def _update_prompt(self, prompt: str) -> None:
        self.prompt = prompt
        if prompt.endswith("#"):
            self.prompt_mode = "privileged"
        elif prompt.endswith(">"):
            self.prompt_mode = "user"
        else:
            self.prompt_mode = None

    def wait_for(self, substring: str, timeout: float | None = None) -> str:
        """Read from the channel until ``substring`` is found or timeout expires."""

        channel = self._ensure_channel()
        buffer = ""
        deadline = time.monotonic() + (timeout or self.timeout)

        while time.monotonic() < deadline:
            if channel.recv_ready():
                data = channel.recv(4096)
                buffer += data.decode("utf-8", errors="replace")
                prompt = _extract_prompt(buffer)
                if prompt:
                    self._update_prompt(prompt)
                if substring in buffer:
                    return buffer
            else:
                time.sleep(0.1)
        raise TimeoutError(f"Timed out waiting for substring: {substring}")

    def wait_for_prompt(self, timeout: float | None = None) -> str:
        """Read from the channel until a prompt (``>`` or ``#``) is detected."""

        channel = self._ensure_channel()
        buffer = ""
        deadline = time.monotonic() + (timeout or self.timeout)

        while time.monotonic() < deadline:
            if channel.recv_ready():
                data = channel.recv(4096)
                buffer += data.decode("utf-8", errors="replace")
                prompt = _extract_prompt(buffer)
                if prompt:
                    self._update_prompt(prompt)
                    return buffer
            else:
                time.sleep(0.1)
        raise TimeoutError("Timed out waiting for prompt.")

    def send(self, command: str) -> None:
        """Send a raw command to the channel with newline."""

        channel = self._ensure_channel()
        channel.send(command + "\n")

    def run_command(self, command: str) -> str:
        """Send a command and wait for a prompt, returning the raw buffer."""

        self.send(command)
        return self.wait_for_prompt()

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
            self._ensure_enable(session, logger, resolved_log_extra)
            self._disable_paging(session, logger, resolved_log_extra)
            raw_output = session.run_command("show running-config")
            return _extract_command_output(raw_output, "show running-config")
        except TimeoutError as exc:
            raise CiscoClientError("Timed out during Cisco command execution.") from exc
        finally:
            if session is not None:
                session.close()

    def _ensure_enable(
        self, session: CiscoSSHSession, logger: logging.Logger, log_extra: Mapping[str, Any]
    ) -> None:
        """Move the session to privileged EXEC mode when requested."""

        if session.prompt_mode == "privileged":
            logger.info("device=%s enable not required (already privileged)", self.name, extra=log_extra)
            return

        if not self.enable_password:
            logger.info("device=%s enable skipped (no enable_password)", self.name, extra=log_extra)
            return

        logger.info("device=%s enable requested", self.name, extra=log_extra)
        try:
            session.send("enable")
            session.wait_for("Password:")
            session.send(self.enable_password)
            session.wait_for_prompt()
        except Exception as exc:
            logger.error("device=%s enable failed", self.name, extra=log_extra)
            raise CiscoEnableError("Failed to enter privileged EXEC mode.") from exc

        if session.prompt_mode != "privileged":
            logger.error("device=%s enable failed", self.name, extra=log_extra)
            raise CiscoEnableError("Privileged prompt not detected after enable.")

        logger.info("device=%s enable ok", self.name, extra=log_extra)

    def _disable_paging(
        self, session: CiscoSSHSession, logger: logging.Logger, log_extra: Mapping[str, Any]
    ) -> None:
        """Disable paging to capture full command output."""

        logger.debug("device=%s sending terminal length 0", self.name, extra=log_extra)
        session.run_command("terminal length 0")


def _extract_command_output(raw_output: str, command: str) -> str:
    """Strip echoed command and prompt from raw channel output."""

    lines = raw_output.splitlines()
    cleaned: list[str] = []
    command_seen = False

    for line in lines:
        if not command_seen:
            if line.strip().startswith(command):
                command_seen = True
            continue
        cleaned.append(line)

    while cleaned and cleaned[-1].strip().endswith((">", "#")):
        cleaned.pop()

    if not cleaned and lines:
        cleaned = lines

    output = "\n".join(cleaned).rstrip() + "\n"
    return output
