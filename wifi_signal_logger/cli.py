"""Command-line interface for Wi-Fi Signal Logger Version 1."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .chart import ChartDependencyError, create_chart
from .collector import WifiDisconnectedError, WifiLoggerError, collect_sample
from .storage import append_sample, read_rows, sample_to_row, summarize_rows


DEFAULT_CSV = Path("data/wifi_signal.csv")
DEFAULT_CHART = Path("outputs/wifi_signal.png")


def _nonnegative_float(value: str) -> float:
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return number


def _positive_float(value: str) -> float:
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wifi-signal-logger",
        description="Record Windows Wi-Fi signal strength to CSV and generate a chart.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    once = subparsers.add_parser("once", help="Display one live Wi-Fi reading")
    once.add_argument("--include-identifiers", action="store_true",
                      help="Show the real SSID and BSSID instead of privacy-safe labels")

    log = subparsers.add_parser("log", help="Record readings at a fixed interval")
    log.add_argument("--interval", type=_positive_float, default=5.0, help="Seconds between readings (default: 5)")
    log.add_argument("--duration", type=_nonnegative_float, default=300.0,
                     help="Total seconds to run; 0 means until Ctrl+C (default: 300)")
    log.add_argument("--output", type=Path, default=DEFAULT_CSV, help=f"CSV destination (default: {DEFAULT_CSV})")
    log.add_argument("--include-identifiers", action="store_true",
                     help="Store the real SSID and BSSID; default output uses stable anonymous labels")

    chart = subparsers.add_parser("chart", help="Create a PNG chart from recorded CSV data")
    chart.add_argument("--input", type=Path, default=DEFAULT_CSV, help=f"Input CSV (default: {DEFAULT_CSV})")
    chart.add_argument("--output", type=Path, default=DEFAULT_CHART,
                       help=f"PNG destination (default: {DEFAULT_CHART})")

    report = subparsers.add_parser("report", help="Print summary statistics from recorded CSV data")
    report.add_argument("--input", type=Path, default=DEFAULT_CSV, help=f"Input CSV (default: {DEFAULT_CSV})")
    return parser


def _display_row(row: dict[str, object]) -> None:
    channel = row.get("channel") or "N/A"
    receive = row.get("receive_mbps") or "N/A"
    transmit = row.get("transmit_mbps") or "N/A"
    print(f"Network: {row.get('ssid') or 'unknown'}")
    print(f"Signal:  {row['signal_percent']}%")
    print(f"Channel: {channel}")
    print(f"Rates:   {receive} Mbps down / {transmit} Mbps up")


def command_once(include_identifiers: bool) -> int:
    sample = collect_sample()
    row = sample_to_row(sample, include_identifiers=include_identifiers)
    print("Wi-Fi Signal Logger\n")
    _display_row(row)
    return 0


def command_log(interval: float, duration: float, output: Path, include_identifiers: bool) -> int:
    print("Wi-Fi Signal Logger")
    print(f"Writing to {output}")
    print("Press Ctrl+C to stop.\n")

    started = time.monotonic()
    saved = 0
    try:
        while duration == 0 or time.monotonic() - started <= duration:
            cycle_started = time.monotonic()
            try:
                sample = collect_sample()
                row = append_sample(output, sample, include_identifiers=include_identifiers)
                saved += 1
                stamp = sample.timestamp.strftime("%H:%M:%S")
                print(f"{stamp}  Signal: {sample.signal_percent:3d}%  "
                      f"Channel: {row.get('channel') or 'N/A'}  Network: {row.get('ssid') or 'unknown'}")
            except WifiDisconnectedError as exc:
                print(f"{time.strftime('%H:%M:%S')}  Waiting: {exc}", file=sys.stderr)

            elapsed = time.monotonic() - cycle_started
            remaining = interval - elapsed
            if duration != 0 and time.monotonic() - started + max(remaining, 0) > duration:
                break
            if remaining > 0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        print("\nStopped by user.")

    print(f"Saved {saved} reading(s) to {output}.")
    return 0 if saved else 1


def command_chart(input_path: Path, output_path: Path) -> int:
    summary = create_chart(input_path, output_path)
    print(f"Chart saved to {output_path}.")
    print(f"Readings: {summary['count']} | Average: {summary['average']:.1f}% | "
          f"Range: {summary['minimum']}-{summary['maximum']}%")
    return 0


def command_report(input_path: Path) -> int:
    summary = summarize_rows(read_rows(input_path))
    print("Wi-Fi Signal Report")
    print(f"Readings: {summary['count']}")
    print(f"Period:   {summary['first_at'].isoformat(timespec='seconds')} to "
          f"{summary['last_at'].isoformat(timespec='seconds')}")
    print(f"Average:  {summary['average']:.1f}%")
    print(f"Weakest:  {summary['minimum']}% at {summary['minimum_at'].isoformat(timespec='seconds')}")
    print(f"Strongest: {summary['maximum']}% at {summary['maximum_at'].isoformat(timespec='seconds')}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "once":
            return command_once(args.include_identifiers)
        if args.command == "log":
            return command_log(args.interval, args.duration, args.output, args.include_identifiers)
        if args.command == "chart":
            return command_chart(args.input, args.output)
        if args.command == "report":
            return command_report(args.input)
    except (WifiLoggerError, ChartDependencyError, FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    parser.error("unknown command")
    return 2
