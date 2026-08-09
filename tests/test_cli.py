from pathlib import Path

from wifi_signal_logger.cli import main


EXAMPLE_CSV = Path(__file__).parents[1] / "examples" / "sample_wifi_signal.csv"


def test_report_command_prints_summary(capsys) -> None:
    result = main(["report", "--input", str(EXAMPLE_CSV)])
    output = capsys.readouterr().out
    assert result == 0
    assert "Readings: 18" in output
    assert "Average:" in output


def test_chart_command_writes_output(tmp_path, capsys) -> None:
    destination = tmp_path / "cli-chart.png"
    result = main(["chart", "--input", str(EXAMPLE_CSV), "--output", str(destination)])
    assert result == 0
    assert destination.exists()
    assert "Chart saved" in capsys.readouterr().out


def test_missing_report_file_returns_error(tmp_path, capsys) -> None:
    result = main(["report", "--input", str(tmp_path / "missing.csv")])
    assert result == 1
    assert "Error: CSV file not found" in capsys.readouterr().err


def test_once_uses_privacy_labels_by_default(monkeypatch, capsys) -> None:
    from datetime import datetime, timezone

    from wifi_signal_logger.models import WifiSample

    sample = WifiSample(
        timestamp=datetime(2026, 8, 8, tzinfo=timezone.utc),
        interface="Wi-Fi",
        state="connected",
        ssid="Secret SSID",
        bssid="aa:bb:cc:dd:ee:ff",
        signal_percent=75,
    )
    monkeypatch.setattr("wifi_signal_logger.cli.collect_sample", lambda: sample)
    assert main(["once"]) == 0
    output = capsys.readouterr().out
    assert "network-" in output
    assert "Secret SSID" not in output
