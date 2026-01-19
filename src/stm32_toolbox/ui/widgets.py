"""Reusable Tkinter widgets."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


class LabeledEntry(ttk.Frame):
    def __init__(self, master, label: str, textvariable=None, width: int = 40, **kwargs):
        super().__init__(master, **kwargs)
        ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0, 6))
        self.entry = ttk.Entry(self, textvariable=textvariable, width=width)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)


class OutputText(ScrolledText):
    def __init__(self, master, **kwargs):
        super().__init__(master, height=12, wrap=tk.WORD, **kwargs)
        self.configure(state=tk.DISABLED)

    def append(self, line: str) -> None:
        self.configure(state=tk.NORMAL)
        self.insert(tk.END, line + "\n")
        self.see(tk.END)
        self.configure(state=tk.DISABLED)

    def clear(self) -> None:
        self.configure(state=tk.NORMAL)
        self.delete("1.0", tk.END)
        self.configure(state=tk.DISABLED)
