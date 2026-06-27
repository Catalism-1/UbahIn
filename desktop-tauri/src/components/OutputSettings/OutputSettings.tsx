import type { PdfPreset, PdfPresetConfig, PdfToJpgOptions } from '../../pages/PdfToJpgPage/types';
import styles from '../../pages/PdfToJpgPage/PdfToJpgPage.module.css';

interface OutputSettingsProps {
  options: PdfToJpgOptions;
  presets: PdfPresetConfig[];
  validFileCount: number;
  totalPages: number;
  disabled: boolean;
  canStart: boolean;
  onPickOutput: () => void;
  onChangePreset: (preset: PdfPreset) => void;
  onToggle: (key: 'optimizeFileSize' | 'createZip' | 'openOutputAfterFinish') => void;
  onStart: () => void;
}

export function OutputSettings({
  options,
  presets,
  validFileCount,
  totalPages,
  disabled,
  canStart,
  onPickOutput,
  onChangePreset,
  onToggle,
  onStart,
}: OutputSettingsProps) {
  return (
    <aside className={styles.card}>
      <div className={styles.sectionHead}>
        <div>
          <h3>Pengaturan Hasil</h3>
          <p>Atur folder dan kualitas JPG.</p>
        </div>
      </div>

      <div className={styles.outputPicker}>
        <span>Folder hasil</span>
        <button type="button" className="secondary-button" onClick={onPickOutput} disabled={disabled}>
          Pilih Folder
        </button>
        <strong title={options.outputDirectory}>{options.outputDirectory || 'Belum dipilih'}</strong>
      </div>

      <div className={styles.presetGrid}>
        {presets.map((preset) => (
          <button
            key={preset.id}
            type="button"
            className={options.preset === preset.id ? styles.presetActive : styles.presetButton}
            onClick={() => onChangePreset(preset.id)}
            disabled={disabled}
          >
            <strong>{preset.label}</strong>
            <span>
              {preset.dpi} DPI / JPG {preset.jpegQuality}
            </span>
          </button>
        ))}
      </div>

      <div className={styles.toggleList}>
        <label>
          <span>Optimalkan ukuran file</span>
          <input type="checkbox" checked={options.optimizeFileSize} onChange={() => onToggle('optimizeFileSize')} disabled={disabled} />
        </label>
        <label>
          <span>Buat ZIP hasil</span>
          <input type="checkbox" checked={options.createZip} onChange={() => onToggle('createZip')} disabled={disabled} />
        </label>
        <label>
          <span>Buka folder setelah selesai</span>
          <input
            type="checkbox"
            checked={options.openOutputAfterFinish}
            onChange={() => onToggle('openOutputAfterFinish')}
            disabled={disabled}
          />
        </label>
      </div>

      <dl className={styles.summaryGrid}>
        <div>
          <dt>PDF valid</dt>
          <dd>{validFileCount}</dd>
        </div>
        <div>
          <dt>Total halaman</dt>
          <dd>{totalPages}</dd>
        </div>
        <div>
          <dt>Estimasi JPG</dt>
          <dd>{totalPages}</dd>
        </div>
      </dl>

      <button type="button" className={styles.startButton} onClick={onStart} disabled={!canStart || disabled}>
        Mulai Ubah File
      </button>
    </aside>
  );
}
