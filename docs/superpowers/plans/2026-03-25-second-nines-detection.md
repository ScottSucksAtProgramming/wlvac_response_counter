# 2nd 9s Detection Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect how many missed calls were "2nd 9s" — calls that came in while the on-duty WLVAC unit was already on another call.

**Architecture:** Parse the `In District` timestamp from the ESO CSV to determine when each responded call ended. Build busy windows (dispatch time → in-district time) for responded calls, then check each missed call's dispatch time against those windows. Only one crew is in service at a time.

**Tech Stack:** Python (parser), Rust/Tauri (backend), React/TypeScript (frontend)

---

## Chunk 1: Parser — ESO `In District` Parsing and 2nd 9s Logic

### Task 1: Add `in_district_dt` field to EsoCall and parse from CSV

**Files:**
- Modify: `parser/parse_dispatch_report.py:78-86` (EsoCall dataclass)
- Modify: `parser/parse_dispatch_report.py:171-222` (parse_eso_calls raw_rows loop)
- Modify: `parser/parse_dispatch_report.py:248-267` (EsoCall construction in clusters)
- Modify: `parser/parse_dispatch_report.py:281-291` (EsoCall construction in no-dt group)

- [ ] **Step 1: Write failing test for In District parsing**

Add to `parser/tests/test_regression.py`:

```python
def test_in_district_parsed_from_eso(self) -> None:
    parser = Path(__file__).resolve().parents[1] / "parse_dispatch_report.py"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        dispatch = tmp_path / "Report.xls"
        eso = tmp_path / "Responses.csv"
        out = tmp_path / "summary.txt"
        dispatch.write_text(_make_dispatch_html(), encoding="utf-8")
        eso.write_text(
            "Incident Number,Unit,Scene Address 1,In District\n"
            "AAA-1,292,10 MAIN ST,2026-01-01 11:00:00.000\n",
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                sys.executable,
                str(parser),
                str(dispatch),
                "--eso-file",
                str(eso),
                "--exclude-units",
                "290,291",
                "--wlvac-units",
                "292,293,294",
                "-o",
                str(out),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
```

- [ ] **Step 2: Run test to verify it passes (baseline — no assertion on In District yet)**

Run: `python3 -m unittest parser/tests/test_regression.py -v`
Expected: PASS (the parser should not crash on the new column)

- [ ] **Step 3: Add `in_district_dt` to EsoCall dataclass**

In `parser/parse_dispatch_report.py`, modify the `EsoCall` dataclass (line 78-86):

```python
@dataclass
class EsoCall:
    eso_id: str
    units: list[str]
    address_raw: str
    address_key: str
    event_dt: datetime | None
    row_index: int
    source_ids: list[str] = field(default_factory=list)
    in_district_dt: datetime | None = None
```

- [ ] **Step 4: Parse `In District` in `parse_eso_calls`**

In the `raw_rows` loop (after line 212 where `event_dt` is parsed), add:

```python
        in_district_value = _get_csv_value(
            row,
            ["In District", "In District Date/Time", "In District Date Time"],
        )
        in_district_dt = parse_any_datetime(in_district_value)
        raw_rows.append(
            {
                "incident": incident,
                "unit": unit,
                "address_raw": address,
                "address_key": address_key,
                "event_dt": event_dt,
                "in_district_dt": in_district_dt,
                "row_index": idx,
            }
        )
```

Note: The `parse_any_datetime` function already supports `%Y-%m-%d %H:%M:%S` format, but the ESO timestamps have `.000` millisecond suffix. Add `%Y-%m-%d %H:%M:%S.%f` to the `parse_any_datetime` formats tuple.

- [ ] **Step 5: Propagate `in_district_dt` through EsoCall construction**

In the cluster loop (around line 248-267), when constructing `EsoCall`, use the latest `in_district_dt` from the cluster:

```python
            # After collecting units and source_ids from cluster items
            latest_in_district = None
            for item in cluster:
                idt = item.get("in_district_dt")
                if idt is not None:
                    if latest_in_district is None or idt > latest_in_district:
                        latest_in_district = idt
            # ... existing EsoCall construction ...
            calls.append(
                EsoCall(
                    eso_id=eso_id,
                    units=sort_units(units),
                    address_raw=first["address_raw"],
                    address_key=address_key,
                    event_dt=first["event_dt"],
                    row_index=first["row_index"],
                    source_ids=source_ids,
                    in_district_dt=latest_in_district,
                )
            )
```

