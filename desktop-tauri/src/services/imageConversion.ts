import { invoke } from '@tauri-apps/api/core';

export interface ImageConversionInspectionResult {
    path: string;
    file_id: string;
    filename: string;
    size_bytes: number;
    format: string | null;
    width: number | null;
    height: number | null;
    status: 'ready' | 'failed';
    warning: string | null;
    error: string | null;
    error_code?: string | null;
    thumbnail_data_uri: string | null;
}

export interface ImageConversionInputFile {
    file_id: string;
    path: string;
}

export interface StartImageConversionPayload {
    job_id: string;
    files: ImageConversionInputFile[];
    output_directory: string;
    output_format: string;
    jpeg_quality: number;
    webp_quality: number;
    png_compression_level: number;
    heic_quality: number;
    preserve_metadata: boolean;
    open_output_after_finish: boolean;
    performance_mode: string;
}

export interface EngineTransportResponse {
    ok: boolean;
    data?: any;
    error?: {
        code: string;
        message: string;
    };
}

export async function pickConversionFiles(): Promise<string[]> {
    return invoke<string[]>('pick_conversion_files');
}

export async function inspectImageConversionFiles(paths: string[]): Promise<ImageConversionInspectionResult[]> {
    const response = await invoke<EngineTransportResponse>('inspect_image_conversion_files', {
        payload: { paths }
    });
    
    if (response.ok && response.data?.files) {
        return response.data.files as ImageConversionInspectionResult[];
    }
    throw new Error(response.error?.message || 'Gagal memuat detail gambar');
}

export async function startImageConversion(payload: StartImageConversionPayload): Promise<EngineTransportResponse> {
    return invoke<EngineTransportResponse>('start_image_conversion', { payload });
}
