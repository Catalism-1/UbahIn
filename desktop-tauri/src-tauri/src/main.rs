mod commands;
mod sidecar;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            commands::check_engine,
            commands::app_info,
            commands::self_check,
            commands::open_log_folder
        ])
        .run(tauri::generate_context!())
        .expect("error while running Ubahin");
}
