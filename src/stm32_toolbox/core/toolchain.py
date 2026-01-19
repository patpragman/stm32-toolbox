"""Toolchain discovery and environment checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from .errors import ToolNotFoundError


@dataclass(frozen=True)
class ToolchainStatus:
    arm_none_eabi_gcc: str | None
    arm_none_eabi_objcopy: str | None
    cmake: str | None
    ninja: str | None
    openocd: str | None
    cubeprog: str | None


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def detect_tools() -> ToolchainStatus:
    return ToolchainStatus(
        arm_none_eabi_gcc=_which("arm-none-eabi-gcc"),
        arm_none_eabi_objcopy=_which("arm-none-eabi-objcopy"),
        cmake=_which("cmake"),
        ninja=_which("ninja"),
        openocd=_which("openocd"),
        cubeprog=_which("STM32_Programmer_CLI"),
    )


def require_tools(status: ToolchainStatus) -> None:
    missing = []
    if not status.arm_none_eabi_gcc:
        missing.append("arm-none-eabi-gcc")
    if not status.arm_none_eabi_objcopy:
        missing.append("arm-none-eabi-objcopy")
    if not status.cmake:
        missing.append("cmake")
    if not status.ninja:
        missing.append("ninja")
    if not status.openocd:
        missing.append("openocd")
    if missing:
        raise ToolNotFoundError(", ".join(missing)
        )
