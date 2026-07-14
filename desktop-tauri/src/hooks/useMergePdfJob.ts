import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { openLogFolder } from '../services/engine';
import {
  cancelMergePdfJob,
  createJobId,
  inspectPdfFiles,
  openOutputDirectory,
  pickOutputDirectory,
  pickPdfFiles,
  startMergePdf,
} from '../services/mergePdf';
import type { ToastMessage, ToastTone } from '../components/common/Toast';
import { useTauriEvent } from './useTauriEvent';
import type {
  MergePdfDefaults,
  MergePdfFileCompletedEvent,
  MergePdfInspectionResult,
  MergePdfOptions,
  MergePdfProgress,
  MergePdfQueueItem,
  MergePdfResult,
  MergePdfStatus,
  MergePdfWarningEvent,
} from '../pages/MergePdfPage/types';

const MAX_FILES = 50;

export const DEFAULT_MERGE_PDF_DEFAULTS: MergePdfDefaults = {
  outputDirectory: '',
  openOutputAfterFinish: true,
  performanceMode: 'balanced',
};

function optionsFromDefaults(defaults: MergePdfDefaults): MergePdfOptions {
  return {
    outputDirectory: defaults.outputDirectory,
    outputFilename: 'Gabungan_PDF.pdf',
    openOutputAfterFinish: defaults.openOutputAfterFinish,
    performanceMode: defaults.performanceMode,
  };
}

