"""Privacy-aware CSV persistence and summary statistics."""

from __future__ import annotations

import csv
import hashlib
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable

from .models import WifiSample


CSV_FIELDS = (
    "timestamp",
    "interface",
    "state",
    "ssid",
    "bssid",
    "signal_percent",
    "channel",
    "radio_type",
    "authentication",
    "cipher",
    "receive_mbps",
    "transmit_mbps",
)


def pseudonymize(value: str, prefix: str) -> str:
    """Create a stable non-reversible label for a network identifier."""
    if not value:
        return ""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"


def sample_to_row(sample: WifiSample, *, include_identifiers: bool = False) -> dict[str, Any]:
    ssid = sample.ssid if include_identifiers else pseudonymize(sample.ssid, "network")
    bssid = sample.bssid if include_identifiers else pseudonymize(sample.bssid, "access-point")
    return {
        "timestamp": sample.timestamp.isoformat(timespec="seconds"),
        "interface": sample.interface,
        "state": sample.state,
        "ssid": ssid,
        "bssid": bssid,
        "signal_percent": sample.signal_percent,
        "channel": "" if sample.channel is None else sample.channel,
        "radio_type": sample.radio_type,
        "authentication": sample.authentication,
        "cipher": sample.cipher,
        "receive_mbps": "" if sample.receive_mbps is None else sample.receive_mbps,
        "transmit_mbps": "" if sample.transmit_mbps is None else sample.transmit_mbps,
    }


def append_sample(path: str | Path, sample: WifiSample, *, include_identifiers: bool = False) -> dict[str, Any]:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    exists = destination.exists() and destination.stat().st_size > 0
    row = sample_to_row(sample, include_identifiers=include_identifiers)

    with destination.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
    return row


def read_rows(path: str | Path) -> list[dict[str, str]]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"CSV file not found: {source}")
    with source.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def summarize_rows(rows: Iterable[dict[str, str]]) -> dict[str, Any]:
    valid: list[tuple[datetime, int]] = []
    for row in rows:
        try:
            timestamp = datetime.fromisoformat(row["timestamp"])
            signal = int(float(row["signal_percent"]))
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= signal <= 100:
            valid.append((timestamp, signal))

    if not valid:
        raise ValueError("The CSV does not contain any valid signal readings.")

    weakest = min(valid, key=lambda item: item[1])
    strongest = max(valid, key=lambda item: item[1])
    signals = [signal for _, signal in valid]
    return {
        "count": len(valid),
        "average": fmean(signals),
        "minimum": weakest[1],
        "minimum_at": weakest[0],
        "maximum": strongest[1],
        "maximum_at": strongest[0],
        "first_at": valid[0][0],
        "last_at": valid[-1][0],
    }
