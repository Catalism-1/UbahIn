import { useCallback, useEffect, useMemo, useState } from 'react';
import { getSettings, saveSettings as saveSettingsService } from '../services/settings';
import { DEFAULT_SETTINGS } from '../types/settings';
import type { AppSettings, ResolvedTheme, ThemePreference } from '../types/settings';

// localStorage HANYA cache tema untuk paint awal + fallback dev bila engine belum
// tersedia. Sumber kebenaran tetap engine Python.
const THEME_CACHE_KEY = 'ubahin.theme';

function readCachedTheme(): ThemePreference {
  const value = window.localStorage.getItem(THEME_CACHE_KEY);
  if (value === 'light' || value === 'dark' || value === 'system') return value;
  return DEFAULT_SETTINGS.theme;
}

function getSystemTheme(): ResolvedTheme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export interface UseAppSettings {
  settings: AppSettings;
  theme: ThemePreference;
  resolvedTheme: ResolvedTheme;
  isLoaded: boolean;
  usingFallback: boolean;
  /** Terapkan tema secara langsung tanpa menyimpan (preview di halaman Pengaturan). */
  previewTheme: (theme: ThemePreference) => void;
  /** Terapkan + simpan tema (toggle cepat di topbar). */
  persistTheme: (theme: ThemePreference) => Promise<void>;
  /** Simpan seluruh pengaturan secara eksplisit (tombol Simpan). */
  saveSettings: (payload: AppSettings) => Promise<AppSettings>;
  reload: () => Promise<void>;
}

export function useAppSettings(): UseAppSettings {
  const cachedTheme = useMemo(() => readCachedTheme(), []);
  const [settings, setSettings] = useState<AppSettings>({ ...DEFAULT_SETTINGS, theme: cachedTheme });
  const [theme, setTheme] = useState<ThemePreference>(cachedTheme);
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(() => getSystemTheme());
  const [isLoaded, setIsLoaded] = useState(false);
  const [usingFallback, setUsingFallback] = useState(false);

  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setSystemTheme(getSystemTheme());
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  const resolvedTheme = useMemo<ResolvedTheme>(
    () => (theme === 'system' ? systemTheme : theme),
    [theme, systemTheme],
  );

  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme;
  }, [resolvedTheme]);

  useEffect(() => {
    window.localStorage.setItem(THEME_CACHE_KEY, theme);
  }, [theme]);

  const applyLoaded = useCallback((next: AppSettings) => {
    setSettings(next);
    setTheme(next.theme);
  }, []);

  const reload = useCallback(async () => {
    try {
      const loaded = await getSettings();
      applyLoaded(loaded);
      setUsingFallback(false);
    } catch (error) {
      // Engine belum tersedia: pertahankan tema cache, jangan rusak state.
      setUsingFallback(true);
      console.error('Gagal memuat pengaturan dari engine:', error);
    } finally {
      setIsLoaded(true);
    }
  }, [applyLoaded]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const previewTheme = useCallback((next: ThemePreference) => {
    setTheme(next);
  }, []);

  const saveSettings = useCallback(
    async (payload: AppSettings): Promise<AppSettings> => {
      const saved = await saveSettingsService(payload);
      applyLoaded(saved);
      setUsingFallback(false);
      return saved;
    },
    [applyLoaded],
  );

  const persistTheme = useCallback(
    async (next: ThemePreference): Promise<void> => {
      setTheme(next);
      try {
        const saved = await saveSettingsService({ ...settings, theme: next });
        setSettings(saved);
        setUsingFallback(false);
      } catch (error) {
        // Tema tetap terterap secara visual; cache localStorage menjaga preferensi.
        setUsingFallback(true);
        console.error('Gagal menyimpan tema:', error);
      }
    },
    [settings],
  );

  return {
    settings,
    theme,
    resolvedTheme,
    isLoaded,
    usingFallback,
    previewTheme,
    persistTheme,
    saveSettings,
    reload,
  };
}
