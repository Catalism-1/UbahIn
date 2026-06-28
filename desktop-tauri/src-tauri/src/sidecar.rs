use serde::Serialize;
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};
use tokio::sync::{oneshot, watch};
use tokio::time::{sleep, timeout};
use uuid::Uuid;

use crate::app_log::{log_error, log_info};

const ENGINE_SIDECAR: &str = "ubahin-engine";
const ENGINE_TIMEOUT: Duration = Duration::from_secs(10);
const SHUTDOWN_RESPONSE_TIMEOUT: Duration = Duration::from_secs(3);
const CHILD_EXIT_TIMEOUT: Duration = Duration::from_secs(2);
const CANCEL_CLEANUP_TIMEOUT: Duration = Duration::from_secs(5);

type PendingSender = oneshot::Sender<Result<Value, String>>;
type SharedPending = Arc<Mutex<HashMap<String, PendingSender>>>;
type SharedChild = Arc<Mutex<Option<CommandChild>>>;
type SharedActiveJobs = Arc<Mutex<HashSet<String>>>;
type SharedTermination = Arc<Mutex<Option<watch::Receiver<bool>>>>;

#[derive(Debug, Serialize)]
pub struct ShutdownReport {
    pub shutdown_response_received: bool,
    pub child_exited: bool,
    pub forced_terminate: bool,
    pub cancel_requested: bool,
    pub cancel_completed: bool,
    pub active_jobs: Vec<String>,
    pub warnings: Vec<String>,
}

impl ShutdownReport {
    fn new(active_jobs: Vec<String>) -> Self {
        Self {
            shutdown_response_received: false,
            child_exited: false,
            forced_terminate: false,
            cancel_requested: false,
            cancel_completed: false,
            active_jobs,
            warnings: Vec::new(),
        }
    }
}

#[derive(Clone)]
pub struct SidecarManager {
    app: AppHandle,
    child: SharedChild,
    pending: SharedPending,
    start_lock: Arc<Mutex<()>>,
    active_jobs: SharedActiveJobs,
    is_shutting_down: Arc<AtomicBool>,
    termination: SharedTermination,
}

impl SidecarManager {
    pub fn new(app: AppHandle) -> Self {
        Self {
            app,
            child: Arc::new(Mutex::new(None)),
            pending: Arc::new(Mutex::new(HashMap::new())),
            start_lock: Arc::new(Mutex::new(())),
            active_jobs: Arc::new(Mutex::new(HashSet::new())),
            is_shutting_down: Arc::new(AtomicBool::new(false)),
            termination: Arc::new(Mutex::new(None)),
        }
    }

    pub async fn request(&self, action: &str, payload: Value) -> Result<Value, String> {
        self.request_with_timeout(action, payload, ENGINE_TIMEOUT)
            .await
    }

    pub async fn request_with_timeout(
        &self,
        action: &str,
        payload: Value,
        duration: Duration,
    ) -> Result<Value, String> {
        self.request_inner(action, payload, duration, true).await
    }

    pub fn begin_shutdown(&self) -> bool {
        !self.is_shutting_down.swap(true, Ordering::SeqCst)
    }

    pub fn is_shutting_down(&self) -> bool {
        self.is_shutting_down.load(Ordering::SeqCst)
    }

    pub fn is_running(&self) -> bool {
        self.child
            .lock()
            .map(|child_guard| child_guard.is_some())
            .unwrap_or(false)
    }

    pub fn track_active_job(&self, job_id: impl Into<String>) {
        let job_id = job_id.into();
        if job_id.trim().is_empty() {
            return;
        }
        if let Ok(mut active_jobs) = self.active_jobs.lock() {
            active_jobs.insert(job_id);
        }
    }

    pub fn clear_active_job(&self, job_id: &str) {
        if let Ok(mut active_jobs) = self.active_jobs.lock() {
            active_jobs.remove(job_id);
        }
    }

