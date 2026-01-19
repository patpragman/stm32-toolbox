"""Pack schema and loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .errors import PackNotFoundError
from .util import read_json, find_data_root


@dataclass(frozen=True)
class PackTemplates:
    cmakelists: str
    linker: str
    system: str
    main: str
    family_gpio: str
    startup: str
    makefile: str
    hal_h: str
    hal_gpio_h: str
    hal_gpio_c: str
    hal_clock_h: str
    hal_clock_c: str
    hal_delay_h: str
    hal_delay_c: str
    app_pins_h: str
    app_pins_c: str


@dataclass(frozen=True)
class OpenOCDDefaults:
    target_cfg: str
    transport: str = "swd"
    speed_khz: int = 4000


@dataclass(frozen=True)
class PackDefinition:
    id: str
    name: str
    cpu: str
    cmsis_strategy: str
    templates: PackTemplates
    openocd: OpenOCDDefaults
    system_clock_hz: int
    root: Path


class PackLibrary:
    def __init__(self, packs_dir: Path | None = None) -> None:
        data_root = find_data_root()
        self._packs_dir = packs_dir or (data_root / "packs")
        self._packs: Dict[str, PackDefinition] = {}
        self._load()

    @property
    def packs_dir(self) -> Path:
        return self._packs_dir

    def _load(self) -> None:
        if not self._packs_dir.exists():
            return
        for pack_dir in self._packs_dir.iterdir():
            if not pack_dir.is_dir():
                continue
            pack_json = pack_dir / "pack.json"
            if not pack_json.exists():
                continue
            data = read_json(pack_json)
            templates = PackTemplates(
                cmakelists=data["templates"]["cmakelists"],
                linker=data["templates"]["linker"],
                system=data["templates"]["system"],
                main=data["templates"]["main"],
                family_gpio=data["templates"]["family_gpio"],
                startup=data["templates"]["startup"],
                makefile=data["templates"]["makefile"],
                hal_h=data["templates"]["hal_h"],
                hal_gpio_h=data["templates"]["hal_gpio_h"],
                hal_gpio_c=data["templates"]["hal_gpio_c"],
                hal_clock_h=data["templates"]["hal_clock_h"],
                hal_clock_c=data["templates"]["hal_clock_c"],
                hal_delay_h=data["templates"]["hal_delay_h"],
                hal_delay_c=data["templates"]["hal_delay_c"],
                app_pins_h=data["templates"]["app_pins_h"],
                app_pins_c=data["templates"]["app_pins_c"],
            )
            openocd = OpenOCDDefaults(
                target_cfg=data["openocd"]["target_cfg"],
                transport=data["openocd"].get("transport", "swd"),
                speed_khz=int(data["openocd"].get("speed_khz", 4000)),
            )
            pack = PackDefinition(
                id=data["id"],
                name=data.get("name", data["id"]),
                cpu=data["cpu"],
                cmsis_strategy=data["cmsis"]["strategy"],
                templates=templates,
                openocd=openocd,
                system_clock_hz=int(data.get("defaults", {}).get("system_clock_hz", 0)),
                root=pack_dir,
            )
            self._packs[pack.id] = pack

    def list(self) -> list[PackDefinition]:
        return list(self._packs.values())

    def get(self, pack_id: str) -> PackDefinition:
        if pack_id not in self._packs:
            raise PackNotFoundError(pack_id)
        return self._packs[pack_id]
