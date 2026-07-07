import { useEffect, useMemo } from 'react';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import { Toast } from '../../components/common/Toast';
import { useMergePdfJob } from '../../hooks/useMergePdfJob';
import type { EngineStatus } from '../../types/navigation';
import type { AppSettings } from '../../types/settings';
import type { MergePdfDefaults, MergePdfOptions, MergePdfQueueItem, MergePdfResult } from './types';
import styles from './MergePdfPage.module.css';

interface MergePdfPageProps {
  isEngineReady: boolean;
  engineStatus: EngineStatus;
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

function engineNoticeText(status: EngineStatus): string {
  if (status === 'checking') return 'Menyiapkan engine... Merge PDF bisa dimulai setelah status engine siap.';
  if (status === 'error') return 'Engine belum dapat dijalankan. Buka Diagnostik untuk melihat detail atau coba lagi.';
  return 'Engine belum siap. Buka Diagnostik untuk menjalankan pemeriksaan.';
}

function statusLabel(file: MergePdfQueueItem): string {
  if (file.status === 'ready') return 'Siap';
  if (file.status === 'processing') return 'Diproses';
  if (file.status === 'completed') return 'Selesai';
  if (file.status === 'cancelled') return 'Dibatalkan';
  return 'Gagal';
}

function durationText(seconds?: number | null): string {
  if (seconds === undefined || seconds === null) return '-';
  if (seconds < 60) return `${seconds.toFixed(1)} detik`;
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds % 60);
  return `${minutes} menit ${remainder} detik`;
}

function resultTitle(result: MergePdfResult): string {
  if (result.status === 'cancelled') return 'Merge PDF dibatalkan';
  if (result.status === 'failed' || result.errors.length > 0) return 'Merge PDF gagal';
  return 'PDF berhasil digabungkan';
}

function percent(value: number | undefined): number {
  if (value === undefined || Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(100, value));
}

