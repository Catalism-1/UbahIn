import React, { useEffect, useMemo } from 'react';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import { Toast } from '../../components/common/Toast';
import { useHeicConversionJob } from '../../hooks/useHeicConversionJob';
import type { AppSettings } from '../../types/settings';
import type { HeicToImageOptions, HeicOutputFormat, JpegQualityPreset } from './types';
import styles from './HeicToImagePage.module.css';

interface HeicToImagePageProps {
  isEngineReady: boolean;
  settings: AppSettings;
  onJobStateChange: (state: { activeJobId: string | null; isConversionRunning: boolean }) => void;
}

function formatBytes(bytes: number): string {
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

export function HeicToImagePage({ isEngineReady, settings, onJobStateChange }: HeicToImagePageProps) {
  const defaults = useMemo<HeicToImageOptions>(
    () => ({
      outputDirectory: settings.default_output_directory || '',
      outputFormat: 'jpg',
      jpegQualityPreset: 'balanced',
      jpegQuality: 85,
      pngCompressionLevel: 6,
      preserveMetadata: false,
      openOutputAfterFinish: settings.open_output_after_finish,
      performanceMode: settings.performance_mode,
    }),
    [settings],
  );

  const job = useHeicConversionJob(isEngineReady, defaults);
  const isConversionRunning = job.status === 'starting' || job.status === 'processing' || job.status === 'cancelling';

  useEffect(() => {
    onJobStateChange({ activeJobId: job.activeJobId, isConversionRunning });
  }, [isConversionRunning, job.activeJobId, onJobStateChange]);

  const handleSelectChange = (key: keyof HeicToImageOptions, e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    job.setOptions((current) => ({ ...current, [key]: value }));
  };

  const handleQualityPresetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value as JpegQualityPreset;
    job.setOptions((current) => ({ ...current, jpegQualityPreset: value }));
  };

  const handleQualitySliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    job.setOptions((current) => ({ ...current, jpegQuality: value }));
  };

  const handlePngCompressionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = parseInt(e.target.value, 10);
    job.setOptions((current) => ({ ...current, pngCompressionLevel: value }));
  };

  const handleToggle = (key: 'preserveMetadata' | 'openOutputAfterFinish') => {
    job.setOptions((current) => ({ ...current, [key]: !current[key] }));
  };

  const showProgress = isConversionRunning;

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <h2>HEIC ke JPG / PNG</h2>
        <p>Ubah foto HEIC menjadi JPG atau PNG agar lebih mudah dibuka dan dibagikan secara offline.</p>
      </section>

      {!isEngineReady ? (
        <div style={{ background: 'var(--red-light)', border: '1px solid var(--red)', color: 'var(--red)', padding: 14, borderRadius: 14, fontSize: 13.5 }}>
          Engine belum diperiksa. Jalankan Pemeriksaan Engine dari tombol di kanan atas sebelum memulai konversi.
        </div>
      ) : null}

      {showProgress && job.progress ? (
        <div className={styles.progressCard}>
          <div className={styles.sectionHead}>
            <div>
              <h3>Sedang Mengonversi Foto HEIC...</h3>
              <p>Jangan menutup aplikasi selama proses sedang berlangsung.</p>
            </div>
            {job.status !== 'cancelling' && (
              <button type="button" className="secondary-button" onClick={job.cancelJob}>
                Batalkan
              </button>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span>{job.progress.message || `Memproses foto ${job.progress.current_file_index} dari ${job.progress.total_files}`}</span>
              <strong style={{ fontFamily: 'var(--font-mono)' }}>{Math.round(job.progress.overall_percent)}%</strong>
            </div>
            <div style={{ width: '100%', height: 10, background: 'var(--surface-3)', borderRadius: 5, overflow: 'hidden' }}>
              <div
                style={{
                  width: `${job.progress.overall_percent}%`,
                  height: '100%',
                  background: 'var(--accent)',
                  borderRadius: 5,
                  transition: 'width 0.25s ease-out',
                }}
              />
            </div>
            <span style={{ fontSize: 12, color: 'var(--text-3)' }}>
              Memproses: <span style={{ fontFamily: 'var(--font-mono)' }}>{job.progress.current_file}</span>
            </span>
          </div>
        </div>
      ) : null}

      <div className={styles.layout}>
        <div className={styles.mainColumn}>
          <section className={styles.card}>
            <div className={styles.sectionHead}>
              <div>
                <h3>Antrean Foto</h3>
                <p>Pilih atau tarik berkas foto HEIC/HEIF yang ingin dikonversi.</p>
              </div>
              <div className={styles.actionRow}>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={job.handlePickFiles}
                  disabled={job.isBusy || job.files.length >= 50}
                >
                  Pilih Foto HEIC
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={job.requestClearFiles}
                  disabled={job.isBusy || job.files.length === 0}
                >
                  Hapus Semua
                </button>
              </div>
            </div>

            <div className={styles.uploadZone} onClick={job.handlePickFiles}>
              <span>HEIC</span>
              <strong>Tarik foto HEIC ke sini atau pilih dari laptop</strong>
              <small>Mendukung HEIC dan HEIF • Maksimal 50 file</small>
            </div>

            <div className={styles.fileQueueScroll}>
              <div className={styles.fileList}>
                {job.files.length === 0 ? (
                  <div className={styles.queueEmpty}>Belum ada foto di antrean.</div>
                ) : (
                  job.files.map((file, idx) => (
                    <article
                      key={file.fileId}
                      className={`${styles.fileRow} ${file.status === 'failed' ? styles.fileFailed : ''}`}
                    >
                      <span className={styles.rowOrder}>{idx + 1}</span>
                      <div className={styles.thumbnailContainer}>
                        {file.thumbnailDataUri ? (
                          <img src={file.thumbnailDataUri} alt="" className={styles.thumbnail} />
                        ) : (
                          <span className={styles.thumbnailPlaceholder}>{file.format || 'HEIC'}</span>
                        )}
                      </div>
                      <div className={styles.fileDetails}>
                        <strong className={styles.fileName} title={file.filename}>
                          {file.filename}
                        </strong>
                        <div className={styles.metaRow}>
                          <span className={styles.fileFormat}>{file.format || 'HEIC'}</span>
                          <span className={styles.fileSize}>{formatBytes(file.sizeBytes)}</span>
                          {file.width > 0 && file.height > 0 && (
                            <span className={styles.fileDimensions}>
                              {file.width} × {file.height} px
                            </span>
                          )}
                        </div>
                        {file.error && <em style={{ color: 'var(--red)', fontSize: 11, fontStyle: 'normal' }}>{file.error}</em>}
                      </div>

                      <div className={styles.rowControls}>
                        <button
                          type="button"
                          className={`${styles.iconBtn} ${styles.delete}`}
                          title="Hapus dari antrean"
                          onClick={() => job.removeFile(file.fileId)}
                          disabled={job.isBusy}
                        >
                          ✕
                        </button>
                      </div>
                    </article>
                  ))
                )}
              </div>
            </div>
          </section>
        </div>

        <div className={styles.sideColumn}>
          <section className={styles.card} style={{ maxHeight: 'none' }}>
            <div className={styles.sectionHead}>
              <div>
                <h3>Pengaturan Hasil</h3>
                <p>Konfigurasi format & kualitas output.</p>
              </div>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Format Hasil</label>
              <select
                className={styles.selectField}
                value={job.options.outputFormat}
                onChange={(e) => handleSelectChange('outputFormat', e)}
                disabled={job.isBusy}
              >
                <option value="jpg">JPG (Foto Standar)</option>
                <option value="png">PNG (Tanpa Rugi / Lossless)</option>
              </select>
            </div>

            {job.options.outputFormat === 'jpg' ? (
              <>
                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>Preset Kualitas JPG</label>
                  <select
                    className={styles.selectField}
                    value={job.options.jpegQualityPreset}
                    onChange={handleQualityPresetChange}
                    disabled={job.isBusy}
                  >
                    <option value="high">Tinggi (Kualitas terbaik, file besar)</option>
                    <option value="balanced">Seimbang (Optimasi terbaik)</option>
                    <option value="compact">Hemat (Ukuran file sekecil mungkin)</option>
                    <option value="custom">Kustom (Tentukan manual)</option>
                  </select>
                </div>

                {job.options.jpegQualityPreset === 'custom' && (
                  <div className={styles.formGroup}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <label className={styles.formLabel}>Kualitas Kustom JPEG</label>
                      <strong style={{ fontSize: 13, fontFamily: 'var(--font-mono)' }}>{job.options.jpegQuality}%</strong>
                    </div>
                    <input
                      type="range"
                      min="50"
                      max="95"
                      value={job.options.jpegQuality}
                      onChange={handleQualitySliderChange}
                      disabled={job.isBusy}
                      style={{ accentColor: 'var(--accent)', cursor: 'pointer' }}
                    />
                  </div>
                )}
              </>
            ) : (
              <div className={styles.formGroup}>
                <label className={styles.formLabel}>Tingkat Kompresi PNG</label>
                <select
                  className={styles.selectField}
                  value={job.options.pngCompressionLevel}
                  onChange={handlePngCompressionChange}
                  disabled={job.isBusy}
                >
                  <option value="1">Rendah (Proses cepat, file lebih besar)</option>
                  <option value="6">Seimbang (Standar)</option>
                  <option value="9">Tinggi (Proses lebih lambat, file lebih kecil)</option>
                </select>
                <span style={{ fontSize: 11.5, color: 'var(--text-3)', marginTop: 4 }}>
                  PNG mempertahankan kualitas visual penuh (lossless), namun ukuran berkas output umumnya lebih besar daripada JPG.
                </span>
              </div>
            )}

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Folder Hasil</label>
              <div className={styles.inputGroup}>
                <input
                  type="text"
                  readOnly
                  placeholder="Pilih folder..."
                  className={styles.inputField}
                  value={job.options.outputDirectory}
                />
                <button
                  type="button"
                  className="secondary-button"
                  onClick={job.handlePickOutput}
                  disabled={job.isBusy}
                >
                  Pilih
                </button>
              </div>
            </div>

            <hr style={{ border: 'none', borderTop: '1px solid var(--border-2)', margin: '4px 0' }} />

            <div className={styles.toggleRow} onClick={() => !job.isBusy && handleToggle('preserveMetadata')}>
              <span className={styles.toggleLabel}>Pertahankan metadata foto (EXIF)</span>
              <label className={styles.switch}>
                <input
                  type="checkbox"
                  checked={job.options.preserveMetadata}
                  onChange={() => {}}
                  disabled={job.isBusy}
                />
                <span className={styles.slider} />
              </label>
            </div>

            <div className={styles.toggleRow} onClick={() => !job.isBusy && handleToggle('openOutputAfterFinish')}>
              <span className={styles.toggleLabel}>Buka folder setelah selesai</span>
              <label className={styles.switch}>
                <input
                  type="checkbox"
                  checked={job.options.openOutputAfterFinish}
                  onChange={() => {}}
                  disabled={job.isBusy}
                />
                <span className={styles.slider} />
              </label>
            </div>

            <button
              type="button"
              className="primary-button"
              style={{ width: '100%', padding: '12px 16px', borderRadius: 12, marginTop: 8 }}
              disabled={!job.canStart}
              onClick={job.startJob}
            >
              Mulai Konversi
            </button>
          </section>
        </div>
      </div>

      <ConfirmDialog
        open={job.showClearConfirm}
        title="Kosongkan Antrean"
        description="Apakah Anda yakin ingin menghapus semua foto HEIC dari antrean?"
        confirmLabel="Ya, Hapus"
        cancelLabel="Batal"
        onCancel={() => job.setShowClearConfirm(false)}
        onConfirm={job.confirmClearFiles}
      />

      {job.showResult && job.result ? (() => {
        const isSuccess = job.result.status !== 'failed' && job.result.status !== 'cancelled' && job.result.successful_files > 0;
        return (
          <div className="app-modal-root" role="presentation" onMouseDown={() => job.setShowResult(false)}>
            <section
              className="app-modal"
              role="dialog"
              aria-modal="true"
              onMouseDown={(event) => event.stopPropagation()}
              style={{ width: 'min(100%, 600px)' }}
            >
              <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 20 }}>
                <div
                  style={{
                    background: !isSuccess ? 'var(--red-light)' : 'var(--sage-light)',
                    color: !isSuccess ? 'var(--red)' : 'var(--sage)',
                    width: 46,
                    height: 46,
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 22,
                    fontWeight: 'bold',
                  }}
                >
                  {isSuccess ? '✓' : '!'}
                </div>
                <div>
                  <h2 style={{ fontSize: 20 }}>
                    {isSuccess ? 'Konversi Selesai' : 'Konversi Gagal'}
                  </h2>
                  <p style={{ fontSize: 13, color: 'var(--text-2)', marginTop: 4 }}>
                    {isSuccess
                      ? 'Foto HEIC Anda berhasil dikonversi ke format tujuan.'
                      : 'Proses konversi tidak dapat diselesaikan. Silakan buka log.'}
                  </p>
                </div>
              </div>

              <div className={styles.resultContent}>
                {isSuccess ? (
                  <>
                    <div className={styles.resultStats}>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Berhasil</span>
                        <span className={styles.statVal} style={{ color: 'var(--sage)' }}>
                          {job.result.successful_files} foto
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Gagal</span>
                        <span className={styles.statVal} style={{ color: job.result.failed_files > 0 ? 'var(--red)' : 'var(--text-3)' }}>
                          {job.result.failed_files} foto
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Total Output</span>
                        <span className={styles.statVal}>
                          {job.result.total_outputs} file
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Durasi</span>
                        <span className={styles.statVal}>
                          {job.result.duration_seconds.toFixed(1)} detik
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className={styles.formLabel}>Lokasi Folder Hasil</span>
                      <span className={styles.resultPath}>{job.result.output_directory || '-'}</span>
                    </div>
                  </>
                ) : (
                  <div style={{ display: 'grid', gap: 12 }}>
                    <div style={{ background: 'var(--red-light)', border: '1px solid var(--red)', borderRadius: 10, padding: 12, fontSize: 13, color: 'var(--text)' }}>
                      <strong>Detail error:</strong>
                      <p style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>
                        {job.result.errors.join('\n') || 'Terjadi kesalahan internal saat konversi foto.'}
                      </p>
                    </div>
                  </div>
                )}

                {job.result.warnings.length > 0 && (
                  <div style={{ background: 'var(--warning-light)', border: '1px solid var(--warning)', borderRadius: 10, padding: 12, fontSize: 12.5, color: 'var(--text)' }}>
                    <strong>Peringatan:</strong>
                    <ul style={{ paddingLeft: 18, marginTop: 4 }}>
                      {job.result.warnings.map((w, idx) => (
                        <li key={idx}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="button-row" style={{ justifyContent: 'flex-end', marginTop: 24, gap: 10 }}>
                {(!isSuccess || job.result.warnings.length > 0 || job.result.errors.length > 0) ? (
                  <button type="button" className="secondary-button" onClick={job.openLogs}>
                    Buka Log
                  </button>
                ) : null}

                {isSuccess && (
                  <button type="button" className="secondary-button" onClick={job.openOutput}>
                    Buka Folder Hasil
                  </button>
                )}

                <button type="button" className="primary-button" onClick={job.resetAfterResult}>
                  Konversi Lagi
                </button>
              </div>
            </section>
          </div>
        );
      })() : null}

      <Toast messages={job.toasts} />
    </div>
  );
}
