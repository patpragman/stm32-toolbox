"""Project generation engine."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
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

    def generate(
        self,
        board: BoardDefinition,
        pack: PackDefinition,
        pins: list[dict] | None = None,
    ) -> Path:
        try:
            ensure_dir(self.output_dir)
            (self.output_dir / "cmake").mkdir(exist_ok=True)
            (self.output_dir / "out").mkdir(exist_ok=True)
            (self.output_dir / "build").mkdir(exist_ok=True)
        except OSError as exc:
            raise GenerationError(f"Unable to create output directories: {exc}") from exc

        normalized_pins = self._normalize_pins(board, pins or [])
        context = self._build_context(board, pack, normalized_pins)
        templates_dir = pack.root / "templates"
        env = jinja_env(templates_dir)

        self._render(env, pack.templates.cmakelists, "CMakeLists.txt", context)
        self._render(env, pack.templates.linker, "linker.ld", context)
        self._render(env, pack.templates.system, "system.c", context)
        self._render(env, pack.templates.main, "main.c", context)
        self._render(env, pack.templates.family_gpio, "family_gpio.h", context)
        self._render(env, pack.templates.hal_h, "hal.h", context)
        self._render(env, pack.templates.hal_gpio_h, "hal_gpio.h", context)
        self._render(env, pack.templates.hal_gpio_c, "hal_gpio.c", context)
        self._render(env, pack.templates.hal_clock_h, "hal_clock.h", context)
        self._render(env, pack.templates.hal_clock_c, "hal_clock.c", context)
        self._render(env, pack.templates.hal_delay_h, "hal_delay.h", context)
        self._render(env, pack.templates.hal_delay_c, "hal_delay.c", context)
        self._render(env, pack.templates.app_pins_h, "app_pins.h", context)
        self._render(env, pack.templates.app_pins_c, "app_pins.c", context)

        startup_src = templates_dir / pack.templates.startup
        if not startup_src.exists():
            raise GenerationError(f"Startup file not found: {startup_src}")
        (self.output_dir / "startup_gcc.s").write_text(
            startup_src.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        toolchain_path = self.output_dir / "cmake" / "toolchain-arm-none-eabi.cmake"
        atomic_write(toolchain_path, TOOLCHAIN_CMAKE)

        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        manifest = {
            "generated_at": generated_at,
            "board": board.id,
            "pack": pack.id,
            "mcu": board.mcu,
            "output_dir": str(self.output_dir.resolve()),
            "toolchain": "arm-none-eabi",
            "pins": [
                {
                    "name": pin["name"],
                    "port": pin["port"],
                    "pin": pin["pin"],
                    "mode": pin["mode"],
                    "pull": pin["pull"],
                    "initial": pin["initial"],
                    "active_high": pin["active_high"],
                }
                for pin in normalized_pins
            ],
        }
        write_json(self.output_dir / "stm32toolbox.project.json", manifest)
        return self.output_dir

    def _render(self, env, template_name: str, output_name: str, context: dict) -> None:
        template = env.get_template(template_name)
        content = template.render(**context)
        atomic_write(self.output_dir / output_name, content)

    @staticmethod
    def _build_context(
        board: BoardDefinition,
        pack: PackDefinition,
        pins: list[dict],
    ) -> dict:
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
            "system_clock_hz": pack.system_clock_hz,
            "pins": pins,
        }

    @staticmethod
    def _normalize_pins(board: BoardDefinition, pins: list[dict]) -> list[dict]:
        normalized = []
        names = set()

        def add_pin(entry: dict) -> None:
            name = entry.get("name", "").strip()
            if not name:
                raise GenerationError("Pin name is required.")
            safe = ProjectGenerator._to_identifier(name)
            enum_name = f"APP_PIN_{safe}"
            if enum_name in names:
                raise GenerationError(f"Duplicate pin name: {name}")
            names.add(enum_name)

            port = str(entry.get("port", "")).upper()
            if port not in {"A", "B", "C", "D", "E", "F", "G", "H"}:
                raise GenerationError(f"Invalid GPIO port: {port}")

            pin = int(entry.get("pin", 0))
            if pin < 0 or pin > 15:
                raise GenerationError(f"Invalid GPIO pin: {pin}")

            mode = str(entry.get("mode", "output")).lower()
            if mode not in {"input", "output"}:
                raise GenerationError(f"Invalid GPIO mode: {mode}")

            pull = str(entry.get("pull", "none")).lower()
            if pull not in {"none", "up", "down"}:
                raise GenerationError(f"Invalid GPIO pull: {pull}")

            initial = str(entry.get("initial", "low")).lower()
            if initial not in {"low", "high"}:
                raise GenerationError(f"Invalid GPIO initial: {initial}")

            active_high = bool(entry.get("active_high", True))

            normalized.append(
                {
                    "name": name,
                    "enum_name": enum_name,
                    "port": port,
                    "pin": pin,
                    "mode": mode,
                    "pull": pull,
                    "initial": initial,
                    "active_high": active_high,
                    "port_enum": f"HAL_PORT_{port}",
                    "mode_enum": "HAL_GPIO_MODE_OUTPUT"
                    if mode == "output"
                    else "HAL_GPIO_MODE_INPUT",
                    "pull_enum": {
                        "none": "HAL_GPIO_PULL_NONE",
                        "up": "HAL_GPIO_PULL_UP",
                        "down": "HAL_GPIO_PULL_DOWN",
                    }[pull],
                    "initial_high": initial == "high",
                }
            )

        add_pin(
            {
                "name": "led",
                "port": board.led.port,
                "pin": board.led.pin,
                "mode": "output",
                "pull": "none",
                "initial": "low",
                "active_high": board.led.active_high,
            }
        )

        for entry in pins:
            add_pin(entry)

        return normalized

    @staticmethod
    def _to_identifier(value: str) -> str:
        cleaned = []
        for ch in value.upper():
            if ch.isalnum():
                cleaned.append(ch)
            else:
                cleaned.append("_")
        name = "".join(cleaned).strip("_")
        if not name:
            name = "PIN"
        if name[0].isdigit():
            name = f"PIN_{name}"
        return name
