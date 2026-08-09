from pathlib import Path

from wifi_signal_logger.chart import create_chart


EXAMPLE_CSV = Path(__file__).parents[1] / "examples" / "sample_wifi_signal.csv"


def test_chart_creates_nonempty_png(tmp_path) -> None:
    destination = tmp_path / "chart.png"
    summary = create_chart(EXAMPLE_CSV, destination)
    assert destination.read_bytes().startswith(b"\x89PNG")
    assert destination.stat().st_size > 10_000
    assert summary["count"] == 18
