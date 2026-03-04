# WLVAC Response Counts

Cross-platform desktop app for generating WLVAC response reports from:

- Dispatch export (`.xls` / `.xlsx` HTML export format)
- ESO/ePCR Responses export (`.csv`)

The app outputs a timestamped report file:

- `WLVACResponseCounts-YYMMDD-HHMMSS.txt`

and displays top counts in the UI:

- Calls assigned to us
- Calls we went to
- Calls missed
- Calls likely handled by outside agency

## Repository structure

1. `desktop/` - Tauri + React desktop app (Mac + Windows)
2. `parser/` - Python parser engine + sidecar build scripts
3. `packaging/` - release and installer notes
4. `build_mac_app.sh` / `build_windows_exe.ps1` - top-level build entrypoints

## Quick start (developer machine)

### macOS

```bash
cd desktop
npm install
npm run tauri:build
```

Built app:

- `desktop/src-tauri/target/release/bundle/macos/WLVAC Response Counts.app`

### Windows

```powershell
cd desktop
npm install
npm run tauri:build
```

Built installers:

- `desktop\src-tauri\target\release\bundle\msi\...`
- `desktop\src-tauri\target\release\bundle\nsis\...`

### Windows prerequisites

Install these first on a fresh machine:

- Node.js LTS
- Rustup + stable MSVC toolchain
- Visual Studio 2022 Build Tools with Desktop C++ workload
- Microsoft Edge WebView2 Runtime

Example setup commands:

```powershell
winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
winget install Rustlang.Rustup --accept-source-agreements --accept-package-agreements
rustup default stable
winget install Microsoft.VisualStudio.2022.BuildTools --exact --accept-source-agreements --accept-package-agreements --override "--wait --passive --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
winget install Microsoft.EdgeWebView2Runtime --accept-source-agreements --accept-package-agreements
```

## Detailed docs

- [User Guide](./docs/USER_GUIDE.md)
- [Release Checklist](./docs/RELEASE_CHECKLIST.md)
- [Desktop Dev Notes](./desktop/README.md)
- [Parser Notes](./parser/README.md)
- [Packaging Notes](./packaging/README.md)

## Notes before publishing to GitHub

- Check sample files in repo root (like `Report.xls`) and remove any sensitive data before publishing.
- `.gitignore` is configured to exclude generated app/build artifacts and local output reports.
