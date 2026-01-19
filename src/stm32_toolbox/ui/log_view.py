"""Log output view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .widgets import OutputText


class LogView(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        ttk.Label(self, text="Build / Flash Log").pack(anchor=tk.W)
        self.output = OutputText(self)
        self.output.pack(fill=tk.BOTH, expand=True)

    def append(self, line: str) -> None:
        self.output.append(line)

    def clear(self) -> None:
        self.output.clear()
