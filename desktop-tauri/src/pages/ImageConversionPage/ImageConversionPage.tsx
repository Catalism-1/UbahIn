import { useEffect, useMemo, useState } from 'react';
import styles from './ImageConversionPage.module.css';
import { useImageConversionJob } from '../../hooks/useImageConversionJob';
import { useAppSettings } from '../../hooks/useAppSettings';
import { ImageConversionOptions } from './types';
import { pickConversionFiles } from '../../services/imageConversion';
import { openOutputDirectory, pickOutputDirectory } from '../../services/pdfToJpg';
import { openLogFolder } from '../../services/engine';

function formatBytes(bytes: number) {
    if (!Number.isFinite(bytes) || bytes <= 0) return '0 KB';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unit = 0;
    while (size >= 1024 && unit < units.length - 1) {
        size /= 1024;
        unit += 1;
    }
    return `${size.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

export function ImageConversionPage() {
    const { settings } = useAppSettings();
    const {
        queue,
        stats,
        isConverting,
        isInspecting,
        showSuccessDialog,
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

    const isBusy = isConverting || isInspecting;
    const queueFull = queue.length >= 50;
    const canStart = queue.length > 0 && Boolean(options.outputDirectory) && !isBusy;

    const disabledReason = useMemo(() => {
        if (isConverting) return null;
        if (queue.length === 0 && !options.outputDirectory) {
            return 'Pilih gambar dan folder hasil untuk memulai.';
        }
        if (queue.length === 0) return 'Tambahkan minimal satu gambar ke antrean.';
        if (!options.outputDirectory) return 'Pilih folder hasil terlebih dahulu.';
        return null;
    }, [isConverting, queue.length, options.outputDirectory]);

    const renderFormatSettings = () => {
        switch (options.outputFormat) {
            case 'jpg':
                return (
                    <div className={styles.formGroup}>
                        <label className={styles.formLabel}>Kualitas JPEG/JPG</label>
                        <div className={styles.sliderRow}>
                            <input
                                type="range"
                                className={styles.slider}
                                min={50}
                                max={100}
                                value={options.jpegQuality}
                                onChange={(e) => setOptions({ ...options, jpegQuality: parseInt(e.target.value, 10) })}
                                disabled={isConverting}
                            />
                            <span className={styles.sliderValue}>{options.jpegQuality}</span>
                        </div>
                        <span className={styles.helpText}>Kualitas lebih rendah menghasilkan ukuran file lebih kecil.</span>
                    </div>
                );
            case 'webp':
                return (
                    <div className={styles.formGroup}>
                        <label className={styles.formLabel}>Kualitas WEBP</label>
                        <div className={styles.sliderRow}>
                            <input
                                type="range"
                                className={styles.slider}
                                min={50}
                                max={100}
                                value={options.webpQuality}
                                onChange={(e) => setOptions({ ...options, webpQuality: parseInt(e.target.value, 10) })}
                                disabled={isConverting}
                            />
                            <span className={styles.sliderValue}>{options.webpQuality}</span>
                        </div>
                        <span className={styles.helpText}>WEBP biasanya lebih efisien dari JPG pada kualitas yang sama.</span>
                    </div>
                );
            case 'png':
                return (
                    <div className={styles.formGroup}>
                        <label className={styles.formLabel}>Kompresi PNG</label>
                        <select
                            className={styles.selectField}
                            value={options.pngCompressionLevel}
                            onChange={(e) => setOptions({ ...options, pngCompressionLevel: parseInt(e.target.value, 10) })}
                            disabled={isConverting}
                        >
                            <option value={1}>Cepat (ukuran lebih besar)</option>
                            <option value={6}>Seimbang (rekomendasi)</option>
                            <option value={9}>Tinggi (paling kecil, lebih lambat)</option>
                        </select>
                    </div>
                );
            case 'heic':
                return (
                    <div className={styles.formGroup}>
                        <label className={styles.formLabel}>Kualitas HEIC</label>
                        <div className={styles.sliderRow}>
                            <input
                                type="range"
                                className={styles.slider}
                                min={50}
                                max={100}
                                value={options.heicQuality}
                                onChange={(e) => setOptions({ ...options, heicQuality: parseInt(e.target.value, 10) })}
                                disabled={isConverting}
                            />
                            <span className={styles.sliderValue}>{options.heicQuality}</span>
                        </div>
                        <span className={styles.helpText}>HEIC menghemat ruang dibanding JPG pada kualitas serupa.</span>
                    </div>
                );
            default:
                return null;
        }
    };

    const statusLabelFor = (item: typeof queue[number]) => {
        if (item.status === 'completed') {
            return <span className={`${styles.fileStatus} ${styles.statusCompleted}`}>Selesai</span>;
        }
        if (item.status === 'failed') {
            return <span className={`${styles.fileStatus} ${styles.statusFailed}`}>Gagal</span>;
        }
        if (item.status === 'processing') {
            return <span className={`${styles.fileStatus} ${styles.statusProcessing}`}>{Math.round(item.progress)}%</span>;
        }
        if (item.status === 'inspecting') {
            return <span className={`${styles.fileStatus} ${styles.statusReady}`}>Memeriksa…</span>;
        }
        return <span className={`${styles.fileStatus} ${styles.statusReady}`}>Siap</span>;
    };

    return (
        <div className={styles.page}>
            <section className={styles.hero}>
                <h2>Ubah Format Gambar</h2>
                <p>Ubah JPG, PNG, WEBP, dan HEIC secara lokal di laptopmu — tanpa unggah ke internet.</p>
            </section>

            <div className={styles.layout}>
                {/* Kiri: File Gambar */}
                <div className={styles.mainColumn}>
                    <section className={styles.card}>
                        <div className={styles.sectionHead}>
                            <div>
                                <h3>File Gambar</h3>
                                <p>Pilih gambar yang ingin diubah formatnya. Maksimal 50 file dalam satu antrean.</p>
                            </div>
                            <div className={styles.actionRow}>
                                <button
                                    type="button"
                                    className="secondary-button"
                                    onClick={handlePickFiles}
                                    disabled={isBusy || queueFull}
                                >
                                    {isInspecting ? 'Memuat…' : 'Pilih Gambar'}
                                </button>
                                <button
                                    type="button"
                                    className="secondary-button"
                                    onClick={clearQueue}
                                    disabled={isConverting || queue.length === 0}
                                >
                                    Hapus Semua
                                </button>
                            </div>
                        </div>

                        {queue.length === 0 ? (
                            <button
                                type="button"
                                className={styles.uploadZone}
                                onClick={handlePickFiles}
                                disabled={isBusy}
                            >
                                <span className={styles.uploadIcon}>IMG</span>
                                <strong>Tarik gambar ke sini atau pilih dari laptop</strong>
                                <small>Mendukung JPG, PNG, WEBP, HEIC, dan HEIF</small>
                                <span className={styles.uploadCta}>Pilih Gambar</span>
                            </button>
                        ) : (
                            <div className={styles.queueScroll}>
                                <div className={styles.fileList}>
                                    {queue.map((item) => (
                                        <article
                                            key={item.id}
                                            className={`${styles.fileRow} ${item.status === 'failed' ? styles.fileFailed : ''}`}
                                        >
                                            <div className={styles.thumbnailContainer}>
                                                {item.thumbnailDataUri ? (
                                                    <img src={item.thumbnailDataUri} alt="" className={styles.thumbnail} />
                                                ) : (
                                                    <span className={styles.thumbnailPlaceholder}>
                                                        {item.format || 'IMG'}
                                                    </span>
                                                )}
                                            </div>
                                            <div className={styles.fileDetails}>
                                                <strong className={styles.fileName} title={item.path}>
                                                    {item.filename}
                                                </strong>
                                                <div className={styles.metaRow}>
                                                    <span className={styles.formatBadge}>
                                                        {item.format ? item.format.toUpperCase() : 'Unknown'}
                                                    </span>
                                                    {item.width > 0 && item.height > 0 && (
                                                        <span>{item.width} × {item.height} px</span>
                                                    )}
                                                    <span>{formatBytes(item.sizeBytes)}</span>
                                                </div>
                                                {item.error && (
                                                    <em className={styles.errorText}>{item.error}</em>
                                                )}
                                                {(item.status === 'processing' || item.status === 'completed' || item.status === 'failed') && (
                                                    <div className={styles.progressTrack}>
                                                        <span
                                                            className={`${styles.progressFill} ${item.status === 'failed' ? styles.failed : ''} ${item.status === 'completed' ? styles.done : ''}`}
                                                            style={{ width: `${item.progress}%` }}
                                                        />
                                                    </div>
                                                )}
                                            </div>
                                            {statusLabelFor(item)}
                                            <button
                                                type="button"
                                                className={styles.removeButton}
                                                onClick={() => removeFile(item.id)}
                                                disabled={isConverting}
                                                title="Hapus dari antrean"
                                                aria-label={`Hapus ${item.filename}`}
                                            >
                                                ×
                                            </button>
                                        </article>
                                    ))}
                                </div>
                            </div>
                        )}

                        {queue.length === 0 && (
                            <div className={styles.queueEmpty}>Belum ada gambar dalam antrean.</div>
                        )}

                        {queue.length > 0 && (
                            <div className={styles.statsRow}>
                                <span>Total: <strong>{stats.totalFiles}</strong> berkas</span>
                                <span>Ukuran: <strong>{formatBytes(stats.totalSizeBytes)}</strong></span>
                            </div>
                        )}
                    </section>
                </div>

                {/* Kanan: Pengaturan */}
                <div className={styles.sideColumn}>
                    <section className={styles.card}>
                        <div className={styles.sectionHead}>
                            <div>
                                <h3>Pengaturan Hasil</h3>
                                <p>Atur format dan kualitas gambar output.</p>
                            </div>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.formLabel}>Format Target</label>
                            <select
                                className={styles.selectField}
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

                        <label className={styles.toggleRow}>
                            <span>Pertahankan metadata (EXIF)</span>
                            <input
                                type="checkbox"
                                checked={options.preserveMetadata}
                                onChange={(e) => setOptions({ ...options, preserveMetadata: e.target.checked })}
                                disabled={isConverting}
                            />
                        </label>

                        <div className={styles.formGroup}>
                            <label className={styles.formLabel}>Folder Hasil</label>
                            <div className={styles.inputGroup}>
                                <input
                                    type="text"
                                    className={styles.inputField}
                                    value={options.outputDirectory}
                                    readOnly
                                    placeholder="Belum dipilih"
                                />
                                <button
                                    type="button"
                                    className="secondary-button"
                                    onClick={handlePickOutputFolder}
                                    disabled={isConverting}
                                >
                                    Pilih Folder
                                </button>
                            </div>
                        </div>

                        <label className={styles.toggleRow}>
                            <span>Buka folder setelah selesai</span>
                            <input
                                type="checkbox"
                                checked={options.openOutputAfterFinish}
                                onChange={(e) => setOptions({ ...options, openOutputAfterFinish: e.target.checked })}
                                disabled={isConverting}
                            />
                        </label>

                        <div className={styles.actionArea}>
                            {isConverting ? (
                                <button type="button" className={styles.cancelButton} onClick={cancelJob}>
                                    Batalkan Proses
                                </button>
                            ) : (
                                <>
                                    <button
                                        type="button"
                                        className={styles.startButton}
                                        onClick={handleStart}
                                        disabled={!canStart}
                                    >
                                        Mulai Konversi
                                    </button>
                                    {disabledReason && (
                                        <span className={styles.disabledHint}>{disabledReason}</span>
                                    )}
                                </>
                            )}
                        </div>
                    </section>
                </div>
            </div>

            {showSuccessDialog && (
                <div className={styles.modalRoot} role="presentation" onMouseDown={resetJobState}>
                    <div
                        className={styles.modal}
                        role="dialog"
                        aria-modal="true"
                        onMouseDown={(e) => e.stopPropagation()}
                    >
                        <div className={styles.modalHead}>
                            <div className={styles.modalIcon}>✓</div>
                            <div>
                                <h2 className={styles.modalTitle}>Konversi Selesai</h2>
                                <p className={styles.modalSubtitle}>
                                    Berhasil: {stats.completedFiles} · Gagal: {stats.failedFiles}
                                </p>
                            </div>
                        </div>
                        <div className={styles.modalActions}>
                            {stats.failedFiles > 0 && (
                                <button type="button" className="secondary-button" onClick={openLogFolder}>
                                    Cek Log Error
                                </button>
                            )}
                            <button
                                type="button"
                                className="secondary-button"
                                onClick={() => {
                                    resetJobState();
                                    handleOpenOutput();
                                }}
                            >
                                Buka Folder
                            </button>
                            <button type="button" className="primary-button" onClick={resetJobState}>
                                Tutup
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
