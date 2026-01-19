import unittest

from stm32_toolbox.core.errors import (
    BoardNotFoundError,
    PackNotFoundError,
    ProcessError,
    SerialError,
    ToolNotFoundError,
    normalize_error,
)


class ErrorTests(unittest.TestCase):
    def test_tool_not_found(self) -> None:
        detail = normalize_error(ToolNotFoundError("openocd"))
        self.assertIn("Missing tool", detail.summary)
        self.assertIn("Install", detail.action)

    def test_board_not_found(self) -> None:
        detail = normalize_error(BoardNotFoundError("missing"))
        self.assertIn("Board not found", detail.summary)
        self.assertIn("boards", detail.action)

    def test_pack_not_found(self) -> None:
        detail = normalize_error(PackNotFoundError("missing"))
        self.assertIn("Pack not found", detail.summary)
        self.assertIn("packs", detail.action)

    def test_process_error(self) -> None:
        detail = normalize_error(ProcessError(["cmd"], 2, "fail"))
        self.assertIn("exit code 2", detail.summary)
        self.assertIn("command output", detail.action)

    def test_serial_error(self) -> None:
        detail = normalize_error(SerialError("bad"))
        self.assertEqual(detail.summary, "bad")
        self.assertIn("serial port", detail.action)


if __name__ == "__main__":
    unittest.main()
