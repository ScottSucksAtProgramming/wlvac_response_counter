---
title: "WLVAC Response Counter Lessons Learned"
summary: "Running log of corrections, preferences, and discoveries for the WLVAC response counter project"
created: 2026-03-25
updated: 2026-03-25
---

# WLVAC Response Counter Lessons Learned

<!-- Append dated one-liners below. When 3+ related lessons accumulate, extract into a dedicated context file. -->

- 2026-03-25: The sidecar binary (`parser/binaries/`) is NOT auto-rebuilt when Python source changes — must delete it manually to force rebuild. This caused "n/a" in the UI for new stats.
- 2026-03-25: ESO address-based matching can cross-match calls at the same address from different months, creating impossibly long busy windows. Fixed by capping busy window duration at 8 hours.
- 2026-03-25: ESO CSV `In District` timestamps use `%Y-%m-%d %H:%M:%S.%f` format (with milliseconds) — needed to add this format to `parse_any_datetime`.
- 2026-03-25: The ESO CSV column names change between exports. The parser uses flexible column name lookups via `_get_csv_value()` with multiple fallback names. Always add new column names this way.
- 2026-03-25: The PyInstaller sidecar must be codesigned with Developer ID + hardened runtime + timestamp BEFORE `tauri:build`, otherwise Apple notarization rejects it. Sign order: sidecar → tauri:build → sign .app → build DMG → sign DMG → notarize → staple.
- 2026-03-25: Notary profile is `--keychain-profile "aha-form-filler"` (shared across projects). Signing identity: `"Developer ID Application: Scott Kostolni (5N69HV7X7S)"`.
