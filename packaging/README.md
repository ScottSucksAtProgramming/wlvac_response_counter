# Packaging and Release

## Target outputs

- macOS installer: `.dmg` or signed `.app` zip
- Windows installer: `.msi` (or `.exe` bundle target)

## Prerequisites

1. Build parser sidecar binaries first.
2. Ensure sidecar files exist:
   - `parser/binaries/parse_dispatch_report-macos`
   - `parser/binaries/parse_dispatch_report-windows.exe`

The desktop app bundles `parser/binaries/**` as resources via `desktop/src-tauri/tauri.conf.json`.

## Local build commands

### macOS

```bash
cd desktop
npm install
npm run tauri:build
```

### Windows

```powershell
cd desktop
npm install
npm run tauri:build
```

## Signing / notarization notes

- macOS: configure Apple signing + notarization for production distribution.
- Windows: use code-signing certificate for trusted install experience.

## Manual distribution checklist

1. Build parser sidecar for target OS.
2. Build desktop installer for target OS.
3. Smoke-test app with known regression data.
4. Publish installer plus release notes:
   - supported file formats
   - default unit settings
   - output filename format
