import { useEffect, useMemo, useState } from 'react';

export type ThemePreference = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

const THEME_KEY = 'ubahin.theme';

const themeStorage = {
  read(): ThemePreference {
    const value = window.localStorage.getItem(THEME_KEY);
    if (value === 'light' || value === 'dark' || value === 'system') return value;
    return 'light';
  },
  write(value: ThemePreference) {
    window.localStorage.setItem(THEME_KEY, value);
  },
};

function getSystemTheme(): ResolvedTheme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function useTheme() {
  const [preference, setPreferenceState] = useState<ThemePreference>(() => themeStorage.read());
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(() => getSystemTheme());

  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setSystemTheme(getSystemTheme());
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  const resolvedTheme = useMemo<ResolvedTheme>(
    () => (preference === 'system' ? systemTheme : preference),
    [preference, systemTheme],
  );

  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme;
  }, [resolvedTheme]);

  function setPreference(value: ThemePreference) {
    setPreferenceState(value);
    themeStorage.write(value);
  }

  return { preference, resolvedTheme, setPreference };
}
