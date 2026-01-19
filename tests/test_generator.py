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
            self.assertTrue((output_dir / "stm32toolbox.project.json").exists())

            manifest = json.loads((output_dir / "stm32toolbox.project.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["board"], "nucleo_f091rc")
            self.assertEqual(manifest["pack"], "stm32f0")

            family_gpio = (output_dir / "family_gpio.h").read_text(encoding="utf-8")
            self.assertIn("#define LED_PIN 5U", family_gpio)
            self.assertIn("#define GPIO_BASE 0x48000000U", family_gpio)


if __name__ == "__main__":
    unittest.main()
