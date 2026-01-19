# stm32-toolbox

stm32-toolbox is a Linux-first desktop application for STM32 project generation,
building, flashing, and serial monitoring without vendor IDEs. It is designed
around declarative packs (MCU families) and boards (hardware definitions) so
adding support for new targets does not require code changes.

## Requirements

- Python 3.14
- CMake + Ninja
- GNU Arm Embedded Toolchain (`arm-none-eabi-*`)
- OpenOCD (primary flasher)
- Optional: STM32CubeProgrammer CLI

## Quick start

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e .

stm32-toolbox
```

## Pack/board data

- Packs live under `packs/` and describe an MCU family.
- Boards live under `boards/` and describe concrete hardware.
- Generated projects are created from a pack + board selection.

## Project output

Generated projects are self-contained and buildable outside the GUI with:

```bash
cmake -S . -B build -G Ninja
cmake --build build
```

## Status

This repository contains the initial scaffolding and core modules. Expand packs,
board definitions, and templates to support more STM32 families and boards.
