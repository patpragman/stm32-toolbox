"""GPIO pin configuration panel."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox


class PinDialog(tk.Toplevel):
    def __init__(self, master) -> None:
        super().__init__(master)
        self.title("Add GPIO Pin")
        self.resizable(False, False)
        self.result = None

        self._name_var = tk.StringVar()
        self._port_var = tk.StringVar(value="A")
        self._pin_var = tk.StringVar(value="0")
        self._mode_var = tk.StringVar(value="output")
        self._pull_var = tk.StringVar(value="none")
        self._initial_var = tk.StringVar(value="low")
        self._active_high_var = tk.BooleanVar(value=True)

        form = ttk.Frame(self, padding=10)
        form.pack(fill=tk.BOTH, expand=True)

        self._add_row(form, 0, "Name", ttk.Entry(form, textvariable=self._name_var))
        self._add_row(
            form,
            1,
            "Port",
            ttk.Combobox(
                form,
                textvariable=self._port_var,
                state="readonly",
                values=["A", "B", "C", "D", "E", "F", "G", "H"],
                width=6,
            ),
        )
        self._add_row(
            form,
            2,
            "Pin",
            ttk.Spinbox(form, textvariable=self._pin_var, from_=0, to=15, width=6),
        )
        self._add_row(
            form,
            3,
            "Mode",
            ttk.Combobox(
                form,
                textvariable=self._mode_var,
                state="readonly",
                values=["output", "input"],
                width=10,
            ),
        )
        self._add_row(
            form,
            4,
            "Pull",
            ttk.Combobox(
                form,
                textvariable=self._pull_var,
                state="readonly",
                values=["none", "up", "down"],
                width=10,
            ),
        )
        self._add_row(
            form,
            5,
            "Initial",
            ttk.Combobox(
                form,
                textvariable=self._initial_var,
                state="readonly",
                values=["low", "high"],
                width=10,
            ),
        )

        active = ttk.Checkbutton(form, text="Active high", variable=self._active_high_var)
        active.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))

        buttons = ttk.Frame(form)
        buttons.grid(row=7, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))
        ttk.Button(buttons, text="Cancel", command=self._cancel).pack(side=tk.RIGHT)
        ttk.Button(buttons, text="Add", command=self._accept).pack(side=tk.RIGHT, padx=(0, 6))

        self.transient(master)
        self.grab_set()
        self.wait_window(self)

    @staticmethod
    def _add_row(form: ttk.Frame, row: int, label: str, widget: ttk.Widget) -> None:
        ttk.Label(form, text=label).grid(row=row, column=0, sticky=tk.W, padx=(0, 8), pady=2)
        widget.grid(row=row, column=1, sticky=tk.W, pady=2)

    def _accept(self) -> None:
        name = self._name_var.get().strip()
        if not name:
            messagebox.showerror("Missing name", "Provide a name for this pin.")
            return
        try:
            pin = int(self._pin_var.get())
        except ValueError:
            messagebox.showerror("Invalid pin", "Pin must be a number between 0 and 15.")
            return
        if pin < 0 or pin > 15:
            messagebox.showerror("Invalid pin", "Pin must be between 0 and 15.")
            return

        self.result = {
            "name": name,
            "port": self._port_var.get(),
            "pin": pin,
            "mode": self._mode_var.get(),
            "pull": self._pull_var.get(),
            "initial": self._initial_var.get(),
            "active_high": bool(self._active_high_var.get()),
        }
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class PinConfigView(ttk.LabelFrame):
    def __init__(self, master, on_change=None, **kwargs):
        super().__init__(master, text="GPIO Pins", padding=8, **kwargs)
        self._on_change = on_change

        self._led_label = ttk.Label(self, text="Board LED: -")
        self._led_label.pack(anchor=tk.W)

        self._tree = ttk.Treeview(
            self,
            columns=("name", "port", "pin", "mode", "pull", "initial", "active"),
            show="headings",
            height=6,
        )
        for col, label, width in [
            ("name", "Name", 120),
            ("port", "Port", 50),
            ("pin", "Pin", 50),
            ("mode", "Mode", 70),
            ("pull", "Pull", 70),
            ("initial", "Initial", 70),
            ("active", "Active", 70),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor=tk.W)
        self._tree.pack(fill=tk.BOTH, expand=True, pady=(6, 6))

        buttons = ttk.Frame(self)
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Add", command=self._add_pin).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Remove", command=self._remove_pin).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="Clear", command=self._clear_pins).pack(side=tk.LEFT)

    def set_board_led(self, port: str, pin: int) -> None:
        self._led_label.configure(text=f"Board LED: {port}{pin}")

    def _add_pin(self) -> None:
        dialog = PinDialog(self)
        if not dialog.result:
            return
        data = dialog.result
        values = (
            data["name"],
            data["port"],
            str(data["pin"]),
            data["mode"],
            data["pull"],
            data["initial"],
            "high" if data["active_high"] else "low",
        )
        self._tree.insert("", tk.END, values=values)
        self._notify_change()

    def _remove_pin(self) -> None:
        for item in self._tree.selection():
            self._tree.delete(item)
        self._notify_change()

    def _clear_pins(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._notify_change()

    def _notify_change(self) -> None:
        if self._on_change:
            self._on_change()

    def get_pins(self) -> list[dict]:
        pins = []
        for item in self._tree.get_children():
            name, port, pin, mode, pull, initial, active = self._tree.item(item, "values")
            pins.append(
                {
                    "name": name,
                    "port": port,
                    "pin": int(pin),
                    "mode": mode,
                    "pull": pull,
                    "initial": initial,
                    "active_high": active == "high",
                }
            )
        return pins
