import unittest

from stm32_toolbox.core.discover import SerialPortInfo, prefer_stlink


class DiscoverTests(unittest.TestCase):
    def test_prefer_stlink(self) -> None:
        ports = [
            SerialPortInfo(device="/dev/ttyUSB0", description="", hwid="", vid=0x1234, pid=0x5678),
            SerialPortInfo(device="/dev/ttyACM0", description="", hwid="", vid=0x0483, pid=0x374B),
        ]
        ordered = prefer_stlink(ports)
        self.assertEqual(ordered[0].device, "/dev/ttyACM0")


if __name__ == "__main__":
    unittest.main()
