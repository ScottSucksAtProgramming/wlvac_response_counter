# WLVAC Desktop App (Tauri + React)

Cross-platform desktop UI for generating WLVAC response summaries on macOS and Windows.

## Features

- Select dispatch file (`.xls/.xlsx`) and ESO responses file (`.csv`)
- Configure optional unit settings
- Generate timestamped output:
  - `WLVACResponseCounts-YYMMDD-HHMMSS.txt`
- Display top counts in-app:
  - Assigned / Went / Missed / Outside
- Open generated output directly from app

## Development

```bash
cd desktop
npm install
npm run tauri:dev
```

`tauri:dev` automatically ensures the parser sidecar for your current OS exists.

## Production build

```bash
cd desktop
npm run tauri:build
```

`tauri:build` automatically builds the parser sidecar for the current OS (if missing) and bundles it.

- macOS build targets: `.app` bundle + installer `.dmg` with `Applications` shortcut
- Windows build targets: `.msi` and `.exe` (NSIS)

## Tauri command contract

Frontend invokes `run_summary` with:

- `dispatchPath`
- `esoPath`
- `outputDir`
- `excludeUnits`
- `wlvacUnits`

Backend returns:

- `success`
- `outputPath`
- `stdout`
- `stderr`
- `counts`
