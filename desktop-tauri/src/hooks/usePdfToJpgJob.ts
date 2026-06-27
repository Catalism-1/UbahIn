import { useCallback, useMemo, useState } from 'react';
import { openLogFolder } from '../services/engine';
import {
  cancelPdfToJpgJob,
  createJobId,
  inspectPdfFiles,
  openOutputDirectory,
  pickOutputDirectory,
  pickPdfFiles,
  startPdfToJpg,
} from '../services/pdfToJpg';
import type { ToastMessage, ToastTone } from '../components/common/Toast';
import { useTauriEvent } from './useTauriEvent';
import type {
  FileCompletedEvent,
  JobProgress,
  JobResult,
  JobStatus,
  PdfInspectionResult,
  PdfPreset,
  PdfPresetConfig,
  PdfQueueItem,
  PdfToJpgOptions,
  WarningEvent,
} from '../pages/PdfToJpgPage/types';

const MAX_FILES = 50;

export const pdfPresets: PdfPresetConfig[] = [
  { id: 'standard', label: 'Standard', dpi: 150, jpegQuality: 80 },
  { id: 'high', label: 'Tinggi', dpi: 200, jpegQuality: 90 },
  { id: 'ultra', label: 'Sangat Tinggi', dpi: 300, jpegQuality: 95 },
];

function inspectionToQueueItem(file: PdfInspectionResult): PdfQueueItem {
  const failed = file.status === 'failed' || Boolean(file.error);
  return {
    fileId: file.file_id,
    path: file.path,
    filename: file.filename,
    sizeBytes: file.size_bytes,
    pageCount: file.page_count,
    status: failed ? 'failed' : 'ready',
    warning: file.warning,
    error: file.error,
  };
}

