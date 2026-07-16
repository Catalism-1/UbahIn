import { useState, useCallback, useEffect, useRef } from 'react';
import {
    ImageConversionOptions,
    ImageQueueItem,
    ImageConversionStats
} from '../pages/ImageConversionPage/types';
import {
    inspectImageConversionFiles,
    startImageConversion,
    StartImageConversionPayload
} from '../services/imageConversion';
import { useTauriEvent } from './useTauriEvent';
import { cancelEngineJob } from '../services/engine';
import { useToasts } from './useToasts';

const generateId = () => crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);

export interface UseImageConversionJobResult {
    queue: ImageQueueItem[];
    stats: ImageConversionStats;
    isConverting: boolean;
    isInspecting: boolean;
    activeJobId: string | null;
    showSuccessDialog: boolean;
    setShowSuccessDialog: (show: boolean) => void;
    addFiles: (paths: string[]) => Promise<void>;
    removeFile: (id: string) => void;
    clearQueue: () => void;
    startJob: (options: ImageConversionOptions) => Promise<void>;
    cancelJob: () => Promise<void>;
    resetJobState: () => void;
}

export function useImageConversionJob(): UseImageConversionJobResult {
    const { addToast } = useToasts();
    
    const [queue, setQueue] = useState<ImageQueueItem[]>([]);
    const [isConverting, setIsConverting] = useState(false);
    const [isInspecting, setIsInspecting] = useState(false);
    const [activeJobId, setActiveJobId] = useState<string | null>(null);
    const [showSuccessDialog, setShowSuccessDialog] = useState(false);

    const activeJobIdRef = useRef<string | null>(activeJobId);
    useEffect(() => { activeJobIdRef.current = activeJobId; }, [activeJobId]);

    // Make queue available to callbacks without dependency arrays
    const queueRef = useRef<ImageQueueItem[]>(queue);
    useEffect(() => { queueRef.current = queue; }, [queue]);
    const isConvertingRef = useRef(isConverting);
    useEffect(() => { isConvertingRef.current = isConverting; }, [isConverting]);

    const calculateStats = (items: ImageQueueItem[]): ImageConversionStats => {
        return items.reduce(
            (acc, item) => {
                if (item.status === 'completed') acc.completedFiles++;
                if (item.status === 'failed') acc.failedFiles++;
                acc.totalSizeBytes += item.sizeBytes;
                return acc;
            },
            {
                totalFiles: items.length,
                completedFiles: 0,
                failedFiles: 0,
                totalSizeBytes: 0
            }
        );
    };

    const addFiles = useCallback(async (paths: string[]) => {
        if (paths.length === 0) return;

        console.info('[image-convert] IMAGE_PICKER_SELECTED count=' + paths.length);
        paths.forEach(p => console.info('[image-convert] IMAGE_PICKER_PATH path=' + p));

        setIsInspecting(true);
        const newItems: ImageQueueItem[] = paths.map(path => {
            const filename = path.split('\\').pop()?.split('/').pop() || path || 'Unknown';
            return {
                id: generateId(),
                fileId: generateId(),
                path,
                filename,
                sizeBytes: 0,
                width: 0,
                height: 0,
                format: null,
                thumbnailDataUri: null,
                status: 'inspecting',
                error: null,
                progress: 0
            };
        });

        setQueue(prev => {
            const merged = [...prev];
            const existingPaths = new Set(merged.map(item => item.path.toLowerCase()));
            const filteredNewItems = newItems.filter(item => !existingPaths.has(item.path.toLowerCase()));
            return [...merged, ...filteredNewItems];
        });

        try {
            paths.forEach(p => console.info('[image-convert] IMAGE_INSPECT_REQUEST path=' + p));
            const results = await inspectImageConversionFiles(paths);

            setQueue(prev => prev.map(item => {
                const inspection = results.find(r => r.path === item.path);
                if (!inspection) return item;

                const isReady = inspection.status === 'ready';
                const next: ImageQueueItem = {
                    ...item,
                    sizeBytes: typeof inspection.size_bytes === 'number' ? inspection.size_bytes : item.sizeBytes,
                    width: typeof inspection.width === 'number' ? inspection.width : 0,
                    height: typeof inspection.height === 'number' ? inspection.height : 0,
                    format: inspection.format,
                    thumbnailDataUri: inspection.thumbnail_data_uri,
                    status: isReady ? 'ready' : 'failed',
                    error: inspection.error,
                    fileId: inspection.file_id || item.fileId,
                };
                console.info(
                    '[image-convert] IMAGE_INSPECT_REACT_RECEIVED status=' + next.status +
                    ' format=' + (next.format ?? 'null') +
                    ' bytes=' + next.sizeBytes +
                    ' error=' + (next.error ?? 'null') +
                    ' path=' + item.path,
                );
                return next;
            }));
        } catch (error: any) {
            // Transport-level failure (engine down, malformed response).
            const message = error?.message || 'Tidak ada respons dari engine.';
            console.error('[image-convert] IMAGE_INSPECT_TRANSPORT_FAILED ' + message);
            addToast(`Gagal memeriksa beberapa file: ${message}`, 'error');
            setQueue(prev => prev.map(item => {
                const isNew = newItems.find(ni => ni.id === item.id);
                if (isNew) {
                    return {
                        ...item,
                        status: 'failed',
                        error: `Transport error: ${message}`,
                    };
                }
                return item;
            }));
        } finally {
            setIsInspecting(false);
        }
    }, [addToast]);

    const removeFile = useCallback((id: string) => {
        setQueue(prev => prev.filter(item => item.id !== id));
    }, []);

    const clearQueue = useCallback(() => {
        setQueue([]);
    }, []);

    const startJob = useCallback(async (options: ImageConversionOptions) => {
        // File gagal TIDAK boleh ikut payload konversi.
        const readyItems = queueRef.current.filter(
            item => item.status === 'ready' || item.status === 'completed'
        );
        if (readyItems.length === 0) {
            addToast('Tidak ada file yang siap diproses.', 'error');
            return;
        }

        if (readyItems.length > 50) {
            addToast('Maksimal 50 file dapat diproses sekaligus.', 'error');
            return;
        }

        if (!options.outputDirectory) {
            addToast('Pilih folder penyimpanan hasil terlebih dahulu.', 'error');
            return;
        }

        const readyIds = new Set(readyItems.map(item => item.id));
        const jobId = generateId();
        activeJobIdRef.current = jobId;
        setActiveJobId(jobId);
        setIsConverting(true);
        setShowSuccessDialog(false);

        // Reset progress hanya untuk item yang akan diproses; file failed tetap failed.
        setQueue(prev => prev.map(item => {
            if (!readyIds.has(item.id)) return item;
            return {
                ...item,
                status: item.status === 'completed' ? 'ready' : item.status,
                progress: 0,
                error: null,
            };
        }));

        const payload: StartImageConversionPayload = {
            job_id: jobId,
            files: readyItems.map(item => ({
                file_id: item.fileId,
                path: item.path
            })),
            output_directory: options.outputDirectory,
            output_format: options.outputFormat,
            jpeg_quality: options.jpegQuality,
            webp_quality: options.webpQuality,
            png_compression_level: options.pngCompressionLevel,
            heic_quality: options.heicQuality,
            preserve_metadata: options.preserveMetadata,
            open_output_after_finish: options.openOutputAfterFinish,
            performance_mode: options.performanceMode,
        };

        try {
            await startImageConversion(payload);
        } catch (error: any) {
            addToast(`Gagal memulai konversi: ${error.message || 'Unknown error'}`, 'error');
            setIsConverting(false);
            setActiveJobId(null);
            activeJobIdRef.current = null;
        }
    }, [addToast]);

    const cancelJob = useCallback(async () => {
        if (!activeJobId) return;
        try {
            await cancelEngineJob(activeJobId);
            addToast('Membatalkan konversi...', 'info');
        } catch (error: any) {
            addToast(`Gagal membatalkan: ${error.message}`, 'error');
        }
    }, [activeJobId, addToast]);

    const resetJobState = useCallback(() => {
        setIsConverting(false);
        setActiveJobId(null);
        activeJobIdRef.current = null;
        setShowSuccessDialog(false);
    }, []);

    // Engine Events Listeners
    useTauriEvent('engine://job-started', (data: any) => {
        if (data.job_id === activeJobIdRef.current) {
            setQueue(prev => prev.map(item =>
                item.status === 'ready' ? { ...item, status: 'processing', progress: 0 } : item
            ));
        }
    });

    useTauriEvent('engine://progress', (data: any) => {
        if (data.job_id === activeJobIdRef.current) {
            setQueue(prev => {
                const newQueue = [...prev];
                const idx = newQueue.findIndex(q => q.filename === data.current_file);
                if (idx !== -1 && newQueue[idx].status !== 'failed') {
                    const progressValue =
                        typeof data.file_percent === 'number' && data.file_percent > 0
                            ? data.file_percent
                            : Number(data.overall_percent ?? data.percentage ?? 0);
                    newQueue[idx] = {
                        ...newQueue[idx],
                        progress: progressValue,
                        status: 'processing'
                    };
                }
                return newQueue;
            });
        }
    });

    useTauriEvent('engine://file-completed', (data: any) => {
        if (data.job_id === activeJobIdRef.current) {
            setQueue(prev => {
                const newQueue = [...prev];
                const dataPath = data.path || data.input_path || '';
                const idx = newQueue.findIndex(q => q.path.toLowerCase() === dataPath.toLowerCase() || q.fileId === data.file_id);
                if (idx !== -1) {
                    newQueue[idx] = {
                        ...newQueue[idx],
                        status: data.status === 'completed' ? 'completed' : 'failed',
                        progress: 100,
                        error: data.error
                    };
                }
                return newQueue;
            });
        }
    });

    useTauriEvent('engine://warning', (data: any) => {
        if (data.job_id === activeJobIdRef.current) {
            setQueue(prev => {
                const newQueue = [...prev];
                const dataPath = data.path || data.input_path || '';
                const idx = newQueue.findIndex(q => q.path.toLowerCase() === dataPath.toLowerCase() || q.fileId === data.file_id);
                if (idx !== -1) {
                    newQueue[idx] = {
                        ...newQueue[idx],
                        status: 'failed',
                        progress: 100,
                        error: data.message || data.error || 'Gagal'
                    };
                }
                return newQueue;
            });
        }
    });

    useTauriEvent('engine://job-completed', (data: any) => {
        if (data.job_id === activeJobIdRef.current) {
            setIsConverting(false);
            setShowSuccessDialog(true);
            setActiveJobId(null);
            activeJobIdRef.current = null;
        }
    });

    useTauriEvent('engine://job-failed', (data: any) => {
        if (data.job_id === activeJobIdRef.current) {
            setIsConverting(false);
            const errMsg = data.errors?.[0] || 'Konversi gagal.';
            addToast(errMsg, 'error');
            setQueue(prev => prev.map(item => item.status === 'completed' ? item : { ...item, status: 'failed', error: 'Job gagal' }));
            setActiveJobId(null);
            activeJobIdRef.current = null;
        }
    });

    useTauriEvent('engine://job-cancelled', (data: any) => {
        if (data.job_id === activeJobIdRef.current) {
            setIsConverting(false);
            addToast('Konversi dibatalkan.', 'warning');
            setQueue(prev => prev.map(item => item.status === 'processing' ? { ...item, status: 'ready', progress: 0 } : item));
            setActiveJobId(null);
            activeJobIdRef.current = null;
        }
    });

    return {
        queue,
        stats: calculateStats(queue),
        isConverting,
        isInspecting,
        activeJobId,
        showSuccessDialog,
        setShowSuccessDialog,
        addFiles,
        removeFile,
        clearQueue,
        startJob,
        cancelJob,
        resetJobState
    };
}
