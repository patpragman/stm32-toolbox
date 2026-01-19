"""Serial monitor with auto-reconnect."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from .errors import SerialError


@dataclass
class SerialConfig:
    port: str
    baud: int = 115200


class SerialMonitor:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self, config: SerialConfig, on_line, on_status=None) -> None:
        if self._thread and self._thread.is_alive():
            raise SerialError("Serial monitor is already running")
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(config, on_line, on_status),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self, config: SerialConfig, on_line, on_status) -> None:
        try:
            import serial
        except Exception as exc:
            raise SerialError("pyserial is not available") from exc

        while not self._stop.is_set():
            try:
                if on_status:
                    on_status(f"Connecting to {config.port} @ {config.baud}...")
                with serial.Serial(config.port, config.baud, timeout=0.2) as ser:
                    if on_status:
                        on_status("Serial connected")
                    while not self._stop.is_set():
                        data = ser.readline()
                        if data:
                            try:
                                text = data.decode("utf-8", errors="replace").rstrip("\n")
                            except Exception:
                                text = repr(data)
                            on_line(text)
            except (serial.SerialException, OSError) as exc:
                if on_status:
                    on_status(f"Serial disconnected: {exc}")
                time.sleep(0.5)
