"""Board schema and loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .errors import BoardNotFoundError
from .util import read_json, find_data_root


@dataclass(frozen=True)
class MemoryRegion:
    origin: int
    length: int


@dataclass(frozen=True)
class LedDefinition:
    name: str
    port: str
    pin: int
    active_high: bool = True


@dataclass(frozen=True)
class ReservedPinDefinition:
    port: str
    pin: int
    reason: str = ""


@dataclass(frozen=True)
class SerialPinDefinition:
    port: str
    pin: int
    af: int


@dataclass(frozen=True)
class SerialDefinition:
    usart: str
    tx: SerialPinDefinition
    rx: SerialPinDefinition
    baud: int = 115200


@dataclass(frozen=True)
class OpenOCDBoardConfig:
    interface_cfg: str
    transport: str = "swd"
    speed_khz: int = 4000
    reset_config: list[str] | None = None


@dataclass(frozen=True)
class BoardDefinition:
    id: str
    name: str
    pack: str
    mcu: str
    flash: MemoryRegion
    ram: MemoryRegion
    led: LedDefinition
    serial: SerialDefinition | None
    reserved_pins: list[ReservedPinDefinition]
    openocd: OpenOCDBoardConfig
    gpio_ports: list[str] | None
    root: Path


class BoardLibrary:
    def __init__(self, boards_dir: Path | None = None) -> None:
        data_root = find_data_root()
        self._boards_dir = boards_dir or (data_root / "boards")
        self._boards: Dict[str, BoardDefinition] = {}
        self._load()

    @property
    def boards_dir(self) -> Path:
        return self._boards_dir

    def _load(self) -> None:
        if not self._boards_dir.exists():
            return
        for board_path in self._boards_dir.glob("*.json"):
            data = read_json(board_path)
            flash = MemoryRegion(
                origin=int(data["memory"]["flash"]["origin"], 0),
                length=int(data["memory"]["flash"]["length"], 0),
            )
            ram = MemoryRegion(
                origin=int(data["memory"]["ram"]["origin"], 0),
                length=int(data["memory"]["ram"]["length"], 0),
            )
            led = LedDefinition(
                name=str(data["led"].get("name", "LED")),
                port=data["led"]["port"],
                pin=int(data["led"]["pin"]),
                active_high=bool(data["led"].get("active_high", True)),
            )
            reserved_pins = []
            for entry in data.get("reserved_pins", []):
                reserved_pins.append(
                    ReservedPinDefinition(
                        port=str(entry["port"]).upper(),
                        pin=int(entry["pin"]),
                        reason=str(entry.get("reason", "")),
                    )
                )
            serial = None
            if data.get("serial"):
                serial_data = data["serial"]
                serial = SerialDefinition(
                    usart=str(serial_data["usart"]).upper(),
                    baud=int(serial_data.get("baud", 115200)),
                    tx=SerialPinDefinition(
                        port=str(serial_data["tx"]["port"]).upper(),
                        pin=int(serial_data["tx"]["pin"]),
                        af=int(serial_data["tx"]["af"]),
                    ),
                    rx=SerialPinDefinition(
                        port=str(serial_data["rx"]["port"]).upper(),
                        pin=int(serial_data["rx"]["pin"]),
                        af=int(serial_data["rx"]["af"]),
                    ),
                )
            openocd = OpenOCDBoardConfig(
                interface_cfg=data["openocd"]["interface_cfg"],
                transport=data["openocd"].get("transport", "swd"),
                speed_khz=int(data["openocd"].get("speed_khz", 4000)),
                reset_config=data["openocd"].get("reset_config"),
            )
            gpio_ports = data.get("gpio_ports")
            if gpio_ports:
                gpio_ports = [str(port).upper() for port in gpio_ports]

            board = BoardDefinition(
                id=data["id"],
                name=data.get("name", data["id"]),
                pack=data["pack"],
                mcu=data.get("mcu", ""),
                flash=flash,
                ram=ram,
                led=led,
                serial=serial,
                reserved_pins=reserved_pins,
                openocd=openocd,
                gpio_ports=gpio_ports,
                root=board_path.parent,
            )
            self._boards[board.id] = board

    def list(self) -> list[BoardDefinition]:
        return list(self._boards.values())

    def get(self, board_id: str) -> BoardDefinition:
        if board_id not in self._boards:
            raise BoardNotFoundError(board_id)
        return self._boards[board_id]
