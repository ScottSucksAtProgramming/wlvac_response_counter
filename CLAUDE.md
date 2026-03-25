# WLVAC Response Counter

## Purpose

Cross-platform desktop app (Tauri + React) that parses WLVAC dispatch reports (.xls HTML exports) and ESO/ePCR response exports (.csv) to generate response count summaries. Outputs a timestamped report and displays key metrics: calls assigned, calls responded to, calls missed, calls likely handled by outside agencies, daytime vs primary hour breakdowns, and 2nd 9s (missed calls during active responses).

## Tree

```
wlvac_response_counter/
  CLAUDE.md
  INDEX.md
  README.md
  Report.xls                  # sample dispatch file (may contain sensitive data)
  .gitignore
  .gitattributes
  build_mac_app.sh             # top-level macOS build entrypoint
  build_windows_exe.ps1        # top-level Windows build entrypoint
  desktop/                     # Tauri + React frontend
    src/App.tsx                # main React UI
    src/main.tsx
    src/App.css, index.css
    src-tauri/                 # Rust backend (Tauri commands)
      src/lib.rs, main.rs
      tauri.conf.json
      Cargo.toml
    scripts/                   # build helper scripts (Node)
    package.json
  parser/                      # Python parsing engine
    parse_dispatch_report.py   # core parser (CLI + sidecar)
    binaries/                  # PyInstaller-bundled sidecar (auto-built)
    tests/test_regression.py
    scripts/                   # sidecar build scripts per platform
  packaging/                   # release and installer notes
  docs/
    USER_GUIDE.md
    RELEASE_CHECKLIST.md
  context/
    conventions.md
    lessons.md
```

## Rules

1. On session start within `wlvac_response_counter/`, read this file, then `INDEX.md`.
2. The app has three layers: Python parser (standalone CLI), Rust/Tauri backend (invokes parser as sidecar), React frontend (UI). Changes often span multiple layers.
3. The parser is the source of truth for report logic — all counting, deduplication, and matching lives in `parser/parse_dispatch_report.py`.
4. `Report.xls` in the repo root is a sample file that may contain sensitive dispatch data — never commit changes to it or reference its contents in output.
5. Build the app with `cd desktop && npm run tauri:build`. Dev mode: `npm run tauri:dev`. The sidecar (PyInstaller-bundled parser) is built automatically via `prepare:sidecar`.
6. When creating, renaming, or deleting files, update the Tree section above.
7. Follow the Note-Taking protocol: after completing tasks, log lessons to `context/lessons.md`.

## Note-Taking Protocol

After completing a task, consider whether anything learned should be recorded:

- **Corrections or surprises** — behavior that differed from expectations
- **Non-obvious decisions** — choices that future sessions would benefit from knowing
- **Gotchas** — pitfalls encountered during the work

Append a dated one-liner to `context/lessons.md`. When 3+ related lessons accumulate, extract them into a dedicated context file.
