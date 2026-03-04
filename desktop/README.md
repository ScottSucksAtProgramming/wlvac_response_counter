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

## Windows prerequisites

Install before running the production build on Windows:

- Node.js LTS
- Rustup with stable MSVC toolchain (`rustup default stable`)
- Visual Studio 2022 Build Tools with `Desktop development with C++`
- Microsoft Edge WebView2 Runtime

The repository root helper script `build_windows_exe.ps1` resolves and launches `VsDevCmd.bat` automatically so Rust can find `link.exe`.

## Troubleshooting

- `failed to run 'cargo metadata' ... program not found`
  - Cargo is not on `PATH`. Add `%USERPROFILE%\.cargo\bin` or run in a new shell after installing rustup.
- `linker 'link.exe' not found`
  - Visual Studio Build Tools / Desktop C++ workload is missing, or build is not running in a developer command prompt.
- `failed to bundle project` when downloading WiX/NSIS
  - First bundle run needs network access to download bundler toolchains.
- `error during build: Error: spawn EPERM` while running Vite/esbuild
  - Local process policy or security software blocked child-process execution. Retry from a normal local path and shell policy, or prebuild frontend assets and run Tauri with `--config` override for `beforeBuildCommand`.

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
