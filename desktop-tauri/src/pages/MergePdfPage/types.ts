import type {
  EngineTransportResponse,
  FileCompletedEvent,
  JobProgress,
  JobResult,
  JobStatus,
  PdfInspectionResult,
  PdfQueueItem,
  PerformanceMode,
  WarningEvent,
} from '../PdfToJpgPage/types';

export type MergePdfQueueItem = PdfQueueItem;
export type MergePdfInspectionResult = PdfInspectionResult;
export type MergePdfProgress = JobProgress;
export type MergePdfStatus = JobStatus;
export type MergePdfFileCompletedEvent = FileCompletedEvent;
export type MergePdfWarningEvent = WarningEvent;

export interface MergePdfResult extends JobResult {
  output_pdf_path?: string;
  output_filename?: string;
  output_size_bytes?: number;
  tool_type?: string;
}

export interface MergePdfOptions {
  outputDirectory: string;
  outputFilename: string;
  openOutputAfterFinish: boolean;
  performanceMode: PerformanceMode;
}

export interface MergePdfDefaults {
  outputDirectory: string;
  openOutputAfterFinish: boolean;
  performanceMode: PerformanceMode;
}

export type { EngineTransportResponse };
