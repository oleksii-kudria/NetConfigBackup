"""MikroTik SSH client implementation."""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from typing import Any

import paramiko


class MikroTikClientError(RuntimeError):
    """Base exception for MikroTik client errors."""


class MikroTikAuthenticationError(MikroTikClientError):
    """Raised when SSH authentication fails."""


class MikroTikCommandError(MikroTikClientError):
    """Raised when a command cannot be executed successfully."""


@dataclass(slots=True)
class MikroTikClient:
    """SSH client for MikroTik devices."""

    host: str
    username: str
    password: str
    port: int = 22
    timeout: float = 5.0

    def fetch_export(self, logger: logging.Logger, log_extra: dict[str, Any]) -> str:
        """Retrieve the export configuration from the device."""

        command = "/export"
        logger.debug(
            "connecting to device=%s host=%s port=%s",
            log_extra.get("device", "-"),
            self.host,
            self.port,
            extra=log_extra,
        )
        client = self._connect(logger, log_extra)
        try:
            logger.debug("executing mikrotik command='%s'", command, extra=log_extra)
            output, error_output, exit_status = self._run_command(client, command)
            if exit_status == 0 and output.strip():
                logger.debug("export received bytes=%d", len(output.encode("utf-8")), extra=log_extra)
                return output

            error_message = error_output or f"exit_status={exit_status}"
            logger.warning("export command failed command=%s status=%s", command, exit_status, extra=log_extra)
            raise MikroTikCommandError(error_message)
        finally:
            client.close()

    def _connect(self, logger: logging.Logger, log_extra: dict[str, Any]) -> paramiko.SSHClient:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            logger.debug("opening ssh session host=%s port=%s", self.host, self.port, extra=log_extra)
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
            logger.info("ssh ok host=%s port=%s", self.host, self.port, extra=log_extra)
            return ssh
        except paramiko.AuthenticationException as exc:  # pragma: no cover - network dependent
            raise MikroTikAuthenticationError("SSH authentication failed") from exc
        except (paramiko.SSHException, socket.error, TimeoutError) as exc:  # pragma: no cover - network dependent
            raise MikroTikClientError("SSH connection failed") from exc

    def _run_command(self, client: paramiko.SSHClient, command: str) -> tuple[str, str, int]:
        try:
            stdin, stdout, stderr = client.exec_command(command, timeout=self.timeout)
        except paramiko.SSHException as exc:  # pragma: no cover - network dependent
            raise MikroTikCommandError(f"Unable to execute command '{command}'") from exc

        output = stdout.read().decode("utf-8", errors="replace")
        error_output = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        return output, error_output, exit_status
