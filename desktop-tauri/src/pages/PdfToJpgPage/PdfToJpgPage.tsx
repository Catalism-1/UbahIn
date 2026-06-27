import { useEffect } from 'react';
import { ConversionProgress } from '../../components/ConversionProgress/ConversionProgress';
import { FileQueue } from '../../components/FileQueue/FileQueue';
import { OutputSettings } from '../../components/OutputSettings/OutputSettings';
import { ResultDialog } from '../../components/ResultDialog/ResultDialog';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import { Toast } from '../../components/common/Toast';
import { usePdfToJpgJob } from '../../hooks/usePdfToJpgJob';
import styles from './PdfToJpgPage.module.css';

interface PdfToJpgPageProps {
  isEngineReady: boolean;
  onJobStateChange: (state: { activeJobId: string | null; isConversionRunning: boolean }) => void;
}

export function PdfToJpgPage({ isEngineReady, onJobStateChange }: PdfToJpgPageProps) {
  const job = usePdfToJpgJob(isEngineReady);
  const isConversionRunning = job.status === 'starting' || job.status === 'processing' || job.status === 'cancelling';

  useEffect(() => {
    onJobStateChange({ activeJobId: job.activeJobId, isConversionRunning });
  }, [isConversionRunning, job.activeJobId, onJobStateChange]);

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <h2>PDF ke JPG</h2>
        <p>
          Pilih PDF, tentukan folder hasil, lalu biarkan Ubahin mengubah setiap halaman menjadi JPG langsung di laptopmu.
        </p>
      </section>

      {!isEngineReady ? (
        <div className={styles.engineNotice}>
          Engine belum diperiksa. Jalankan Pemeriksaan Engine dari tombol di kanan atas sebelum memulai konversi.
        </div>
      ) : null}

      {isConversionRunning ? (
        <ConversionProgress
          progress={job.progress}
          completedFiles={job.completedFiles}
          totalFiles={job.validFileCount}
          cancelling={job.status === 'cancelling'}
          onCancel={job.cancelJob}
        />
      ) : null}

      <div className={styles.layout}>
        <div className={styles.mainColumn}>
          <FileQueue
            files={job.files}
            disabled={job.isBusy}
            onPickFiles={job.handlePickFiles}
            onRemoveFile={job.removeFile}
            onClearFiles={job.requestClearFiles}
          />
        </div>
        <div className={styles.sideColumn}>
          <OutputSettings
            options={job.options}
            presets={job.presets}
            validFileCount={job.validFileCount}
            totalPages={job.totalPages}
            disabled={job.isBusy}
            canStart={job.canStart}
            onPickOutput={job.handlePickOutput}
            onChangePreset={job.changePreset}
            onToggle={job.toggleOption}
            onStart={job.startJob}
          />
        </div>
      </div>

      <ConfirmDialog
        open={job.showClearConfirm}
        title="Hapus semua file?"
        description="Antrean PDF akan dikosongkan dari tampilan. Tidak ada file asli yang dihapus dari laptop."
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
