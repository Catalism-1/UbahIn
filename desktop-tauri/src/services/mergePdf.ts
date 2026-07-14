import { invokeWithTimeout, unwrapEngineResponse } from './transport';
import { createJobId, inspectPdfFiles, openOutputDirectory, pickOutputDirectory, pickPdfFiles } from './pdfToJpg';
import type { EngineTransportResponse, MergePdfOptions, MergePdfQueueItem } from '../pages/MergePdfPage/types';

interface StartJobData {
  job_id: string;
  status: string;
}

interface CancelJobData {
  job_id: string;
  status: string;
}

interface StartMergePdfPayload {
  job_id: string;
  files: Array<{
    file_id: string;
    path: string;
  }>;
  output_directory: string;
  output_filename: string;
  open_output_after_finish: boolean;
  performance_mode: string;
}

export { createJobId, inspectPdfFiles, openOutputDirectory, pickOutputDirectory, pickPdfFiles };

export async function startMergePdf(
  jobId: string,
  files: MergePdfQueueItem[],
  options: MergePdfOptions,
): Promise<StartJobData> {
  const payload: StartMergePdfPayload = {
    job_id: jobId,
    files: files.map((file) => ({ file_id: file.fileId, path: file.path })),
    output_directory: options.outputDirectory,
    output_filename: options.outputFilename,
    open_output_after_finish: options.openOutputAfterFinish,
    performance_mode: options.performanceMode,
  };
  const response = await invokeWithTimeout<EngineTransportResponse<StartJobData>>('start_merge_pdf', { payload }, 15000);
  return unwrapEngineResponse(response);
}

export async function cancelMergePdfJob(jobId: string): Promise<CancelJobData> {
  const response = await invokeWithTimeout<EngineTransportResponse<CancelJobData>>(
    'cancel_engine_job',
    { jobId },
    10000,
  );
  return unwrapEngineResponse(response);
}
