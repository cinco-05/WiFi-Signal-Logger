"""Allow ``python -m wifi_signal_logger`` execution."""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
