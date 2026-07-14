export type ThemePreference = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';
export type PerformanceMode = 'ram_saver' | 'balanced' | 'fast';
export type PdfPreset = 'standard' | 'high' | 'ultra';

export interface AppSettings {
  theme: ThemePreference;
  default_output_directory: string;
  performance_mode: PerformanceMode;
  default_pdf_preset: PdfPreset;
  default_dpi: number;
  default_jpeg_quality: number;
  create_zip_after_conversion: boolean;
  open_output_after_finish: boolean;
  notifications_enabled: boolean;
}

export type SaveSettingsPayload = AppSettings;

export const DEFAULT_SETTINGS: AppSettings = {
  theme: 'system',
  default_output_directory: '',
  performance_mode: 'balanced',
  default_pdf_preset: 'standard',
  default_dpi: 150,
  default_jpeg_quality: 80,
  create_zip_after_conversion: false,
  open_output_after_finish: true,
  notifications_enabled: true,
};

const THEME_VALUES: readonly ThemePreference[] = ['light', 'dark', 'system'];
const MODE_VALUES: readonly PerformanceMode[] = ['ram_saver', 'balanced', 'fast'];
const PRESET_VALUES: readonly PdfPreset[] = ['standard', 'high', 'ultra'];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function pickEnum<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return typeof value === 'string' && (allowed as readonly string[]).includes(value) ? (value as T) : fallback;
}

function pickInt(value: unknown, fallback: number, low: number, high: number): number {
  const parsed = typeof value === 'number' ? value : typeof value === 'string' ? Number(value) : Number.NaN;
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(low, Math.min(high, Math.round(parsed)));
}

function pickBool(value: unknown, fallback: boolean): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

/**
 * Validasi & normalisasi response settings dari engine tanpa `any`.
 * Field hilang atau rusak memakai default aman.
 */
export function parseAppSettings(raw: unknown): AppSettings {
  if (!isRecord(raw)) return { ...DEFAULT_SETTINGS };
  return {
    theme: pickEnum(raw.theme, THEME_VALUES, DEFAULT_SETTINGS.theme),
    default_output_directory:
      typeof raw.default_output_directory === 'string'
        ? raw.default_output_directory
        : DEFAULT_SETTINGS.default_output_directory,
    performance_mode: pickEnum(raw.performance_mode, MODE_VALUES, DEFAULT_SETTINGS.performance_mode),
    default_pdf_preset: pickEnum(raw.default_pdf_preset, PRESET_VALUES, DEFAULT_SETTINGS.default_pdf_preset),
    default_dpi: pickInt(raw.default_dpi, DEFAULT_SETTINGS.default_dpi, 72, 600),
    default_jpeg_quality: pickInt(raw.default_jpeg_quality, DEFAULT_SETTINGS.default_jpeg_quality, 40, 100),
    create_zip_after_conversion: pickBool(raw.create_zip_after_conversion, DEFAULT_SETTINGS.create_zip_after_conversion),
    open_output_after_finish: pickBool(raw.open_output_after_finish, DEFAULT_SETTINGS.open_output_after_finish),
    notifications_enabled: pickBool(raw.notifications_enabled, DEFAULT_SETTINGS.notifications_enabled),
  };
}
