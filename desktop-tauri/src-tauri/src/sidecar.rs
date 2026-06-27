use serde_json::{json, Value};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::{AppHandle, Emitter};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};
use tokio::sync::oneshot;
use tokio::time::timeout;
use uuid::Uuid;

use crate::app_log::{log_error, log_info};

const ENGINE_SIDECAR: &str = "ubahin-engine";
const ENGINE_TIMEOUT: Duration = Duration::from_secs(10);

type PendingSender = oneshot::Sender<Result<Value, String>>;
type SharedPending = Arc<Mutex<HashMap<String, PendingSender>>>;
type SharedChild = Arc<Mutex<Option<CommandChild>>>;

pub struct SidecarManager {
    app: AppHandle,
    child: SharedChild,
    pending: SharedPending,
    start_lock: Mutex<()>,
}

impl SidecarManager {
    pub fn new(app: AppHandle) -> Self {
        Self {
            app,
            child: Arc::new(Mutex::new(None)),
            pending: Arc::new(Mutex::new(HashMap::new())),
            start_lock: Mutex::new(()),
        }
    }

    pub async fn request(&self, action: &str, payload: Value) -> Result<Value, String> {
        self.request_with_timeout(action, payload, ENGINE_TIMEOUT).await
    }

    pub async fn request_with_timeout(&self, action: &str, payload: Value, duration: Duration) -> Result<Value, String> {
        self.ensure_started()?;

        let request_id = Uuid::new_v4().to_string();
        let request = json!({
            "id": request_id,
            "action": action,
            "payload": payload,
        });
        let line = format!("{request}\n");
        let (tx, rx) = oneshot::channel::<Result<Value, String>>();

        {
            let mut pending = self.pending.lock().map_err(|_| "Engine lock gagal.".to_string())?;
            pending.insert(request_id.clone(), tx);
        }

        let write_result: Result<(), String> = {
            let mut child_guard = self.child.lock().map_err(|_| "Engine lock gagal.".to_string())?;
            if let Some(child) = child_guard.as_mut() {
                child.write(line.as_bytes()).map_err(|error| error.to_string())
            } else {
                Err("sidecar belum berjalan".to_string())
            }
        };

        if let Err(error) = write_result {
            let mut pending = self.pending.lock().map_err(|_| "Engine lock gagal.".to_string())?;
            pending.remove(&request_id);
            log_error(format!("Gagal menulis request sidecar action={action}: {error}"));
            return Err("Engine Python tidak dapat menerima request.".to_string());
        }

        match timeout(duration, rx).await {
            Ok(Ok(result)) => result,
            Ok(Err(_)) => Err("Engine berhenti sebelum response diterima.".to_string()),
            Err(_) => {
                let mut pending = self.pending.lock().map_err(|_| "Engine lock gagal.".to_string())?;
                pending.remove(&request_id);
                log_error(format!("Timeout request sidecar action={action}"));
                Err("Engine terlalu lama merespons.".to_string())
            }
        }
    }

    pub fn shutdown(&self) {
        if let Ok(mut child_guard) = self.child.lock() {
            if let Some(mut child) = child_guard.take() {
                // Try sending shutdown request gracefully
                let request_id = Uuid::new_v4().to_string();
                let request = json!({
                    "id": request_id,
                    "action": "shutdown",
                    "payload": {},
                });
                let line = format!("{request}\n");
                let _ = child.write(line.as_bytes());
                
                // Wait briefly then kill if still alive
                std::thread::sleep(Duration::from_millis(100));
                let _ = child.kill();
                log_info("engine sidecar stopped");
            }
        }
    }