function inspectionToQueueItem(file: MergePdfInspectionResult): MergePdfQueueItem {
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

function updateFileFromEvent(
  files: MergePdfQueueItem[],
  event: MergePdfFileCompletedEvent,
  status: MergePdfQueueItem['status'],
): MergePdfQueueItem[] {
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

export function useMergePdfJob(isEngineReady: boolean, defaults: MergePdfDefaults = DEFAULT_MERGE_PDF_DEFAULTS) {
  const [files, setFiles] = useState<MergePdfQueueItem[]>([]);
  const [options, setOptions] = useState<MergePdfOptions>(() => optionsFromDefaults(defaults));
  const [status, setStatus] = useState<MergePdfStatus>('idle');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const activeJobIdRef = useRef<string | null>(null);
  const [progress, setProgress] = useState<MergePdfProgress | null>(null);
  const [result, setResult] = useState<MergePdfResult | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const isBusy = status === 'inspecting' || status === 'starting' || status === 'processing' || status === 'cancelling';
  const validFiles = useMemo(() => files.filter((file) => file.status !== 'failed'), [files]);
  const validFileCount = validFiles.length;
  const totalPages = useMemo(() => validFiles.reduce((sum, file) => sum + file.pageCount, 0), [validFiles]);
  const completedFiles = useMemo(() => files.filter((file) => file.status === 'completed').length, [files]);
  const canStart = isEngineReady && validFileCount >= 2 && Boolean(options.outputDirectory) && Boolean(options.outputFilename.trim()) && !isBusy;

  const addToast = useCallback((title: string, tone: ToastTone = 'info', message?: string) => {
    const id = toastId();
    setToasts((current) => [...current.slice(-2), { id, title, message, tone }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 4200);
  }, []);

  const freshnessRef = useRef({ status, fileCount: files.length });
  freshnessRef.current = { status, fileCount: files.length };
  const defaultsKey = JSON.stringify(defaults);
  useEffect(() => {
    if (freshnessRef.current.status === 'idle' && freshnessRef.current.fileCount === 0) {
      setOptions((current) => ({ ...optionsFromDefaults(defaults), outputFilename: current.outputFilename }));
    }
  }, [defaultsKey]);

  const handlePickFiles = useCallback(async () => {
    if (isBusy) return;
    try {
      const pickedPaths = await pickPdfFiles();
      if (pickedPaths.length === 0) return;

      const existingPaths = new Set(files.map((file) => file.path.toLocaleLowerCase()));
      const uniquePaths = pickedPaths.filter((path) => !existingPaths.has(path.toLocaleLowerCase()));
      const allowedPaths = uniquePaths.slice(0, Math.max(0, MAX_FILES - files.length));

      if (allowedPaths.length === 0) {
        addToast('Tidak ada PDF baru ditambahkan.', 'warning', 'File duplikat atau antrean sudah mencapai batas 50 PDF.');
        return;
      }

      setStatus('inspecting');
      const inspected = await inspectPdfFiles(allowedPaths);
      setFiles((current) => [...current, ...inspected.map(inspectionToQueueItem)].slice(0, MAX_FILES));
      const failed = inspected.filter((item) => item.status === 'failed' || item.error).length;
      addToast(
        'File PDF selesai diperiksa.',
        failed > 0 ? 'warning' : 'success',
        failed > 0 ? `${failed} file tidak dapat digabungkan.` : `${inspected.length} PDF siap digabungkan.`,
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

  const moveFile = useCallback((index: number, direction: 'up' | 'down') => {
    if (isBusy) return;
    setFiles((current) => {
      const nextIndex = direction === 'up' ? index - 1 : index + 1;
      if (nextIndex < 0 || nextIndex >= current.length) return current;
      const copy = [...current];
      const item = copy[index];
      copy[index] = copy[nextIndex];
      copy[nextIndex] = item;
      return copy;
    });
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
    addToast('Semua PDF telah dihapus dari antrean.', 'success');
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

  const startJob = useCallback(async () => {
    if (!isEngineReady) {
      addToast('Engine belum siap.', 'warning', 'Tunggu proses penyiapan selesai atau buka Diagnostik untuk mencoba lagi.');
      return;
    }
    if (validFileCount < 2) {
      addToast('Butuh minimal dua PDF.', 'warning', 'Tambahkan PDF lain sebelum menjalankan merge.');
      return;
    }
    if (!canStart) return;

    const jobId = createJobId();
    activeJobIdRef.current = jobId;
    setActiveJobId(jobId);
    setProgress(null);
    setResult(null);
    setShowResult(false);
    setStatus('starting');
    setFiles((current) => current.map((file) => (file.status === 'ready' ? { ...file, outputCount: undefined } : file)));

    try {
      await startMergePdf(jobId, validFiles, options);
      setStatus('processing');
    } catch (error) {
      activeJobIdRef.current = null;
      setActiveJobId(null);
      setStatus('ready');
      addToast('Merge PDF tidak dapat dimulai.', 'error', error instanceof Error ? error.message : 'Silakan coba lagi.');
      console.error(error);
    }
  }, [addToast, canStart, isEngineReady, options, validFileCount, validFiles]);

  const cancelJob = useCallback(async () => {
    if (!activeJobId || status === 'cancelling') return;
    setStatus('cancelling');
    try {
      await cancelMergePdfJob(activeJobId);
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
    activeJobIdRef.current = null;
    setActiveJobId(null);
    setStatus('idle');
  }, []);

  const handleProgressEvent = useCallback((event: MergePdfProgress) => {
    if (!activeJobIdRef.current || event.job_id !== activeJobIdRef.current) return;
    setStatus('processing');
    setProgress(event);
    setFiles((current) =>
      current.map((file) => (file.filename === event.current_file && file.status === 'ready' ? { ...file, status: 'processing' } : file)),
    );
  }, []);

  const handleFileCompletedEvent = useCallback((event: MergePdfFileCompletedEvent) => {
    if (!activeJobIdRef.current || event.job_id !== activeJobIdRef.current) return;
    setFiles((current) => updateFileFromEvent(current, event, 'completed'));
  }, []);

  const handleWarningEvent = useCallback((event: MergePdfWarningEvent) => {
    if (!activeJobIdRef.current || event.job_id !== activeJobIdRef.current) return;
    setFiles((current) => updateFileFromEvent(current, event, 'failed'));
    addToast('Satu PDF gagal diproses.', 'warning', event.message);
  }, [addToast]);

  const finishJob = useCallback((event: MergePdfResult, nextStatus: MergePdfStatus) => {
    if (!activeJobIdRef.current || event.job_id !== activeJobIdRef.current) return;
    setResult(event);
    setShowResult(true);
    setStatus(nextStatus);
    activeJobIdRef.current = null;
    setActiveJobId(null);
    if (nextStatus === 'cancelled') {
      setFiles((current) => current.map((file) => (file.status === 'processing' ? { ...file, status: 'cancelled' } : file)));
      addToast('Merge PDF dibatalkan.', 'warning');
    } else if (nextStatus === 'failed') {
      addToast('Merge PDF gagal.', 'error', event.errors[0] ?? 'Tidak ada PDF yang berhasil digabungkan.');
    } else {
      addToast('PDF berhasil digabungkan.', 'success', event.output_filename || 'File PDF hasil sudah dibuat.');
    }
  }, [addToast]);

  useTauriEvent<MergePdfProgress>('engine://progress', handleProgressEvent, true);
  useTauriEvent<MergePdfFileCompletedEvent>('engine://file-completed', handleFileCompletedEvent, true);
  useTauriEvent<MergePdfWarningEvent>('engine://warning', handleWarningEvent, true);
  useTauriEvent<MergePdfResult>('engine://job-completed', (event) => finishJob(event, 'completed'), true);
  useTauriEvent<MergePdfResult>('engine://job-failed', (event) => finishJob(event, 'failed'), true);
  useTauriEvent<MergePdfResult>('engine://job-cancelled', (event) => finishJob(event, 'cancelled'), true);

  return {
    files,
    options,
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
    setOptions,
    setShowResult,
    setShowClearConfirm,
    handlePickFiles,
    removeFile,
    moveFile,
    requestClearFiles,
    confirmClearFiles,
    handlePickOutput,
    startJob,
    cancelJob,
    openOutput,
    openLogs,
    resetAfterResult,
  };
}
