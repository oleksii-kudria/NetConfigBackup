"""MikroTik SSH client implementation."""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from pathlib import Path
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

    def fetch_system_backup(
        self,
        backup_name: str,
        destination: Path,
        logger: logging.Logger,
        log_extra: dict[str, Any],
    ) -> Path:
        """Create and download a binary system backup."""

        remote_filename = f"{backup_name}.backup"
        command = f"/system backup save name={backup_name} dont-encrypt=yes"

        logger.info("start system-backup device=%s", log_extra.get("device", "-"), extra=log_extra)
        client = self._connect(logger, log_extra)
        sftp: paramiko.SFTPClient | None = None
        try:
            logger.debug("executing mikrotik command='%s'", command, extra=log_extra)
            _, error_output, exit_status = self._run_command(client, command)
            if exit_status != 0:
                error_message = error_output or f"exit_status={exit_status}"
                logger.error(
                    "system-backup command failed command=%s status=%s", command, exit_status, extra=log_extra
                )
                raise MikroTikCommandError(error_message)

            logger.debug("system-backup created on device file=%s", remote_filename, extra=log_extra)

            try:
                sftp = client.open_sftp()
            except paramiko.SSHException as exc:  # pragma: no cover - network dependent
                raise MikroTikClientError("Unable to open SFTP session") from exc

            try:
                remote_stats = sftp.stat(remote_filename)
            except FileNotFoundError as exc:
                logger.error("system-backup missing file=%s", remote_filename, extra=log_extra)
                raise MikroTikCommandError(f"Backup file not found: {remote_filename}") from exc
            except OSError as exc:
                logger.error(
                    "system-backup access failed file=%s reason=\"%s\"",
                    remote_filename,
                    exc,
                    extra=log_extra,
                )
                raise MikroTikClientError("Unable to access backup file") from exc

            if remote_stats.st_size <= 0:
                logger.error("system-backup empty file=%s size=%d", remote_filename, remote_stats.st_size, extra=log_extra)
                raise MikroTikCommandError("Backup file is empty on device")

            destination.parent.mkdir(parents=True, exist_ok=True)

            try:
                sftp.get(remote_filename, str(destination))
            except (OSError, paramiko.SSHException) as exc:  # pragma: no cover - network dependent
                logger.error(
                    "system-backup download failed file=%s reason=\"%s\"",
                    remote_filename,
                    exc,
                    extra=log_extra,
                )
                raise MikroTikClientError("Unable to download system backup") from exc

            local_size = destination.stat().st_size
            if local_size <= 0:
                logger.error("system-backup saved empty path=%s size=%d", destination, local_size, extra=log_extra)
                raise MikroTikClientError("Downloaded backup file is empty")

            logger.info("system-backup saved path=%s size=%d", destination, local_size, extra=log_extra)
            return destination
        finally:
            if sftp is not None:
                sftp.close()
            client.close()