    fn ensure_started(&self) -> Result<(), String> {
        let _start_guard = self.start_lock.lock().map_err(|_| "Engine lock gagal.".to_string())?;
        if self.child.lock().map_err(|_| "Engine lock gagal.".to_string())?.is_some() {
            return Ok(());
        }

        let shell = self.app.shell();
        let command = shell
            .sidecar(ENGINE_SIDECAR)
            .map_err(|error| {
                log_error(format!("Gagal menyiapkan sidecar: {error}"));
                "Engine Python tidak ditemukan atau belum dibangun.".to_string()
            })?
            .args(["--stdio"]);

        let (mut rx, child) = command.spawn().map_err(|error| {
            log_error(format!("Gagal menjalankan sidecar: {error}"));
            "Engine Python tidak dapat dijalankan.".to_string()
        })?;

        let app = self.app.clone();
        let pending = Arc::clone(&self.pending);
        let child_slot = Arc::clone(&self.child);

        tauri::async_runtime::spawn(async move {
            let mut stdout_buffer = String::new();
            while let Some(event) = rx.recv().await {
                match event {
                    CommandEvent::Stdout(bytes) => {
                        let text = String::from_utf8_lossy(&bytes);
                        stdout_buffer.push_str(&text);
                        while let Some(newline) = stdout_buffer.find('\n') {
                            let line = stdout_buffer[..newline].trim().to_string();
                            stdout_buffer = stdout_buffer[newline + 1..].to_string();
                            handle_stdout_line(&app, &pending, &line);
                        }
                        let trimmed = stdout_buffer.trim().to_string();
                        if !trimmed.is_empty() && trimmed.ends_with('}') {
                            stdout_buffer.clear();
                            handle_stdout_line(&app, &pending, &trimmed);
                        }
                    }
                    CommandEvent::Stderr(bytes) => {
                        let text = String::from_utf8_lossy(&bytes);
                        if !text.trim().is_empty() {
                            log_error(format!("stderr sidecar: {}", text.trim()));
                        }
                    }
                    CommandEvent::Error(error) => {
                        log_error(format!("sidecar event error: {error}"));
                    }
                    CommandEvent::Terminated(payload) => {
                        log_error(format!("sidecar terminated: {payload:?}"));
                        fail_all_pending(&pending, "Engine Python berhenti.".to_string());
                        if let Ok(mut child_guard) = child_slot.lock() {
                            let _ = child_guard.take();
                        }
                        break;
                    }
                    _ => {}
                }
            }
        });

        {
            let mut child_guard = self.child.lock().map_err(|_| "Engine lock gagal.".to_string())?;
            *child_guard = Some(child);
        }
        log_info("engine sidecar started");
        Ok(())
    }
}

impl Drop for SidecarManager {
    fn drop(&mut self) {
        self.shutdown();
    }
}

fn handle_stdout_line(app: &AppHandle, pending: &SharedPending, line: &str) {
    if line.is_empty() {
        return;
    }
    let value: Value = match serde_json::from_str(line) {
        Ok(value) => value,
        Err(error) => {
            log_error(format!("stdout sidecar bukan JSON valid: {error}; raw={line}"));
            return;
        }
    };

    match value.get("type").and_then(Value::as_str) {
        Some("response") => {
            if let Some(id) = value.get("id").and_then(Value::as_str) {
                if let Ok(mut pending_guard) = pending.lock() {
                    if let Some(sender) = pending_guard.remove(id) {
                        let _ = sender.send(Ok(value));
                    }
                }
            } else {
                log_error(format!("response sidecar tanpa id: {value}"));
            }
        }
        Some("event") => forward_engine_event(app, &value),
        _ => log_error(format!("pesan sidecar tanpa type valid: {value}")),
    }
}

fn forward_engine_event(app: &AppHandle, value: &Value) {
    let Some(event) = value.get("event").and_then(Value::as_str) else {
        log_error(format!("event sidecar tanpa nama: {value}"));
        return;
    };
    let event_name = format!("engine://{}", event.replace('_', "-"));
    let mut payload = value
        .get("data")
        .cloned()
        .unwrap_or_else(|| json!({}));
    if let Some(job_id) = value.get("job_id") {
        if let Some(object) = payload.as_object_mut() {
            object.entry("job_id".to_string()).or_insert_with(|| job_id.clone());
        } else {
            payload = json!({
                "job_id": job_id,
                "data": payload,
            });
        }
    }
    if let Err(error) = app.emit(&event_name, payload) {
        log_error(format!("Gagal emit event {event_name}: {error}"));
    }
}

fn fail_all_pending(pending: &SharedPending, message: String) {
    if let Ok(mut pending_guard) = pending.lock() {
        for (_, sender) in pending_guard.drain() {
            let _ = sender.send(Err(message.clone()));
        }
    }
}
