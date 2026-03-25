use chrono::Local;
use rfd::FileDialog;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use tauri::AppHandle;
use tauri::Manager;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RunSummaryRequest {
  dispatch_path: String,
  eso_path: String,
  output_dir: String,
  exclude_units: String,
  wlvac_units: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct SummaryCounts {
  calls_assigned_to_us: String,
  calls_we_went_to: String,
  calls_missed: String,
  calls_likely_handled_by_outside_agency: String,
  daytime_calls: String,
  primary_calls: String,
  missed_calls_daytime: String,
  missed_calls_primary: String,
  missed_calls_second_nines: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct RunSummaryResponse {
  success: bool,
  output_path: String,
  stdout: String,
  stderr: String,
  counts: SummaryCounts,
}

fn parser_sidecar_name() -> &'static str {
  if cfg!(target_os = "windows") {
    "parse_dispatch_report-windows.exe"
  } else if cfg!(target_os = "macos") {
    "parse_dispatch_report-macos"
  } else {
    "parse_dispatch_report-linux"
  }
}

fn find_file_recursive(dir: &Path, filename: &str) -> Option<PathBuf> {
  let entries = fs::read_dir(dir).ok()?;
  for entry in entries.flatten() {
    let path = entry.path();
    if path.is_file() {
      if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
        if name == filename {
          return Some(path);
        }
      }
    } else if path.is_dir() {
      if let Some(found) = find_file_recursive(&path, filename) {
        return Some(found);
      }
    }
  }
  None
}

fn resolve_parser_command(app: &AppHandle) -> Result<(PathBuf, Vec<String>), String> {
  let sidecar = parser_sidecar_name();
  if let Ok(resource_dir) = app.path().resource_dir() {
    if let Some(sidecar_path) = find_file_recursive(&resource_dir, sidecar) {
      return Ok((sidecar_path, vec![]));
    }
  }

  let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
  let parser_script = manifest_dir
    .join("..")
    .join("..")
    .join("parser")
    .join("parse_dispatch_report.py");
  if !parser_script.exists() {
    return Err(format!(
      "Parser not found. Expected bundled sidecar ({}) or script at {}",
      sidecar,
      parser_script.display()
    ));
  }

  let python_bin = if cfg!(target_os = "windows") {
    PathBuf::from("python")
  } else {
    PathBuf::from("python3")
  };
  Ok((python_bin, vec![parser_script.to_string_lossy().to_string()]))
}

fn parse_summary_counts(summary_text: &str) -> SummaryCounts {
  let mut counts = SummaryCounts {
    calls_assigned_to_us: "n/a".into(),
    calls_we_went_to: "n/a".into(),
    calls_missed: "n/a".into(),
    calls_likely_handled_by_outside_agency: "n/a".into(),
    daytime_calls: "n/a".into(),
    primary_calls: "n/a".into(),
    missed_calls_daytime: "n/a".into(),
    missed_calls_primary: "n/a".into(),
    missed_calls_second_nines: "n/a".into(),
  };

  for line in summary_text.lines() {
    if let Some(v) = line.strip_prefix("Calls assigned to us: ") {
      counts.calls_assigned_to_us = v.trim().to_string();
    } else if let Some(v) = line.strip_prefix("Calls we went to: ") {
      counts.calls_we_went_to = v.trim().to_string();
    } else if let Some(v) = line.strip_prefix("Calls missed: ") {
      counts.calls_missed = v.trim().to_string();
    } else if let Some(v) = line.strip_prefix("Calls likely handled by outside agency: ") {
      counts.calls_likely_handled_by_outside_agency = v.trim().to_string();
    } else if let Some(v) = line.strip_prefix("Daytime calls (M-F 0700-1900): ") {
      counts.daytime_calls = v.trim().to_string();
    } else if let Some(v) = line.strip_prefix("Primary calls (nights/weekends): ") {
      counts.primary_calls = v.trim().to_string();
    } else if let Some(v) = line.strip_prefix("Missed calls during daytime: ") {
      counts.missed_calls_daytime = v.trim().to_string();
    } else if let Some(v) = line.strip_prefix("Missed calls during primary: ") {
      counts.missed_calls_primary = v.trim().to_string();
    } else if let Some(v) = line.strip_prefix("Missed calls that were 2nd 9s: ") {
      counts.missed_calls_second_nines = v.trim().to_string();
    }
  }
  counts
}

