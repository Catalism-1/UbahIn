import type { ThemePreference } from '../hooks/useTheme';
import './pages.css';

interface SettingsPageProps {
  theme: ThemePreference;
  performanceMode: string;
  openFolderAfterFinish: boolean;
  onThemeChange: (theme: ThemePreference) => void;
  onPerformanceModeChange: (mode: string) => void;
  onOpenFolderAfterFinishChange: (value: boolean) => void;
}

const themes: Array<{ value: ThemePreference; label: string }> = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'Ikuti sistem' },
];

const performanceModes = ['Hemat RAM', 'Seimbang', 'Cepat'];

export function SettingsPage({
  theme,
  performanceMode,
  openFolderAfterFinish,
  onThemeChange,
  onPerformanceModeChange,
  onOpenFolderAfterFinishChange,
}: SettingsPageProps) {
  return (
    <div className="page">
      <section className="settings-list">
        <div className="setting-row">
          <div>
            <h3>Tema</h3>
            <p>Pilih tampilan terang, gelap, atau ikuti sistem Windows.</p>
          </div>
          <div className="segmented">
            {themes.map((item) => (
              <button
                key={item.value}
                type="button"
                className={theme === item.value ? 'active' : ''}
                onClick={() => onThemeChange(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <div className="setting-row">
          <div>
            <h3>Folder output default</h3>
            <p>Placeholder sampai settings backend dihubungkan.</p>
          </div>
          <div className="field-placeholder">C:\Users\NamaPengguna\Documents\Ubahin\Hasil</div>
        </div>

        <div className="setting-row">
          <div>
            <h3>Mode performa</h3>
            <p>Atur seberapa banyak tenaga laptop yang dipakai.</p>
          </div>
          <div className="segmented">
            {performanceModes.map((mode) => (
              <button
                key={mode}
                type="button"
                className={performanceMode === mode ? 'active' : ''}
                onClick={() => onPerformanceModeChange(mode)}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        <div className="setting-row">
          <div>
            <h3>Buka folder setelah selesai</h3>
            <p>Nanti akan dikirim ke backend settings Python.</p>
          </div>
          <div className="toggle-row">
            <button
              type="button"
              className={openFolderAfterFinish ? 'switch active' : 'switch'}
              onClick={() => onOpenFolderAfterFinishChange(!openFolderAfterFinish)}
              aria-pressed={openFolderAfterFinish}
            >
              <span />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
