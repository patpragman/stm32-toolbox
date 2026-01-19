"""OpenOCD flashing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .boards import BoardDefinition
from .packs import PackDefinition
from .errors import ProcessError, ConfigError
from .util import stream_process


@dataclass(frozen=True)
class FlashConfig:
    board: BoardDefinition
    pack: PackDefinition
    adapter_speed_khz: int | None = None


class Flasher:
    def __init__(self, config: FlashConfig) -> None:
        self.config = config

    def flash(self, elf_path: Path, on_line) -> None:
        board = self.config.board
        pack = self.config.pack

        interface_cfg = board.openocd.interface_cfg
        target_cfg = pack.openocd.target_cfg
        target_path = (pack.root / target_cfg).resolve() if not Path(target_cfg).is_absolute() else Path(target_cfg)

        speed = self.config.adapter_speed_khz or board.openocd.speed_khz or pack.openocd.speed_khz
        transport = board.openocd.transport or pack.openocd.transport
        transport = self._normalize_transport(transport)

        script_parts = []
        if board.openocd.reset_config:
            script_parts.extend(board.openocd.reset_config)
        script_parts.extend(
            [
                f"transport select {transport}" if transport else "",
                f"adapter speed {speed}",
                "init",
                "reset init",
                f"program {elf_path} verify reset exit",
            ]
        )
        script = "; ".join(script_parts)

        cmd = [
            "openocd",
            "-f",
            interface_cfg,
            "-f",
            str(target_path),
            "-c",
            script,
        ]
        code = stream_process(cmd, cwd=elf_path.parent, on_line=on_line)
        if code != 0:
            raise ProcessError(cmd, code, "OpenOCD flash failed")

    @staticmethod
    def _normalize_transport(value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().lower()
        if normalized in {"", "auto", "none"}:
            return None
        return value


@dataclass(frozen=True)
class MakeFlashConfig:
    project_dir: Path
    target: str = "flash"


class MakeFlasher:
    def __init__(self, config: MakeFlashConfig) -> None:
        self.config = config

    def flash(self, on_line) -> None:
        if not (self.config.project_dir / "Makefile").exists():
            raise ConfigError("Makefile not found in the project directory.")
        cmd = ["make", self.config.target]
        code = stream_process(cmd, cwd=self.config.project_dir, on_line=on_line)
        if code != 0:
            raise ProcessError(cmd, code, "Make flash failed")
