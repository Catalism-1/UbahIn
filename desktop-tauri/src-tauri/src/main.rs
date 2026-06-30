#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app_log;
mod commands;
mod sidecar;

use app_log::{log_error, log_info};
use serde_json::json;
use tauri::{Emitter, LogicalSize, Manager, Size, WindowEvent};
use tauri_plugin_window_state::{StateFlags, WindowExt};

fn setup_panic_hook() {
    std::panic::set_hook(Box::new(|info| {
        let mut msg = String::new();
        if let Some(s) = info.payload().downcast_ref::<&str>() {
            msg.push_str(s);
        } else if let Some(s) = info.payload().downcast_ref::<String>() {
            msg.push_str(s);
        } else {
            msg.push_str("Unknown panic");
        }

        let time = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        let local_app_data = std::env::var("LOCALAPPDATA").unwrap_or_else(|_| ".".to_string());
        let log_dir = std::path::PathBuf::from(local_app_data)
            .join("Ubahin")
            .join("logs");
        let _ = std::fs::create_dir_all(&log_dir);
        let error_file = log_dir.join("last_error.txt");
        let detail_log = log_dir.join("tauri.log");

        let content = format!(
            "Waktu (Unix Timestamp): {}\nArea Error: Core Application Panic\nPesan Sederhana: {}\nLokasi Log Detail: {}\n\n{}",
            time,
            msg,
            detail_log.display(),
            info
        );
        let _ = std::fs::write(&error_file, content);
    }));
}

fn main() {
    setup_panic_hook();
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .on_window_event(|window, event| {
            let WindowEvent::CloseRequested { api, .. } = event else {
                return;
            };
            if window.label() != "main" {
                return;
            }

            let app = window.app_handle().clone();
            let manager_state = app.state::<sidecar::SidecarManager>();
            let active_jobs = manager_state.active_job_ids();
            log_info(format!(
                "close requested active_jobs={} shutting_down={}",
                active_jobs.len(),
                manager_state.is_shutting_down()
            ));

            api.prevent_close();

            if manager_state.is_shutting_down() {
                log_info("close ignored: shutdown already in progress");
                return;
            }

            if !active_jobs.is_empty() {
                log_info(format!(
                    "active job state at close: {}",
                    active_jobs.join(",")
                ));
                if let Err(error) = window.emit(
                    "app://close-active-job",
                    json!({ "active_job_id": active_jobs.first().cloned() }),
                ) {
                    log_error(format!("failed to emit close active job event: {error}"));
                }
                return;
            }

            if !manager_state.begin_shutdown() {
                log_info("close ignored: shutdown flag already set");
                return;
            }

            let manager = manager_state.inner().clone();
            let window = window.clone();
            tauri::async_runtime::spawn(async move {
                let _report = manager.shutdown_sidecar().await;
                log_info("final app exit");
                if let Err(error) = window.destroy() {
                    log_error(format!("final window destroy failed: {error}"));
                }
            });
        })
        .setup(|app| {
            app.manage(sidecar::SidecarManager::new(app.handle().clone()));
            log_info("startup window: default=1440x900 min=1100x700 native_decorations=true");

            if let Some(window) = app.get_webview_window("main") {
                match window.restore_state(StateFlags::all()) {
                    Ok(_) => log_info("window state restored"),
                    Err(error) => {
                        log_error(format!(
                            "window state restore failed, using fallback: {error}"
                        ));
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
            commands::pick_pdf_files,
            commands::inspect_pdf_files,
            commands::pick_image_files,
            commands::inspect_image_files,
            commands::start_image_to_pdf,
            commands::pick_output_directory,
            commands::start_pdf_to_jpg,
            commands::cancel_pdf_to_jpg_job,
            commands::open_output_directory,
            commands::get_job_status,
            commands::open_log_folder,
            commands::log_window_event,
            commands::cancel_engine_job,
            commands::cancel_active_job_and_close,
            commands::get_settings,
            commands::save_settings,
            commands::select_default_output_directory,
            commands::list_history,
            commands::get_recent_history,
            commands::delete_history_item,
            commands::clear_history,
            commands::open_history_output_directory,
            commands::pick_heic_files,
            commands::inspect_heic_files,
            commands::start_heic_conversion
        ])
        .run(tauri::generate_context!())
        .expect("error while running Ubahin");
}
