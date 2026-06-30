use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::path::Path;
use std::process::Command;
use tauri::{State, WebviewWindow};

use crate::app_log::{log_error, log_info, open_logs};
use crate::sidecar::SidecarManager;

#[derive(Debug, Deserialize, Serialize)]
pub struct InspectPdfFilesPayload {
    paths: Vec<String>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct InspectImageFilesPayload {
    paths: Vec<String>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct PdfInputFile {
    file_id: String,
    path: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct ImageInputFile {
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
pub struct StartImageToPdfPayload {
    job_id: String,
    files: Vec<ImageInputFile>,
    output_directory: String,
    output_filename: String,
    page_size: String,
    orientation: String,
    margin: String,
    fit_mode: String,
    image_quality_preset: String,
    jpeg_quality: u8,
    optimize_pdf_size: bool,
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

#[derive(Debug, Deserialize, Serialize)]
pub struct SaveSettingsPayload {
    theme: String,
    default_output_directory: String,
    performance_mode: String,
    default_pdf_preset: String,
    default_dpi: u32,
    default_jpeg_quality: u8,
    create_zip_after_conversion: bool,
    open_output_after_finish: bool,
    notifications_enabled: bool,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct ListHistoryPayload {
    #[serde(default = "default_history_limit")]
    limit: u32,
    #[serde(default)]
    offset: u32,
    #[serde(default = "default_filter")]
    status: String,
    #[serde(default = "default_filter")]
    tool_type: String,
}

fn default_history_limit() -> u32 {
    50
}

fn default_filter() -> String {
    "all".to_string()
}

#[derive(Debug, Deserialize, Serialize)]
pub struct RecentHistoryPayload {
    #[serde(default = "default_recent_limit")]
    limit: u32,
}

fn default_recent_limit() -> u32 {
    5
}

#[derive(Debug, Deserialize, Serialize)]
pub struct HistoryIdPayload {
    history_id: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct ClearHistoryPayload {
    #[serde(default = "default_scope")]
    scope: String,
}

fn default_scope() -> String {
    "all".to_string()
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
pub fn pick_image_files() -> Result<Vec<String>, String> {
    let paths = rfd::FileDialog::new()
        .set_title("Pilih file Gambar")
        .add_filter("Gambar (*.jpg, *.jpeg, *.png, *.webp)", &["jpg", "jpeg", "png", "webp"])
        .pick_files()
        .unwrap_or_default()
        .into_iter()
        .take(50)
        .map(|path| path.to_string_lossy().to_string())
        .collect::<Vec<_>>();

    log_info(format!("picked {} Gambar file(s)", paths.len()));
    Ok(paths)
}

#[tauri::command]
pub async fn inspect_image_files(
    manager: State<'_, SidecarManager>,
    payload: InspectImageFilesPayload,
) -> Result<Value, String> {
    manager
        .request("inspect_image_files", json!({ "paths": payload.paths }))
        .await
}

#[tauri::command]
pub async fn start_image_to_pdf(
    manager: State<'_, SidecarManager>,
    payload: StartImageToPdfPayload,
) -> Result<Value, String> {
    let job_id = payload.job_id.clone();
    let response = manager.request("start_image_to_pdf", json!(payload)).await?;
    if response.get("ok").and_then(Value::as_bool) == Some(true) {
        manager.track_active_job(job_id);
    }
    Ok(response)
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
    let job_id = payload.job_id.clone();
    let response = manager.request("start_pdf_to_jpg", json!(payload)).await?;
    if response.get("ok").and_then(Value::as_bool) == Some(true) {
        manager.track_active_job(job_id);
    }
    Ok(response)
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
    manager
        .request("cancel_job", json!({ "job_id": job_id }))
        .await
}

#[tauri::command]
pub async fn cancel_active_job_and_close(
    manager: State<'_, SidecarManager>,
    window: WebviewWindow,
    job_id: Option<String>,
) -> Result<Value, String> {
    log_info(format!(
        "cancel and close requested job={}",
        job_id.as_deref().unwrap_or("active")
    ));

    if !manager.begin_shutdown() {
        log_info("cancel and close ignored: shutdown already in progress");
        return Ok(json!({
            "ok": true,
            "data": { "status": "already_shutting_down" }
        }));
    }

    let report = manager.shutdown_for_app_close(job_id).await;
    log_info("final app exit");
    window.destroy().map_err(|error| {
        log_error(format!("final window destroy failed: {error}"));
        "Window aplikasi tidak dapat ditutup.".to_string()
    })?;

    Ok(json!({
        "ok": true,
        "data": report
    }))
}

// ----------------------------------------------------------------- settings

#[tauri::command]
pub async fn get_settings(manager: State<'_, SidecarManager>) -> Result<Value, String> {
    manager.request("get_settings", json!({})).await
}

#[tauri::command]
pub async fn save_settings(
    manager: State<'_, SidecarManager>,
    payload: SaveSettingsPayload,
) -> Result<Value, String> {
    manager.request("save_settings", json!(payload)).await
}

#[tauri::command]
pub fn select_default_output_directory() -> Result<Option<String>, String> {
    let directory = rfd::FileDialog::new()
        .set_title("Pilih folder hasil default")
        .pick_folder()
        .map(|path| path.to_string_lossy().to_string());

    if let Some(path) = &directory {
        log_info(format!("selected default output directory: {path}"));
    }

    Ok(directory)
}

// ------------------------------------------------------------------ history

#[tauri::command]
pub async fn list_history(
    manager: State<'_, SidecarManager>,
    payload: ListHistoryPayload,
) -> Result<Value, String> {
    manager.request("list_history", json!(payload)).await
}

#[tauri::command]
pub async fn get_recent_history(
    manager: State<'_, SidecarManager>,
    payload: RecentHistoryPayload,
) -> Result<Value, String> {
    manager.request("get_recent_history", json!(payload)).await
}

#[tauri::command]
pub async fn delete_history_item(
    manager: State<'_, SidecarManager>,
    payload: HistoryIdPayload,
) -> Result<Value, String> {
    manager.request("delete_history_item", json!(payload)).await
}

#[tauri::command]
pub async fn clear_history(
    manager: State<'_, SidecarManager>,
    payload: ClearHistoryPayload,
) -> Result<Value, String> {
    manager.request("clear_history", json!(payload)).await
}

#[tauri::command]
pub async fn open_history_output_directory(
    manager: State<'_, SidecarManager>,
    payload: HistoryIdPayload,
) -> Result<(), String> {
    // Engine adalah pemilik database: ia memvalidasi keberadaan folder hasil.
    let response = manager
        .request("open_history_output_directory", json!(payload))
        .await?;

    if response.get("ok").and_then(Value::as_bool) != Some(true) {
        let message = response
            .get("error")
            .and_then(|error| error.get("message"))
            .and_then(Value::as_str)
            .unwrap_or("Folder hasil tidak ditemukan.")
            .to_string();
        return Err(message);
    }

    let path = response
        .get("data")
        .and_then(|data| data.get("path"))
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string();

    if path.is_empty() || !Path::new(&path).exists() {
        return Err("Folder hasil tidak ditemukan.".to_string());
    }

    Command::new("explorer")
        .arg(&path)
        .spawn()
        .map_err(|error| {
            log_error(format!("Gagal membuka folder riwayat {path}: {error}"));
            "Folder hasil tidak dapat dibuka.".to_string()
        })?;
    Ok(())
}

#[derive(Debug, Deserialize, Serialize)]
pub struct InspectHeicFilesPayload {
    pub paths: Vec<String>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct HeicInputFile {
    pub file_id: String,
    pub path: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct StartHeicConversionPayload {
    pub job_id: String,
    pub files: Vec<HeicInputFile>,
    pub output_directory: String,
    pub output_format: String,
    pub jpeg_quality_preset: String,
    pub jpeg_quality: u8,
    pub png_compression_level: u8,
    pub preserve_metadata: bool,
    pub open_output_after_finish: bool,
    pub performance_mode: String,
}

#[tauri::command]
pub fn pick_heic_files() -> Result<Vec<String>, String> {
    let paths = rfd::FileDialog::new()
        .set_title("Pilih file HEIC atau HEIF")
        .add_filter("HEIC/HEIF (*.heic, *.heif)", &["heic", "heif"])
        .pick_files()
        .unwrap_or_default()
        .into_iter()
        .take(50)
        .map(|path| path.to_string_lossy().to_string())
        .collect::<Vec<_>>();

    log_info(format!("picked {} HEIC file(s)", paths.len()));
    Ok(paths)
}

#[tauri::command]
pub async fn inspect_heic_files(
    manager: State<'_, SidecarManager>,
    payload: InspectHeicFilesPayload,
) -> Result<Value, String> {
    manager
        .request("inspect_heic_files", json!({ "paths": payload.paths }))
        .await
}

#[tauri::command]
pub async fn start_heic_conversion(
    manager: State<'_, SidecarManager>,
    payload: StartHeicConversionPayload,
) -> Result<Value, String> {
    let job_id = payload.job_id.clone();
    let response = manager.request("start_heic_conversion", json!(payload)).await?;
    if response.get("ok").and_then(Value::as_bool) == Some(true) {
        manager.track_active_job(job_id);
    }
    Ok(response)
}