    pub fn clear_all_active_jobs(&self) {
        if let Ok(mut active_jobs) = self.active_jobs.lock() {
            active_jobs.clear();
        }
    }

    pub fn active_job_ids(&self) -> Vec<String> {
        let mut jobs = self
            .active_jobs
            .lock()
            .map(|active_jobs| active_jobs.iter().cloned().collect::<Vec<_>>())
            .unwrap_or_default();
        jobs.sort();
        jobs
    }

    pub async fn shutdown_for_app_close(&self, cancel_job_id: Option<String>) -> ShutdownReport {
        let mut report = ShutdownReport::new(self.active_job_ids());
        let job_to_cancel = cancel_job_id
            .filter(|job_id| !job_id.trim().is_empty())
            .or_else(|| report.active_jobs.first().cloned());

        if let Some(job_id) = job_to_cancel {
            report.cancel_requested = true;
            if self.is_running() {
                log_info(format!("cancel_job sent job={job_id}"));
                match self
                    .request_with_timeout(
                        "cancel_job",
                        json!({ "job_id": job_id }),
                        Duration::from_secs(2),
                    )
                    .await
                {
                    Ok(_) => log_info(format!("cancel_job response received job={job_id}")),
                    Err(error) => {
                        let warning = format!("cancel_job request failed job={job_id}: {error}");
                        log_error(&warning);
                        report.warnings.push(warning);
                    }
                }
            } else {
                log_info(format!(
                    "cancel_job skipped because sidecar is not running job={job_id}"
                ));
            }

            report.cancel_completed = self
                .wait_for_job_cleanup(&job_id, CANCEL_CLEANUP_TIMEOUT)
                .await;
            if report.cancel_completed {
                log_info(format!("cancel cleanup completed job={job_id}"));
            } else {
                let warning = format!("cancel cleanup timeout job={job_id}");
                log_error(&warning);
                report.warnings.push(warning);
            }
        }

        self.shutdown_sidecar_into(&mut report).await;
        report
    }

    pub async fn shutdown_sidecar(&self) -> ShutdownReport {
        let mut report = ShutdownReport::new(self.active_job_ids());
        self.shutdown_sidecar_into(&mut report).await;
        report
    }

    async fn shutdown_sidecar_into(&self, report: &mut ShutdownReport) {
        if !self.is_running() {
            report.child_exited = true;
            self.clear_all_active_jobs();
            log_info("shutdown completed: sidecar was not running");
            return;
        }

        log_info("shutdown request sent");
        let timeout_seconds = CHILD_EXIT_TIMEOUT.as_secs_f64();
        match self
            .request_inner(
                "shutdown",
                json!({
                    "cancel_active": true,
                    "timeout_seconds": timeout_seconds,
                }),
                SHUTDOWN_RESPONSE_TIMEOUT,
                false,
            )
            .await
        {
            Ok(response) => {
                report.shutdown_response_received = true;
                log_info(format!(
                    "shutdown response received ok={}",
                    response.get("ok").and_then(Value::as_bool).unwrap_or(false)
                ));
            }
            Err(error) => {
                let warning = format!("shutdown response timeout/error: {error}");
                log_error(&warning);
                report.warnings.push(warning);
            }
        }

        if self.wait_for_child_exit(CHILD_EXIT_TIMEOUT).await {
            report.child_exited = true;
            log_info("child exited");
        } else {
            let warning = "timeout waiting for sidecar child exit".to_string();
            log_error(&warning);
            report.warnings.push(warning);
            report.forced_terminate = self.force_terminate_child();
        }

        fail_all_pending(&self.pending, "Engine Python sedang ditutup.".to_string());
        self.clear_all_active_jobs();
        log_info("shutdown completed");
    }

