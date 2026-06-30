export type HeicOutputFormat = 'jpg' | 'png';
export type JpegQualityPreset = 'high' | 'balanced' | 'compact' | 'custom';
export type PngCompressionLevel = number;

export interface HeicQueueItem {
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

export interface HeicInspectionResult {
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

export interface HeicToImageOptions {
  outputDirectory: string;
  outputFormat: HeicOutputFormat;
  jpegQualityPreset: JpegQualityPreset;
  jpegQuality: number;
  pngCompressionLevel: PngCompressionLevel;
  preserveMetadata: boolean;
  openOutputAfterFinish: boolean;
  performanceMode: string;
}

export interface HeicConversionProgress {
  job_id?: string;
  current_file: string;
  current_file_index: number;
  total_files: number;
  overall_percent: number;
  file_percent: number;
  message: string;
}

export interface HeicConversionResult {
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
  output_directory: string;
  output_paths: string[];
  duration_seconds: number;
  warnings: string[];
  errors: string[];
  total_images?: number;
  successful_images?: number;
  failed_images?: number;
}
