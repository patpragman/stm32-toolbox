"""Board selection widget."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class BoardSelect(ttk.Frame):
    def __init__(self, master, on_change=None, **kwargs):
        super().__init__(master, **kwargs)
        ttk.Label(self, text="Board").pack(anchor=tk.W)
        self._combo = ttk.Combobox(self, state="readonly")
        self._combo.pack(fill=tk.X, expand=True)
        self._boards = []
        if on_change:
            self._combo.bind("<<ComboboxSelected>>", lambda _evt: on_change())

    def set_boards(self, boards) -> None:
        self._boards = boards
        names = [f"{b.name} ({b.id})" for b in boards]
        self._combo["values"] = names
        if names:
            self._combo.current(0)

    def get_selected_id(self) -> str:
        idx = self._combo.current()
        if idx < 0 or idx >= len(self._boards):
            return ""
        return self._boards[idx].id
