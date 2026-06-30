import { invoke } from '@tauri-apps/api/core';
import type { EngineTransportResponse } from '../pages/ImageToPdfPage/types';
import type { HeicInspectionResult, HeicQueueItem, HeicToImageOptions } from '../pages/HeicToImagePage/types';

interface InspectHeicFilesData {
  files: HeicInspectionResult[];
}

interface StartJobData {
  job_id: string;
  status: string;
}

interface CancelJobData {
  job_id: string;
  status: string;
}

function timeoutPromise<T>(timeoutMs: number, message: string): Promise<T> {
  return new Promise((_, reject) => {
    window.setTimeout(() => reject(new Error(message)), timeoutMs);
  });
}

async function invokeWithTimeout<T>(command: string, args?: Record<string, unknown>, timeoutMs = 15000): Promise<T> {
  return Promise.race([
    invoke<T>(command, args),
    timeoutPromise<T>(timeoutMs, `Operasi ${command} terlalu lama.`),
  ]);
}

function unwrapEngineResponse<T>(response: EngineTransportResponse<T>): T {
  if (!response.ok || response.data === undefined) {
    throw new Error(response.error?.message ?? 'Engine mengembalikan respons gagal.');
  }
  return response.data;
}

export async function pickHeicFiles(): Promise<string[]> {
  return invokeWithTimeout<string[]>('pick_heic_files', undefined, 60000);
}

export async function inspectHeicFiles(paths: string[]): Promise<HeicInspectionResult[]> {
  const response = await invokeWithTimeout<EngineTransportResponse<InspectHeicFilesData>>(
    'inspect_heic_files',
    { payload: { paths } },
    20000,
  );
  return unwrapEngineResponse(response).files;
}

export async function startHeicConversion(
  jobId: string,
  files: HeicQueueItem[],
  options: HeicToImageOptions,
): Promise<StartJobData> {
  const payload = {
    job_id: jobId,
    files: files.map((file) => ({ file_id: file.fileId, path: file.path })),
    output_directory: options.outputDirectory,
    output_format: options.outputFormat,
    jpeg_quality_preset: options.jpegQualityPreset,
    jpeg_quality: options.jpegQuality,
    png_compression_level: options.pngCompressionLevel,
    preserve_metadata: options.preserveMetadata,
    open_output_after_finish: options.openOutputAfterFinish,
    performance_mode: options.performanceMode,
  };
  const response = await invokeWithTimeout<EngineTransportResponse<StartJobData>>('start_heic_conversion', { payload }, 20000);
  return unwrapEngineResponse(response);
}

export async function cancelHeicConversionJob(jobId: string): Promise<CancelJobData> {
  const response = await invokeWithTimeout<EngineTransportResponse<CancelJobData>>(
    'cancel_engine_job',
    { jobId: jobId },
    10000,
  );
  return unwrapEngineResponse(response);
}
