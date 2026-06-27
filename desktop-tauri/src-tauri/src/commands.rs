use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::path::Path;
use std::process::Command;
use tauri::State;

use crate::app_log::{log_error, log_info, open_logs};
use crate::sidecar::SidecarManager;

#[derive(Debug, Deserialize, Serialize)]
pub struct InspectPdfFilesPayload {
    paths: Vec<String>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct PdfInputFile {
    file_id: String,
    path: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct StartPdfToJpgPayload {
    job_id: String,
    files: Vec<PdfInputFile>,
    output_directory: String,
    preset: String,
    dpi: u32,
    jpeg_quality: u8,
    optimize_file_size: bool,
    create_zip: bool,
    open_output_after_finish: bool,
    performance_mode: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct JobPayload {
    job_id: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct OpenDirectoryPayload {
    path: String,
}

#[tauri::command]
pub async fn check_engine(manager: State<'_, SidecarManager>) -> Result<Value, String> {
    manager.request("health", json!({})).await
}

#[tauri::command]
pub async fn app_info(manager: State<'_, SidecarManager>) -> Result<Value, String> {
    manager.request("app_info", json!({})).await
}

#[tauri::command]
pub async fn self_check(manager: State<'_, SidecarManager>) -> Result<Value, String> {
    manager.request("self_check", json!({})).await
}

#[tauri::command]
pub fn pick_pdf_files() -> Result<Vec<String>, String> {
    let paths = rfd::FileDialog::new()
        .set_title("Pilih file PDF")
        .add_filter("PDF", &["pdf"])
        .pick_files()
        .unwrap_or_default()
        .into_iter()
        .take(50)
        .map(|path| path.to_string_lossy().to_string())
        .collect::<Vec<_>>();

    log_info(format!("picked {} PDF file(s)", paths.len()));
    Ok(paths)
}

#[tauri::command]
pub async fn inspect_pdf_files(
    manager: State<'_, SidecarManager>,
    payload: InspectPdfFilesPayload,
) -> Result<Value, String> {
    manager
        .request("inspect_pdf_files", json!({ "paths": payload.paths }))
        .await
}

#[tauri::command]
pub fn pick_output_directory() -> Result<Option<String>, String> {
    let directory = rfd::FileDialog::new()
        .set_title("Pilih folder hasil")
        .pick_folder()
        .map(|path| path.to_string_lossy().to_string());

    if let Some(path) = &directory {
        log_info(format!("picked output directory: {path}"));
    }

    Ok(directory)
}

#[tauri::command]
pub async fn start_pdf_to_jpg(
    manager: State<'_, SidecarManager>,
    payload: StartPdfToJpgPayload,
) -> Result<Value, String> {
    manager.request("start_pdf_to_jpg", json!(payload)).await
}

#[tauri::command]
pub async fn cancel_pdf_to_jpg_job(
    manager: State<'_, SidecarManager>,
    payload: JobPayload,
) -> Result<Value, String> {
    manager.request("cancel_job", json!(payload)).await
}

#[tauri::command]
pub async fn get_job_status(
    manager: State<'_, SidecarManager>,
    payload: JobPayload,
) -> Result<Value, String> {
    manager.request("get_job_status", json!(payload)).await
}

#[tauri::command]
pub fn open_output_directory(payload: OpenDirectoryPayload) -> Result<(), String> {
    let path = payload.path.trim();
    if path.is_empty() {
        return Err("Folder hasil belum dipilih.".to_string());
    }
    if !Path::new(path).exists() {
        return Err("Folder hasil tidak ditemukan.".to_string());
    }

    Command::new("explorer")
        .arg(path)
        .spawn()
        .map_err(|error| {
            log_error(format!("Gagal membuka folder hasil {path}: {error}"));
            "Folder hasil tidak dapat dibuka.".to_string()
        })?;
    Ok(())
}

#[tauri::command]
pub fn open_log_folder() -> Result<(), String> {
    open_logs()
}

#[tauri::command]
pub fn log_window_event(message: String) -> Result<(), String> {
    log_info(format!("window event: {message}"));
    Ok(())
}

#[tauri::command]
pub async fn cancel_engine_job(
    manager: State<'_, SidecarManager>,
    job_id: Option<String>,
) -> Result<Value, String> {
    let Some(job_id) = job_id else {
        log_info("cancel requested without active job");
        return Ok(json!({
            "type": "response",
            "id": "local-cancel",
            "ok": true,
            "data": { "status": "noop" }
        }));
    };

    log_info(format!("cancel requested for job={job_id}"));
    manager.request("cancel_job", json!({ "job_id": job_id })).await
}
