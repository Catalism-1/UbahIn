import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { openLogFolder } from '../services/engine';
import {
  pickImageFiles,
  inspectImageFiles,
  startImageToPdf,
  cancelImageToPdfJob,
} from '../services/imageToPdf';
import {
  pickOutputDirectory,
  openOutputDirectory,
  createJobId,
} from '../services/pdfToJpg';
import type { ToastMessage, ToastTone } from '../components/common/Toast';
import { useTauriEvent } from './useTauriEvent';
import type {
  ImageQueueItem,
  ImageInspectionResult,
  ImageToPdfOptions,
  ImageToPdfProgress,
  ImageToPdfResult,
  JobStatus,
} from '../pages/ImageToPdfPage/types';

const MAX_FILES = 50;

export const DEFAULT_IMAGE_JOB_DEFAULTS: ImageToPdfOptions = {
  outputDirectory: '',
  outputFilename: 'Hasil_Dokumen.pdf',
  pageSize: 'original',
  orientation: 'auto',
  margin: 'normal',
  fitMode: 'contain',
  openOutputAfterFinish: true,
  performanceMode: 'balanced',
};

function toastId(): string {
  return `toast-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function samePath(left: string, right: string): boolean {
  return left.toLowerCase().trim() === right.toLowerCase().trim();
}

export function useImageToPdfJob(isEngineReady: boolean, defaults: ImageToPdfOptions = DEFAULT_IMAGE_JOB_DEFAULTS) {
  const [files, setFiles] = useState<ImageQueueItem[]>([]);
  const [options, setOptions] = useState<ImageToPdfOptions>(defaults);
  const [status, setStatus] = useState<JobStatus>('idle');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState<ImageToPdfProgress | null>(null);
  const [result, setResult] = useState<ImageToPdfResult | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const isBusy = status === 'inspecting' || status === 'starting' || status === 'processing' || status === 'cancelling';
  const validFiles = useMemo(() => files.filter((file) => file.status !== 'failed'), [files]);
  const validFileCount = validFiles.length;
  const completedFiles = useMemo(() => files.filter((file) => file.status === 'completed').length, [files]);
  const canStart = isEngineReady && validFileCount > 0 && Boolean(options.outputDirectory) && Boolean(options.outputFilename) && !isBusy;

  const addToast = useCallback((title: string, tone: ToastTone = 'info', message?: string) => {
    const id = toastId();
    setToasts((current) => [...current.slice(-2), { id, title, message, tone }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 4200);
  }, []);

  // Update default output folder from global settings when loaded
  const freshnessRef = useRef({ status, fileCount: files.length });
  freshnessRef.current = { status, fileCount: files.length };
  const defaultsKey = JSON.stringify(defaults);
  useEffect(() => {
    if (freshnessRef.current.status === 'idle' && freshnessRef.current.fileCount === 0) {
      setOptions(defaults);
    }
  }, [defaultsKey]);

  const handlePickFiles = useCallback(async () => {
    if (isBusy) return;
    try {
      const pickedPaths = await pickImageFiles();
      if (pickedPaths.length === 0) return;

      const existingPaths = new Set(files.map((file) => file.path.toLowerCase().trim()));
      const uniquePaths = pickedPaths.filter((path) => !existingPaths.has(path.toLowerCase().trim()));
      const allowedPaths = uniquePaths.slice(0, Math.max(0, MAX_FILES - files.length));

      if (allowedPaths.length === 0) {
        addToast('Tidak ada gambar baru ditambahkan.', 'warning', 'File duplikat atau antrean sudah mencapai batas 50 gambar.');
        return;
      }

      setStatus('inspecting');
      const inspected = await inspectImageFiles(allowedPaths);
      const queueItems = inspected.map((file): ImageQueueItem => {
        const failed = file.status === 'failed' || Boolean(file.error);
        return {
          fileId: file.file_id,
          path: file.path,
          filename: file.filename,
          sizeBytes: file.size_bytes,
          format: file.format,
          width: file.width,
          height: file.height,
          status: failed ? 'failed' : 'ready',
          warning: file.warning,
          error: file.error,
          thumbnailDataUri: file.thumbnail_data_uri,
        };
      });

      setFiles((current) => [...current, ...queueItems].slice(0, MAX_FILES));
      const failedCount = inspected.filter((item) => item.status === 'failed' || item.error).length;
      addToast(
        'Gambar selesai diperiksa.',
        failedCount > 0 ? 'warning' : 'success',
        failedCount > 0 ? `${failedCount} file tidak valid.` : `${inspected.length} file ditambahkan ke antrean.`,
      );
      setStatus('ready');
    } catch (error) {
      setStatus(files.length > 0 ? 'ready' : 'idle');
      addToast('Gagal memeriksa gambar.', 'error', error instanceof Error ? error.message : 'Silakan coba lagi.');
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
      const temp = copy[index];
      copy[index] = copy[nextIndex];
      copy[nextIndex] = temp;
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

    try {
      await startImageToPdf(jobId, validFiles, options);
      setStatus('processing');
    } catch (error) {
      setActiveJobId(null);
      setStatus('ready');
      addToast('Konversi gagal dimulai.', 'error', error instanceof Error ? error.message : 'Silakan coba lagi.');
      console.error(error);
    }
  }, [addToast, canStart, isEngineReady, options, validFiles]);

  const cancelJob = useCallback(async () => {
    if (!activeJobId || status === 'cancelling') return;
    setStatus('cancelling');
    try {
      await cancelImageToPdfJob(activeJobId);
    } catch (error) {
      addToast('Permintaan pembatalan gagal.', 'error', error instanceof Error ? error.message : 'Engine tidak merespons.');
      console.error(error);
    }
  }, [activeJobId, addToast, status]);

  const openOutput = useCallback(async () => {
    const directory = result?.output_directory || options.outputDirectory;
    if (!directory) return;
    try {
      await openOutputDirectory(directory);
    } catch (error) {
      addToast('Folder hasil tidak dapat dibuka.', 'error', error instanceof Error ? error.message : 'Silakan buka secara manual.');
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

  const handleProgressEvent = useCallback((event: ImageToPdfProgress) => {
    if (event.job_id && activeJobId && event.job_id !== activeJobId) return;
    setStatus('processing');
    setProgress(event);
    setFiles((current) =>
      current.map((file) => (file.filename === event.current_file && file.status === 'ready' ? { ...file, status: 'processing' } : file)),
    );
  }, [activeJobId]);

  const handleFileCompletedEvent = useCallback((event: { file_id?: string; path?: string; filename: string; error?: string }) => {
    if (!activeJobId) return;
    setFiles((current) =>
      current.map((file) => {
        const sameFileId = Boolean(event.file_id) && file.fileId === event.file_id;
        const sameFilePath = Boolean(event.path) && samePath(file.path, event.path!);
        if (!sameFileId && !sameFilePath) return file;
        return {
          ...file,
          status: 'completed',
        };
      })
    );
  }, [activeJobId]);

  const handleWarningEvent = useCallback((event: { file_id?: string; path?: string; filename: string; error?: string; message: string }) => {
    if (!activeJobId) return;
    setFiles((current) =>
      current.map((file) => {
        const sameFileId = Boolean(event.file_id) && file.fileId === event.file_id;
        const sameFilePath = Boolean(event.path) && samePath(file.path, event.path!);
        if (!sameFileId && !sameFilePath) return file;
        return {
          ...file,
          status: 'failed',
          error: event.error || event.message,
        };
      })
    );
    addToast('Satu file gagal diproses.', 'warning', event.message);
  }, [activeJobId, addToast]);

  const finishJob = useCallback((event: ImageToPdfResult, nextStatus: JobStatus) => {
    if (event.job_id && activeJobId && event.job_id !== activeJobId) return;
    setResult(event);
    setShowResult(true);
    setStatus(nextStatus);
    setActiveJobId(null);

    if (nextStatus === 'cancelled') {
      setFiles((current) => current.map((file) => (file.status === 'processing' ? { ...file, status: 'cancelled' } : file)));
      addToast('Konversi dibatalkan.', 'warning');
    } else if (event.failed_files > 0 && event.successful_files > 0) {
      addToast('Selesai dengan beberapa file gagal.', 'warning', 'Beberapa gambar tidak dapat dimasukkan ke PDF.');
    } else if (nextStatus === 'failed') {
      addToast('Konversi gagal.', 'error', event.errors[0] ?? 'Gagal membuat file PDF.');
    } else {
      addToast('PDF berhasil dibuat!', 'success', `${event.successful_files} gambar digabungkan.`);
    }
  }, [activeJobId, addToast]);

  useTauriEvent<ImageToPdfProgress>('engine://progress', handleProgressEvent, Boolean(activeJobId));
  useTauriEvent<any>('engine://file-completed', handleFileCompletedEvent, Boolean(activeJobId));
  useTauriEvent<any>('engine://warning', handleWarningEvent, Boolean(activeJobId));
  useTauriEvent<ImageToPdfResult>('engine://job-completed', (event) => finishJob(event, 'completed'), Boolean(activeJobId));
  useTauriEvent<ImageToPdfResult>('engine://job-failed', (event) => finishJob(event, 'failed'), Boolean(activeJobId));
  useTauriEvent<ImageToPdfResult>('engine://job-cancelled', (event) => finishJob(event, 'cancelled'), Boolean(activeJobId));

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
