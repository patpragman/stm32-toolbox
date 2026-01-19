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
from .core.toolchain import detect_tools, require_tools
from .core.builder import Builder, BuildConfig
from .core.flasher import Flasher, FlashConfig
from .core.discover import list_serial_ports, prefer_stlink
from .core.serialmon import SerialMonitor, SerialConfig
from .core.errors import normalize_error
from .ui.board_select import BoardSelect
from .ui.project_wizard import ProjectWizard
from .ui.log_view import LogView
from .ui.serial_view import SerialView


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

        self._build_ui()
        self._refresh_ports()
        self._log_toolchain_status()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(root)
        left.pack(side=tk.LEFT, fill=tk.Y)

        right = ttk.Frame(root)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0))

        self.board_select = BoardSelect(left)
        self.board_select.pack(fill=tk.X, pady=(0, 12))
        self.board_select.set_boards(self.board_lib.list())

        self.project_wizard = ProjectWizard(left, on_generate=self._generate_project)
        self.project_wizard.pack(fill=tk.X, pady=(0, 12))
        if self.settings.last_project_dir:
            self.project_wizard.set_project_dir(self.settings.last_project_dir)

        actions = ttk.LabelFrame(left, text="Actions", padding=8)
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="Build", command=self._build_project).pack(fill=tk.X)
        ttk.Button(actions, text="Flash", command=self._flash_project).pack(fill=tk.X, pady=4)
        ttk.Button(actions, text="Refresh Ports", command=self._refresh_ports).pack(fill=tk.X)

        self.serial_view = SerialView(
            right,
            on_start=self._start_serial,
            on_stop=self._stop_serial,
        )
        self.serial_view.pack(fill=tk.BOTH, expand=True)

        self.log_view = LogView(right)
        self.log_view.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

    def _log(self, line: str) -> None:
        self.after(0, lambda: self.log_view.append(line))

    def _log_toolchain_status(self) -> None:
        status = detect_tools()
        missing = [name for name, value in status.__dict__.items() if value is None]
        if missing:
            self._log(f"Missing tools: {', '.join(missing)}")
        else:
            self._log("All required tools detected.")

    def _get_selected_board_pack(self):
        board_id = self.board_select.get_selected_id()
        board = self.board_lib.get(board_id)
        pack = self.pack_lib.get(board.pack)
        return board, pack

    def _generate_project(self) -> None:
        project_dir = self.project_wizard.get_project_dir()
        if not project_dir:
            messagebox.showerror("Missing path", "Select a project directory first.")
            return
        board, pack = self._get_selected_board_pack()
        self._current_project_dir = Path(project_dir)

        def work():
            try:
                generator = ProjectGenerator(self._current_project_dir)
                generator.generate(board, pack)
                self._log(f"Generated project at {self._current_project_dir}")
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
        if not self._current_project_dir:
            messagebox.showerror("Missing project", "Generate or select a project first.")
            return

        def work():
            try:
                status = detect_tools()
                require_tools(status)
                config = BuildConfig(
                    source_dir=self._current_project_dir,
                    build_dir=self._current_project_dir / "build",
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

        def work():
            try:
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
