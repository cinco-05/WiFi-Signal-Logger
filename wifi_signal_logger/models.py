"""Data models shared by the collector, storage, and CLI layers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class WifiSample:
    """One point-in-time reading from a connected Windows Wi-Fi interface."""

    timestamp: datetime
    interface: str
    state: str
    ssid: str
    bssid: str
    signal_percent: int
    channel: Optional[int] = None
    radio_type: str = ""
    authentication: str = ""
    cipher: str = ""
    receive_mbps: Optional[float] = None
    transmit_mbps: Optional[float] = None
