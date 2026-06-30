import React, { useState, useEffect } from 'react';
import styles from './ImageConversionPage.module.css';
import { useImageConversionJob } from '../../hooks/useImageConversionJob';
import { useAppSettings } from '../../hooks/useAppSettings';
import { ImageConversionOptions } from './types';
import { pickConversionFiles } from '../../services/imageConversion';
import { openOutputDirectory, pickOutputDirectory } from '../../services/pdfToJpg';
import { openLogFolder } from '../../services/engine';

function formatBytes(bytes: number) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function ImageConversionPage() {
    const { settings } = useAppSettings();
    const {
        queue,
        stats,
        isConverting,
        isInspecting,
        showSuccessDialog,
        setShowSuccessDialog,
        addFiles,
        removeFile,
        clearQueue,
        startJob,
        cancelJob,
        resetJobState
    } = useImageConversionJob();

    const [options, setOptions] = useState<ImageConversionOptions>({
        outputDirectory: settings.default_output_directory || '',
        outputFormat: 'jpg',
        jpegQuality: 85,
        webpQuality: 85,
        pngCompressionLevel: 6,
        heicQuality: 80,
        preserveMetadata: false,
        openOutputAfterFinish: settings.open_output_after_finish ?? true,
        performanceMode: (settings.performance_mode as any) || 'balanced'
    });

    useEffect(() => {
        if (!options.outputDirectory && settings.default_output_directory) {
            setOptions(prev => ({ ...prev, outputDirectory: settings.default_output_directory }));
        }
    }, [settings.default_output_directory, options.outputDirectory]);

    const handlePickFiles = async () => {
        try {
            const paths = await pickConversionFiles();
            if (paths && paths.length > 0) {
                await addFiles(paths);
            }
        } catch (e) {
            console.error(e);
        }
    };

    const handlePickOutputFolder = async () => {
        try {
            const dir = await pickOutputDirectory();
            if (dir) {
                setOptions(prev => ({ ...prev, outputDirectory: dir }));
            }
        } catch (e) {
            console.error(e);
        }
    };

    const handleStart = () => {
        startJob(options);
    };

    const handleOpenOutput = () => {
        if (options.outputDirectory) {
            openOutputDirectory(options.outputDirectory).catch(console.error);
        }
    };

    const renderFormatSettings = () => {
        switch (options.outputFormat) {
            case 'jpg':
                return (
                    <div className={styles.formGroup}>
                        <div className={styles.label}>Kualitas JPEG/JPG</div>
                        <div className={styles.sliderContainer}>
                            <input
                                type="range"
                                className={styles.slider}
                                min="50"
                                max="100"
                                value={options.jpegQuality}
                                onChange={(e) => setOptions({ ...options, jpegQuality: parseInt(e.target.value) })}
                                disabled={isConverting}
                            />
                            <span className={styles.sliderValue}>{options.jpegQuality}</span>
                        </div>
                        <div className={styles.helpText}>Kualitas lebih rendah ukuran file lebih kecil.</div>
                    </div>
                );
            case 'webp':
                return (
                    <div className={styles.formGroup}>
                        <div className={styles.label}>Kualitas WEBP</div>
                        <div className={styles.sliderContainer}>
                            <input
                                type="range"
                                className={styles.slider}
                                min="50"
                                max="100"
                                value={options.webpQuality}
                                onChange={(e) => setOptions({ ...options, webpQuality: parseInt(e.target.value) })}
                                disabled={isConverting}
                            />
                            <span className={styles.sliderValue}>{options.webpQuality}</span>
                        </div>
                    </div>
                );
            case 'png':
                return (
                    <div className={styles.formGroup}>
                        <div className={styles.label}>Kompresi PNG</div>
                        <select
                            className={styles.select}
                            value={options.pngCompressionLevel}
                            onChange={(e) => setOptions({ ...options, pngCompressionLevel: parseInt(e.target.value) })}
                            disabled={isConverting}
                        >
                            <option value={1}>Cepat (Ukuran lebih besar)</option>
                            <option value={6}>Seimbang (Rekomendasi)</option>
                            <option value={9}>Tinggi (Ukuran paling kecil, lambat)</option>
                        </select>
                    </div>
                );
            case 'heic':
                return (
                    <div className={styles.formGroup}>
                        <div className={styles.label}>Kualitas HEIC</div>
                        <div className={styles.sliderContainer}>
                            <input
                                type="range"
                                className={styles.slider}
                                min="50"
                                max="100"
                                value={options.heicQuality}
                                onChange={(e) => setOptions({ ...options, heicQuality: parseInt(e.target.value) })}
                                disabled={isConverting}
                            />
                            <span className={styles.sliderValue}>{options.heicQuality}</span>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.content}>
                {/* Kiri: Queue Area */}
                <div className={styles.mainColumn}>
                    <div className={styles.header}>
                        <h1 className={styles.title}>Ubah Format Gambar</h1>
                        <p className={styles.subtitle}>Konversi berbagai format gambar (JPG, PNG, WEBP, HEIC) dengan kualitas tinggi.</p>
                    </div>
                    <div className={styles.queueArea}>
                        {queue.length === 0 ? (
                            <div className={styles.emptyState}>
                                <p>Belum ada gambar yang dipilih.</p>
                                <button className={styles.secondaryButton} onClick={handlePickFiles} disabled={isInspecting}>
                                    {isInspecting ? 'Memuat...' : 'Pilih Gambar'}
                                </button>
                            </div>
                        ) : (
                            <div className={styles.queueList}>
                                {queue.map(item => (
                                    <div key={item.id} className={styles.queueItem}>
                                        {item.thumbnailDataUri ? (
                                            <img src={item.thumbnailDataUri} alt="" className={styles.itemThumbnail} />
                                        ) : (
                                            <div className={styles.itemThumbnailPlaceholder}>
                                                IMG
                                            </div>
                                        )}
                                        <div className={styles.itemDetails}>
                                            <div className={styles.itemName} title={item.path}>{item.filename}</div>
                                            <div className={styles.itemMeta}>
                                                <span>{item.format ? item.format.toUpperCase() : 'Unknown'}</span>
                                                <span>&bull;</span>
                                                <span>{item.width && item.height ? `${item.width}x${item.height}` : ''}</span>
                                                <span>&bull;</span>
                                                <span>{formatBytes(item.sizeBytes)}</span>
                                            </div>
                                            {(item.status === 'processing' || item.status === 'completed' || item.status === 'failed') && (
                                                <div className={styles.progressBar}>
                                                    <div 
                                                        className={styles.progressFill} 
                                                        style={{ width: `${item.progress}%`, background: item.status === 'failed' ? 'var(--color-danger)' : item.status === 'completed' ? 'var(--color-success)' : 'var(--color-primary)' }}
                                                    ></div>
                                                </div>
                                            )}
                                            {item.error && (
                                                <div className={styles.formatWarning} style={{ marginTop: '4px' }}>
                                                    {item.error}
                                                </div>
                                            )}
                                        </div>
                                        <div className={styles.itemActions}>
                                            {item.status === 'completed' && <span className={`${styles.itemStatus} ${styles.statusCompleted}`}>Selesai</span>}
                                            {item.status === 'failed' && <span className={`${styles.itemStatus} ${styles.statusFailed}`}>Gagal</span>}
                                            {item.status === 'processing' && <span className={`${styles.itemStatus} ${styles.statusProcessing}`}>{Math.round(item.progress)}%</span>}
                                            
                                            <button 
                                                className={styles.iconButton} 
                                                onClick={() => removeFile(item.id)}
                                                disabled={isConverting}
                                                title="Hapus dari antrean"
                                            >
                                                X
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    {queue.length > 0 && (
                        <div className={styles.header} style={{ borderTop: '1px solid var(--color-border)', borderBottom: 'none' }}>
                            <div className={styles.statsRow}>
                                <span>Total: {stats.totalFiles} berkas</span>
                                <span>Ukuran: {formatBytes(stats.totalSizeBytes)}</span>
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                                <button className={styles.secondaryButton} onClick={handlePickFiles} disabled={isConverting || isInspecting}>
                                    Tambah File
                                </button>
                                <button className={styles.secondaryButton} onClick={clearQueue} disabled={isConverting}>
                                    Bersihkan
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Kanan: Settings Panel */}
                <div className={styles.sidebarColumn}>
                    <div className={styles.panel}>
                        <h2 className={styles.panelTitle}>Pengaturan Hasil</h2>
                        
                        <div className={styles.formGroup}>
                            <label className={styles.label}>Format Target</label>
                            <select 
                                className={styles.select}
                                value={options.outputFormat}
                                onChange={(e) => setOptions({ ...options, outputFormat: e.target.value as any })}
                                disabled={isConverting}
                            >
                                <option value="jpg">JPG / JPEG</option>
                                <option value="png">PNG</option>
                                <option value="webp">WEBP</option>
                                <option value="heic">HEIC / HEIF</option>
                            </select>
                        </div>

                        {renderFormatSettings()}

                        <div className={styles.formGroup} style={{ marginTop: '0.5rem' }}>
                            <label className={styles.toggleContainer}>
                                <input 
                                    type="checkbox" 
                                    checked={options.preserveMetadata}
                                    onChange={(e) => setOptions({ ...options, preserveMetadata: e.target.checked })}
                                    disabled={isConverting}
                                />
                                <span className={styles.toggleLabel}>Pertahankan metadata (EXIF)</span>
                            </label>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.label}>Folder Hasil</label>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <input 
                                    type="text" 
                                    className={styles.input} 
                                    style={{ flex: 1 }}
                                    value={options.outputDirectory}
                                    readOnly
                                    placeholder="Pilih folder tujuan..."
                                />
                                <button 
                                    className={styles.secondaryButton}
                                    onClick={handlePickOutputFolder}
                                    disabled={isConverting}
                                    title="Pilih folder"
                                >
                                    Pilih
                                </button>
                            </div>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.toggleContainer}>
                                <input 
                                    type="checkbox" 
                                    checked={options.openOutputAfterFinish}
                                    onChange={(e) => setOptions({ ...options, openOutputAfterFinish: e.target.checked })}
                                    disabled={isConverting}
                                />
                                <span className={styles.toggleLabel}>Buka folder setelah selesai</span>
                            </label>
                        </div>

                        <div className={styles.actions}>
                            {isConverting ? (
                                <button className={styles.dangerButton} onClick={cancelJob}>
                                    Batalkan Proses
                                </button>
                            ) : (
                                <button 
                                    className={styles.primaryButton} 
                                    onClick={handleStart}
                                    disabled={queue.length === 0 || !options.outputDirectory || isInspecting}
                                >
                                    Mulai Konversi
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Dialog Selesai */}
            {showSuccessDialog && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 100,
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                    <div style={{
                        background: 'var(--color-surface)', padding: '2rem', borderRadius: '12px',
                        width: '400px', maxWidth: '90%', display: 'flex', flexDirection: 'column', gap: '1.5rem',
                        boxShadow: 'var(--shadow-lg)'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <div>
                                <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--color-text)' }}>Konversi Selesai</h2>
                                <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                                    Berhasil: {stats.completedFiles} | Gagal: {stats.failedFiles}
                                </p>
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                            {stats.failedFiles > 0 && (
                                <button className={styles.secondaryButton} onClick={openLogFolder}>
                                    Cek Log Error
                                </button>
                            )}
                            <button className={styles.secondaryButton} onClick={() => {
                                resetJobState();
                                handleOpenOutput();
                            }}>
                                Buka Folder
                            </button>
                            <button className={styles.primaryButton} onClick={resetJobState}>
                                Tutup
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
