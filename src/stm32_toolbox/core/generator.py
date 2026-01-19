"""Project generation engine."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .boards import BoardDefinition
from .packs import PackDefinition
from .errors import GenerationError
from .util import ensure_dir, jinja_env, atomic_write, write_json


TOOLCHAIN_CMAKE = """
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR ARM)

set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

set(TOOLCHAIN_PREFIX arm-none-eabi-)

set(CMAKE_C_COMPILER ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_ASM_COMPILER ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_OBJCOPY ${TOOLCHAIN_PREFIX}objcopy)
set(CMAKE_SIZE ${TOOLCHAIN_PREFIX}size)

set(CMAKE_C_FLAGS_INIT "-Wall -Wextra -Werror -ffunction-sections -fdata-sections")
set(CMAKE_EXE_LINKER_FLAGS_INIT "-Wl,--gc-sections")
""".lstrip()


class ProjectGenerator:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def generate(self, board: BoardDefinition, pack: PackDefinition) -> Path:
        try:
            ensure_dir(self.output_dir)
            (self.output_dir / "cmake").mkdir(exist_ok=True)
            (self.output_dir / "out").mkdir(exist_ok=True)
            (self.output_dir / "build").mkdir(exist_ok=True)
        except OSError as exc:
            raise GenerationError(f"Unable to create output directories: {exc}") from exc

        context = self._build_context(board, pack)
        templates_dir = pack.root / "templates"
        env = jinja_env(templates_dir)

        self._render(env, pack.templates.cmakelists, "CMakeLists.txt", context)
        self._render(env, pack.templates.linker, "linker.ld", context)
        self._render(env, pack.templates.system, "system.c", context)
        self._render(env, pack.templates.main, "main.c", context)
        self._render(env, pack.templates.family_gpio, "family_gpio.h", context)

        startup_src = templates_dir / pack.templates.startup
        if not startup_src.exists():
            raise GenerationError(f"Startup file not found: {startup_src}")
        (self.output_dir / "startup_gcc.s").write_text(
            startup_src.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        toolchain_path = self.output_dir / "cmake" / "toolchain-arm-none-eabi.cmake"
        atomic_write(toolchain_path, TOOLCHAIN_CMAKE)

        manifest = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "board": board.id,
            "pack": pack.id,
            "mcu": board.mcu,
            "output_dir": str(self.output_dir.resolve()),
            "toolchain": "arm-none-eabi",
        }
        write_json(self.output_dir / "stm32toolbox.project.json", manifest)
        return self.output_dir

    def _render(self, env, template_name: str, output_name: str, context: dict) -> None:
        template = env.get_template(template_name)
        content = template.render(**context)
        atomic_write(self.output_dir / output_name, content)

    @staticmethod
    def _build_context(board: BoardDefinition, pack: PackDefinition) -> dict:
        return {
            "board": asdict(board),
            "pack": asdict(pack),
            "flash_origin": f"0x{board.flash.origin:08X}",
            "flash_length": f"0x{board.flash.length:X}",
            "ram_origin": f"0x{board.ram.origin:08X}",
            "ram_length": f"0x{board.ram.length:X}",
            "led_port": board.led.port,
            "led_pin": board.led.pin,
            "led_active_high": board.led.active_high,
        }
