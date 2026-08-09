"""Collect and parse Windows Wi-Fi interface readings from ``netsh``."""

from __future__ import annotations

import locale
import platform
import re
import subprocess
from datetime import datetime
from typing import Callable, Iterable, Mapping, Optional

from .models import WifiSample


class WifiLoggerError(RuntimeError):
    """Base exception for expected Wi-Fi logger failures."""


class UnsupportedPlatformError(WifiLoggerError):
    """Raised when live collection is requested outside Windows."""


class NetshCommandError(WifiLoggerError):
    """Raised when Windows cannot return wireless interface information."""


class WifiDisconnectedError(WifiLoggerError):
    """Raised when no connected wireless interface is present."""


KEY_VALUE_PATTERN = re.compile(r"^\s*([^:]+?)\s*:\s*(.*?)\s*$")


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _parse_number(value: Optional[str], *, integer: bool = False) -> Optional[float | int]:
    if not value:
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", value)
    if not match:
        return None
    number = float(match.group(0).replace(",", "."))
    return int(number) if integer else number


def parse_interfaces(output: str) -> list[dict[str, str]]:
    """Convert English ``netsh wlan show interfaces`` output into records."""
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for line in output.splitlines():
        match = KEY_VALUE_PATTERN.match(line)
        if not match:
            continue
        key, value = _normalize_key(match.group(1)), match.group(2).strip()
        if key == "name" and current:
            records.append(current)
            current = {}
        current[key] = value

    if current:
        records.append(current)
    return records


def _first(record: Mapping[str, str], keys: Iterable[str], default: str = "") -> str:
    for key in keys:
        value = record.get(key)
        if value:
            return value
    return default


def parse_netsh_output(output: str, *, now: Optional[datetime] = None) -> WifiSample:
    """Return the first connected interface from raw ``netsh`` output."""
    lowered = output.lower()
    if "returns error 5" in lowered or "requires elevation" in lowered or "access is denied" in lowered:
        raise NetshCommandError(
            "Windows denied access to Wi-Fi interface details. Try a normal interactive terminal first; "
            "if your device policy requires it, run the terminal as Administrator."
        )
    if "wlan autoconfig service" in lowered and "not running" in lowered:
        raise NetshCommandError("The Windows WLAN AutoConfig service is not running.")

    interfaces = parse_interfaces(output)
    connected = [item for item in interfaces if item.get("state", "").strip().lower() == "connected"]
    if not connected:
        raise WifiDisconnectedError("No connected Wi-Fi interface was found.")

    record = connected[0]
    signal = _parse_number(record.get("signal"), integer=True)
    if signal is None:
        raise NetshCommandError("Windows returned a connected interface without signal strength.")

    return WifiSample(
        timestamp=now or datetime.now().astimezone(),
        interface=record.get("name", "Wi-Fi"),
        state=record.get("state", "connected"),
        ssid=record.get("ssid", ""),
        bssid=_first(record, ("bssid", "ap bssid")),
        signal_percent=max(0, min(100, int(signal))),
        channel=_parse_number(record.get("channel"), integer=True),
        radio_type=record.get("radio type", ""),
        authentication=record.get("authentication", ""),
        cipher=record.get("cipher", ""),
        receive_mbps=_parse_number(record.get("receive rate (mbps)")),
        transmit_mbps=_parse_number(record.get("transmit rate (mbps)")),
    )


def run_netsh() -> str:
    """Execute the read-only Windows command used by the collector."""
    if platform.system() != "Windows":
        raise UnsupportedPlatformError("Live collection requires Windows 10 or Windows 11.")

    try:
        completed = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise NetshCommandError(f"Could not start netsh: {exc}") from exc

    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    if completed.returncode != 0 and not output.strip():
        raise NetshCommandError(f"netsh exited with status {completed.returncode}.")
    return output


def collect_sample(
    *,
    runner: Callable[[], str] = run_netsh,
    now: Optional[datetime] = None,
) -> WifiSample:
    """Collect one live reading; injectable arguments keep tests offline."""
    return parse_netsh_output(runner(), now=now)
