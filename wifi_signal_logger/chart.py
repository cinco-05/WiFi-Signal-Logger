"""Generate a headless PNG chart from Wi-Fi signal CSV data."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .storage import read_rows, summarize_rows


class ChartDependencyError(RuntimeError):
    """Raised when the plotting dependency is unavailable."""


def create_chart(csv_path: str | Path, output_path: str | Path) -> dict[str, object]:
    rows = read_rows(csv_path)
    summary = summarize_rows(rows)
    timestamps = []
    signals = []

    for row in rows:
        try:
            timestamp = datetime.fromisoformat(row["timestamp"])
            signal = int(float(row["signal_percent"]))
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= signal <= 100:
            timestamps.append(timestamp)
            signals.append(signal)

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        raise ChartDependencyError(
            "Charting requires Matplotlib. Install it with: python -m pip install -r requirements.txt"
        ) from exc

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    figure, axis = plt.subplots(figsize=(11, 5.5))
    axis.axhspan(0, 40, color="#ef4444", alpha=0.10, label="Weak (<40%)")
    axis.axhspan(40, 70, color="#f59e0b", alpha=0.10, label="Fair (40-69%)")
    axis.axhspan(70, 100, color="#22c55e", alpha=0.10, label="Good (70%+)")
    axis.plot(timestamps, signals, color="#2563eb", marker="o", markersize=3, linewidth=1.8)
    axis.axhline(summary["average"], color="#7c3aed", linestyle="--", linewidth=1.2,
                 label=f"Average ({summary['average']:.1f}%)")
    axis.set_title("Wi-Fi Signal Strength Over Time")
    axis.set_xlabel("Time")
    axis.set_ylabel("Signal strength (%)")
    axis.set_ylim(0, 100)
    axis.grid(True, alpha=0.25)
    # Preserve the timezone recorded in the CSV instead of silently displaying UTC.
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S", tz=timestamps[0].tzinfo))
    axis.legend(loc="lower left", ncols=2, fontsize=8)
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return summary
