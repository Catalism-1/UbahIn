import { useEffect, useState } from 'react';
import { Toast } from '../components/common/Toast';
import { useToasts } from '../hooks/useToasts';
import { selectDefaultOutputDirectory } from '../services/settings';
import type { AppSettings, PdfPreset, PerformanceMode, ThemePreference } from '../types/settings';
import './pages.css';

interface SettingsPageProps {
  settings: AppSettings;
  usingFallback: boolean;
  onPreviewTheme: (theme: ThemePreference) => void;
  onSave: (payload: AppSettings) => Promise<AppSettings>;
}

const themes: Array<{ value: ThemePreference; label: string }> = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'Ikuti Sistem' },
];

const performanceModes: Array<{ value: PerformanceMode; label: string }> = [
  { value: 'ram_saver', label: 'Hemat RAM' },
  { value: 'balanced', label: 'Seimbang' },
  { value: 'fast', label: 'Cepat' },
];

const presets: Array<{ value: PdfPreset; label: string }> = [
  { value: 'standard', label: 'Standard' },
  { value: 'high', label: 'Tinggi' },
  { value: 'ultra', label: 'Sangat Tinggi' },
];

interface ToggleProps {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
}

function Toggle({ checked, onChange, label }: ToggleProps) {
  return (
    <button
      type="button"
      className={checked ? 'switch active' : 'switch'}
      onClick={() => onChange(!checked)}
      aria-pressed={checked}
      aria-label={label}
    >
      <span />
    </button>
  );
}

export function SettingsPage({ settings, usingFallback, onPreviewTheme, onSave }: SettingsPageProps) {
  const [draft, setDraft] = useState<AppSettings>(settings);
  const [saving, setSaving] = useState(false);
  const { toasts, addToast } = useToasts();

  // Sinkronkan draft ketika sumber kebenaran (settings) berubah.
  useEffect(() => {
    setDraft(settings);
  }, [settings]);

  function update<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function handleThemeChange(value: ThemePreference) {
    update('theme', value);
    onPreviewTheme(value); // Terapkan langsung sebagai pratinjau.
  }

  async function handlePickFolder() {
    try {
      const directory = await selectDefaultOutputDirectory();
      if (!directory) return;
      update('default_output_directory', directory);
    } catch (error) {
      addToast('Folder tidak dapat dipilih.', 'error', error instanceof Error ? error.message : 'Silakan coba lagi.');
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      await onSave(draft);
      addToast('Pengaturan berhasil disimpan.', 'success');
    } catch (error) {
      addToast(
        'Pengaturan gagal disimpan.',
        'error',
        error instanceof Error ? error.message : 'Engine belum siap. Coba lagi.',
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page">
      {usingFallback ? (
        <div className="notice">
          Engine belum tersedia. Pengaturan ditampilkan dari cache sementara dan belum tersimpan permanen.
        </div>
      ) : null}

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
                className={draft.theme === item.value ? 'active' : ''}
                onClick={() => handleThemeChange(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <div className="setting-row">
          <div>
            <h3>Folder hasil default</h3>
            <p>Folder yang dipakai otomatis saat memulai konversi baru.</p>
          </div>
          <div className="folder-field">
            <span className="field-placeholder" title={draft.default_output_directory || undefined}>
              {draft.default_output_directory || 'Belum dipilih'}
            </span>
            <button type="button" className="secondary-button" onClick={handlePickFolder}>
              Pilih Folder
            </button>
          </div>
        </div>

        <div className="setting-row">
          <div>
            <h3>Mode performa</h3>
            <p>Atur seberapa banyak tenaga laptop yang dipakai.</p>
          </div>
          <div className="segmented">
            {performanceModes.map((mode) => (
              <button
                key={mode.value}
                type="button"
                className={draft.performance_mode === mode.value ? 'active' : ''}
                onClick={() => update('performance_mode', mode.value)}
              >
                {mode.label}
              </button>
            ))}
          </div>
        </div>

        <div className="setting-row">
          <div>
            <h3>Kualitas PDF ke JPG default</h3>
            <p>Preset bawaan saat membuka alat PDF ke JPG.</p>
          </div>
          <div className="segmented">
            {presets.map((preset) => (
              <button
                key={preset.value}
                type="button"
                className={draft.default_pdf_preset === preset.value ? 'active' : ''}
                onClick={() => update('default_pdf_preset', preset.value)}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        <div className="setting-row">
          <div>
            <h3>Buat ZIP setelah selesai</h3>
            <p>Kemas semua hasil menjadi satu file ZIP otomatis.</p>
          </div>
          <div className="toggle-row">
            <Toggle
              checked={draft.create_zip_after_conversion}
              onChange={(value) => update('create_zip_after_conversion', value)}
              label="Buat ZIP setelah selesai"
            />
          </div>
        </div>

        <div className="setting-row">
          <div>
            <h3>Buka folder hasil setelah selesai</h3>
            <p>Otomatis membuka folder hasil ketika konversi rampung.</p>
          </div>
          <div className="toggle-row">
            <Toggle
              checked={draft.open_output_after_finish}
              onChange={(value) => update('open_output_after_finish', value)}
              label="Buka folder hasil setelah selesai"
            />
          </div>
        </div>

        <div className="setting-row">
          <div>
            <h3>Tampilkan notifikasi saat selesai</h3>
            <p>Beri tahu saat konversi selesai diproses.</p>
          </div>
          <div className="toggle-row">
            <Toggle
              checked={draft.notifications_enabled}
              onChange={(value) => update('notifications_enabled', value)}
              label="Tampilkan notifikasi saat selesai"
            />
          </div>
        </div>
      </section>

      <div className="button-row" style={{ justifyContent: 'flex-end' }}>
        <button type="button" className="primary-button" onClick={handleSave} disabled={saving}>
          {saving ? 'Menyimpan…' : 'Simpan Pengaturan'}
        </button>
      </div>

      <Toast messages={toasts} />
    </div>
  );
}
