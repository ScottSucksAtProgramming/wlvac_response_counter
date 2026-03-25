---
title: "WLVAC Response Counter Conventions"
summary: "Tech stack details, layer boundaries, and naming patterns for the WLVAC response counter app"
created: 2026-03-25
updated: 2026-03-25
---

# WLVAC Response Counter Conventions

## What Belongs Here

- Desktop app code (Tauri + React frontend, Rust backend, Python parser)
- Build scripts and packaging artifacts
- Regression tests for the parser
- User-facing and release documentation

## What Does NOT Belong Here

- Raw dispatch reports or ESO exports (except `Report.xls` as a dev sample) — these are operational data, not source code
- Planning notes or project management — those live in the Obsidian vault at `~/Documents/1_projects/`

## Architecture Layers

1. **Python parser** (`parser/parse_dispatch_report.py`) — standalone CLI. Reads .xls HTML exports and .csv ESO files, outputs .txt summaries and optional JSON. All report logic lives here.
2. **Rust/Tauri backend** (`desktop/src-tauri/`) — wraps the parser as a sidecar binary (PyInstaller-bundled). Exposes Tauri commands for file dialogs and running the parser.
3. **React frontend** (`desktop/src/`) — single-page UI with file pickers, advanced settings, and result tiles. Communicates with backend via `invoke()`.

## Naming Patterns

- Output files: `WLVACResponseCounts-YYMMDD-HHMMSS.txt`
- Unit identifiers: numeric strings (e.g., "290", "292") — kept as strings throughout
- Default excluded units: 290, 291
- Default WLVAC units: 292, 293, 294

## Domain Concepts

- **Daytime hours**: M-F 0700-1900
- **Primary hours** (aka "second 9s" shift): M-F 1900-0700 and Sat+Sun all day. This is the volunteer overnight/weekend coverage period.
- **2nd 9s**: A missed call that came in while the on-duty unit was already on another call. Only one crew is in service at a time (one of 292, 293, or 294).
- **In District**: ESO timestamp indicating when a unit returned to service after a call. Used as the end of the "busy window" for 2nd 9s detection.

## Data Flow for New Stats

Adding a new stat requires changes across all three layers:
1. **Parser**: compute the stat in `write_summary()`, add to text output lines and JSON dict
2. **Rust backend**: add field to `SummaryCounts` struct, add line parser in `parse_summary_counts()`
3. **React frontend**: add field to `Counts` type, add tile to JSX

The text output line prefix in the parser must **exactly match** the `strip_prefix()` string in the Rust backend.

## Sidecar Build

The `prepare:sidecar` script (`desktop/scripts/ensure-parser-sidecar.mjs`) skips rebuilding if the binary already exists in `parser/binaries/`. After modifying the Python parser, **delete the stale sidecar** before running `tauri:dev`:

```bash
rm parser/binaries/parse_dispatch_report-macos
cd desktop && npm run tauri:dev
```

## Lessons Learned

<!-- Append dated one-liners here as conventions are refined. -->
