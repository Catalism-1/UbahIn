use serde_json::{json, Value};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::time::{Duration, SystemTime};
use tauri::AppHandle;
use tauri_plugin_shell::{process::CommandEvent, ShellExt};
use tokio::time::timeout;

const ENGINE_SIDECAR: &str = "ubahin-engine";
const ENGINE_TIMEOUT: Duration = Duration::from_secs(10);

pub async fn request_engine(app: &AppHandle, action: &str) -> Result<Value, String> {
    let request_id = format!("tauri-{:?}", SystemTime::now());
    let request = json!({
        "id": request_id,
        "action": action,
    });

    let shell = app.shell();
    let command = shell
        .sidecar(ENGINE_SIDECAR)
        .map_err(|error| {
            log_error(format!("Gagal menyiapkan sidecar: {error}"));
            "Engine Python tidak ditemukan atau belum dibangun.".to_string()
        })?
        .args(["--stdio"]);

    let (mut rx, mut child) = command.spawn().map_err(|error| {
        log_error(format!("Gagal menjalankan sidecar: {error}"));
        "Engine Python tidak dapat dijalankan.".to_string()
    })?;

    let line = format!("{}\n", request);
    child.write(line.as_bytes()).map_err(|error| {
        log_error(format!("Gagal mengirim request ke sidecar: {error}"));
        "Engine Python tidak dapat menerima request.".to_string()
    })?;

    let response_result = timeout(ENGINE_TIMEOUT, async {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let text = String::from_utf8_lossy(&bytes);
                    for line in text.lines() {
                        let trimmed = line.trim();
                        if trimmed.is_empty() {
                            continue;
                        }
                        let value: Value = serde_json::from_str(trimmed).map_err(|error| {
                            log_error(format!("Response sidecar bukan JSON valid: {error}; raw={trimmed}"));
                            "Engine mengirim response yang tidak valid.".to_string()
                        })?;
                        return Ok(value);
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    let text = String::from_utf8_lossy(&bytes);
                    if !text.trim().is_empty() {
                        log_error(format!("stderr sidecar: {}", text.trim()));
                    }
                }
                CommandEvent::Terminated(payload) => {
                    log_error(format!("Sidecar berhenti sebelum response: {payload:?}"));
                    return Err("Engine berhenti sebelum mengirim response.".to_string());
                }
                _ => {}
            }
        }
        Err("Engine berhenti tanpa response.".to_string())
    })
    .await;

    let _ = child.kill();

    let response = response_result
        .map_err(|_| {
            log_error(format!("Timeout request sidecar untuk action={action}"));
            "Engine terlalu lama merespons.".to_string()
        })??;

    Ok(response)
}

pub fn open_logs() -> Result<(), String> {
    let dir = log_dir();
    fs::create_dir_all(&dir).map_err(|error| format!("Folder log tidak dapat dibuat: {error}"))?;
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("explorer")
            .arg(&dir)
            .spawn()
            .map_err(|error| format!("Folder log tidak dapat dibuka: {error}"))?;
        return Ok(());
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(format!("Membuka folder log belum didukung di platform ini: {}", dir.display()))
    }
}

fn log_dir() -> PathBuf {
    if let Ok(local_app_data) = std::env::var("LOCALAPPDATA") {
        return PathBuf::from(local_app_data).join("Ubahin").join("logs");
    }
    std::env::temp_dir().join("Ubahin").join("logs")
}

fn log_error(message: impl AsRef<str>) {
    let dir = log_dir();
    let _ = fs::create_dir_all(&dir);
    let path = dir.join("tauri.log");
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) {
        let _ = writeln!(file, "{:?} | {}", SystemTime::now(), message.as_ref());
    }
}
