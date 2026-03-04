# Parser Engine

This directory contains the source-of-truth Python parser:

- `parse_dispatch_report.py`

## What it does

Given:

- dispatch HTML export (`.xls/.xlsx`)
- ESO/ePCR responses CSV

It writes:

- detailed text summary (`.txt`)
- optional machine-readable summary (`--json-summary`)

## Build sidecar binaries

### macOS

```bash
zsh parser/scripts/build_sidecar_macos.sh
```

Output:

- `parser/binaries/parse_dispatch_report-macos`

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File parser/scripts/build_sidecar_windows.ps1
```

Output:

- `parser/binaries/parse_dispatch_report-windows.exe`

## Tests

Run parser regression tests:

```bash
python3 -m unittest discover -s parser/tests -p 'test_*.py'
```
