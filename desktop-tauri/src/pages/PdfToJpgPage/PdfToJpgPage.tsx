import { useEffect, useMemo } from 'react';
import { ConversionProgress } from '../../components/ConversionProgress/ConversionProgress';
import { FileQueue } from '../../components/FileQueue/FileQueue';
import { OutputSettings } from '../../components/OutputSettings/OutputSettings';
import { ResultDialog } from '../../components/ResultDialog/ResultDialog';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import { Toast } from '../../components/common/Toast';
import { usePdfToJpgJob } from '../../hooks/usePdfToJpgJob';
import type { EngineStatus } from '../../types/navigation';
import type { AppSettings } from '../../types/settings';
import type { PdfJobDefaults } from './types';
import styles from './PdfToJpgPage.module.css';

interface PdfToJpgPageProps {
  isEngineReady: boolean;
  engineStatus: EngineStatus;
  settings: AppSettings;
  onJobStateChange: (state: { activeJobId: string | null; isConversionRunning: boolean }) => void;
}

function engineNoticeText(status: EngineStatus): string {
  if (status === 'checking') return 'Menyiapkan engine... Konversi bisa dimulai setelah status engine siap.';
  if (status === 'error') return 'Engine belum dapat dijalankan. Buka Diagnostik untuk melihat detail atau coba lagi.';
  return 'Engine belum siap. Buka Diagnostik untuk menjalankan pemeriksaan.';
}

export function PdfToJpgPage({ isEngineReady, engineStatus, settings, onJobStateChange }: PdfToJpgPageProps) {
  const defaults = useMemo<PdfJobDefaults>(
    () => ({
      outputDirectory: settings.default_output_directory,
      preset: settings.default_pdf_preset,
      dpi: settings.default_dpi,
      jpegQuality: settings.default_jpeg_quality,
      createZip: settings.create_zip_after_conversion,
      openOutputAfterFinish: settings.open_output_after_finish,
      performanceMode: settings.performance_mode,
    }),
    [settings],
  );
  const job = usePdfToJpgJob(isEngineReady, defaults);
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
          {engineNoticeText(engineStatus)}
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
