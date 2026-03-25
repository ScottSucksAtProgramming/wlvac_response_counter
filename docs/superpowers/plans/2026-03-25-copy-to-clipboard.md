# Copy Output to Clipboard Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Copy Output" button that copies the full generated report text to the clipboard.

**Architecture:** Add `tauri-plugin-clipboard-manager` to the Rust backend with a new `copy_output_to_clipboard` Tauri command that reads the output file and writes it to the system clipboard. The React frontend adds a button with "Copied!" feedback state.

**Tech Stack:** Rust/Tauri (tauri-plugin-clipboard-manager), React/TypeScript, CSS

---

## Chunk 1: Rust Backend — Clipboard Plugin and Command

### Task 1: Add clipboard plugin dependency and command

**Files:**
- Modify: `desktop/src-tauri/Cargo.toml` (add dependency)
- Modify: `desktop/src-tauri/src/lib.rs` (add command and register plugin)
- Modify: `desktop/src-tauri/capabilities/default.json` (add clipboard permission)
- Modify: `desktop/package.json` (add npm plugin package)

- [ ] **Step 1: Add Rust and npm dependencies**

In `desktop/src-tauri/Cargo.toml`, add to `[dependencies]`:

```toml
tauri-plugin-clipboard-manager = "2"
```

In `desktop/package.json`, add to `"dependencies"`:

```json
"@tauri-apps/plugin-clipboard-manager": "^2.2.1"
```

Run: `cd desktop && npm install`

- [ ] **Step 2: Add clipboard permission to capabilities**

In `desktop/src-tauri/capabilities/default.json`, add to `"permissions"` array:

```json
"clipboard-manager:allow-write-text"
```

- [ ] **Step 3: Register the clipboard plugin in lib.rs**

In `desktop/src-tauri/src/lib.rs`, in the `run()` function, add the plugin registration after `tauri_plugin_opener::init()`:

```rust
    .plugin(tauri_plugin_clipboard_manager::init())
```

- [ ] **Step 4: Add the `copy_output_to_clipboard` Tauri command**

In `desktop/src-tauri/src/lib.rs`, add the new command:

```rust
#[tauri::command]
fn copy_output_to_clipboard(app: AppHandle, path: String) -> Result<String, String> {
  let p = Path::new(&path);
  if !p.exists() {
    return Err(format!("Output file not found: {}", p.display()));
  }
  let content = fs::read_to_string(p)
    .map_err(|e| format!("Failed to read output file: {e}"))?;
  app.clipboard().write_text(&content)
    .map_err(|e| format!("Failed to copy to clipboard: {e}"))?;
  Ok(content.lines().count().to_string())
}
```

Add this import at the top of the file:

```rust
use tauri_plugin_clipboard_manager::ClipboardExt;
```

- [ ] **Step 5: Register the command in the invoke handler**

Add `copy_output_to_clipboard` to the `generate_handler!` macro:

```rust
    .invoke_handler(tauri::generate_handler![
      pick_dispatch_file,
      pick_eso_file,
      pick_output_dir,
      default_output_dir,
      open_path,
      run_summary,
      copy_output_to_clipboard
    ])
```

- [ ] **Step 6: Verify Rust compiles**

Run: `cd desktop && npx tauri build --debug 2>&1 | tail -5`
Or for faster feedback: `cd desktop/src-tauri && cargo check`
Expected: Compiles successfully

- [ ] **Step 7: Commit**

```bash
git add desktop/src-tauri/Cargo.toml desktop/src-tauri/src/lib.rs desktop/src-tauri/capabilities/default.json desktop/package.json desktop/package-lock.json
git commit -m "feat: add clipboard plugin and copy_output_to_clipboard command"
```

## Chunk 2: React Frontend — Button and Feedback

### Task 2: Add Copy Output button with feedback

**Files:**
- Modify: `desktop/src/App.tsx` (add button, state, handler)
- Modify: `desktop/src/App.css` (add button styles)

- [ ] **Step 1: Add copied state and handler to App.tsx**

Add a new state variable after the existing state declarations:

```typescript
const [copied, setCopied] = useState(false);
```

Add the handler function after `runSummary`:

```typescript
  async function copyOutput() {
    if (!result?.outputPath) return;
    setError("");
    try {
      await invoke("copy_output_to_clipboard", { path: result.outputPath });
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      const msg = typeof err === "string" ? err : "Failed to copy to clipboard.";
      setError(msg);
    }
  }
```

- [ ] **Step 2: Add the button to the results section**

Replace the existing `{result?.outputPath && <p className="path">Saved: {result.outputPath}</p>}` block with:

```tsx
        {result?.outputPath && (
          <div className="results-footer">
            <p className="path">Saved: {result.outputPath}</p>
            <button className="copy-btn" onClick={copyOutput} type="button">
              {copied ? "Copied!" : "Copy Output"}
            </button>
          </div>
        )}
```

- [ ] **Step 3: Add CSS styles**

In `desktop/src/App.css`, add before the `@media` query:

```css
.results-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
  gap: 12px;
}

.results-footer .path {
  margin: 0;
  min-width: 0;
}

.copy-btn {
  flex-shrink: 0;
  height: 36px;
  padding: 0 16px;
  font-size: 13px;
  white-space: nowrap;
}
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd desktop && npx tsc -b --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add desktop/src/App.tsx desktop/src/App.css
git commit -m "feat: add Copy Output button with clipboard feedback"
```

### Task 3: End-to-end verification

- [ ] **Step 1: Delete stale sidecar and rebuild**

```bash
rm -f parser/binaries/parse_dispatch_report-macos
cd desktop && npm run tauri:dev
```

- [ ] **Step 2: Verify in the running app**

1. Load dispatch and ESO reports
2. Click Generate Summary
3. Verify "Copy Output" button appears at bottom-right of results
4. Click "Copy Output" — verify it shows "Copied!" for 2 seconds
5. Paste into a text editor — verify the full report text is there

- [ ] **Step 3: Run parser regression tests**

Run: `python3 -m unittest parser/tests/test_regression.py -v`
Expected: All PASS (no parser changes in this feature)
