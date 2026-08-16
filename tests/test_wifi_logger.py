import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import wifi_logger


FIXTURES = Path(__file__).parent / "fixtures"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class SignalTests(unittest.TestCase):
    def test_reads_signal_from_connected_interface(self) -> None:
        self.assertEqual(wifi_logger.parse_signal(fixture_text("connected.txt")), 87)

    def test_returns_none_when_wifi_is_disconnected(self) -> None:
        self.assertIsNone(wifi_logger.parse_signal(fixture_text("disconnected.txt")))

    def test_signal_stays_within_percentage_range(self) -> None:
        output = fixture_text("connected.txt").replace("87%", "108%")
        self.assertEqual(wifi_logger.parse_signal(output), 100)

    def test_access_denied_is_explained(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "denied access"):
            wifi_logger.parse_signal(fixture_text("access_denied.txt"))

    def test_signal_ratings(self) -> None:
        expected = {
            100: "good",
            70: "good",
            69: "fair",
            40: "fair",
            39: "weak",
            0: "weak",
        }
        for percent, rating in expected.items():
            with self.subTest(percent=percent):
                self.assertEqual(wifi_logger.signal_rating(percent), rating)

    def test_output_is_short_and_plain(self) -> None:
        output = io.StringIO()
        with patch("wifi_logger.get_signal", return_value=62), redirect_stdout(output):
            self.assertEqual(wifi_logger.main(), 0)
        self.assertEqual(output.getvalue(), "Wi-Fi signal: 62% (fair)\n")

    def test_disconnected_message(self) -> None:
        output = io.StringIO()
        with patch("wifi_logger.get_signal", return_value=None), redirect_stdout(output):
            self.assertEqual(wifi_logger.main(), 1)
        self.assertEqual(output.getvalue(), "Not connected to Wi-Fi.\n")

    def test_read_error_is_clear(self) -> None:
        output = io.StringIO()
        with patch("wifi_logger.get_signal", side_effect=RuntimeError("test error")), redirect_stdout(output):
            self.assertEqual(wifi_logger.main(), 1)
        self.assertEqual(output.getvalue(), "Could not read Wi-Fi signal: test error\n")


if __name__ == "__main__":
    unittest.main()
