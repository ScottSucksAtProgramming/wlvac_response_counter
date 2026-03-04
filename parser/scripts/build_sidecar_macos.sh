#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARSER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PARSER_DIR/binaries"

mkdir -p "$OUTPUT_DIR"
cd "$PARSER_DIR"
python3 -m pip install --upgrade pyinstaller
python3 -m PyInstaller \
  --noconfirm \
  --onefile \
  --name parse_dispatch_report-macos \
  "parse_dispatch_report.py"

cp "$PARSER_DIR/dist/parse_dispatch_report-macos" "$OUTPUT_DIR/parse_dispatch_report-macos"
chmod +x "$OUTPUT_DIR/parse_dispatch_report-macos"
echo "Built $OUTPUT_DIR/parse_dispatch_report-macos"
