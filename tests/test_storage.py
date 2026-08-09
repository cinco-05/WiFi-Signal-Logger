import csv
from datetime import datetime, timezone

import pytest

from wifi_signal_logger.models import WifiSample
from wifi_signal_logger.storage import append_sample, read_rows, sample_to_row, summarize_rows


def make_sample() -> WifiSample:
    return WifiSample(
        timestamp=datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc),
        interface="Wi-Fi",
        state="connected",
        ssid="Private Network",
        bssid="aa:bb:cc:dd:ee:ff",
        signal_percent=82,
        channel=36,
        radio_type="802.11ax",
        authentication="WPA2-Personal",
        cipher="CCMP",
        receive_mbps=1201.0,
        transmit_mbps=960.5,
    )


def test_identifiers_are_anonymous_by_default() -> None:
    row = sample_to_row(make_sample())
    assert row["ssid"].startswith("network-")
    assert row["bssid"].startswith("access-point-")
    assert "Private Network" not in row.values()


def test_real_identifiers_require_explicit_opt_in() -> None:
    row = sample_to_row(make_sample(), include_identifiers=True)
    assert row["ssid"] == "Private Network"
    assert row["bssid"] == "aa:bb:cc:dd:ee:ff"


def test_append_writes_one_header_and_multiple_rows(tmp_path) -> None:
    destination = tmp_path / "nested" / "readings.csv"
    append_sample(destination, make_sample())
    append_sample(destination, make_sample())

    with destination.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert len(rows) == 3
    assert rows[0].count("timestamp") == 1


def test_read_and_summarize_rows(tmp_path) -> None:
    destination = tmp_path / "readings.csv"
    append_sample(destination, make_sample())
    summary = summarize_rows(read_rows(destination))
    assert summary["count"] == 1
    assert summary["average"] == 82.0
    assert summary["minimum"] == 82
    assert summary["maximum"] == 82


def test_summary_ignores_invalid_rows() -> None:
    rows = [
        {"timestamp": "bad", "signal_percent": "nope"},
        {"timestamp": "2026-08-08T12:00:00+00:00", "signal_percent": "55"},
    ]
    assert summarize_rows(rows)["count"] == 1


def test_summary_rejects_file_without_valid_readings() -> None:
    with pytest.raises(ValueError, match="valid signal"):
        summarize_rows([{"timestamp": "bad", "signal_percent": "bad"}])


def test_missing_csv_has_clear_error(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="CSV file not found"):
        read_rows(tmp_path / "missing.csv")
