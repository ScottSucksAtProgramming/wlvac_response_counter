import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, statSync, unlinkSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const parserDir = path.join(repoRoot, "parser");
const parserSource = path.join(parserDir, "parse_dispatch_report.py");
const binariesDir = path.join(parserDir, "binaries");

const platformMap = {
  darwin: "parse_dispatch_report-macos",
  win32: "parse_dispatch_report-windows.exe",
  linux: "parse_dispatch_report-linux",
};

const targetName = platformMap[process.platform];
if (!targetName) {
  console.error(`Unsupported platform for sidecar build: ${process.platform}`);
  process.exit(1);
}

const targetBinary = path.join(binariesDir, targetName);
if (existsSync(targetBinary)) {
  const sourceMtime = statSync(parserSource).mtimeMs;
  const binaryMtime = statSync(targetBinary).mtimeMs;
  if (sourceMtime > binaryMtime) {
    console.log(`Parser source is newer than sidecar — rebuilding...`);
    unlinkSync(targetBinary);
  } else {
    console.log(`Parser sidecar is up to date: ${targetBinary}`);
    process.exit(0);
  }
}

if (!existsSync(parserSource)) {
  console.error(`Parser source not found: ${parserSource}`);
  process.exit(1);
}

mkdirSync(binariesDir, { recursive: true });

function run(command, args, cwd = parserDir) {
  const result = spawnSync(command, args, {
    cwd,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

const pythonCmd = process.platform === "win32" ? "py" : "python3";
const pyInstallerModule = "PyInstaller";

console.log(`Building parser sidecar for ${process.platform}...`);
run(pythonCmd, ["-m", "pip", "install", "--upgrade", "pyinstaller"]);
run(pythonCmd, [
  "-m",
  pyInstallerModule,
  "--noconfirm",
  "--onefile",
  "--name",
  targetName,
  "parse_dispatch_report.py",
]);

const builtBinary = path.join(parserDir, "dist", targetName);
if (!existsSync(builtBinary)) {
  console.error(`Expected PyInstaller output not found: ${builtBinary}`);
  process.exit(1);
}

copyFileSync(builtBinary, targetBinary);
console.log(`Built parser sidecar: ${targetBinary}`);
