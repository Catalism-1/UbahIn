import { invoke } from '@tauri-apps/api/core';
import type {
  EngineTransportResponse,
  ImageInspectionResult,
  ImageQueueItem,
  ImageToPdfOptions,
  ImageToPdfResult,
} from '../pages/ImageToPdfPage/types';

interface InspectImageFilesData {
  files: ImageInspectionResult[];
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

export async function pickImageFiles(): Promise<string[]> {
  return invokeWithTimeout<string[]>('pick_image_files', undefined, 60000);
}

export async function inspectImageFiles(paths: string[]): Promise<ImageInspectionResult[]> {
  const response = await invokeWithTimeout<EngineTransportResponse<InspectImageFilesData>>(
    'inspect_image_files',
    { payload: { paths } },
    20000,
  );
  return unwrapEngineResponse(response).files;
}

export async function startImageToPdf(
  jobId: string,
  files: ImageQueueItem[],
  options: ImageToPdfOptions,
): Promise<StartJobData> {
  const payload = {
    job_id: jobId,
    files: files.map((file) => ({ file_id: file.fileId, path: file.path })),
    output_directory: options.outputDirectory,
    output_filename: options.outputFilename,
    page_size: options.pageSize,
    orientation: options.orientation,
    margin: options.margin,
    fit_mode: options.fitMode,
    image_quality_preset: options.imageQualityPreset,
    jpeg_quality: options.jpegQuality,
    optimize_pdf_size: options.optimizePdfSize,
    open_output_after_finish: options.openOutputAfterFinish,
    performance_mode: options.performanceMode,
  };
  const response = await invokeWithTimeout<EngineTransportResponse<StartJobData>>('start_image_to_pdf', { payload }, 20000);
  return unwrapEngineResponse(response);
}

export async function cancelImageToPdfJob(jobId: string): Promise<CancelJobData> {
  const response = await invokeWithTimeout<EngineTransportResponse<CancelJobData>>(
    'cancel_engine_job',
    { jobId },
    10000,
  );
  return unwrapEngineResponse(response);
}
