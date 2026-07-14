import type { JobProgress } from '../../pages/PdfToJpgPage/types';
import styles from '../../pages/PdfToJpgPage/PdfToJpgPage.module.css';

interface ConversionProgressProps {
  progress: JobProgress | null;
  completedFiles: number;
  totalFiles: number;
  cancelling: boolean;
  onCancel: () => void;
}

function percent(value: number | undefined): number {
  if (value === undefined || Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(100, value));
}

export function ConversionProgress({ progress, completedFiles, totalFiles, cancelling, onCancel }: ConversionProgressProps) {
  const overall = percent(progress?.overall_percent);
  const file = percent(progress?.file_percent);
  return (
    <section className={styles.progressCard}>
      <div className={styles.sectionHead}>
        <div>
          <h3>Proses Konversi</h3>
          <p>{cancelling ? 'Membatalkan proses...' : progress?.message ?? 'Menyiapkan job konversi...'}</p>
        </div>
        <button type="button" className="secondary-button" onClick={onCancel} disabled={cancelling}>
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
          <span>{progress?.current_file || 'File aktif'}</span>
          <strong>{Math.round(file)}%</strong>
        </div>
        <div className={styles.progressTrack}>
          <span style={{ width: `${file}%` }} />
        </div>
      </div>

      <dl className={styles.progressStats}>
        <div>
          <dt>File selesai</dt>
          <dd>
            {completedFiles} / {totalFiles}
          </dd>
        </div>
        <div>
          <dt>File aktif</dt>
          <dd>
            {progress?.current_file_index ?? 0} / {progress?.total_files ?? totalFiles}
          </dd>
        </div>
        <div>
          <dt>Halaman aktif</dt>
          <dd>
            {progress?.current_page ?? 0} / {progress?.total_pages ?? 0}
          </dd>
        </div>
      </dl>
    </section>
  );
}
