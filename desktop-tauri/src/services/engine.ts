import { invoke } from '@tauri-apps/api/core';
import type { EngineHealth, EngineResponse } from '../types/engine';

export async function checkEngine(): Promise<EngineResponse<EngineHealth>> {
  return invoke<EngineResponse<EngineHealth>>('check_engine');
}

export async function openLogFolder(): Promise<void> {
  await invoke('open_log_folder');
}

export async function logWindowEvent(message: string): Promise<void> {
  await invoke('log_window_event', { message });
}

export async function cancelEngineJob(jobId: string | null): Promise<void> {
  await invoke('cancel_engine_job', { jobId });
}
