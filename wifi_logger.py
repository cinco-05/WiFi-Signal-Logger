"""Show the current Wi-Fi signal strength on Windows."""

import locale
import platform
import re
import subprocess


LINE_PATTERN = re.compile(r"^\s*([^:]+?)\s*:\s*(.*?)\s*$")


def parse_signal(output: str) -> int | None:
    """Read the signal percentage from ``netsh wlan show interfaces`` output."""
    lowered = output.lower()
    if "error 5" in lowered or "access is denied" in lowered or "requires elevation" in lowered:
        raise RuntimeError("Windows denied access to the Wi-Fi information.")
    if "wlan autoconfig service" in lowered and "not running" in lowered:
        raise RuntimeError("The Windows WLAN service is not running.")

    interfaces: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for line in output.splitlines():
        match = LINE_PATTERN.match(line)
        if not match:
            continue

        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        if key == "name" and current:
            interfaces.append(current)
            current = {}
        current[key] = value

    if current:
        interfaces.append(current)

    for interface in interfaces:
        if interface.get("state", "").lower() != "connected":
            continue

        match = re.search(r"\d+", interface.get("signal", ""))
        if not match:
            raise RuntimeError("Windows did not report a signal percentage.")
        return max(0, min(100, int(match.group())))

    return None


def get_signal() -> int | None:
    if platform.system() != "Windows":
        raise RuntimeError("This program only works on Windows.")

    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
            check=False,
        )
    except OSError as error:
        raise RuntimeError("Could not run the Windows network command.") from error

    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if result.returncode != 0 and not output.strip():
        raise RuntimeError("Windows could not read the Wi-Fi information.")
    return parse_signal(output)


def signal_rating(percent: int) -> str:
    if percent >= 70:
        return "good"
    if percent >= 40:
        return "fair"
    return "weak"


def main() -> int:
    try:
        signal = get_signal()
    except RuntimeError as error:
        print(f"Could not read Wi-Fi signal: {error}")
        return 1

    if signal is None:
        print("Not connected to Wi-Fi.")
        return 1

    print(f"Wi-Fi signal: {signal}% ({signal_rating(signal)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
