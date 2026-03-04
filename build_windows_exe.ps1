Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

powershell -ExecutionPolicy Bypass -File ".\parser\scripts\build_sidecar_windows.ps1"

Set-Location (Join-Path $scriptDir "desktop")
npm install
npm run tauri:build

Write-Host "Built Windows desktop installer via Tauri."
