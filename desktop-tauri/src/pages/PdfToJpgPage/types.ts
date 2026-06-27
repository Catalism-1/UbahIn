import type { EngineError, EngineResponse } from '../../types/engine';

export type PdfQueueStatus = 'ready' | 'failed' | 'processing' | 'completed' | 'cancelled';

export interface PdfInspectionResult {
  path: string;
  file_id: string;
  filename: string;
  size_bytes: number;
  page_count: number;
  status: string;
  warning?: string;
  error?: string;
}

export interface PdfQueueItem {
  fileId: string;
  path: string;
  filename: string;
  sizeBytes: number;
  pageCount: number;
  status: PdfQueueStatus;
  warning?: string;
  error?: string;
  outputCount?: number;
}

export type PdfPreset = 'standard' | 'high' | 'ultra';
export type PerformanceMode = 'memory_saver' | 'balanced' | 'fast';

export interface PdfPresetConfig {
  id: PdfPreset;
  label: string;
  dpi: number;
  jpegQuality: number;
}

export interface PdfToJpgOptions {
  outputDirectory: string;
  preset: PdfPreset;
  dpi: number;
  jpegQuality: number;
  optimizeFileSize: boolean;
  createZip: boolean;
  openOutputAfterFinish: boolean;
  performanceMode: PerformanceMode;
}

export type JobStatus = 'idle' | 'inspecting' | 'ready' | 'starting' | 'processing' | 'cancelling' | 'completed' | 'failed' | 'cancelled';

export interface JobProgress {
  job_id?: string;
  current_file: string;
  current_file_index: number;
  total_files: number;
  current_page: number;
  total_pages: number;
  overall_percent: number;
  file_percent: number;
  message: string;
}

export interface FileCompletedEvent {
  job_id?: string;
  file_id: string;
  filename: string;
  path: string;
  status: string;
  output_count: number;
  output_paths: string[];
  error?: string | null;
}

export interface WarningEvent extends FileCompletedEvent {
  message: string;
}

export interface JobResult {
  job_id: string;
  status: string;
  successful_files: number;
  failed_files: number;
  skipped_files: number;
  total_input_files: number;
  processed_files: number;
  total_outputs: number;
  total_jpg: number;
  output_directory: string;
  output_paths: string[];
  duration_seconds?: number | null;
  warnings: string[];
  errors: string[];
  failed_file_details: Array<{
    filename: string;
    path: string;
    error: string;
  }>;
}

export type EngineEvent =
  | { event: 'progress'; data: JobProgress }
  | { event: 'file_completed'; data: FileCompletedEvent }
  | { event: 'warning'; data: WarningEvent }
  | { event: 'job_completed'; data: JobResult }
  | { event: 'job_failed'; data: JobResult }
  | { event: 'job_cancelled'; data: JobResult };

export type EngineTransportResponse<TData> = EngineResponse<TData>;
export type { EngineError };
