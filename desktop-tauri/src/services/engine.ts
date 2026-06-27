import { invoke } from '@tauri-apps/api/core';
import type { EngineHealth, EngineResponse } from '../types/engine';

export async function checkEngine(): Promise<EngineResponse<EngineHealth>> {
  return invoke<EngineResponse<EngineHealth>>('check_engine');
}

export async function openLogFolder(): Promise<void> {
  await invoke('open_log_folder');
}