    async fn request_inner(
        &self,
        action: &str,
        payload: Value,
        duration: Duration,
        start_if_needed: bool,
    ) -> Result<Value, String> {
        if self.is_shutting_down() {
            if !is_request_allowed_during_shutdown(action) {
                log_info(format!("request rejected during shutdown action={action}"));
                return Err("Aplikasi sedang ditutup.".to_string());
            }
            if start_if_needed && !self.is_running() {
                log_info(format!(
                    "request rejected during shutdown because sidecar is stopped action={action}"
                ));
                return Err("sidecar belum berjalan".to_string());
            }
        }

        if start_if_needed {
            self.ensure_started()?;
        } else if !self.is_running() {
            return Err("sidecar belum berjalan".to_string());
        }

        let request_id = Uuid::new_v4().to_string();
        let request = json!({
            "id": request_id,
            "action": action,
            "payload": payload,
        });
        let line = format!("{request}\n");
        let (tx, rx) = oneshot::channel::<Result<Value, String>>();

        {
            let mut pending = self
                .pending
                .lock()
                .map_err(|_| "Engine lock gagal.".to_string())?;
            pending.insert(request_id.clone(), tx);
        }

        let write_result: Result<(), String> = {
            let mut child_guard = self
                .child
                .lock()
                .map_err(|_| "Engine lock gagal.".to_string())?;
            if let Some(child) = child_guard.as_mut() {
                child
                    .write(line.as_bytes())
                    .map_err(|error| error.to_string())
            } else {
                Err("sidecar belum berjalan".to_string())
            }
        };

        if let Err(error) = write_result {
            let mut pending = self
                .pending
                .lock()
                .map_err(|_| "Engine lock gagal.".to_string())?;
            pending.remove(&request_id);
            log_error(format!(
                "Gagal menulis request sidecar action={action}: {error}"
            ));
            return Err("Engine Python tidak dapat menerima request.".to_string());
        }

        match timeout(duration, rx).await {
            Ok(Ok(result)) => result,
            Ok(Err(_)) => Err("Engine berhenti sebelum response diterima.".to_string()),
            Err(_) => {
                let mut pending = self
                    .pending
                    .lock()
                    .map_err(|_| "Engine lock gagal.".to_string())?;
                pending.remove(&request_id);
                log_error(format!("Timeout request sidecar action={action}"));
                Err("Engine terlalu lama merespons.".to_string())
            }
        }
    }

    async fn wait_for_job_cleanup(&self, job_id: &str, duration: Duration) -> bool {
        let deadline = Instant::now() + duration;
        loop {
            if !self.is_running() {
                self.clear_active_job(job_id);
                return true;
            }
            if !self
                .active_jobs
                .lock()
                .map(|active_jobs| active_jobs.contains(job_id))
                .unwrap_or(false)
            {
                return true;
            }

            let now = Instant::now();
            if now >= deadline {
                return false;
            }
            let remaining = deadline.saturating_duration_since(now);
            let request_timeout = remaining.min(Duration::from_secs(1));
            match self
                .request_with_timeout(
                    "get_job_status",
                    json!({ "job_id": job_id }),
                    request_timeout,
                )
                .await
            {
                Ok(response) => {
                    if let Some(status) = response
                        .get("data")
                        .and_then(|data| data.get("job"))
                        .and_then(|job| job.get("status"))
                        .and_then(Value::as_str)
                    {
                        if is_terminal_job_status(status) {
                            self.clear_active_job(job_id);
                            return true;
                        }
                    }
                }
                Err(error) => {
                    log_error(format!(
                        "get_job_status during close failed job={job_id}: {error}"
                    ));
                }
            }
            sleep(Duration::from_millis(250)).await;
        }
    }

    async fn wait_for_child_exit(&self, duration: Duration) -> bool {
        let Some(mut receiver) = self
            .termination
            .lock()
            .ok()
            .and_then(|termination| termination.as_ref().cloned())
        else {
            return true;
        };

        if *receiver.borrow() {
            return true;
        }

        match timeout(duration, receiver.changed()).await {
            Ok(Ok(())) => *receiver.borrow(),
            Ok(Err(_)) => true,
            Err(_) => false,
        }
    }

