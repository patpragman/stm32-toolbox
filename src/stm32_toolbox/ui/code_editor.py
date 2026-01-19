"""Simple dark-mode code editor for main.c."""

from __future__ import annotations

from pathlib import Path
import re
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont


class CodeEditorView(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._path: Path | None = None
        self._highlight_after: str | None = None

        header = ttk.Frame(self)
        header.pack(fill=tk.X)
        self._path_label = ttk.Label(header, text="main.c (not loaded)")
        self._path_label.pack(side=tk.LEFT)
        ttk.Button(header, text="Reload", command=self.reload).pack(side=tk.RIGHT)
        ttk.Button(header, text="Save", command=self.save).pack(side=tk.RIGHT, padx=6)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        self.text = tk.Text(
            body,
            wrap=tk.NONE,
            undo=True,
            background="#1e1e1e",
            foreground="#d4d4d4",
            insertbackground="#d4d4d4",
            selectbackground="#264f78",
        )
        fixed_font = tkfont.nametofont("TkFixedFont")
        fixed_font.configure(size=11)
        self.text.configure(font=fixed_font)

        scroll_y = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.text.yview)
        scroll_x = ttk.Scrollbar(body, orient=tk.HORIZONTAL, command=self.text.xview)
        self.text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.text.grid(row=0, column=0, sticky=tk.NSEW)
        scroll_y.grid(row=0, column=1, sticky=tk.NS)
        scroll_x.grid(row=1, column=0, sticky=tk.EW)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self._configure_tags()
        self.text.bind("<KeyRelease>", self._on_change)
        self.text.bind("<ButtonRelease>", self._on_change)

    def _configure_tags(self) -> None:
        self.text.tag_configure("keyword", foreground="#569cd6")
        self.text.tag_configure("type", foreground="#4ec9b0")
        self.text.tag_configure("string", foreground="#ce9178")
        self.text.tag_configure("comment", foreground="#6a9955")
        self.text.tag_configure("number", foreground="#b5cea8")

    def set_path(self, path: Path | None) -> None:
        self._path = path
        if path:
            self._path_label.configure(text=f"main.c ({path})")
        else:
            self._path_label.configure(text="main.c (not loaded)")

    def get_path(self) -> Path | None:
        return self._path

    def load_file(self, path: Path) -> None:
        self.set_path(path)
        if not path.exists():
            self.text.delete("1.0", tk.END)
            self.text.edit_modified(False)
            self._schedule_highlight()
            return
        content = path.read_text(encoding="utf-8")
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.text.edit_modified(False)
        self._schedule_highlight()

    def reload(self) -> None:
        if not self._path:
            messagebox.showinfo("No file", "Generate a project to load main.c.")
            return
        if self.text.edit_modified():
            if not messagebox.askyesno(
                "Discard changes",
                "Discard unsaved changes and reload main.c?",
            ):
                return
        self.load_file(self._path)

    def save(self) -> bool:
        if not self._path:
            messagebox.showinfo("No file", "Generate a project to save main.c.")
            return False
        try:
            self._path.write_text(self.text.get("1.0", "end-1c"), encoding="utf-8")
            self.text.edit_modified(False)
            return True
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
            return False

    def has_unsaved_changes(self) -> bool:
        return bool(self.text.edit_modified())

    def save_if_dirty(self) -> bool:
        if not self.has_unsaved_changes():
            return True
        if messagebox.askyesno("Unsaved changes", "Save main.c before proceeding?"):
            return self.save()
        return True

    def _on_change(self, _event=None) -> None:
        self._schedule_highlight()

    def _schedule_highlight(self) -> None:
        if self._highlight_after:
            self.after_cancel(self._highlight_after)
        self._highlight_after = self.after(150, self._highlight)

    def _highlight(self) -> None:
        self._highlight_after = None
        text = self.text.get("1.0", "end-1c")
        for tag in ("keyword", "type", "string", "comment", "number"):
            self.text.tag_remove(tag, "1.0", tk.END)

        comment_pattern = r"//.*?$|/\*.*?\*/"
        string_pattern = r"\"(\\.|[^\"])*\"|'(\\.|[^'])*'"
        number_pattern = r"\b0x[0-9A-Fa-f]+\b|\b\d+\b"
        keyword_pattern = (
            r"\b(auto|break|case|char|const|continue|default|do|double|else|enum|"
            r"extern|float|for|goto|if|inline|int|long|register|restrict|return|short|"
            r"signed|sizeof|static|struct|switch|typedef|union|unsigned|void|volatile|"
            r"while|_Bool|_Complex|_Imaginary)\b"
        )
        type_pattern = r"\b(uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t|size_t|bool)\b"

        for match in re.finditer(comment_pattern, text, re.MULTILINE | re.DOTALL):
            self._tag_span("comment", match.start(), match.end())
        for match in re.finditer(string_pattern, text):
            self._tag_span("string", match.start(), match.end())
        for match in re.finditer(keyword_pattern, text):
            self._tag_span("keyword", match.start(), match.end())
        for match in re.finditer(type_pattern, text):
            self._tag_span("type", match.start(), match.end())
        for match in re.finditer(number_pattern, text):
            self._tag_span("number", match.start(), match.end())

        self.text.tag_raise("comment")
        self.text.tag_raise("string")

    def _tag_span(self, tag: str, start: int, end: int) -> None:
        self.text.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")
