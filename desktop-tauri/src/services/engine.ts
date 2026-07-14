import { invoke } from '@tauri-apps/api/core';
import type { EngineHealth, EngineResponse } from '../types/engine';
import { invokeWithTimeout } from './transport';

let checkEngineInFlight: Promise<EngineResponse<EngineHealth>> | null = null;

export async function checkEngine(): Promise<EngineResponse<EngineHealth>> {
  if (!checkEngineInFlight) {
    checkEngineInFlight = invokeWithTimeout<EngineResponse<EngineHealth>>('check_engine', undefined, 15000).finally(() => {
      checkEngineInFlight = null;
    });
  }
  return checkEngineInFlight;
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

export async function cancelActiveJobAndClose(jobId: string | null): Promise<void> {
  await invoke('cancel_active_job_and_close', { jobId });
}