Do the same for the no-dt group construction (around line 281-291).

- [ ] **Step 6: Run tests**

Run: `python3 -m unittest parser/tests/test_regression.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add parser/parse_dispatch_report.py parser/tests/test_regression.py
git commit -m "feat: parse In District timestamp from ESO CSV"
```

### Task 2: Propagate `in_district_dt` to merged calls and detect 2nd 9s

**Files:**
- Modify: `parser/parse_dispatch_report.py:423-478` (match_dispatch_to_eso_calls)
- Modify: `parser/parse_dispatch_report.py:521-659` (write_summary)

- [ ] **Step 1: Write failing test for 2nd 9s detection**

Add to `parser/tests/test_regression.py`:

```python
def test_second_nines_detection(self) -> None:
    """A missed call during an active response should be flagged as a 2nd 9."""
    parser_script = Path(__file__).resolve().parents[1] / "parse_dispatch_report.py"

    def row(date: str, time: str, message: str) -> str:
        return f'<tr class="toprow"><td>{date}</td><td>{time}</td><td>addr</td><td>{message}</td></tr>'

    # Call 1: dispatched 10:00, unit 292 responds, in district at 11:00
    # Call 2: dispatched 10:30 (during call 1's busy window) — should be 2nd 9
    # Call 3: dispatched 12:00 (after call 1 cleared) — NOT a 2nd 9
    html = "<html><table>"
    html += row("01/05/2026", "10:00:00",
                "Call Type: Test\nAddress: 10 MAIN ST\nCFS Number: 100\nUnit: 292\nTX: ok\n[2026-00001 X]")
    html += row("01/05/2026", "10:30:00",
                "Call Type: Test\nAddress: 20 OAK AVE\nCFS Number: 101\nUnit: 292\nTX: ok\n[2026-00002 X]")
    html += row("01/05/2026", "12:00:00",
                "Call Type: Test\nAddress: 30 ELM ST\nCFS Number: 102\nUnit: 292\nTX: ok\n[2026-00003 X]")
    html += "</table></html>"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        dispatch = tmp_path / "Report.xls"
        eso = tmp_path / "Responses.csv"
        out = tmp_path / "summary.txt"
        dispatch.write_text(html, encoding="utf-8")
        # Only call 1 has an ESO match (responded). Calls 2 and 3 are missed.
        eso.write_text(
            "Incident Number,Unit,Scene Address 1,In District\n"
            "ESO-1,292,10 MAIN ST,2026-01-05 11:00:00.000\n",
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                sys.executable,
                str(parser_script),
                str(dispatch),
                "--eso-file",
                str(eso),
                "--exclude-units", "290,291",
                "--wlvac-units", "292,293,294",
                "-o", str(out),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        summary = out.read_text(encoding="utf-8")

        self.assertEqual(_parse_value(summary, "Calls we went to"), "1")
        self.assertEqual(_parse_value(summary, "Calls missed"), "2")
        # Call 2 (10:30) overlaps with call 1's 10:00-11:00 window → 2nd 9
        # Call 3 (12:00) does not overlap → not a 2nd 9
        self.assertEqual(_parse_value(summary, "Missed calls that were 2nd 9s"), "1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest parser/tests/test_regression.py -v`
Expected: FAIL — "Missing key in summary: Missed calls that were 2nd 9s"

- [ ] **Step 3: Store `in_district_dt` on matched calls in `match_dispatch_to_eso_calls`**

After `call["matched_eso_source_ids"] = chosen.source_ids` (line 478), add:

```python
        call["in_district_dt"] = chosen.in_district_dt
```

Also add `call["in_district_dt"] = None` in the no-candidates branch (after line 453).

- [ ] **Step 4: Add 2nd 9s detection logic in `write_summary`**

After the `daytime_missed` / `primary_missed` block (around line 588), add:

```python
    # 2nd 9s detection: missed calls that arrived during an active response
    second_nines_count = 0
    second_nines_ids: list[str] = []
    if eso_calls is not None:
        # Build busy windows from responded calls with valid timestamps
        busy_windows: list[tuple[datetime, datetime]] = []
        for call in merged_calls:
            if not call["responded"]:
                continue
            start = call.get("first_received")
            end = call.get("in_district_dt")
            if start is not None and end is not None and end > start:
                busy_windows.append((start, end))

        # Check each missed call against busy windows
        for call in merged_calls:
            if call["responded"] or call.get("likely_outside_agency"):
                continue
            dispatch_dt = call.get("first_received")
            if dispatch_dt is None:
                continue
            for window_start, window_end in busy_windows:
                if window_start <= dispatch_dt <= window_end:
                    second_nines_count += 1
                    second_nines_ids.append(call["call_id"])
                    break
```