#[tauri::command]
fn pick_dispatch_file() -> Option<String> {
  FileDialog::new()
    .add_filter("Dispatch report", &["xls", "xlsx"])
    .set_title("Select DISPATCH report (.xls export)")
    .pick_file()
    .map(|p| p.to_string_lossy().to_string())
}

#[tauri::command]
fn pick_eso_file() -> Option<String> {
  FileDialog::new()
    .add_filter("ESO/ePCR report", &["csv"])
    .set_title("Select ESO/ePCR Responses report (.csv)")
    .pick_file()
    .map(|p| p.to_string_lossy().to_string())
}

#[tauri::command]
fn pick_output_dir() -> Option<String> {
  FileDialog::new()
    .set_title("Select output folder")
    .pick_folder()
    .map(|p| p.to_string_lossy().to_string())
}

#[tauri::command]
fn default_output_dir(app: AppHandle) -> String {
  if let Ok(dir) = app.path().download_dir() {
    return dir.to_string_lossy().to_string();
  }
  if let Ok(dir) = app.path().app_local_data_dir() {
    return dir.to_string_lossy().to_string();
  }
  ".".to_string()
}

#[tauri::command]
fn open_path(path: String) -> Result<(), String> {
  let p = Path::new(&path);
  if !p.exists() {
    return Err(format!("Path does not exist: {}", p.display()));
  }

  #[cfg(target_os = "windows")]
  {
    Command::new("cmd")
      .args(["/C", "start", "", &path])
      .status()
      .map_err(|e| format!("Failed to open path: {e}"))?;
  }
  #[cfg(target_os = "macos")]
  {
    Command::new("open")
      .arg(path)
      .status()
      .map_err(|e| format!("Failed to open path: {e}"))?;
  }
  #[cfg(all(unix, not(target_os = "macos")))]
  {
    Command::new("xdg-open")
      .arg(path)
      .status()
      .map_err(|e| format!("Failed to open path: {e}"))?;
  }
  Ok(())
}

#[tauri::command]
fn run_summary(app: AppHandle, req: RunSummaryRequest) -> Result<RunSummaryResponse, String> {
  let dispatch_path = PathBuf::from(req.dispatch_path.trim());
  let eso_path = PathBuf::from(req.eso_path.trim());
  let output_dir = PathBuf::from(req.output_dir.trim());

  if !dispatch_path.exists() {
    return Err(format!("Dispatch file not found: {}", dispatch_path.display()));
  }
  if !eso_path.exists() {
    return Err(format!("ESO file not found: {}", eso_path.display()));
  }
  if !output_dir.exists() {
    return Err(format!("Output directory not found: {}", output_dir.display()));
  }

  let ts = Local::now().format("%y%m%d-%H%M%S").to_string();
  let output_path = output_dir.join(format!("WLVACResponseCounts-{}.txt", ts));
  let json_path = output_dir.join(format!("WLVACResponseCounts-{}.json", ts));

  let (program, mut pre_args) = resolve_parser_command(&app)?;
  let mut cmd = Command::new(program);
  for arg in pre_args.drain(..) {
    cmd.arg(arg);
  }
  cmd
    .arg(dispatch_path.to_string_lossy().to_string())
    .arg("--eso-file")
    .arg(eso_path.to_string_lossy().to_string())
    .arg("--exclude-units")
    .arg(req.exclude_units.trim())
    .arg("--wlvac-units")
    .arg(req.wlvac_units.trim())
    .arg("--json-summary")
    .arg(json_path.to_string_lossy().to_string())
    .arg("-o")
    .arg(output_path.to_string_lossy().to_string());

  let output = cmd
    .output()
    .map_err(|e| format!("Failed to execute parser: {e}"))?;
  let stdout = String::from_utf8_lossy(&output.stdout).to_string();
  let stderr = String::from_utf8_lossy(&output.stderr).to_string();
  if !output.status.success() {
    return Err(if stderr.trim().is_empty() {
      format!("Parser failed. {}", stdout.trim())
    } else {
      stderr
    });
  }

  let summary_text = fs::read_to_string(&output_path)
    .map_err(|e| format!("Failed to read output file {}: {e}", output_path.display()))?;
  let counts = parse_summary_counts(&summary_text);

  Ok(RunSummaryResponse {
    success: true,
    output_path: output_path.to_string_lossy().to_string(),
    stdout,
    stderr,
    counts,
  })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .plugin(tauri_plugin_opener::init())
    .invoke_handler(tauri::generate_handler![
      pick_dispatch_file,
      pick_eso_file,
      pick_output_dir,
      default_output_dir,
      open_path,
      run_summary
    ])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
