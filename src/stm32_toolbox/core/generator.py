"""Project generation engine."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import shutil

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
        led_alias: str | None = None,
    ) -> Path:
        try:
            ensure_dir(self.output_dir)
            (self.output_dir / "cmake").mkdir(exist_ok=True)
            (self.output_dir / "out").mkdir(exist_ok=True)
            (self.output_dir / "build").mkdir(exist_ok=True)
        except OSError as exc:
            raise GenerationError(f"Unable to create output directories: {exc}") from exc

        normalized_pins = self._normalize_pins(board, pins or [], led_alias)
        context = self._build_context(board, pack, normalized_pins)
        templates_dir = pack.root / "templates"
        env = jinja_env(templates_dir)

        self._render(env, pack.templates.cmakelists, "CMakeLists.txt", context)
        self._render(env, pack.templates.linker, "linker.ld", context)
        self._render(env, pack.templates.system, "system.c", context)
        self._render(env, pack.templates.main, "main.c", context)
        self._render(env, pack.templates.family_gpio, "family_gpio.h", context)
        self._render(env, pack.templates.makefile, "Makefile", context)
        self._render(env, pack.templates.hal_h, "hal.h", context)
        self._render(env, pack.templates.hal_gpio_h, "hal_gpio.h", context)
        self._render(env, pack.templates.hal_gpio_c, "hal_gpio.c", context)
        self._render(env, pack.templates.hal_clock_h, "hal_clock.h", context)
        self._render(env, pack.templates.hal_clock_c, "hal_clock.c", context)
        self._render(env, pack.templates.hal_delay_h, "hal_delay.h", context)
        self._render(env, pack.templates.hal_delay_c, "hal_delay.c", context)
        self._render(env, pack.templates.hal_uart_h, "hal_uart.h", context)
        self._render(env, pack.templates.hal_uart_c, "hal_uart.c", context)
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

        openocd_dir = self.output_dir / "openocd"
        ensure_dir(openocd_dir)
        target_src = Path(pack.openocd.target_cfg)
        if not target_src.is_absolute():
            target_src = pack.root / target_src
        target_dst = openocd_dir / "target.cfg"
        try:
            shutil.copyfile(target_src, target_dst)
        except OSError as exc:
            raise GenerationError(f"Unable to copy OpenOCD target config: {exc}") from exc

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
                    "reserved": pin.get("reserved", False),
                    "reserved_reason": pin.get("reserved_reason", ""),
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
        led_enum_name = "APP_PIN_LED"
        for pin in pins:
            if pin.get("is_led"):
                led_enum_name = pin["enum_name"]
                break
        button_enum_name = ProjectGenerator._find_button_enum(pins)
        openocd_speed = board.openocd.speed_khz or pack.openocd.speed_khz
        openocd_transport = board.openocd.transport or pack.openocd.transport
        openocd_transport = ProjectGenerator._normalize_transport(openocd_transport)
        openocd_reset = ""
        if board.openocd.reset_config:
            openocd_reset = "; ".join(board.openocd.reset_config)
        openocd_commands = "; ".join(
            part
            for part in [
                openocd_reset,
                f"transport select {openocd_transport}" if openocd_transport else "",
                f"adapter speed {openocd_speed}",
                "init",
                "reset init",
                "program $(ELF) verify",
                "reset run",
                "exit",
            ]
            if part
        )
        serial = asdict(board.serial) if board.serial else None
        serial_baud = board.serial.baud if board.serial else 115200

        return {
            "board": asdict(board),
            "pack": asdict(pack),
            "serial": serial,
            "serial_enabled": bool(serial),
            "serial_baud": serial_baud,
            "flash_origin": f"0x{board.flash.origin:08X}",
            "flash_length": f"0x{board.flash.length:X}",
            "ram_origin": f"0x{board.ram.origin:08X}",
            "ram_length": f"0x{board.ram.length:X}",
            "led_port": board.led.port,
            "led_pin": board.led.pin,
            "led_active_high": board.led.active_high,
            "system_clock_hz": pack.system_clock_hz,
            "led_enum_name": led_enum_name,
            "button_enum_name": button_enum_name or "",
            "button_present": bool(button_enum_name),
            "pins": pins,
            "project_name": board.id,
            "openocd_interface_cfg": board.openocd.interface_cfg,
            "openocd_target_cfg": "openocd/target.cfg",
            "openocd_commands": openocd_commands,
        }

    @staticmethod
    def _normalize_transport(value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().lower()
        if normalized in {"", "auto", "none"}:
            return None
        return value

    @staticmethod
    def _normalize_pins(
        board: BoardDefinition,
        pins: list[dict],
        led_alias: str | None,
    ) -> list[dict]:
        normalized: list[dict] = []
        name_to_index: dict[str, int] = {}
        locations = set()
        led_location = (board.led.port, board.led.pin)
        led_alias = (led_alias or board.led.name or "LED").strip() or "LED"
        reserved_lookup = {
            (pin.port.upper(), pin.pin): pin.reason for pin in board.reserved_pins or []
        }

        def add_pin(entry: dict) -> int:
            name = entry.get("name", "").strip()
            if not name:
                raise GenerationError("Pin name is required.")
            safe = ProjectGenerator._to_identifier(name)
            enum_name = f"APP_PIN_{safe}"

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
            reserved = bool(entry.get("reserved", False)) or (port, pin) in reserved_lookup
            reserved_reason = reserved_lookup.get((port, pin), "")

            location = (port, pin)
            if location in locations:
                raise GenerationError(f"Duplicate GPIO pin: P{port}{pin}")
            locations.add(location)

            is_led = location == led_location

            if enum_name in name_to_index:
                if is_led:
                    conflict_index = name_to_index[enum_name]
                    new_enum = ProjectGenerator._unique_enum(enum_name, name_to_index)
                    normalized[conflict_index]["enum_name"] = new_enum
                    name_to_index[new_enum] = conflict_index
                    name_to_index.pop(enum_name, None)
                else:
                    enum_name = ProjectGenerator._unique_enum(enum_name, name_to_index)

            entry = {
                "name": name,
                "enum_name": enum_name,
                "port": port,
                "pin": pin,
                "mode": "output" if is_led else mode,
                "pull": "none" if is_led else pull,
                "initial": "low" if is_led else initial,
                "active_high": board.led.active_high if is_led else active_high,
                "port_enum": f"HAL_PORT_{port}",
                "mode_enum": "HAL_GPIO_MODE_OUTPUT"
                if (is_led or mode == "output")
                else "HAL_GPIO_MODE_INPUT",
                "pull_enum": "HAL_GPIO_PULL_NONE"
                if is_led
                else {
                    "none": "HAL_GPIO_PULL_NONE",
                    "up": "HAL_GPIO_PULL_UP",
                    "down": "HAL_GPIO_PULL_DOWN",
                }[pull],
                "initial_high": False if is_led else initial == "high",
                "is_led": is_led,
                "reserved": reserved,
                "reserved_reason": reserved_reason,
                "skip_init": reserved and not is_led,
            }
            normalized.append(entry)
            name_to_index[enum_name] = len(normalized) - 1
            return len(normalized) - 1

        for entry in pins:
            add_pin(entry)

        led_index = next(
            (idx for idx, pin in enumerate(normalized) if pin.get("is_led")), None
        )

        if led_index is None:
            add_pin(
                {
                    "name": led_alias,
                    "port": board.led.port,
                    "pin": board.led.pin,
                    "mode": "output",
                    "pull": "none",
                    "initial": "low",
                    "active_high": board.led.active_high,
                }
            )
        else:
            desired_enum = f"APP_PIN_{ProjectGenerator._to_identifier(led_alias)}"
            current_enum = normalized[led_index]["enum_name"]
            if desired_enum != current_enum:
                if desired_enum in name_to_index and name_to_index[desired_enum] != led_index:
                    conflict_index = name_to_index[desired_enum]
                    new_enum = ProjectGenerator._unique_enum(desired_enum, name_to_index)
                    normalized[conflict_index]["enum_name"] = new_enum
                    name_to_index[new_enum] = conflict_index
                name_to_index.pop(current_enum, None)
                normalized[led_index]["enum_name"] = desired_enum
                name_to_index[desired_enum] = led_index
            normalized[led_index]["name"] = led_alias

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

    @staticmethod
    def _unique_enum(base: str, existing: dict[str, int]) -> str:
        counter = 2
        candidate = f"{base}_{counter}"
        while candidate in existing:
            counter += 1
            candidate = f"{base}_{counter}"
        return candidate

    @staticmethod
    def _find_button_enum(pins: list[dict]) -> str | None:
        button_names = {
            "B1",
            "USER_BUTTON",
            "USER_BTN",
            "BUTTON",
            "BTN",
            "SW1",
            "SW",
        }
        for pin in pins:
            name = str(pin.get("name", "")).strip().upper().replace(" ", "_")
            enum_name = str(pin.get("enum_name", "")).upper().replace("APP_PIN_", "")
            if name in button_names or enum_name in button_names:
                return pin.get("enum_name")
        return None
