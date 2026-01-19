"""Toolchain discovery and environment checks."""

from __future__ import annotations

from dataclasses import dataclass
import shutil

from .errors import ToolNotFoundError


@dataclass(frozen=True)
class ToolchainStatus:
    arm_none_eabi_gcc: str | None
    arm_none_eabi_objcopy: str | None
    cmake: str | None
    ninja: str | None
    make: str | None
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
        make=_which("make"),
        openocd=_which("openocd"),
        cubeprog=_which("STM32_Programmer_CLI"),
    )

BUILD_SYSTEM_CMAKE = "CMake/Ninja"
BUILD_SYSTEM_MAKE = "Make"


def require_tools(status: ToolchainStatus, required: tuple[str, ...]) -> None:
    missing = [name for name in required if getattr(status, name) is None]
    if missing:
        raise ToolNotFoundError(", ".join(missing))


def require_build_tools(
    status: ToolchainStatus,
    build_system: str,
    needs_cmake: bool = False,
) -> None:
    if build_system == BUILD_SYSTEM_MAKE:
        required = ["make", "arm_none_eabi_gcc", "arm_none_eabi_objcopy"]
        if needs_cmake:
            required.extend(["cmake", "ninja"])
        require_tools(status, tuple(required))
        return
    require_tools(status, ("arm_none_eabi_gcc", "arm_none_eabi_objcopy", "cmake", "ninja"))


def require_flash_tools(
    status: ToolchainStatus,
    build_system: str,
    needs_openocd: bool = False,
) -> None:
    if build_system == BUILD_SYSTEM_MAKE:
        required = ["make"]
        if needs_openocd:
            required.append("openocd")
        require_tools(status, tuple(required))
        return
    require_tools(status, ("openocd",))
