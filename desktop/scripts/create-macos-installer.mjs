import { execSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, rmSync, symlinkSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const desktopRoot = path.resolve(__dirname, "..");
const releaseBundleDir = path.join(desktopRoot, "src-tauri", "target", "release", "bundle", "macos");

const appName = "WLVAC Response Counts.app";
const appPath = path.join(releaseBundleDir, appName);
if (!existsSync(appPath)) {
  console.error(`Missing app bundle at ${appPath}. Run Tauri build first.`);
  process.exit(1);
}

const dmgName = "WLVAC Response Counts_0.1.0_aarch64_installer.dmg";
const outDmg = path.join(releaseBundleDir, dmgName);
const stageDir = path.join(releaseBundleDir, ".dmg_staging");

rmSync(stageDir, { recursive: true, force: true });
mkdirSync(stageDir, { recursive: true });

cpSync(appPath, path.join(stageDir, appName), { recursive: true });
symlinkSync("/Applications", path.join(stageDir, "Applications"));

rmSync(outDmg, { force: true });
execSync(
  `hdiutil create -volname "WLVAC Response Counts" -srcfolder "${stageDir}" -ov -format UDZO "${outDmg}"`,
  { stdio: "inherit" },
);

rmSync(stageDir, { recursive: true, force: true });
console.log(`Created installer DMG: ${outDmg}`);
