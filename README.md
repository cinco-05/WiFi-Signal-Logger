# Wi-Fi signal

A small Windows program that shows the signal strength of the Wi-Fi connection
you are using.

```text
Wi-Fi signal: 62% (fair)
```

## Run it

Open PowerShell in this folder and run:

```powershell
python wifi_logger.py
```

It uses the `netsh` command included with Windows, so the program has no runtime
dependencies.

## What the percentage means

| Signal | Meaning |
| --- | --- |
| 70–100% | Good — a reliable connection |
| 40–69% | Fair — usable, but it may become unstable |
| 0–39% | Weak — dropouts are more likely |

This number describes the connection between the computer and the Wi-Fi access
point. It does not measure internet speed. A strong Wi-Fi signal can still have
slow internet if the connection itself is busy or slow.

## Tests

```powershell
python -m unittest discover -s tests -v
```

The tests use saved `netsh` output, so they do not need a live Wi-Fi connection
or any extra packages.
