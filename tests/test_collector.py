from datetime import datetime, timezone
from pathlib import Path

import pytest

from wifi_signal_logger.collector import (
    NetshCommandError,
    UnsupportedPlatformError,
    WifiDisconnectedError,
    collect_sample,
    parse_interfaces,
    parse_netsh_output,
    run_netsh,
)


FIXTURES = Path(__file__).parent / "fixtures"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parses_connected_interface_and_values() -> None:
    now = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
    sample = parse_netsh_output(fixture_text("connected.txt"), now=now)

    assert sample.timestamp == now
    assert sample.interface == "Wi-Fi"
    assert sample.ssid == "Home Lab"
    assert sample.bssid == "aa:bb:cc:dd:ee:ff"
    assert sample.signal_percent == 87
    assert sample.channel == 36
    assert sample.radio_type == "802.11ax"
    assert sample.authentication == "WPA2-Personal"
    assert sample.cipher == "CCMP"
    assert sample.receive_mbps == 1201.0
    assert sample.transmit_mbps == 960.5


def test_parse_interfaces_keeps_multiple_adapters_separate() -> None:
    records = parse_interfaces(fixture_text("connected.txt"))
    named = [record for record in records if "name" in record]
    assert [record["name"] for record in named] == ["Wi-Fi Backup", "Wi-Fi"]


def test_signal_is_clamped_to_percentage_range() -> None:
    output = fixture_text("connected.txt").replace("87%", "108%")
    assert parse_netsh_output(output).signal_percent == 100


def test_disconnected_interface_is_reported() -> None:
    with pytest.raises(WifiDisconnectedError, match="No connected"):
        parse_netsh_output(fixture_text("disconnected.txt"))


def test_access_denied_has_actionable_error() -> None:
    with pytest.raises(NetshCommandError, match="denied access"):
        parse_netsh_output(fixture_text("access_denied.txt"))


def test_collect_sample_accepts_offline_runner() -> None:
    sample = collect_sample(runner=lambda: fixture_text("connected.txt"))
    assert sample.signal_percent == 87


def test_run_netsh_rejects_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("wifi_signal_logger.collector.platform.system", lambda: "Linux")
    with pytest.raises(UnsupportedPlatformError):
        run_netsh()
