import { ImageConversionInspectionResult } from '../../services/imageConversion';

export interface ImageConversionOptions {
    outputDirectory: string;
    outputFormat: 'jpg' | 'png' | 'webp' | 'heic';
    jpegQuality: number;
    webpQuality: number;
    pngCompressionLevel: number;
    heicQuality: number;
    preserveMetadata: boolean;
    openOutputAfterFinish: boolean;
    performanceMode: 'ram_saver' | 'balanced' | 'fast';
}

export interface ImageQueueItem {
    id: string; // local UI id
    fileId: string;
    path: string;
    filename: string;
    sizeBytes: number;
    width: number;
    height: number;
    format: string | null;
    thumbnailDataUri: string | null;
    status: 'pending' | 'inspecting' | 'ready' | 'processing' | 'completed' | 'failed';
    error: string | null;
    progress: number;
}

export interface ImageConversionStats {
    totalFiles: number;
    completedFiles: number;
    failedFiles: number;
    totalSizeBytes: number;
}
