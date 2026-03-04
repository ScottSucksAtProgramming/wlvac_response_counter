Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$parserDir = Resolve-Path (Join-Path $scriptDir "..")
$outputDir = Join-Path $parserDir "binaries"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
Set-Location $parserDir

py -m pip install --upgrade pyinstaller
py -m PyInstaller `
  --noconfirm `
  --onefile `
  --name "parse_dispatch_report-windows" `
  "parse_dispatch_report.py"

Copy-Item `
  (Join-Path $parserDir "dist\\parse_dispatch_report-windows.exe") `
  (Join-Path $outputDir "parse_dispatch_report-windows.exe") `
  -Force

Write-Host "Built $outputDir\\parse_dispatch_report-windows.exe"
