"""Persisted settings stored under ~/.config/stm32-toolbox."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

CONFIG_DIR = Path.home() / ".config" / "stm32-toolbox"
SETTINGS_PATH = CONFIG_DIR / "settings.json"


@dataclass
class Settings:
    cube_root: str = ""
    adapter_speed_khz: int = 4000
    last_board_id: str = ""
    last_serial_port: str = ""
    last_project_dir: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        return cls(
            cube_root=str(data.get("cube_root", "")),
            adapter_speed_khz=int(data.get("adapter_speed_khz", 4000)),
            last_board_id=str(data.get("last_board_id", "")),
            last_serial_port=str(data.get("last_serial_port", "")),
            last_project_dir=str(data.get("last_project_dir", "")),
        )

    def to_dict(self) -> dict:
        return {
            "cube_root": self.cube_root,
            "adapter_speed_khz": self.adapter_speed_khz,
            "last_board_id": self.last_board_id,
            "last_serial_port": self.last_serial_port,
            "last_project_dir": self.last_project_dir,
        }


def load_settings() -> Settings:
    if not SETTINGS_PATH.exists():
        return Settings()
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    return Settings.from_dict(data)


def save_settings(settings: Settings) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
