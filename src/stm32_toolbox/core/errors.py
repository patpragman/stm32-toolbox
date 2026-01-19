"""Normalized errors with hints for corrective actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ErrorDetail:
    summary: str
    action: str


class ToolboxError(Exception):
    """Base class for stm32-toolbox errors."""


class ToolNotFoundError(ToolboxError):
    def __init__(self, tool: str) -> None:
        super().__init__(f"Missing tool: {tool}")
        self.tool = tool


class ProcessError(ToolboxError):
    def __init__(self, cmd: list[str], returncode: int, output: str) -> None:
        super().__init__(f"Command failed: {' '.join(cmd)}")
        self.cmd = cmd
        self.returncode = returncode
        self.output = output


class BoardNotFoundError(ToolboxError):
    def __init__(self, board_id: str) -> None:
        super().__init__(f"Board not found: {board_id}")
        self.board_id = board_id


class PackNotFoundError(ToolboxError):
    def __init__(self, pack_id: str) -> None:
        super().__init__(f"Pack not found: {pack_id}")
        self.pack_id = pack_id


class GenerationError(ToolboxError):
    pass


class ConfigError(ToolboxError):
    pass


class SerialError(ToolboxError):
    pass


def normalize_error(exc: Exception) -> ErrorDetail:
    if isinstance(exc, ToolNotFoundError):
        return ErrorDetail(
            summary=str(exc),
            action="Install the missing tool and ensure it is on PATH.",
        )
    if isinstance(exc, PermissionError):
        return ErrorDetail(
            summary="Permission denied while accessing a device.",
            action="Add your user to the dialout group and re-login.",
        )
    if isinstance(exc, BoardNotFoundError):
        return ErrorDetail(
            summary=str(exc),
            action="Check board JSON files under boards/.",
        )
    if isinstance(exc, PackNotFoundError):
        return ErrorDetail(
            summary=str(exc),
            action="Check pack directories under packs/.",
        )
    if isinstance(exc, ProcessError):
        return ErrorDetail(
            summary=f"Command failed with exit code {exc.returncode}.",
            action="Review the command output and verify toolchain paths.",
        )
    if isinstance(exc, SerialError):
        return ErrorDetail(
            summary=str(exc),
            action="Check the serial port selection and permissions.",
        )
    return ErrorDetail(
        summary=str(exc) or exc.__class__.__name__,
        action="Review the logs for details and try again.",
    )
