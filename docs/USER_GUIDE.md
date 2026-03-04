# User Guide

## What this app does

The app compares:

1. Dispatch report (`.xls` export)
2. ESO/ePCR Responses report (`.csv`)

Then generates a text report with:

- Calls assigned to us
- Calls we went to
- Calls missed (excluding likely outside-agency calls)
- Calls likely handled by outside agency
- Detailed per-call section

## Using the app

1. Open **WLVAC Response Counts** app.
2. Click **Browse** next to:
   - Dispatch Report (`.xls`)
   - ESO/ePCR Responses Report (`.csv`)
   - Output Folder
3. (Optional) Expand **Advanced Settings**:
   - Exclude Units: default `290,291`
   - WLVAC Units: default `292,293,294`
4. Click **Generate Summary**.
5. Review counts in the **Results** section.
6. Click **Open Output** to open the generated `.txt` report.

## Output file naming

Each run creates:

- `WLVACResponseCounts-YYMMDD-HHMMSS.txt`

in the selected output folder.

## Troubleshooting

### "Not allowed to open path ... by ACL"

Use the latest rebuilt app bundle/installer. That permission issue was fixed in newer builds.

### "Input file not found" or "No report rows found"

- Confirm dispatch file is the correct HTML-export `.xls` report.
- Confirm ESO file is the correct Responses `.csv`.

### Counts look off

Check:

- Exclude Units setting
- WLVAC Units setting
- Whether dispatch IDs were reused across addresses (handled by current logic)
- Whether ESO export is missing addresses/units
