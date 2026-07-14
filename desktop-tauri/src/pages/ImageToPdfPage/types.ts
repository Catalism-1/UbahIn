export type PdfPageSize = 'original' | 'a4' | 'letter';
export type PdfOrientation = 'auto' | 'portrait' | 'landscape';
export type PdfMargin = 'none' | 'small' | 'normal';
export type ImageFitMode = 'contain' | 'fill';

export interface ImageQueueItem {
  fileId: string;
  path: string;
  filename: string;
  sizeBytes: number;
  format: string | null;
  width: number;
  height: number;
  status: 'ready' | 'processing' | 'completed' | 'failed' | 'cancelled';
  warning?: string | null;
  error?: string | null;
  thumbnailDataUri?: string | null;
}

export interface ImageInspectionResult {
  file_id: string;
  path: string;
  filename: string;
  size_bytes: number;
  format: string | null;
  width: number;
  height: number;
  status: 'ready' | 'failed';
  warning: string | null;
  error: string | null;
  thumbnail_data_uri: string | null;
}

export type ImageQualityPreset = 'high' | 'balanced' | 'compact' | 'custom';

export interface ImageToPdfOptions {
  outputDirectory: string;
  outputFilename: string;
  pageSize: PdfPageSize;
  orientation: PdfOrientation;
  margin: PdfMargin;
  fitMode: ImageFitMode;
  imageQualityPreset: ImageQualityPreset;
  jpegQuality: number;
  optimizePdfSize: boolean;
  openOutputAfterFinish: boolean;
  performanceMode: string;
}

export interface ImageToPdfProgress {
  job_id?: string;
  current_file: string;
  current_file_index: number;
  total_files: number;
  overall_percent: number;
  file_percent: number;
  message: string;
}

export interface ImageToPdfResult {
  job_id: string;
  tool_type?: string;
  status: string;
  successful_files: number;
  failed_files: number;
  skipped_files: number;
  total_input_files: number;
  processed_files: number;
  total_outputs: number;
  output_size_bytes?: number;
  output_pdf_path?: string;
  output_filename?: string;
  output_directory: string;
  output_paths: string[];
  duration_seconds: number;
  warnings: string[];
  errors: string[];
  image_quality_preset?: string;
  jpeg_quality?: number;
  total_images?: number;
  successful_images?: number;
  failed_images?: number;
}

export type JobStatus = 'idle' | 'inspecting' | 'ready' | 'starting' | 'processing' | 'cancelling' | 'completed' | 'failed' | 'cancelled';

export interface EngineTransportResponse<T> {
  type: 'response';
  id: string | null;
  ok: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
}
