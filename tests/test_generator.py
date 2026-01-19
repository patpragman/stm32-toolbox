import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from stm32_toolbox.core.boards import BoardLibrary
from stm32_toolbox.core.packs import PackLibrary
from stm32_toolbox.core.generator import ProjectGenerator


class GeneratorTests(unittest.TestCase):
    def test_generate_project_outputs(self) -> None:
        board = BoardLibrary(Path("boards")).get("nucleo_f091rc")
        pack = PackLibrary(Path("packs")).get("stm32f0")

        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "proj"
            generator = ProjectGenerator(output_dir)
            generator.generate(board, pack)

            self.assertTrue((output_dir / "CMakeLists.txt").exists())
            self.assertTrue((output_dir / "linker.ld").exists())
            self.assertTrue((output_dir / "startup_gcc.s").exists())
            self.assertTrue((output_dir / "system.c").exists())
            self.assertTrue((output_dir / "main.c").exists())
            self.assertTrue((output_dir / "family_gpio.h").exists())
            self.assertTrue((output_dir / "Makefile").exists())
            self.assertTrue((output_dir / "hal.h").exists())
            self.assertTrue((output_dir / "hal_gpio.c").exists())
            self.assertTrue((output_dir / "hal_gpio.h").exists())
            self.assertTrue((output_dir / "hal_clock.c").exists())
            self.assertTrue((output_dir / "hal_clock.h").exists())
            self.assertTrue((output_dir / "hal_delay.c").exists())
            self.assertTrue((output_dir / "hal_delay.h").exists())
            self.assertTrue((output_dir / "app_pins.c").exists())
            self.assertTrue((output_dir / "app_pins.h").exists())
            self.assertTrue((output_dir / "openocd" / "target.cfg").exists())

            makefile = (output_dir / "Makefile").read_text(encoding="utf-8")
            self.assertIn("arm-none-eabi-gcc", makefile)
            self.assertIn("flash:", makefile)
            self.assertTrue((output_dir / "stm32toolbox.project.json").exists())

            manifest = json.loads((output_dir / "stm32toolbox.project.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["board"], "nucleo_f091rc")
            self.assertEqual(manifest["pack"], "stm32f0")

            family_gpio = (output_dir / "family_gpio.h").read_text(encoding="utf-8")
            self.assertIn("#define LED_PIN 5U", family_gpio)
            self.assertIn("#define GPIO_BASE 0x48000000U", family_gpio)

            app_pins = (output_dir / "app_pins.h").read_text(encoding="utf-8")
            self.assertIn("APP_PIN_LED", app_pins)

    def test_generate_project_with_custom_pins(self) -> None:
        board = BoardLibrary(Path("boards")).get("nucleo_f091rc")
        pack = PackLibrary(Path("packs")).get("stm32f0")

        pins = [
            {
                "name": "BTN1",
                "port": "C",
                "pin": 13,
                "mode": "input",
                "pull": "up",
                "initial": "low",
                "active_high": True,
            }
        ]

        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "proj"
            generator = ProjectGenerator(output_dir)
            generator.generate(board, pack, pins=pins, led_alias="LD2")

            app_pins = (output_dir / "app_pins.h").read_text(encoding="utf-8")
            self.assertIn("APP_PIN_LD2", app_pins)
            self.assertIn("APP_PIN_BTN1", app_pins)

            main_c = (output_dir / "main.c").read_text(encoding="utf-8")
            self.assertIn("APP_PIN_LD2", main_c)


if __name__ == "__main__":
    unittest.main()
