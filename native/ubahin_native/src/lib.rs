use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{Read, Result as IoResult};
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;
use sysinfo::System;

fn sanitize_windows_name(name: &str) -> String {
    let mut out = String::new();
    for ch in name.chars() {
        if matches!(ch, '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*') || ch.is_control() {
            out.push('_');
        } else {
            out.push(ch);
        }
    }
    let trimmed = out.trim().trim_matches('.').to_string();
    if trimmed.is_empty() {
        "file".to_string()
    } else {
        trimmed.chars().take(120).collect()
    }
}

fn hash_file(path: &Path) -> IoResult<String> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 1024 * 1024];
    loop {
        let read = file.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }
    Ok(format!("{:x}", hasher.finalize()))
}

#[pyfunction]
fn fast_file_hash(path: String) -> PyResult<String> {
    hash_file(Path::new(&path)).map_err(|err| pyo3::exceptions::PyOSError::new_err(err.to_string()))
}

#[pyfunction]
fn scan_files(py: Python<'_>, paths: &PyList) -> PyResult<Vec<PyObject>> {
    let mut rows = Vec::new();
    for item in paths.iter() {
        let raw_path: String = item.extract()?;
        let path = PathBuf::from(&raw_path);
        let dict = PyDict::new(py);
        let exists = path.exists();
        dict.set_item("path", raw_path)?;
        dict.set_item("filename", path.file_name().and_then(|s| s.to_str()).unwrap_or(""))?;
        dict.set_item("extension", path.extension().and_then(|s| s.to_str()).map(|s| format!(".{}", s.to_lowercase())).unwrap_or_default())?;
        dict.set_item("exists", exists)?;
        if exists {
            let meta = fs::metadata(&path).map_err(|err| pyo3::exceptions::PyOSError::new_err(err.to_string()))?;
            dict.set_item("size_bytes", meta.len())?;
            let modified = meta.modified().ok().and_then(|time| time.duration_since(UNIX_EPOCH).ok()).map(|d| d.as_secs_f64());
            dict.set_item("modified_time", modified)?;
        } else {
            dict.set_item("size_bytes", 0)?;
            dict.set_item("modified_time", Option::<f64>::None)?;
        }
        rows.push(dict.into());
    }
    Ok(rows)
}

#[pyfunction]
fn safe_output_path(directory: String, filename: String) -> PyResult<String> {
    let dir = PathBuf::from(directory);
    let normalized = filename.replace(['\\', '/'], "_");
    let (stem, extension) = match normalized.rfind('.') {
        Some(index) if index > 0 => (&normalized[..index], &normalized[index + 1..]),
        _ => (normalized.as_str(), ""),
    };
    let safe_stem = sanitize_windows_name(stem);
    let suffix = if extension.is_empty() { String::new() } else { format!(".{}", extension) };
    let mut index = 0;
    loop {
        let name = if index == 0 {
            format!("{}{}", safe_stem, suffix)
        } else {
            format!("{}_{:02}{}", safe_stem, index, suffix)
        };
        let candidate = dir.join(name);
        if !candidate.exists() {
            return Ok(candidate.to_string_lossy().to_string());
        }
        index += 1;
    }
}

#[pyfunction]
fn system_snapshot(output_dir: Option<String>) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let mut system = System::new_all();
        system.refresh_memory();
        let dict = PyDict::new(py);
        dict.set_item("logical_cpu_count", std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1))?;
        dict.set_item("available_memory", system.available_memory())?;
        dict.set_item("total_memory", system.total_memory())?;
        let disk_path = output_dir.unwrap_or_else(|| ".".to_string());
        let available_disk = fs2_available_space(Path::new(&disk_path)).unwrap_or(0);
        dict.set_item("available_disk", available_disk)?;
        Ok(dict.into())
    })
}

fn fs2_available_space(path: &Path) -> IoResult<u64> {
    let target = if path.exists() { path } else { Path::new(".") };
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        use windows_sys::Win32::Storage::FileSystem::GetDiskFreeSpaceExW;
        let mut wide: Vec<u16> = target.as_os_str().encode_wide().collect();
        wide.push(0);
        let mut free: u64 = 0;
        let ok = unsafe { GetDiskFreeSpaceExW(wide.as_ptr(), &mut free, std::ptr::null_mut(), std::ptr::null_mut()) };
        if ok == 0 {
            Ok(0)
        } else {
            Ok(free)
        }
    }
    #[cfg(not(windows))]
    {
        let _ = target;
        Ok(0)
    }
}

#[pyfunction]
fn estimate_file_size(pages: u64, dpi: u64, quality: u64) -> PyResult<u64> {
    let dpi_factor = (dpi as f64 / 150.0).powf(2.0);
    let quality_factor = 0.7 + ((quality.saturating_sub(70)) as f64 / 25.0) * 0.6;
    Ok((pages.max(1) as f64 * 300_000.0 * dpi_factor * quality_factor) as u64)
}

#[pymodule]
fn ubahin_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(fast_file_hash, module)?)?;
    module.add_function(wrap_pyfunction!(scan_files, module)?)?;
    module.add_function(wrap_pyfunction!(safe_output_path, module)?)?;
    module.add_function(wrap_pyfunction!(system_snapshot, module)?)?;
    module.add_function(wrap_pyfunction!(estimate_file_size, module)?)?;
    Ok(())
}
