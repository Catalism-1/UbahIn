import React, { useEffect, useMemo } from 'react';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import { Toast } from '../../components/common/Toast';
import { useImageToPdfJob } from '../../hooks/useImageToPdfJob';
import type { AppSettings } from '../../types/settings';
import type { ImageToPdfOptions } from './types';
import styles from './ImageToPdfPage.module.css';

interface ImageToPdfPageProps {
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

export function ImageToPdfPage({ isEngineReady, settings, onJobStateChange }: ImageToPdfPageProps) {
  const defaults = useMemo<ImageToPdfOptions>(
    () => ({
      outputDirectory: settings.default_output_directory || '',
      outputFilename: 'Hasil_Dokumen.pdf',
      pageSize: 'original',
      orientation: 'auto',
      margin: 'normal',
      fitMode: 'contain',
      imageQualityPreset: 'balanced',
      jpegQuality: 85,
      optimizePdfSize: true,
      openOutputAfterFinish: settings.open_output_after_finish,
      performanceMode: settings.performance_mode,
    }),
    [settings],
  );

  const job = useImageToPdfJob(isEngineReady, defaults);
  const isConversionRunning = job.status === 'starting' || job.status === 'processing' || job.status === 'cancelling';

  useEffect(() => {
    onJobStateChange({ activeJobId: job.activeJobId, isConversionRunning });
  }, [isConversionRunning, job.activeJobId, onJobStateChange]);

  const handleFilenameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    job.setOptions((current) => ({ ...current, outputFilename: value }));
  };

  const handleSelectChange = (key: keyof ImageToPdfOptions, e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    job.setOptions((current) => ({ ...current, [key]: value }));
  };

  const handleToggle = (key: 'openOutputAfterFinish') => {
    job.setOptions((current) => ({ ...current, [key]: !current[key] }));
  };

