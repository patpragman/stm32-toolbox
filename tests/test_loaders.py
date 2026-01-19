import unittest
from pathlib import Path

from stm32_toolbox.core.boards import BoardLibrary
from stm32_toolbox.core.packs import PackLibrary


class LoaderTests(unittest.TestCase):
    def test_loads_boards_and_packs(self):
        board_lib = BoardLibrary(Path("boards"))
        pack_lib = PackLibrary(Path("packs"))
        self.assertTrue(board_lib.list())
        self.assertTrue(pack_lib.list())


if __name__ == "__main__":
    unittest.main()