function ResultDialog({
  open,
  result,
  onClose,
  onOpenOutput,
  onOpenLog,
  onReset,
}: {
  open: boolean;
  result: MergePdfResult | null;
  onClose: () => void;
  onOpenOutput: () => void;
  onOpenLog: () => void;
  onReset: () => void;
}) {
  if (!open || !result) return null;
  const hasFailure = result.status === 'failed' || result.errors.length > 0 || result.failed_files > 0;
  return (
    <div className="app-modal-root" role="presentation" onMouseDown={onClose}>
      <section
        className={`app-modal ${styles.resultModal}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="merge-result-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className={styles.resultHead}>
          <span>{hasFailure ? '!' : 'OK'}</span>
          <div>
            <h2 id="merge-result-title">{resultTitle(result)}</h2>
            <p>{hasFailure ? 'Periksa detail error atau buka log untuk diagnosis.' : 'File PDF gabungan sudah tersimpan di folder hasil.'}</p>
          </div>
        </div>

        <dl className={styles.resultGrid}>
          <div>
            <dt>PDF input</dt>
            <dd>{result.total_input_files}</dd>
          </div>
          <div>
            <dt>Output</dt>
            <dd>{result.total_outputs}</dd>
          </div>
          <div>
            <dt>Durasi</dt>
            <dd>{durationText(result.duration_seconds)}</dd>
          </div>
        </dl>

        <div className={styles.outputPath} title={result.output_pdf_path || result.output_directory}>
          {result.output_pdf_path || result.output_directory}
        </div>

        {result.errors.length > 0 ? (
          <div className={styles.failedList}>
            <strong>Detail error</strong>
            {result.errors.map((error) => (
              <p key={error}>{error}</p>
            ))}
          </div>
        ) : null}

        <div className="button-row" style={{ justifyContent: 'flex-end', marginTop: 22 }}>
          {hasFailure ? (
            <button type="button" className="secondary-button" onClick={onOpenLog}>
              Buka Log
            </button>
          ) : null}
          <button type="button" className="secondary-button" onClick={onOpenOutput}>
            Buka Folder Hasil
          </button>
          <button type="button" className="primary-button" onClick={onReset}>
            Gabungkan PDF Lagi
          </button>
        </div>
      </section>
    </div>
  );
}

export function MergePdfPage({ isEngineReady, engineStatus, settings, onJobStateChange }: MergePdfPageProps) {
  const defaults = useMemo<MergePdfDefaults>(
    () => ({
      outputDirectory: settings.default_output_directory || '',
      openOutputAfterFinish: settings.open_output_after_finish,
      performanceMode: settings.performance_mode,
    }),
    [settings],
  );
  const job = useMergePdfJob(isEngineReady, defaults);
  const isConversionRunning = job.status === 'starting' || job.status === 'processing' || job.status === 'cancelling';
  const overall = percent(job.progress?.overall_percent);
  const filePercent = percent(job.progress?.file_percent);

  useEffect(() => {
    onJobStateChange({ activeJobId: job.activeJobId, isConversionRunning });
  }, [isConversionRunning, job.activeJobId, onJobStateChange]);

  function updateOption<K extends keyof MergePdfOptions>(key: K, value: MergePdfOptions[K]) {
    job.setOptions((current) => ({ ...current, [key]: value }));
  }

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <h2>Gabungkan PDF</h2>
        <p>Susun beberapa PDF sesuai urutan yang kamu butuhkan, lalu satukan menjadi satu dokumen lokal.</p>
      </section>

      {!isEngineReady ? <div className={styles.engineNotice}>{engineNoticeText(engineStatus)}</div> : null}

      {isConversionRunning ? (
        <section className={styles.progressCard}>
          <div className={styles.sectionHead}>
            <div>
              <h3>Sedang Menggabungkan PDF</h3>
              <p>{job.status === 'cancelling' ? 'Membatalkan proses...' : job.progress?.message ?? 'Menyiapkan job merge...'}</p>
            </div>
            <button type="button" className="secondary-button" onClick={job.cancelJob} disabled={job.status === 'cancelling'}>
              Batalkan Proses
            </button>
          </div>

          <div className={styles.progressBlock}>
            <div className={styles.progressLabel}>
              <span>Keseluruhan</span>
              <strong>{Math.round(overall)}%</strong>
            </div>
            <div className={styles.progressTrack}>
              <span style={{ width: `${overall}%` }} />
            </div>
          </div>

          <div className={styles.progressBlock}>
            <div className={styles.progressLabel}>
              <span>{job.progress?.current_file || 'PDF aktif'}</span>
              <strong>{Math.round(filePercent)}%</strong>
            </div>
            <div className={styles.progressTrack}>
              <span style={{ width: `${filePercent}%` }} />
            </div>
          </div>

          <dl className={styles.progressStats}>
            <div>
              <dt>File selesai</dt>
              <dd>{job.completedFiles} / {job.validFileCount}</dd>
            </div>
            <div>
              <dt>File aktif</dt>
              <dd>{job.progress?.current_file_index ?? 0} / {job.progress?.total_files ?? job.validFileCount}</dd>
            </div>
            <div>
              <dt>Halaman</dt>
              <dd>{job.progress?.current_page ?? 0} / {job.progress?.total_pages ?? job.totalPages}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      <div className={styles.layout}>
        <div className={styles.mainColumn}>
          <section className={styles.card}>
            <div className={styles.sectionHead}>
              <div>
                <h3>Urutan PDF</h3>
                <p>PDF digabung dari atas ke bawah. Ubah urutan sebelum memulai proses.</p>
              </div>
              <div className={styles.actionRow}>
                <button type="button" className="secondary-button" onClick={job.handlePickFiles} disabled={job.isBusy || job.files.length >= 50}>
                  Tambah PDF
                </button>
                <button type="button" className="secondary-button" onClick={job.requestClearFiles} disabled={job.isBusy || job.files.length === 0}>
                  Hapus Semua
                </button>
              </div>
            </div>

            <button type="button" className={styles.uploadZone} onClick={job.handlePickFiles} disabled={job.isBusy || job.files.length >= 50}>
              <span>PDF</span>
              <strong>Pilih file PDF dari laptop</strong>
              <small>Minimal dua PDF valid untuk memulai merge.</small>
            </button>

            <div className={styles.fileList}>
              {job.files.length === 0 ? (
                <div className={styles.queueEmpty}>Belum ada PDF di antrean.</div>
              ) : (
                job.files.map((file, index) => (
                  <article key={file.fileId} className={`${styles.fileItem} ${file.status === 'failed' ? styles.fileFailed : ''}`}>
                    <span className={styles.fileOrder}>{index + 1}</span>
                    <span className={styles.pdfMark}>PDF</span>
                    <div className={styles.fileMain}>
                      <strong title={file.filename}>{file.filename}</strong>
                      <span>
                        {formatBytes(file.sizeBytes)} - {file.pageCount > 0 ? `${file.pageCount} halaman` : 'Halaman tidak terbaca'} - {statusLabel(file)}
                      </span>
                      {file.warning ? <em>{file.warning}</em> : null}
                      {file.error ? <em>{file.error}</em> : null}
                    </div>
                    <div className={styles.fileActions}>
                      <button
                        type="button"
                        className={styles.iconButton}
                        aria-label={`Pindahkan ${file.filename} ke atas`}
                        onClick={() => job.moveFile(index, 'up')}
                        disabled={job.isBusy || index === 0}
                      >
                        Up
                      </button>
                      <button
                        type="button"
                        className={styles.iconButton}
                        aria-label={`Pindahkan ${file.filename} ke bawah`}
                        onClick={() => job.moveFile(index, 'down')}
                        disabled={job.isBusy || index === job.files.length - 1}
                      >
                        Dn
                      </button>
                      <button
                        type="button"
                        className={`${styles.iconButton} ${styles.deleteButton}`}
                        aria-label={`Hapus ${file.filename}`}
                        onClick={() => job.removeFile(file.fileId)}
                        disabled={job.isBusy}
                      >
                        X
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </div>

        <div className={styles.sideColumn}>
          <section className={styles.card}>
            <div className={styles.sectionHead}>
              <div>
                <h3>Hasil Merge</h3>
                <p>Tentukan folder dan nama file PDF gabungan.</p>
              </div>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="merge-output-name">Nama File Output</label>
              <input
                id="merge-output-name"
                type="text"
                className={styles.inputField}
                value={job.options.outputFilename}
                onChange={(event) => updateOption('outputFilename', event.target.value)}
                disabled={job.isBusy}
                placeholder="Gabungan_PDF.pdf"
              />
            </div>

            <div className={styles.outputPicker}>
              <span>Folder Hasil</span>
              <div className={styles.outputPath} title={job.options.outputDirectory}>
                {job.options.outputDirectory || 'Belum dipilih'}
              </div>
              <button type="button" className="secondary-button" onClick={job.handlePickOutput} disabled={job.isBusy}>
                Pilih Folder
              </button>
            </div>

            <div className={styles.toggleList}>
              <label>
                Buka folder setelah selesai
                <input
                  type="checkbox"
                  checked={job.options.openOutputAfterFinish}
                  onChange={() => updateOption('openOutputAfterFinish', !job.options.openOutputAfterFinish)}
                  disabled={job.isBusy}
                />
              </label>
            </div>

            <dl className={styles.summaryGrid}>
              <div>
                <dt>PDF valid</dt>
                <dd>{job.validFileCount}</dd>
              </div>
              <div>
                <dt>Halaman</dt>
                <dd>{job.totalPages}</dd>
              </div>
              <div>
                <dt>Minimal</dt>
                <dd>2</dd>
              </div>
            </dl>

            <button type="button" className={styles.startButton} onClick={job.startJob} disabled={!job.canStart}>
              Gabungkan PDF
            </button>
          </section>
        </div>
      </div>

      <ConfirmDialog
        open={job.showClearConfirm}
        title="Hapus semua PDF?"
        description="Antrean merge akan dikosongkan dari tampilan. File asli tidak dihapus dari laptop."
        confirmLabel="Ya, hapus"
        cancelLabel="Batal"
        onCancel={() => job.setShowClearConfirm(false)}
        onConfirm={job.confirmClearFiles}
      />

      <ResultDialog
        open={job.showResult}
        result={job.result}
        onClose={() => job.setShowResult(false)}
        onOpenOutput={job.openOutput}
        onOpenLog={job.openLogs}
        onReset={job.resetAfterResult}
      />

      <Toast messages={job.toasts} />
    </div>
  );
}
