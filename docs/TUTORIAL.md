# stm32-toolbox Tutorial

This walkthrough gets you from install → generate → build → flash → serial.
It assumes a Linux host and one of the supported Nucleo boards.

## 1) Install prerequisites

Minimum tools (Make workflow):
- GNU Arm Embedded Toolchain (`arm-none-eabi-*`)
- OpenOCD

Optional (CMake/Ninja workflow):
- CMake
- Ninja

Debian/Ubuntu example:
```bash
sudo apt-get update
sudo apt-get install gcc-arm-none-eabi openocd make
# Optional:
sudo apt-get install cmake ninja-build
```

For serial access:
```bash
sudo usermod -aG dialout $USER
```
Re-login after changing group membership.

## 2) Install and run

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e .

stm32-toolbox
```

## 3) Create or open a project

1. Pick a board (NUCLEO-F091RC or NUCLEO-L552ZE-Q).
2. Click **Browse** and select a project folder.
   - If the folder already contains `stm32toolbox.project.json`, the app loads
     the board, pins, and `main.c` automatically so you do not overwrite edits.
3. Click **Generate Project** for a new project.

Generated projects include `main.c`, `app_pins.*`, `hal_*.c`, `startup_gcc.s`,
`linker.ld`, and a self-contained `Makefile`.

## 4) Configure pins

The **GPIO Pins** panel defines the C pin map used by `app_pins.c`.
- The board LED is always present (default alias `LD2`).
- Board named pins (for example `LD1`, `LD2`, `LD3`, `B1`) are pre-labeled when available.
- Use **Populate All** to make every GPIO available as `P<port><pin>`.
- Reserved SWD pins (PA13/PA14) are listed but skipped during init.
- Use **Add/Edit** to rename pins (e.g., `PA7` → `LD2`).

In C, use:
```c
app_pins_init();
app_pin_write(APP_PIN_LD2, true);
```

## 5) Edit and build

Use the **main.c Editor** tab for quick edits, or edit on disk.
Always click **Save** before building/flashing.

Build options:
- **CMake/Ninja** (default in UI):
  ```bash
  cmake -S . -B build -G Ninja
  cmake --build build
  ```
- **Make** (select in UI or run manually):
  ```bash
  make
  ```

## 6) Flash

From the UI, click **Flash**. From the CLI:
```bash
make flash
```

OpenOCD connects under reset to avoid SWD pin conflicts. If it still fails,
hold the board’s reset button while flashing, then release after OpenOCD starts.

## 7) Serial monitor

Select `/dev/ttyACM*` or `/dev/ttyUSB*`, then click **Start**.
The default baud is 115200. Example output from `main.c`:
```c
hal_uart_init(115200);
hal_uart_write("tick\r\n");
```

If you see permission errors, verify `dialout` group membership.

## 8) Timing and HAL basics

Always call `hal_clock_init()` before delays. The HAL delay uses SysTick.
If a button named `B1` is present, the default `main.c` toggles the blink rate
on each button press.
```c
hal_clock_init();
hal_delay_ms(300);
```

## 9) Extending to new boards

To add a board without code changes:
1. Create a new `boards/<id>.json` with memory map, LED pin, serial pins,
   and OpenOCD settings.
2. Point it at an existing pack, or create a new pack under `packs/`.

If adding a board feels difficult, the pack/board definitions likely need
adjustment rather than app code changes.
