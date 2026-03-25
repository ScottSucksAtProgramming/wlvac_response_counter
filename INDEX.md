# WLVAC Response Counter Index

Quick-reference for finding content in this project. For conventions, see `context/conventions.md`.

## Application Layers

| File/Folder | Purpose | When to Use |
|-------------|---------|-------------|
| `parser/parse_dispatch_report.py` | Core parsing, deduplication, matching, and report generation | Changing report logic, adding fields, fixing count bugs |
| `parser/tests/test_regression.py` | Regression tests for the parser | Verifying parser changes, adding test cases |
| `desktop/src/App.tsx` | React UI — file pickers, settings, result tiles | Changing the user interface |
| `desktop/src/App.css` | App styling | Visual/layout changes |
| `desktop/src-tauri/src/lib.rs` | Rust Tauri commands — file dialogs, sidecar invocation | Changing how the backend calls the parser or handles files |
| `desktop/src-tauri/tauri.conf.json` | Tauri app config — window, permissions, sidecar setup | App metadata, permissions, bundling settings |

## Build & Packaging

| File/Folder | Purpose | When to Use |
|-------------|---------|-------------|
| `build_mac_app.sh` | Top-level macOS build script | Building release on macOS |
| `build_windows_exe.ps1` | Top-level Windows build script | Building release on Windows |
| `desktop/scripts/` | Node helper scripts (sidecar prep, Tauri build, macOS installer) | Debugging build pipeline |
| `parser/scripts/` | Platform-specific sidecar build scripts (PyInstaller) | Debugging sidecar bundling |
| `packaging/` | Release and installer notes | Preparing a release |

## Documentation

| File | Purpose | When to Use |
|------|---------|-------------|
| `docs/USER_GUIDE.md` | End-user instructions | Updating user-facing docs |
| `docs/RELEASE_CHECKLIST.md` | Steps for cutting a release | Shipping a new version |
| `README.md` | Project overview, quick start, prerequisites | Onboarding, updating setup instructions |

## context/

| File | Purpose |
|------|---------|
| `conventions.md` | Tech stack details, naming patterns, and project-specific standards |
| `lessons.md` | Running log of lessons learned |
