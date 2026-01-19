# Repository Guidelines

This repository contains stm32-toolbox, a Linux-first Tkinter desktop app for
STM32 project generation, build, flash, and serial monitoring. The system is
pack- and board-driven: adding a new board should be data-only.

## Project Structure & Module Organization
- `src/stm32_toolbox/` holds the application code. UI modules live in
  `src/stm32_toolbox/ui/`, core subsystems in `src/stm32_toolbox/core/`, and
  persisted settings in `src/stm32_toolbox/state.py`.
- `boards/` contains board JSON definitions (for example
  `boards/nucleo_l552ze_q.json`).
- `packs/` contains family packs (for example `packs/stm32l5/`) with templates
  under `templates/` (HAL, pin map, linker/startup, and CMake) and OpenOCD
  defaults under `openocd/`.
- `tests/` contains unit tests (currently `tests/test_loaders.py`).

## Build, Test, and Development Commands
- `python3.14 -m venv .venv` - create the local virtual environment.
- `source .venv/bin/activate` - activate the venv.
- `pip install -e .` - install in editable mode.
- `stm32-toolbox` - launch the GUI.
- `python -m unittest discover -s tests` - run unit tests.

Generated projects build with:
- `cmake -S . -B build -G Ninja`
- `cmake --build build`
If you use an existing Make-based project instead, the GUI can run `make` and
`make flash`.

## Coding Style & Naming Conventions
- Python: 4-space indentation, `snake_case` functions/variables, `CamelCase`
  classes, and ASCII-only source files.
- C templates: K&R braces, `snake_case` functions, `UPPER_SNAKE_CASE` macros.

## Testing Guidelines
- Use `unittest` for core logic tests; place tests in `tests/test_*.py`.
- Prefer small loader and template rendering tests for packs/boards.

## Commit & Pull Request Guidelines
- Use Conventional Commits (for example, `feat: add board definition`).
- PRs should include a short summary, tests run, and the board(s) validated.
- Attach logs or screenshots only when they add diagnostic value.
