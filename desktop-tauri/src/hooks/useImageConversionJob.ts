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
        
        setIsInspecting(true);
        const newItems: ImageQueueItem[] = paths.map(path => ({
            id: generateId(),
            fileId: generateId(),
            path,
            filename: path.split('\\').pop()?.split('/').pop() || 'Unknown',
            sizeBytes: 0,
            width: 0,
            height: 0,
            format: null,
            thumbnailDataUri: null,
            status: 'inspecting',
            error: null,
            progress: 0
        }));

        setQueue(prev => {
            const merged = [...prev];
            // duplicate prevention based on path
            const existingPaths = new Set(merged.map(item => item.path.toLowerCase()));
            const filteredNewItems = newItems.filter(item => !existingPaths.has(item.path.toLowerCase()));
            return [...merged, ...filteredNewItems];
        });

        try {
            const results = await inspectImageConversionFiles(paths);
            
            setQueue(prev => prev.map(item => {
                const inspection = results.find(r => r.path === item.path);
                if (inspection) {
                    return {
                        ...item,
                        sizeBytes: inspection.size_bytes,
                        width: inspection.width,
                        height: inspection.height,
                        format: inspection.format,
                        thumbnailDataUri: inspection.thumbnail_data_uri,
                        status: inspection.status === 'ready' ? 'ready' : 'failed',
                        error: inspection.error,
                        fileId: inspection.file_id || item.fileId,
                    };
                }
                return item;
            }));
        } catch (error: any) {
            addToast(`Gagal memeriksa file: ${error.message || 'Unknown error'}`, 'error');
            setQueue(prev => prev.map(item => {
                const isNew = newItems.find(ni => ni.id === item.id);
                if (isNew) {
                    return { ...item, status: 'failed', error: 'Gagal diinspeksi' };
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
        const readyItems = queueRef.current.filter(item => item.status === 'ready' || item.status === 'completed' || item.status === 'failed');
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

        const jobId = generateId();
        setActiveJobId(jobId);
        setIsConverting(true);
        setShowSuccessDialog(false);

        // Reset progress on items to be processed
        setQueue(prev => prev.map(item => ({
            ...item,
            status: item.status === 'failed' || item.status === 'completed' ? 'ready' : item.status,
            progress: 0,
            error: null
        })));

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
        setShowSuccessDialog(false);
    }, []);

    // Engine Events Listeners
    useTauriEvent('job_started', (data: any) => {
        if (data.job_id === activeJobId) {
            setQueue(prev => prev.map(item => ({ ...item, status: 'processing', progress: 0 })));
        }
    });

    useTauriEvent('progress', (data: any) => {
        if (data.job_id === activeJobId) {
            const currentItemIdx = data.current_item - 1;
            setQueue(prev => {
                const newQueue = [...prev];
                if (currentItemIdx >= 0 && currentItemIdx < newQueue.length) {
                    newQueue[currentItemIdx] = {
                        ...newQueue[currentItemIdx],
                        progress: data.percentage,
                        status: 'processing'
                    };
                }
                return newQueue;
            });
        }
    });

    useTauriEvent('file_completed', (data: any) => {
        if (data.job_id === activeJobId) {
            setQueue(prev => {
                const newQueue = [...prev];
                const idx = newQueue.findIndex(q => q.path === data.input_path);
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

    useTauriEvent('job_completed', (data: any) => {
        if (data.job_id === activeJobId) {
            setIsConverting(false);
            setShowSuccessDialog(true);
        }
    });

    useTauriEvent('job_failed', (data: any) => {
        if (data.job_id === activeJobId) {
            setIsConverting(false);
            addToast('Konversi gagal.', 'error');
            setQueue(prev => prev.map(item => item.status === 'completed' ? item : { ...item, status: 'failed', error: 'Job gagal' }));
        }
    });

    useTauriEvent('job_cancelled', (data: any) => {
        if (data.job_id === activeJobId) {
            setIsConverting(false);
            addToast('Konversi dibatalkan.', 'warning');
            setQueue(prev => prev.map(item => item.status === 'processing' ? { ...item, status: 'ready', progress: 0 } : item));
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