function toastId(): string {
  return `toast-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function samePath(left: string, right: string): boolean {
  return left.toLocaleLowerCase() === right.toLocaleLowerCase();
}

function updateFileFromEvent(files: PdfQueueItem[], event: FileCompletedEvent, status: PdfQueueItem['status']): PdfQueueItem[] {
  return files.map((file) => {
    const sameFileId = Boolean(event.file_id) && file.fileId === event.file_id;
    const sameFilePath = Boolean(event.path) && samePath(file.path, event.path);
    if (!sameFileId && !sameFilePath) return file;
    return {
      ...file,
      status,
      outputCount: event.output_count,
      error: event.error ?? file.error,
    };
  });
}

export function usePdfToJpgJob(isEngineReady: boolean) {
  const [files, setFiles] = useState<PdfQueueItem[]>([]);
  const [options, setOptions] = useState<PdfToJpgOptions>({
    outputDirectory: '',
    preset: 'standard',
    dpi: 150,
    jpegQuality: 80,
    optimizeFileSize: true,
    createZip: false,
    openOutputAfterFinish: false,
    performanceMode: 'balanced',
  });
  const [status, setStatus] = useState<JobStatus>('idle');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState<JobProgress | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const isBusy = status === 'inspecting' || status === 'starting' || status === 'processing' || status === 'cancelling';
  const validFiles = useMemo(() => files.filter((file) => file.status !== 'failed'), [files]);
  const validFileCount = validFiles.length;
  const totalPages = useMemo(() => validFiles.reduce((sum, file) => sum + file.pageCount, 0), [validFiles]);
  const completedFiles = useMemo(() => files.filter((file) => file.status === 'completed').length, [files]);
  const canStart = isEngineReady && validFileCount > 0 && Boolean(options.outputDirectory) && !isBusy;

  const addToast = useCallback((title: string, tone: ToastTone = 'info', message?: string) => {
    const id = toastId();
    setToasts((current) => [...current.slice(-2), { id, title, message, tone }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 4200);
  }, []);

  const handlePickFiles = useCallback(async () => {
    if (isBusy) return;
    try {
      const pickedPaths = await pickPdfFiles();
      if (pickedPaths.length === 0) return;

      const existingPaths = new Set(files.map((file) => file.path.toLocaleLowerCase()));
      const uniquePaths = pickedPaths.filter((path) => !existingPaths.has(path.toLocaleLowerCase()));
      const allowedPaths = uniquePaths.slice(0, Math.max(0, MAX_FILES - files.length));

      if (allowedPaths.length === 0) {
        addToast('Tidak ada file baru ditambahkan.', 'warning', 'File duplikat atau antrean sudah mencapai batas 50 PDF.');
        return;
      }

      setStatus('inspecting');
      const inspected = await inspectPdfFiles(allowedPaths);
      setFiles((current) => [...current, ...inspected.map(inspectionToQueueItem)].slice(0, MAX_FILES));
      const failed = inspected.filter((item) => item.status === 'failed' || item.error).length;
      addToast(
        'File PDF selesai diperiksa.',
        failed > 0 ? 'warning' : 'success',
        failed > 0 ? `${failed} file tidak dapat diproses.` : `${inspected.length} file siap dikonversi.`,
      );
      setStatus('ready');
    } catch (error) {
      setStatus(files.length > 0 ? 'ready' : 'idle');
      addToast('Gagal memeriksa PDF.', 'error', error instanceof Error ? error.message : 'Silakan coba lagi.');
      console.error(error);
    }
  }, [addToast, files, isBusy]);

  const removeFile = useCallback((fileId: string) => {
    if (isBusy) return;
    setFiles((current) => current.filter((file) => file.fileId !== fileId));
  }, [isBusy]);

  const requestClearFiles = useCallback(() => {
    if (isBusy || files.length === 0) return;
    setShowClearConfirm(true);
  }, [files.length, isBusy]);

  const confirmClearFiles = useCallback(() => {
    setShowClearConfirm(false);
    setFiles([]);
    setProgress(null);
    setResult(null);
    setStatus('idle');
    addToast('Semua file telah dihapus.', 'success');
  }, [addToast]);

  const handlePickOutput = useCallback(async () => {
    if (isBusy) return;
    try {
      const directory = await pickOutputDirectory();
      if (!directory) return;
      setOptions((current) => ({ ...current, outputDirectory: directory }));
    } catch (error) {
      addToast('Folder hasil tidak dapat dipilih.', 'error', error instanceof Error ? error.message : 'Silakan coba lagi.');
    }
  }, [addToast, isBusy]);

  const changePreset = useCallback((presetId: PdfPreset) => {
    const preset = pdfPresets.find((item) => item.id === presetId);
    if (!preset) return;
    setOptions((current) => ({
      ...current,
      preset: preset.id,
      dpi: preset.dpi,
      jpegQuality: preset.jpegQuality,
    }));
  }, []);

  const toggleOption = useCallback((key: 'optimizeFileSize' | 'createZip' | 'openOutputAfterFinish') => {
    setOptions((current) => ({ ...current, [key]: !current[key] }));
  }, []);

  const startJob = useCallback(async () => {
    if (!isEngineReady) {
      addToast('Engine belum siap.', 'warning', 'Jalankan Pemeriksaan Engine terlebih dahulu.');
      return;
    }
    if (!canStart) return;

    const jobId = createJobId();
    setActiveJobId(jobId);
    setProgress(null);
    setResult(null);
    setShowResult(false);
    setStatus('starting');
    setFiles((current) => current.map((file) => (file.status === 'ready' ? { ...file, outputCount: undefined } : file)));

    try {
      await startPdfToJpg(jobId, validFiles, options);
      setStatus('processing');
    } catch (error) {
      setActiveJobId(null);
      setStatus('ready');
      addToast('Konversi tidak dapat dimulai.', 'error', error instanceof Error ? error.message : 'Silakan coba lagi.');
      console.error(error);
    }
  }, [addToast, canStart, isEngineReady, options, validFiles]);

  const cancelJob = useCallback(async () => {
    if (!activeJobId || status === 'cancelling') return;
    setStatus('cancelling');
    try {
      await cancelPdfToJpgJob(activeJobId);
    } catch (error) {
      addToast('Permintaan batal gagal.', 'error', error instanceof Error ? error.message : 'Engine belum merespons.');
      console.error(error);
    }
  }, [activeJobId, addToast, status]);

  const openOutput = useCallback(async () => {
    const directory = result?.output_directory || options.outputDirectory;
    if (!directory) return;
    try {
      await openOutputDirectory(directory);
    } catch (error) {
      addToast('Folder hasil tidak dapat dibuka.', 'error', error instanceof Error ? error.message : 'Silakan buka manual.');
    }
  }, [addToast, options.outputDirectory, result?.output_directory]);

  const openLogs = useCallback(async () => {
    try {
      await openLogFolder();
    } catch (error) {
      addToast('Folder log tidak dapat dibuka.', 'error', error instanceof Error ? error.message : 'Silakan coba lagi.');
    }
  }, [addToast]);

  const resetAfterResult = useCallback(() => {
    setFiles([]);
    setProgress(null);
    setResult(null);
    setShowResult(false);
    setActiveJobId(null);
    setStatus('idle');
  }, []);

  const handleProgressEvent = useCallback((event: JobProgress) => {
    if (event.job_id && activeJobId && event.job_id !== activeJobId) return;
    setStatus('processing');
    setProgress(event);
    setFiles((current) =>
      current.map((file) => (file.filename === event.current_file && file.status === 'ready' ? { ...file, status: 'processing' } : file)),
    );
  }, [activeJobId]);

  const handleFileCompletedEvent = useCallback((event: FileCompletedEvent) => {
    if (event.job_id && activeJobId && event.job_id !== activeJobId) return;
    setFiles((current) => updateFileFromEvent(current, event, 'completed'));
  }, [activeJobId]);

  const handleWarningEvent = useCallback((event: WarningEvent) => {
    if (event.job_id && activeJobId && event.job_id !== activeJobId) return;
    setFiles((current) => updateFileFromEvent(current, event, 'failed'));
    addToast('Satu file gagal diproses.', 'warning', event.message);
  }, [activeJobId, addToast]);

  const finishJob = useCallback((event: JobResult, nextStatus: JobStatus) => {
    if (event.job_id && activeJobId && event.job_id !== activeJobId) return;
    setResult(event);
    setShowResult(true);
    setStatus(nextStatus);
    setActiveJobId(null);
    if (nextStatus === 'cancelled') {
      setFiles((current) => current.map((file) => (file.status === 'processing' ? { ...file, status: 'cancelled' } : file)));
      addToast('Konversi dibatalkan.', 'warning');
    } else if (event.failed_files > 0 && event.successful_files > 0) {
      addToast('Selesai dengan peringatan.', 'warning', 'Beberapa file tidak dapat diproses.');
    } else if (nextStatus === 'failed') {
      addToast('Konversi gagal.', 'error', event.errors[0] ?? 'Tidak ada file yang berhasil diproses.');
    } else {
      addToast('Konversi selesai.', 'success', `${event.total_jpg} JPG dibuat.`);
    }
  }, [activeJobId, addToast]);

  useTauriEvent<JobProgress>('engine://progress', handleProgressEvent, Boolean(activeJobId));
  useTauriEvent<FileCompletedEvent>('engine://file-completed', handleFileCompletedEvent, Boolean(activeJobId));
  useTauriEvent<WarningEvent>('engine://warning', handleWarningEvent, Boolean(activeJobId));
  useTauriEvent<JobResult>('engine://job-completed', (event) => finishJob(event, 'completed'), Boolean(activeJobId));
  useTauriEvent<JobResult>('engine://job-failed', (event) => finishJob(event, 'failed'), Boolean(activeJobId));
  useTauriEvent<JobResult>('engine://job-cancelled', (event) => finishJob(event, 'cancelled'), Boolean(activeJobId));

  return {
    files,
    options,
    presets: pdfPresets,
    status,
    activeJobId,
    progress,
    result,
    showResult,
    showClearConfirm,
    toasts,
    isBusy,
    validFileCount,
    totalPages,
    completedFiles,
    canStart,
    setShowResult,
    setShowClearConfirm,
    handlePickFiles,
    removeFile,
    requestClearFiles,
    confirmClearFiles,
    handlePickOutput,
    changePreset,
    toggleOption,
    startJob,
    cancelJob,
    openOutput,
    openLogs,
    resetAfterResult,
  };
}
