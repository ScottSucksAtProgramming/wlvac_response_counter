#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

zsh parser/scripts/build_sidecar_macos.sh

cd desktop
npm install
npm run tauri:build

echo "Built macOS desktop app bundle via Tauri."