    fn force_terminate_child(&self) -> bool {
        let child = self
            .child
            .lock()
            .ok()
            .and_then(|mut child_guard| child_guard.take());

        if let Some(child) = child {
            let pid = child.pid();
            match terminate_managed_sidecar_tree(pid) {
                Ok(()) => {
                    log_error(format!("forced terminate sidecar pid={pid}"));
                    true
                }
                Err(error) => {
                    log_error(format!(
                        "forced terminate sidecar tree failed pid={pid}: {error}"
                    ));
                    match child.kill() {
                        Ok(_) => {
                            log_error(format!("forced terminate sidecar parent pid={pid}"));
                            true
                        }
                        Err(kill_error) => {
                            log_error(format!(
                                "forced terminate sidecar parent failed pid={pid}: {kill_error}"
                            ));
                            false
                        }
                    }
                }
            }
        } else {
            false
        }
    }

    fn ensure_started(&self) -> Result<(), String> {
        let _start_guard = self
            .start_lock
            .lock()
            .map_err(|_| "Engine lock gagal.".to_string())?;
        if self
            .child
            .lock()
            .map_err(|_| "Engine lock gagal.".to_string())?
            .is_some()
        {
            return Ok(());
        }

        self.is_shutting_down.store(false, Ordering::SeqCst);

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

        let (termination_tx, termination_rx) = watch::channel(false);
        if let Ok(mut termination) = self.termination.lock() {
            *termination = Some(termination_rx);
        }

        let app = self.app.clone();
        let pending = Arc::clone(&self.pending);
        let child_slot = Arc::clone(&self.child);
        let active_jobs = Arc::clone(&self.active_jobs);

        tauri::async_runtime::spawn(async move {
            let mut stdout_buffer = String::new();
            let mut saw_termination = false;
            while let Some(event) = rx.recv().await {
                match event {
                    CommandEvent::Stdout(bytes) => {
                        let text = String::from_utf8_lossy(&bytes);
                        stdout_buffer.push_str(&text);
                        while let Some(newline) = stdout_buffer.find('\n') {
                            let line = stdout_buffer[..newline].trim().to_string();
                            stdout_buffer = stdout_buffer[newline + 1..].to_string();
                            handle_stdout_line(&app, &pending, &active_jobs, &line);
                        }
                        let trimmed = stdout_buffer.trim().to_string();
                        if !trimmed.is_empty() && trimmed.ends_with('}') {
                            stdout_buffer.clear();
                            handle_stdout_line(&app, &pending, &active_jobs, &trimmed);
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
                        saw_termination = true;
                        if payload.code == Some(0) {
                            log_info(format!("sidecar terminated: {payload:?}"));
                        } else {
                            log_error(format!("sidecar terminated: {payload:?}"));
                        }
                        fail_all_pending(&pending, "Engine Python berhenti.".to_string());
                        if let Ok(mut child_guard) = child_slot.lock() {
                            let _ = child_guard.take();
                        }
                        if let Ok(mut active_jobs) = active_jobs.lock() {
                            active_jobs.clear();
                        }
                        let _ = termination_tx.send(true);
                        break;
                    }
                    _ => {}
                }
            }
            if !saw_termination {
                fail_all_pending(&pending, "Engine Python berhenti.".to_string());
                if let Ok(mut child_guard) = child_slot.lock() {
                    let _ = child_guard.take();
                }
                if let Ok(mut active_jobs) = active_jobs.lock() {
                    active_jobs.clear();
                }
                let _ = termination_tx.send(true);
            }
        });

        {
            let mut child_guard = self
                .child
                .lock()
                .map_err(|_| "Engine lock gagal.".to_string())?;
            *child_guard = Some(child);
        }
        log_info("engine sidecar started");
        Ok(())
    }

    fn shutdown_on_drop(&self) {
        if !self.is_running() {
            return;
        }

        if let Ok(mut child_guard) = self.child.lock() {
            if let Some(mut child) = child_guard.take() {
                let request_id = Uuid::new_v4().to_string();
                let request = json!({
                    "id": request_id,
                    "action": "shutdown",
                    "payload": {
                        "cancel_active": true,
                        "timeout_seconds": 1.0,
                    },
                });
                let line = format!("{request}\n");
                let _ = child.write(line.as_bytes());
                std::thread::sleep(Duration::from_secs(1));
                let pid = child.pid();
                let _ = terminate_managed_sidecar_tree(pid)
                    .or_else(|_| child.kill().map_err(|error| error.to_string()));
                log_error(format!("sidecar fallback terminate during drop pid={pid}"));
            }
        }
    }
}

impl Drop for SidecarManager {
    fn drop(&mut self) {
        if Arc::strong_count(&self.child) == 1 {
            self.shutdown_on_drop();
        }
    }
}

fn handle_stdout_line(
    app: &AppHandle,
    pending: &SharedPending,
    active_jobs: &SharedActiveJobs,
    line: &str,
) {
    if line.is_empty() {
        return;
    }
    let value: Value = match serde_json::from_str(line) {
        Ok(value) => value,
        Err(error) => {
            log_error(format!(
                "stdout sidecar bukan JSON valid: {error}; raw={line}"
            ));
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
        Some("event") => {
            update_active_jobs_from_event(active_jobs, &value);
            forward_engine_event(app, &value);
        }
        _ => log_error(format!("pesan sidecar tanpa type valid: {value}")),
    }
}

fn update_active_jobs_from_event(active_jobs: &SharedActiveJobs, value: &Value) {
    let Some(event) = value.get("event").and_then(Value::as_str) else {
        return;
    };
    let Some(job_id) = value.get("job_id").and_then(Value::as_str) else {
        return;
    };

    if let Ok(mut active_jobs) = active_jobs.lock() {
        match event {
            "job_started" => {
                active_jobs.insert(job_id.to_string());
            }
            "job_completed" | "job_failed" | "job_cancelled" => {
                active_jobs.remove(job_id);
            }
            _ => {}
        }
    }
}

fn forward_engine_event(app: &AppHandle, value: &Value) {
    let Some(event) = value.get("event").and_then(Value::as_str) else {
        log_error(format!("event sidecar tanpa nama: {value}"));
        return;
    };
    let event_name = format!("engine://{}", event.replace('_', "-"));
    let mut payload = value.get("data").cloned().unwrap_or_else(|| json!({}));
    if let Some(job_id) = value.get("job_id") {
        if let Some(object) = payload.as_object_mut() {
            object
                .entry("job_id".to_string())
                .or_insert_with(|| job_id.clone());
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

fn is_terminal_job_status(status: &str) -> bool {
    matches!(
        status,
        "completed" | "completed_with_warnings" | "failed" | "cancelled"
    )
}

fn is_request_allowed_during_shutdown(action: &str) -> bool {
    matches!(action, "cancel_job" | "get_job_status" | "shutdown")
}

#[cfg(target_os = "windows")]
fn terminate_managed_sidecar_tree(pid: u32) -> Result<(), String> {
    use std::os::windows::process::CommandExt;

    const CREATE_NO_WINDOW: u32 = 0x08000000;
    let status = std::process::Command::new("taskkill")
        .args(["/PID", &pid.to_string(), "/T", "/F"])
        .creation_flags(CREATE_NO_WINDOW)
        .status()
        .map_err(|error| error.to_string())?;

    if status.success() {
        Ok(())
    } else {
        Err(format!("taskkill exited with status {status}"))
    }
}

#[cfg(not(target_os = "windows"))]
fn terminate_managed_sidecar_tree(_pid: u32) -> Result<(), String> {
    Err("process tree termination is only implemented on Windows".to_string())
}
