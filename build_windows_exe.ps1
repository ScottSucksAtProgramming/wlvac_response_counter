Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

powershell -ExecutionPolicy Bypass -File ".\parser\scripts\build_sidecar_windows.ps1"

$desktopDir = Join-Path $scriptDir "desktop"
$vswherePath = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"

if (-not (Test-Path $vswherePath)) {
  throw "vswhere.exe not found. Install Visual Studio 2022 Build Tools with Desktop C++ workload."
}

$vsInstallPath = & $vswherePath `
  -latest `
  -products * `
  -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
  -property installationPath

if (-not $vsInstallPath) {
  throw "Visual C++ toolchain not found. Install Visual Studio 2022 Build Tools with Desktop C++ workload."
}

$vsDevCmd = Join-Path $vsInstallPath "Common7\Tools\VsDevCmd.bat"
if (-not (Test-Path $vsDevCmd)) {
  throw "VsDevCmd.bat not found at '$vsDevCmd'."
}

Set-Location $desktopDir

$buildCmd = "`"$vsDevCmd`" -arch=x64 && set PATH=%USERPROFILE%\.cargo\bin;%PATH% && npm install && npm run tauri:build"
& cmd.exe /c $buildCmd
if ($LASTEXITCODE -ne 0) {
  throw "Windows desktop build failed with exit code $LASTEXITCODE."
}

Write-Host "Built Windows desktop installer via Tauri."
