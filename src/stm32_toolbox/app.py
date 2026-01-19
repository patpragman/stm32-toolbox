"""Tkinter main app for stm32-toolbox."""

from __future__ import annotations

import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from .state import load_settings, save_settings, Settings
from .core.boards import BoardLibrary
from .core.packs import PackLibrary
from .core.generator import ProjectGenerator
from .core.toolchain import (
    detect_tools,
    require_build_tools,
    require_flash_tools,
    BUILD_SYSTEM_CMAKE,
    BUILD_SYSTEM_MAKE,
)
from .core.builder import Builder, BuildConfig
from .core.flasher import Flasher, FlashConfig, MakeFlasher, MakeFlashConfig
from .core.discover import list_serial_ports, prefer_stlink
from .core.serialmon import SerialMonitor, SerialConfig
from .core.errors import normalize_error
from .ui.board_select import BoardSelect
from .ui.project_wizard import ProjectWizard
from .ui.log_view import LogView
from .ui.serial_view import SerialView
from .ui.tool_status import ToolStatusView
from .ui.pin_config import PinConfigView
from .ui.code_editor import CodeEditorView


class ToolboxApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("stm32-toolbox")
        self.geometry("1000x700")

        self.settings = load_settings()
        self.board_lib = BoardLibrary()
        self.pack_lib = PackLibrary()
        self.serial_monitor = SerialMonitor()

        self._current_project_dir: Path | None = None
        self._build_system_var = tk.StringVar()

        self._build_ui()
        self._refresh_ports()
        self._refresh_tools()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(root)
        left.pack(side=tk.LEFT, fill=tk.Y)

        right = ttk.Frame(root)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0))

        self.board_select = BoardSelect(left, on_change=self._on_board_change)
        self.board_select.pack(fill=tk.X, pady=(0, 12))
        self.board_select.set_boards(self.board_lib.list())

        self.project_wizard = ProjectWizard(left, on_generate=self._generate_project)
        self.project_wizard.pack(fill=tk.X, pady=(0, 12))
        if self.settings.last_project_dir:
            self.project_wizard.set_project_dir(self.settings.last_project_dir)

        self.pin_config = PinConfigView(left)
        self.pin_config.pack(fill=tk.X, pady=(0, 12))
        self._on_board_change()

        actions = ttk.LabelFrame(left, text="Actions", padding=8)
        actions.pack(fill=tk.X)
        ttk.Label(actions, text="Build System").pack(anchor=tk.W)
        self._build_system_var.set(self.settings.build_system or BUILD_SYSTEM_CMAKE)
        self._build_system_combo = ttk.Combobox(
            actions,
            state="readonly",
            values=[BUILD_SYSTEM_CMAKE, BUILD_SYSTEM_MAKE],
            textvariable=self._build_system_var,
        )
        self._build_system_combo.pack(fill=tk.X, pady=(0, 6))
        self._build_system_combo.bind("<<ComboboxSelected>>", self._on_build_system_change)
        ttk.Button(actions, text="Build", command=self._build_project).pack(fill=tk.X)
        ttk.Button(actions, text="Flash", command=self._flash_project).pack(fill=tk.X, pady=4)
        ttk.Button(actions, text="Refresh Ports", command=self._refresh_ports).pack(fill=tk.X)

        self.tool_status = ToolStatusView(left, on_refresh=self._refresh_tools)
        self.tool_status.pack(fill=tk.X, pady=(12, 0))

        self._notebook = ttk.Notebook(right)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        self.serial_view = SerialView(
            self._notebook,
            on_start=self._start_serial,
            on_stop=self._stop_serial,
        )
        self.log_view = LogView(self._notebook)
        self.code_editor = CodeEditorView(self._notebook)

        self._notebook.add(self.serial_view, text="Serial Monitor")
        self._notebook.add(self.log_view, text="Log")
        self._notebook.add(self.code_editor, text="main.c Editor")

    def _log(self, line: str) -> None:
        self.after(0, lambda: self.log_view.append(line))

    def _refresh_tools(self) -> None:
        status = detect_tools()
        self.tool_status.set_status(status)

    def _get_selected_board_pack(self):
        board_id = self.board_select.get_selected_id()
        board = self.board_lib.get(board_id)
        pack = self.pack_lib.get(board.pack)
        return board, pack

    def _on_board_change(self) -> None:
        try:
            board, _pack = self._get_selected_board_pack()
        except Exception:
            return
        self.pin_config.set_board_led(board.led.name, board.led.port, board.led.pin)
        self.pin_config.set_ports(_pack.gpio_ports)
        if not self.pin_config.get_pins():
            self.pin_config.populate_all()

    def _on_build_system_change(self, _event=None) -> None:
        self.settings.build_system = self._build_system_var.get()
        save_settings(self.settings)

    def _get_build_system(self) -> str:
        value = self._build_system_var.get()
        if value in (BUILD_SYSTEM_CMAKE, BUILD_SYSTEM_MAKE):
            return value
        return BUILD_SYSTEM_CMAKE

    def _is_toolbox_project(self) -> bool:
        if not self._current_project_dir:
            return False
        return (self._current_project_dir / "stm32toolbox.project.json").exists()

    def _generate_project(self) -> None:
        project_dir = self.project_wizard.get_project_dir()
        if not project_dir:
            messagebox.showerror("Missing path", "Select a project directory first.")
            return
        board, pack = self._get_selected_board_pack()
        pins = self.pin_config.get_pins()
        led_alias = self.pin_config.get_led_alias()
        self._current_project_dir = Path(project_dir)

        def work():
            try:
                generator = ProjectGenerator(self._current_project_dir)
                generator.generate(board, pack, pins=pins, led_alias=led_alias)
                self._log(f"Generated project at {self._current_project_dir}")
                self.after(0, self._load_main_editor)
                self.settings.last_project_dir = str(self._current_project_dir)
                self.settings.last_board_id = board.id
                save_settings(self.settings)
            except Exception as exc:
                detail = normalize_error(exc)
                self._log(f"Error: {detail.summary}")
                self._log(f"Action: {detail.action}")

        threading.Thread(target=work, daemon=True).start()

    def _build_project(self) -> None:
        if not self._current_project_dir:
            project_dir = self.project_wizard.get_project_dir()
            if project_dir:
                self._current_project_dir = Path(project_dir)
                self.after(0, self._load_main_editor)
        if not self._current_project_dir:
            messagebox.showerror("Missing project", "Generate or select a project first.")
            return
        if not self._load_main_editor():
            return
        if not self.code_editor.save_if_dirty():
            return

        def work():
            try:
                status = detect_tools()
                build_system = self._get_build_system()
                require_build_tools(status, build_system)
                config = BuildConfig(
                    source_dir=self._current_project_dir,
                    build_dir=self._current_project_dir / "build",
                    build_system=build_system,
                )
                builder = Builder(config)
                builder.configure(self._log)
                builder.build(self._log)
                self._log("Build completed.")
            except Exception as exc:
                detail = normalize_error(exc)
                self._log(f"Error: {detail.summary}")
                self._log(f"Action: {detail.action}")

        threading.Thread(target=work, daemon=True).start()

    def _flash_project(self) -> None:
        if not self._current_project_dir:
            messagebox.showerror("Missing project", "Generate or select a project first.")
            return
        if not self._load_main_editor():
            return
        if not self.code_editor.save_if_dirty():
            return

        def work():
            try:
                build_system = self._get_build_system()
                status = detect_tools()
                require_flash_tools(
                    status,
                    build_system,
                    needs_openocd=self._is_toolbox_project(),
                )
                if build_system == BUILD_SYSTEM_MAKE:
                    make_flasher = MakeFlasher(
                        MakeFlashConfig(project_dir=self._current_project_dir)
                    )
                    make_flasher.flash(self._log)
                    self._log("Make flash completed.")
                    return

                board, pack = self._get_selected_board_pack()
                elf = self._find_elf(self._current_project_dir / "build")
                if not elf:
                    self._log("ELF not found. Build the project first.")
                    return
                flasher = Flasher(
                    FlashConfig(
                        board=board,
                        pack=pack,
                        adapter_speed_khz=self.settings.adapter_speed_khz,
                    )
                )
                flasher.flash(elf, self._log)
                self._log("Flash completed.")
            except Exception as exc:
                detail = normalize_error(exc)
                self._log(f"Error: {detail.summary}")
                self._log(f"Action: {detail.action}")

        threading.Thread(target=work, daemon=True).start()

    def _start_serial(self) -> None:
        port, baud = self.serial_view.get_selection()
        if not port:
            messagebox.showerror("Missing port", "Select a serial port first.")
            return

        def on_line(line: str) -> None:
            self.after(0, lambda: self.serial_view.append(line))

        def on_status(status: str) -> None:
            self._log(status)

        try:
            self.serial_monitor.start(
                SerialConfig(port=port, baud=baud),
                on_line=on_line,
                on_status=on_status,
            )
            self.settings.last_serial_port = port
            save_settings(self.settings)
        except Exception as exc:
            detail = normalize_error(exc)
            self._log(f"Error: {detail.summary}")
            self._log(f"Action: {detail.action}")

    def _stop_serial(self) -> None:
        self.serial_monitor.stop()
        self._log("Serial monitor stopped.")

    def _refresh_ports(self) -> None:
        ports = prefer_stlink(list_serial_ports())
        devices = [p.device for p in ports]
        self.serial_view.set_ports(devices)
        if self.settings.last_serial_port in devices:
            self.serial_view.select_port(self.settings.last_serial_port)

    def _load_main_editor(self) -> bool:
        if not self._current_project_dir:
            return False
        main_path = self._current_project_dir / "main.c"
        if not main_path.exists():
            return False
        if self.code_editor.has_unsaved_changes():
            return True
        if self.code_editor.get_path() != main_path:
            self.code_editor.load_file(main_path)
        return True

    @staticmethod
    def _find_elf(build_dir: Path) -> Path | None:
        if not build_dir.exists():
            return None
        for elf in build_dir.glob("*.elf"):
            return elf
        for elf in build_dir.rglob("*.elf"):
            return elf
        return None


def main() -> None:
    app = ToolboxApp()
    app.mainloop()


if __name__ == "__main__":
    main()
