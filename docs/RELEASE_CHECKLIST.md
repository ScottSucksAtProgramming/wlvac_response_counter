# Release Checklist

## 1) Pre-flight

1. Ensure dependencies are installed:
   - Node + npm
   - Rust toolchain
   - Python 3
2. Confirm parser logic changes (if any) are tested.

## 2) Validate locally

### Parser tests

```bash
python3 -m unittest discover -s parser/tests -p 'test_*.py'
```

### Desktop checks

```bash
cd desktop
npm install
npm run lint
npm run build
```

## 3) Build installers

### macOS

```bash
cd desktop
npm run tauri:build
```

Expected artifact:

- `desktop/src-tauri/target/release/bundle/macos/WLVAC Response Counts.app`

### Windows (run on Windows)

```powershell
cd desktop
npm install
npm run tauri:build
```

Expected artifacts:

- `desktop\src-tauri\target\release\bundle\msi\...`
- `desktop\src-tauri\target\release\bundle\nsis\...`

## 4) Smoke test release build

Using real sample files:

1. Select dispatch report
2. Select ESO report
3. Generate summary
4. Verify counts appear
5. Verify **Open Output** works
6. Verify generated text report contains expected header counts

## 5) GitHub prep

1. Remove sensitive sample data before public publishing.
2. Confirm `.gitignore` excludes generated files.
3. Update version number (`desktop/src-tauri/tauri.conf.json`) if releasing.
4. Commit with release notes summary.

## 6) Publish

1. Push to GitHub.
2. Create release/tag.
3. Attach platform installers/app bundles.
