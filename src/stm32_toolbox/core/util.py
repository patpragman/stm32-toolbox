"""Utility helpers for filesystem and templating."""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Callable

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def jinja_env(template_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def stream_process(
    cmd: list[str],
    cwd: Path | None,
    on_line: Callable[[str], None],
) -> int:
    import subprocess

    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        on_line(line.rstrip("\n"))
    return proc.wait()


def find_data_root(start: Path | None = None) -> Path:
    base = start or Path.cwd()
    for _ in range(5):
        if (base / "packs").is_dir() and (base / "boards").is_dir():
            return base
        if base.parent == base:
            break
        base = base.parent
    module_root = Path(__file__).resolve().parents[3]
    if (module_root / "packs").is_dir() and (module_root / "boards").is_dir():
        return module_root
    return Path.cwd()
