"""Project generation panel."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog

from .widgets import LabeledEntry


class ProjectWizard(ttk.Frame):
    def __init__(self, master, on_generate=None, on_select=None, **kwargs):
        super().__init__(master, **kwargs)
        ttk.Label(self, text="Project").pack(anchor=tk.W)
        self._path_var = tk.StringVar()
        self._on_select = on_select
        row = ttk.Frame(self)
        row.pack(fill=tk.X, expand=True)
        LabeledEntry(row, "Directory", textvariable=self._path_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(row, text="Browse", command=self._browse).pack(side=tk.LEFT, padx=6)
        if on_generate:
            ttk.Button(self, text="Generate Project", command=on_generate).pack(
                anchor=tk.W, pady=(6, 0)
            )

    def _browse(self) -> None:
        path = filedialog.askdirectory(mustexist=False)
        if path:
            self._path_var.set(path)
            if self._on_select:
                self._on_select(path)

    def get_project_dir(self) -> str:
        return self._path_var.get().strip()

    def set_project_dir(self, path: str) -> None:
        self._path_var.set(path)
