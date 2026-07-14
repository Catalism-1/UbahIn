import type { JobResult } from '../../pages/PdfToJpgPage/types';
import styles from '../../pages/PdfToJpgPage/PdfToJpgPage.module.css';

interface ResultDialogProps {
  result: JobResult | null;
  open: boolean;
  onClose: () => void;
  onOpenOutput: () => void;
  onOpenLog: () => void;
  onReset: () => void;
}

function durationText(seconds?: number | null): string {
  if (seconds === undefined || seconds === null) return '-';
  if (seconds < 60) return `${seconds.toFixed(1)} detik`;
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds % 60);
  return `${minutes} menit ${remainder} detik`;
}

function titleFor(result: JobResult): string {
  if (result.status === 'cancelled') return 'Konversi dibatalkan';
  if (result.failed_files > 0 && result.successful_files > 0) return 'Selesai dengan peringatan';
  if (result.failed_files > 0) return 'Konversi gagal';
  return 'Konversi selesai';
}

export function ResultDialog({ result, open, onClose, onOpenOutput, onOpenLog, onReset }: ResultDialogProps) {
  if (!open || !result) return null;
  const hasFailures = result.failed_files > 0 || result.errors.length > 0;
  return (
    <div className="app-modal-root" role="presentation" onMouseDown={onClose}>
      <section
        className={`app-modal ${styles.resultModal}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="result-dialog-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className={styles.resultHead}>
          <span>{result.status === 'failed' ? '!' : 'OK'}</span>
          <div>
            <h2 id="result-dialog-title">{titleFor(result)}</h2>
            <p>
              {hasFailures && result.successful_files > 0
                ? 'Beberapa file tidak dapat diproses, tetapi file lainnya berhasil diubah.'
                : 'Ringkasan hasil konversi PDF ke JPG.'}
            </p>
          </div>
        </div>

        <dl className={styles.resultGrid}>
          <div>
            <dt>Berhasil</dt>
            <dd>{result.successful_files}</dd>
          </div>
          <div>
            <dt>Gagal</dt>
            <dd>{result.failed_files}</dd>
          </div>
          <div>
            <dt>Total JPG</dt>
            <dd>{result.total_jpg}</dd>
          </div>
          <div>
            <dt>Durasi</dt>
            <dd>{durationText(result.duration_seconds)}</dd>
          </div>
        </dl>

        <div className={styles.outputPath} title={result.output_directory}>
          {result.output_directory}
        </div>

        {result.failed_file_details.length > 0 ? (
          <div className={styles.failedList}>
            <strong>File gagal</strong>
            {result.failed_file_details.map((file) => (
              <p key={`${file.path}-${file.error}`}>
                {file.filename}: {file.error}
              </p>
            ))}
          </div>
        ) : null}

        <div className="button-row" style={{ justifyContent: 'flex-end', marginTop: 22 }}>
          {hasFailures ? (
            <button type="button" className="secondary-button" onClick={onOpenLog}>
              Buka Log
            </button>
          ) : null}
          <button type="button" className="secondary-button" onClick={onOpenOutput}>
            Buka Folder Hasil
          </button>
          <button type="button" className="primary-button" onClick={onReset}>
            Ubah File Lagi
          </button>
        </div>
      </section>
    </div>
  );
}
