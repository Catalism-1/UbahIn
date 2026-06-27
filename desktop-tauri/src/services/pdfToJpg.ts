import { invoke } from '@tauri-apps/api/core';
import type {
  EngineTransportResponse,
  JobResult,
  PdfInspectionResult,
  PdfQueueItem,
  PdfToJpgOptions,
} from '../pages/PdfToJpgPage/types';

interface InspectPdfFilesData {
  files: PdfInspectionResult[];
}

interface StartJobData {
  job_id: string;
  status: string;
}

interface CancelJobData {
  job_id: string;
  status: string;
}

interface JobStatusData {
  job: unknown;
}

interface StartPdfPayload {
  job_id: string;
  files: Array<{
    file_id: string;
    path: string;
  }>;
  output_directory: string;
  preset: string;
  dpi: number;
  jpeg_quality: number;
  optimize_file_size: boolean;
  create_zip: boolean;
  open_output_after_finish: boolean;
  performance_mode: string;
}

function timeoutPromise<T>(timeoutMs: number, message: string): Promise<T> {
  return new Promise((_, reject) => {
    window.setTimeout(() => reject(new Error(message)), timeoutMs);
  });
}

async function invokeWithTimeout<T>(command: string, args?: Record<string, unknown>, timeoutMs = 10000): Promise<T> {
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

export function createJobId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `job-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function pickPdfFiles(): Promise<string[]> {
  return invokeWithTimeout<string[]>('pick_pdf_files', undefined, 60000);
}

export async function inspectPdfFiles(paths: string[]): Promise<PdfInspectionResult[]> {
  const response = await invokeWithTimeout<EngineTransportResponse<InspectPdfFilesData>>(
    'inspect_pdf_files',
    { payload: { paths } },
    15000,
  );
  return unwrapEngineResponse(response).files;
}

export async function pickOutputDirectory(): Promise<string | null> {
  return invokeWithTimeout<string | null>('pick_output_directory', undefined, 60000);
}

export async function startPdfToJpg(
  jobId: string,
  files: PdfQueueItem[],
  options: PdfToJpgOptions,
): Promise<StartJobData> {
  const payload: StartPdfPayload = {
    job_id: jobId,
    files: files.map((file) => ({ file_id: file.fileId, path: file.path })),
    output_directory: options.outputDirectory,
    preset: options.preset,
    dpi: options.dpi,
    jpeg_quality: options.jpegQuality,
    optimize_file_size: options.optimizeFileSize,
    create_zip: options.createZip,
    open_output_after_finish: options.openOutputAfterFinish,
    performance_mode: options.performanceMode,
  };
  const response = await invokeWithTimeout<EngineTransportResponse<StartJobData>>('start_pdf_to_jpg', { payload }, 15000);
  return unwrapEngineResponse(response);
}

export async function cancelPdfToJpgJob(jobId: string): Promise<CancelJobData> {
  const response = await invokeWithTimeout<EngineTransportResponse<CancelJobData>>(
    'cancel_pdf_to_jpg_job',
    { payload: { job_id: jobId } },
    10000,
  );
  return unwrapEngineResponse(response);
}

export async function getJobStatus(jobId: string): Promise<JobStatusData> {
  const response = await invokeWithTimeout<EngineTransportResponse<JobStatusData>>(
    'get_job_status',
    { payload: { job_id: jobId } },
    10000,
  );
  return unwrapEngineResponse(response);
}

export async function openOutputDirectory(path: string): Promise<void> {
  await invokeWithTimeout<void>('open_output_directory', { payload: { path } }, 10000);
}

export function isFinishedResult(result: JobResult | null): result is JobResult {
  return result !== null;
}
