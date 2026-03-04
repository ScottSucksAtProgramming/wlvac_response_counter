# Packaging and Release

## Target outputs

- macOS installer: `.dmg` or signed `.app` zip
- Windows installer: `.msi` and `.exe` (NSIS)

## Prerequisites

1. Build parser sidecar binaries first.
2. Ensure sidecar files exist:
   - `parser/binaries/parse_dispatch_report-macos`
   - `parser/binaries/parse_dispatch_report-windows.exe`
3. Windows packaging machine requirements:
   - Node.js LTS
   - Rustup + stable toolchain
   - Visual Studio 2022 Build Tools with Desktop C++ workload
   - Microsoft Edge WebView2 Runtime

The desktop app bundles `parser/binaries/**` as resources via `desktop/src-tauri/tauri.conf.json`.

## Clean machine bootstrap (Windows)

```powershell
winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
winget install Rustlang.Rustup --accept-source-agreements --accept-package-agreements
rustup default stable
winget install Microsoft.VisualStudio.2022.BuildTools --exact --accept-source-agreements --accept-package-agreements --override "--wait --passive --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
winget install Microsoft.EdgeWebView2Runtime --accept-source-agreements --accept-package-agreements
```

## Local build commands

### macOS

```bash
cd desktop
npm install
npm run tauri:build
```

### Windows

```powershell
.\build_windows_exe.ps1
```

This script builds the parser sidecar, loads the Visual Studio developer environment, and runs `npm run tauri:build` with the required MSVC linker available.

## Troubleshooting

- `failed to run 'cargo metadata' ... program not found`
  - Cargo is not on `PATH`.
- `linker 'link.exe' not found`
  - Missing Desktop C++ workload or build not running under `VsDevCmd`.
- `failed to bundle project` while verifying WiX/NSIS
  - First bundle run downloads tooling and requires outbound network access.

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
