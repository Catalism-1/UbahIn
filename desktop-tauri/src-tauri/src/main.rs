mod app_log;
mod commands;
mod sidecar;

use app_log::{log_error, log_info};
use tauri::{LogicalSize, Manager, Size};
use tauri_plugin_window_state::{StateFlags, WindowExt};

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .setup(|app| {
            log_info("startup window: default=1440x900 min=1100x700 native_decorations=true");

            if let Some(window) = app.get_webview_window("main") {
                match window.restore_state(StateFlags::all()) {
                    Ok(_) => log_info("window state restored"),
                    Err(error) => {
                        log_error(format!("window state restore failed, using fallback: {error}"));
                        if let Err(size_error) = window.set_size(Size::Logical(LogicalSize {
                            width: 1440.0,
                            height: 900.0,
                        })) {
                            log_error(format!("fallback window size failed: {size_error}"));
                        }
                        if let Err(center_error) = window.center() {
                            log_error(format!("fallback window center failed: {center_error}"));
                        }
                    }
                }

                if let Err(error) = window.show() {
                    log_error(format!("window show failed: {error}"));
                }
                if let Err(error) = window.set_focus() {
                    log_error(format!("window focus failed: {error}"));
                }
            } else {
                log_error("main window was not available during startup");
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::check_engine,
            commands::app_info,
            commands::self_check,
            commands::open_log_folder,
            commands::log_window_event,
            commands::cancel_engine_job
        ])
        .run(tauri::generate_context!())
        .expect("error while running Ubahin");
}
