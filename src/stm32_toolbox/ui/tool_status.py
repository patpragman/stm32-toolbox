"""Tool status panel."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ToolStatusView(ttk.LabelFrame):
    def __init__(self, master, on_refresh=None, **kwargs):
        super().__init__(master, text="Tool Status", padding=8, **kwargs)
        self._labels: dict[str, ttk.Label] = {}
        self._rows: list[tuple[str, str]] = []

        if on_refresh:
            ttk.Button(self, text="Refresh", command=on_refresh).grid(
                row=0,
                column=0,
                columnspan=2,
                sticky=tk.E,
                pady=(0, 6),
            )
            start_row = 1
        else:
            start_row = 0

        self._rows = [
            ("arm-none-eabi-gcc", "arm_none_eabi_gcc"),
            ("arm-none-eabi-objcopy", "arm_none_eabi_objcopy"),
            ("cmake", "cmake"),
            ("ninja", "ninja"),
            ("make", "make"),
            ("openocd", "openocd"),
        ]

        for idx, (label, field) in enumerate(self._rows, start=start_row):
            ttk.Label(self, text=label).grid(row=idx, column=0, sticky=tk.W)
            value = ttk.Label(self, text="Unknown")
            value.grid(row=idx, column=1, sticky=tk.E)
            self._labels[field] = value

        self.columnconfigure(0, weight=1)

    def set_status(self, status) -> None:
        for _label, field in self._rows:
            value = getattr(status, field, None)
            self._labels[field].configure(text="OK" if value else "Missing")
