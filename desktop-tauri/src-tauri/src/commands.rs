use serde_json::Value;
use tauri::AppHandle;

use crate::app_log::{log_info, open_logs};
use crate::sidecar::request_engine;

#[tauri::command]
pub async fn check_engine(app: AppHandle) -> Result<Value, String> {
    request_engine(&app, "health").await
}

#[tauri::command]
pub async fn app_info(app: AppHandle) -> Result<Value, String> {
    request_engine(&app, "app_info").await
}

#[tauri::command]
pub async fn self_check(app: AppHandle) -> Result<Value, String> {
    request_engine(&app, "self_check").await
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
pub fn cancel_engine_job(job_id: Option<String>) -> Result<(), String> {
    let label = job_id.unwrap_or_else(|| "health-check-or-none".to_string());
    log_info(format!("cancel placeholder requested for job={label}"));
    Ok(())
}
