"""Best-effort probe discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SerialPortInfo:
    device: str
    description: str
    hwid: str
    vid: int | None
    pid: int | None


def list_serial_ports() -> list[SerialPortInfo]:
    ports: list[SerialPortInfo] = []
    try:
        from serial.tools import list_ports
    except Exception:
        return ports

    for port in list_ports.comports():
        ports.append(
            SerialPortInfo(
                device=port.device,
                description=port.description or "",
                hwid=port.hwid or "",
                vid=port.vid,
                pid=port.pid,
            )
        )
    return ports


def prefer_stlink(ports: Iterable[SerialPortInfo]) -> list[SerialPortInfo]:
    def key(item: SerialPortInfo) -> tuple[int, str]:
        score = 0
        if item.vid == 0x0483:
            score = -1
        return (score, item.device)

    return sorted(list(ports), key=key)
