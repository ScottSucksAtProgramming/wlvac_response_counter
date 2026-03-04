import { spawnSync } from "node:child_process";

function run(cmd, args) {
  const res = spawnSync(cmd, args, { stdio: "inherit", shell: process.platform === "win32" });
  if (res.status !== 0) process.exit(res.status ?? 1);
}

if (process.platform === "darwin") {
  // Build app bundle first.
  run("npx", ["tauri", "build", "--bundles", "app"]);
  // Create installer DMG with Applications shortcut for drag-and-drop install UX.
  run("node", ["scripts/create-macos-installer.mjs"]);
} else if (process.platform === "win32") {
  run("npx", ["tauri", "build", "--bundles", "msi,nsis"]);
} else {
  run("npx", ["tauri", "build"]);
}
