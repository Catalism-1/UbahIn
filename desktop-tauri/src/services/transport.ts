import { invoke } from '@tauri-apps/api/core';
import type { EngineResponse } from '../types/engine';

function timeoutPromise<T>(timeoutMs: number, message: string): Promise<T> {
  return new Promise((_, reject) => {
    window.setTimeout(() => reject(new Error(message)), timeoutMs);
  });
}

export async function invokeWithTimeout<T>(
  command: string,
  args?: Record<string, unknown>,
  timeoutMs = 10000,
): Promise<T> {
  return Promise.race([invoke<T>(command, args), timeoutPromise<T>(timeoutMs, `Operasi ${command} terlalu lama.`)]);
}

/** Buka pembungkus response engine; lempar pesan bahasa Indonesia bila gagal. */
export function unwrapEngineResponse<T>(response: EngineResponse<T>): T {
  if (!response.ok || response.data === undefined) {
    throw new Error(response.error?.message ?? 'Engine mengembalikan respons gagal.');
  }
  return response.data;
}
