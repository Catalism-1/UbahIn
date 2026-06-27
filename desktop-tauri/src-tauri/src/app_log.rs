use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::time::SystemTime;

pub fn log_info(message: impl AsRef<str>) {
    write_log("INFO", message.as_ref());
}

pub fn log_error(message: impl AsRef<str>) {
    write_log("ERROR", message.as_ref());
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

fn write_log(level: &str, message: &str) {
    let dir = log_dir();
    let _ = fs::create_dir_all(&dir);
    let path = dir.join("tauri.log");
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) {
        let _ = writeln!(file, "{:?} | {level} | {message}", SystemTime::now());
    }
}
