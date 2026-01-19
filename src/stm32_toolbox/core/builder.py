"""CMake + Ninja build pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import ProcessError, ConfigError
from .util import stream_process


@dataclass(frozen=True)
class BuildConfig:
    source_dir: Path
    build_dir: Path
    build_system: str


class Builder:
    def __init__(self, config: BuildConfig) -> None:
        self.config = config

    def configure(self, on_line) -> None:
        if self.config.build_system == "Make":
            return
        cmd = [
            "cmake",
            "-S",
            str(self.config.source_dir),
            "-B",
            str(self.config.build_dir),
            "-G",
            "Ninja",
        ]
        code = stream_process(cmd, cwd=self.config.source_dir, on_line=on_line)
        if code != 0:
            raise ProcessError(cmd, code, "CMake configure failed")

    def build(self, on_line) -> None:
        if self.config.build_system == "Make":
            if not (self.config.source_dir / "Makefile").exists():
                raise ConfigError("Makefile not found in the project directory.")
            cmd = ["make"]
        else:
            cmd = [
                "cmake",
                "--build",
                str(self.config.build_dir),
            ]
        code = stream_process(cmd, cwd=self.config.source_dir, on_line=on_line)
        if code != 0:
            raise ProcessError(cmd, code, "Build failed")