- [ ] **Step 5: Add 2nd 9s to text output**

After the missed-calls-during-primary lines (around line 611), add:

```python
    lines.append(f"Missed calls that were 2nd 9s: {second_nines_count}")
```

- [ ] **Step 6: Add 2nd 9s to JSON summary**

In the return dict (around line 656), add:

```python
        "missed_calls_second_nines": second_nines_count,
        "second_nines_call_ids": second_nines_ids,
```

- [ ] **Step 7: Run tests**

Run: `python3 -m unittest parser/tests/test_regression.py -v`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add parser/parse_dispatch_report.py parser/tests/test_regression.py
git commit -m "feat: detect 2nd 9s (missed calls during active responses)"
```

## Chunk 2: Rust Backend and React Frontend

### Task 3: Add 2nd 9s field to Rust backend

**Files:**
- Modify: `desktop/src-tauri/src/lib.rs:22-31` (SummaryCounts struct)
- Modify: `desktop/src-tauri/src/lib.rs:102-134` (parse_summary_counts)

- [ ] **Step 1: Add field to `SummaryCounts` struct**

Add after `missed_calls_primary`:

```rust
  missed_calls_second_nines: String,
```

- [ ] **Step 2: Initialize in `parse_summary_counts`**

Add to the struct initializer:

```rust
    missed_calls_second_nines: "n/a".into(),
```

- [ ] **Step 3: Parse the new line**

Add to the `for line in summary_text.lines()` block:

```rust
    } else if let Some(v) = line.strip_prefix("Missed calls that were 2nd 9s: ") {
      counts.missed_calls_second_nines = v.trim().to_string();
    }
```

- [ ] **Step 4: Verify Rust compiles**

Run: `cd desktop && npm run build`
Expected: TypeScript + Rust compile successfully

- [ ] **Step 5: Commit**

```bash
git add desktop/src-tauri/src/lib.rs
git commit -m "feat: parse 2nd 9s count in Rust backend"
```

### Task 4: Add 2nd 9s tile to React frontend

**Files:**
- Modify: `desktop/src/App.tsx:6-15` (Counts type)
- Modify: `desktop/src/App.tsx:243-253` (Missed Calls by Time section)

- [ ] **Step 1: Add field to `Counts` type**

Add after `missedCallsPrimary`:

```typescript
  missedCallsSecondNines: string;
```

- [ ] **Step 2: Add tile to the "Missed Calls by Time" section**

Change the `tiles-2` div to `tiles-3` and add a third tile:

```tsx
        <h3 className="section-label">Missed Calls by Time</h3>
        <div className="tiles tiles-3">
          <article>
            <span>Missed Daytime</span>
            <strong>{result?.counts.missedCallsDaytime ?? "-"}</strong>
          </article>
          <article>
            <span>Missed Primary</span>
            <strong>{result?.counts.missedCallsPrimary ?? "-"}</strong>
          </article>
          <article>
            <span>2nd 9s</span>
            <strong>{result?.counts.missedCallsSecondNines ?? "-"}</strong>
          </article>
        </div>
```

- [ ] **Step 3: Add `tiles-3` CSS class**

In `desktop/src/App.css`, add after `.tiles-2`:

```css
.tiles-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
```

- [ ] **Step 4: Verify build**

Run: `cd desktop && npm run build`
Expected: Compiles successfully

- [ ] **Step 5: Commit**

```bash
git add desktop/src/App.tsx desktop/src/App.css
git commit -m "feat: display 2nd 9s count in UI"
```

### Task 5: End-to-end verification

- [ ] **Step 1: Run all regression tests**

Run: `python3 -m unittest parser/tests/test_regression.py -v`
Expected: All PASS

- [ ] **Step 2: Run full Tauri dev build**

Run: `cd desktop && npm run tauri:dev`
Expected: App launches, all tiles render with data when reports are loaded

- [ ] **Step 3: Final commit if any cleanup needed**
