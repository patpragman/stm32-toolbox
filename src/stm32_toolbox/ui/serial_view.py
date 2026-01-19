"""Serial monitor controls and output."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .widgets import OutputText


class SerialView(ttk.Frame):
    def __init__(self, master, on_start=None, on_stop=None, **kwargs):
        super().__init__(master, **kwargs)
        ttk.Label(self, text="Serial Monitor").pack(anchor=tk.W)
        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, expand=True)

        ttk.Label(controls, text="Port").pack(side=tk.LEFT)
        self._port_combo = ttk.Combobox(controls, state="readonly", width=20)
        self._port_combo.pack(side=tk.LEFT, padx=6)

        ttk.Label(controls, text="Baud").pack(side=tk.LEFT)
        self._baud_combo = ttk.Combobox(
            controls,
            state="readonly",
            values=["9600", "38400", "57600", "115200", "230400"],
            width=10,
        )
        self._baud_combo.pack(side=tk.LEFT, padx=6)
        self._baud_combo.set("115200")

        if on_start:
            ttk.Button(controls, text="Start", command=on_start).pack(side=tk.LEFT)
        if on_stop:
            ttk.Button(controls, text="Stop", command=on_stop).pack(side=tk.LEFT, padx=4)

        self.output = OutputText(self)
        self.output.pack(fill=tk.BOTH, expand=True)

    def set_ports(self, ports: list[str]) -> None:
        self._port_combo["values"] = ports
        if ports:
            self._port_combo.current(0)

    def select_port(self, port: str) -> None:
        values = list(self._port_combo["values"])
        if port in values:
            self._port_combo.current(values.index(port))

    def get_selection(self) -> tuple[str, int]:
        port = self._port_combo.get().strip()
        baud = int(self._baud_combo.get())
        return port, baud

    def append(self, line: str) -> None:
        self.output.append(line)

    def clear(self) -> None:
        self.output.clear()
