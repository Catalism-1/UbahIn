use serde_json::Value;
use tauri::AppHandle;

use crate::sidecar::{open_logs, request_engine};

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
