import type { PdfQueueItem } from '../../pages/PdfToJpgPage/types';
import styles from '../../pages/PdfToJpgPage/PdfToJpgPage.module.css';

interface FileQueueProps {
  files: PdfQueueItem[];
  disabled: boolean;
  onPickFiles: () => void;
  onRemoveFile: (fileId: string) => void;
  onClearFiles: () => void;
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

function statusLabel(file: PdfQueueItem): string {
  if (file.status === 'ready') return 'Siap';
  if (file.status === 'processing') return 'Diproses';
  if (file.status === 'completed') return 'Selesai';
  if (file.status === 'cancelled') return 'Dibatalkan';
  return 'Gagal';
}

export function FileQueue({ files, disabled, onPickFiles, onRemoveFile, onClearFiles }: FileQueueProps) {
  return (
    <section className={styles.card}>
      <div className={styles.sectionHead}>
        <div>
          <h3>File PDF</h3>
          <p>Maksimal 50 file PDF dalam satu antrean.</p>
        </div>
        <div className={styles.actionRow}>
          <button type="button" className="secondary-button" onClick={onPickFiles} disabled={disabled || files.length >= 50}>
            Pilih PDF
          </button>
          <button type="button" className="secondary-button" onClick={onClearFiles} disabled={disabled || files.length === 0}>
            Hapus Semua
          </button>
        </div>
      </div>

      <button type="button" className={styles.uploadZone} onClick={onPickFiles} disabled={disabled || files.length >= 50}>
        <span>PDF</span>
        <strong>Pilih file PDF dari laptop</strong>
        <small>File diperiksa lebih dulu sebelum dikonversi.</small>
      </button>

      <div className={styles.fileList}>
        {files.length === 0 ? (
          <div className={styles.queueEmpty}>Belum ada file PDF di antrean.</div>
        ) : (
          files.map((file) => (
            <article key={file.fileId} className={`${styles.fileItem} ${file.status === 'failed' ? styles.fileFailed : ''}`}>
              <span className={styles.pdfMark}>PDF</span>
              <div className={styles.fileMain}>
                <strong title={file.path}>{file.filename}</strong>
                <span>
                  {formatBytes(file.sizeBytes)} - {file.pageCount > 0 ? `${file.pageCount} halaman` : 'Halaman tidak terbaca'}
                </span>
                {file.warning ? <em>{file.warning}</em> : null}
                {file.error ? <em>{file.error}</em> : null}
              </div>
              <span className={`${styles.fileStatus} ${file.status === 'failed' ? styles.bad : styles.good}`}>
                {statusLabel(file)}
              </span>
              <button
                type="button"
                className={styles.removeButton}
                aria-label={`Hapus ${file.filename}`}
                onClick={() => onRemoveFile(file.fileId)}
                disabled={disabled}
              >
                X
              </button>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
