# Repository Guidelines

This repository is currently a scaffolding for STM32 tooling and drivers. Use the
conventions below to keep new modules consistent and update this file when the
structure or tooling changes.

## Project Structure & Module Organization
Place reusable code under `src/` with public headers in `include/`. Add
board-specific configuration in `boards/<board_name>/` (pins, clocks, linker
scripts). Put runnable demos in `examples/` and supporting scripts in `tools/`.
Tests live in `tests/`, and design notes belong in `docs/`. Keep each module
self-contained, for example `src/gpio/` with `include/gpio.h`.

## Build, Test, and Development Commands
A build system is not checked in yet. When adding one, keep a single entrypoint
and document it here. Expected defaults:
- `cmake -S . -B build` - configure.
- `cmake --build build` - build all targets.
- `ctest --test-dir build` - run unit tests.
If you choose Make instead of CMake, provide equivalent `make build`, `make test`,
and `make flash BOARD=<board>` targets.

## Coding Style & Naming Conventions
Use 4-space indentation, LF line endings, and no tabs. For C/C++ code, use K&R
braces, `snake_case` for functions/variables, `snake_case_t` for typedefs, and
`UPPER_SNAKE_CASE` for macros/constants. File names should be
`lower_snake_case.c/.h`.

## Testing Guidelines
Default to Unity and Ceedling for C tests unless the project adopts another
framework. Name tests `tests/test_<module>.c` and cover new drivers or utilities
with at least one unit test plus a runnable example under `examples/`.

## Commit & Pull Request Guidelines
There is no Git history yet. Use Conventional Commits (for example,
`feat: add gpio driver`, `fix: guard null pointer`). PRs should include a short
summary, test commands run, target board(s), and linked issues. Add screenshots
only for documentation or UI changes.