  const showProgress = isConversionRunning;

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <h2>Gambar ke PDF</h2>
        <p>Gabungkan beberapa gambar menjadi satu file PDF secara instan langsung di laptopmu.</p>
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
              <h3>Sedang Menggabungkan Gambar...</h3>
              <p>Jangan menutup aplikasi selama proses sedang berlangsung.</p>
            </div>
            {job.status !== 'cancelling' && (
              <button type="button" className="secondary-button" onClick={job.cancelJob}>
                Batalkan Proses
              </button>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span>{job.progress.message || `Memproses gambar ${job.progress.current_file_index} dari ${job.progress.total_files}`}</span>
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
                <h3>Antrean Gambar</h3>
                <p>Urutkan gambar sesuai halaman PDF yang diinginkan.</p>
              </div>
              <div className={styles.actionRow}>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={job.handlePickFiles}
                  disabled={job.isBusy || job.files.length >= 50}
                >
                  Pilih Gambar
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
              <span>IMG</span>
              <strong>Pilih file gambar dari laptop</strong>
              <small>Mendukung JPG, JPEG, PNG, dan WEBP</small>
            </div>

            <div className={styles.fileQueueScroll}>
              <div className={styles.fileList}>
                {job.files.length === 0 ? (
                  <div className={styles.queueEmpty}>Belum ada gambar di antrean.</div>
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
                          <span className={styles.thumbnailPlaceholder}>{file.format || 'IMG'}</span>
                        )}
                      </div>
                      <div className={styles.fileDetails}>
                        <strong className={styles.fileName} title={file.filename}>
                          {file.filename}
                        </strong>
                        <div className={styles.metaRow}>
                          <span className={styles.fileFormat}>{file.format || 'Unknown'}</span>
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
                          className={styles.iconBtn}
                          title="Pindahkan ke atas"
                          onClick={() => job.moveFile(idx, 'up')}
                          disabled={job.isBusy || idx === 0}
                        >
                          ▲
                        </button>
                        <button
                          type="button"
                          className={styles.iconBtn}
                          title="Pindahkan ke bawah"
                          onClick={() => job.moveFile(idx, 'down')}
                          disabled={job.isBusy || idx === job.files.length - 1}
                        >
                          ▼
                        </button>
                        <button
                          type="button"
                          className={`${styles.iconBtn} ${styles.delete}`}
                          title="Hapus gambar"
                          onClick={() => job.removeFile(file.fileId)}
                          disabled={job.isBusy}
                        >
                          ×
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
          <section className={styles.card}>
            <div className={styles.sectionHead}>
              <div>
                <h3>Pengaturan PDF</h3>
                <p>Tentukan format halaman dan letak output.</p>
              </div>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Nama File PDF</label>
              <input
                type="text"
                className={styles.inputField}
                placeholder="nama_file.pdf"
                value={job.options.outputFilename}
                onChange={handleFilenameChange}
                disabled={job.isBusy}
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Folder Hasil</label>
              <div className={styles.inputGroup}>
                <input
                  type="text"
                  className={styles.inputField}
                  readOnly
                  placeholder="Pilih folder..."
                  value={job.options.outputDirectory}
                  disabled={job.isBusy}
                />
                <button
                  type="button"
                  className="secondary-button"
                  onClick={job.handlePickOutput}
                  disabled={job.isBusy}
                >
                  ...
                </button>
              </div>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Ukuran Halaman</label>
              <select
                className={styles.selectField}
                value={job.options.pageSize}
                onChange={(e) => handleSelectChange('pageSize', e)}
                disabled={job.isBusy}
              >
                <option value="original">Ukuran Asli Gambar</option>
                <option value="a4">A4 (595 × 842 pt)</option>
                <option value="letter">Letter (612 × 792 pt)</option>
              </select>
            </div>

            {job.options.pageSize !== 'original' && (
              <>
                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>Orientasi</label>
                  <select
                    className={styles.selectField}
                    value={job.options.orientation}
                    onChange={(e) => handleSelectChange('orientation', e)}
                    disabled={job.isBusy}
                  >
                    <option value="auto">Otomatis (Ikuti Gambar)</option>
                    <option value="portrait">Tegak (Portrait)</option>
                    <option value="landscape">Mendatar (Landscape)</option>
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>Penyesuaian Gambar</label>
                  <select
                    className={styles.selectField}
                    value={job.options.fitMode}
                    onChange={(e) => handleSelectChange('fitMode', e)}
                    disabled={job.isBusy}
                  >
                    <option value="contain">Pertahankan Seluruh Gambar (Contain)</option>
                    <option value="fill">Penuhi Halaman (Fill/Crop)</option>
                  </select>
                </div>
              </>
            )}

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Margin Halaman</label>
              <select
                className={styles.selectField}
                value={job.options.margin}
                onChange={(e) => handleSelectChange('margin', e)}
                disabled={job.isBusy}
              >
                <option value="none">Tanpa Margin (0 pt)</option>
                <option value="small">Margin Kecil (18 pt)</option>
                <option value="normal">Margin Normal (36 pt)</option>
              </select>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Kualitas Gambar dalam PDF</label>
              <select
                className={styles.selectField}
                value={job.options.imageQualityPreset}
                onChange={(e) => {
                  const val = e.target.value as any;
                  let q = job.options.jpegQuality;
                  let opt = job.options.optimizePdfSize;
                  if (val === 'high') {
                    q = 95;
                    opt = false;
                  } else if (val === 'balanced') {
                    q = 85;
                    opt = true;
                  } else if (val === 'compact') {
                    q = 70;
                    opt = true;
                  }
                  job.setOptions((current) => ({
                    ...current,
                    imageQualityPreset: val,
                    jpegQuality: q,
                    optimizePdfSize: opt,
                  }));
                }}
                disabled={job.isBusy}
              >
                <option value="high">Tinggi (Kualitas 95, Tanpa Optimasi)</option>
                <option value="balanced">Seimbang (Kualitas 85, Optimasi Ukuran)</option>
                <option value="compact">Hemat (Kualitas 70, Optimasi Ukuran)</option>
                <option value="custom">Kustom</option>
              </select>
            </div>

            {job.options.imageQualityPreset === 'custom' && (
              <div className={styles.formGroup}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <label className={styles.formLabel}>Kualitas Kustom: {job.options.jpegQuality}</label>
                </div>
                <input
                  type="range"
                  min="50"
                  max="95"
                  step="1"
                  value={job.options.jpegQuality}
                  onChange={(e) => {
                    const q = parseInt(e.target.value, 10);
                    job.setOptions((current) => ({ ...current, jpegQuality: q }));
                  }}
                  disabled={job.isBusy}
                  style={{ width: '100%', accentColor: 'var(--accent)' }}
                />
              </div>
            )}

            <div className={styles.toggleRow} onClick={() => !job.isBusy && job.setOptions(c => ({ ...c, optimizePdfSize: !c.optimizePdfSize }))}>
              <span className={styles.toggleLabel}>Optimalkan ukuran PDF</span>
              <label className={styles.switch}>
                <input
                  type="checkbox"
                  checked={job.options.optimizePdfSize}
                  disabled={job.isBusy}
                  onChange={() => {}}
                />
                <span className={styles.slider} />
              </label>
            </div>

            <small style={{ display: 'block', color: 'var(--text-3)', fontSize: 11, fontStyle: 'italic', marginTop: -6, marginBottom: 8 }}>
              Kualitas memengaruhi ukuran PDF hasil, bukan urutan atau ukuran halaman.
            </small>

            <div className={styles.toggleRow} onClick={() => !job.isBusy && handleToggle('openOutputAfterFinish')}>
              <span className={styles.toggleLabel}>Buka folder setelah selesai</span>
              <label className={styles.switch}>
                <input
                  type="checkbox"
                  checked={job.options.openOutputAfterFinish}
                  disabled={job.isBusy}
                  onChange={() => {}}
                />
                <span className={styles.slider} />
              </label>
            </div>

            <div className={styles.actionArea}>
              <button
                type="button"
                className="primary-button"
                style={{ width: '100%', height: 44, fontSize: 15 }}
                disabled={!job.canStart}
                onClick={job.startJob}
              >
                Buat PDF
              </button>
            </div>
          </section>
        </div>
      </div>

      <ConfirmDialog
        open={job.showClearConfirm}
        title="Daftar antrean kosongkan?"
        description="Seluruh gambar dalam daftar antrean akan dibersihkan. Tidak ada file asli di laptop yang terhapus."
        confirmLabel="Ya, bersihkan"
        cancelLabel="Batal"
        onCancel={() => job.setShowClearConfirm(false)}
        onConfirm={job.confirmClearFiles}
      />

      {job.showResult && job.result ? (() => {
        const isSuccess = job.result.status !== 'failed' && job.result.output_paths.length > 0 && (job.result.output_size_bytes ?? 0) > 0;
        
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
                    {isSuccess ? 'PDF Berhasil Dibuat' : 'Gagal Membuat PDF'}
                  </h2>
                  <p style={{ fontSize: 13, color: 'var(--text-2)', marginTop: 4 }}>
                    {isSuccess
                      ? 'Seluruh gambar berhasil digabungkan menjadi file PDF tunggal.'
                      : 'PDF belum berhasil dibuat. Silakan cek folder hasil atau buka log.'}
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
                          {job.result.successful_files} gambar
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Gagal</span>
                        <span className={styles.statVal} style={{ color: job.result.failed_files > 0 ? 'var(--red)' : 'var(--text-3)' }}>
                          {job.result.failed_files} gambar
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Ukuran PDF</span>
                        <span className={styles.statVal}>
                          {formatBytes(job.result.output_size_bytes || 0)}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Durasi</span>
                        <span className={styles.statVal}>
                          {job.result.duration_seconds.toFixed(1)} detik
                        </span>
                      </div>
                    </div>

                    <div style={{ fontSize: 13, color: 'var(--text-2)', display: 'flex', gap: 12, marginTop: 4, background: 'var(--surface-2)', padding: '8px 12px', borderRadius: 8 }}>
                      <span>Kualitas Preset: <strong>{job.result.image_quality_preset === 'high' ? 'Tinggi' : job.result.image_quality_preset === 'balanced' ? 'Seimbang' : job.result.image_quality_preset === 'compact' ? 'Hemat' : 'Kustom'}</strong></span>
                      <span>kualitas JPEG: <strong>{job.result.jpeg_quality || 85}</strong></span>
                    </div>

                    <div>
                      <span className={styles.formLabel}>Lokasi Hasil</span>
                      <span className={styles.resultPath}>{job.result.output_paths[0]}</span>
                    </div>
                  </>
                ) : (
                  <div style={{ display: 'grid', gap: 12 }}>
                    <div style={{ background: 'var(--red-light)', border: '1px solid var(--red)', borderRadius: 10, padding: 12, fontSize: 13, color: 'var(--text)' }}>
                      <strong>Detail error:</strong>
                      <p style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>
                        {job.result.errors.join('\n') || 'Terjadi kesalahan internal saat membuat file PDF.'}
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
                
                {isSuccess ? (
                  <button type="button" className="secondary-button" onClick={job.openOutput}>
                    Buka Folder Hasil
                  </button>
                ) : (
                  <button type="button" className="secondary-button" onClick={() => job.setShowResult(false)}>
                    Kembali ke Pengaturan
                  </button>
                )}
                
                <button type="button" className="primary-button" onClick={job.resetAfterResult}>
                  Buat PDF Lagi
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
