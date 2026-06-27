import type { ThemePreference } from '../../hooks/useTheme';
import './ThemeToggle.css';

interface ThemeToggleProps {
  value: ThemePreference;
  onChange: (value: ThemePreference) => void;
  compact?: boolean;
}

const options: Array<{ value: ThemePreference; label: string; short: string }> = [
  { value: 'light', label: 'Light', short: 'L' },
  { value: 'dark', label: 'Dark', short: 'D' },
  { value: 'system', label: 'System', short: 'S' },
];

export function ThemeToggle({ value, onChange, compact = false }: ThemeToggleProps) {
  return (
    <div className={compact ? 'theme-toggle compact' : 'theme-toggle'} aria-label="Tema aplikasi">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={value === option.value ? 'active' : ''}
          onClick={() => onChange(option.value)}
          aria-pressed={value === option.value}
          title={option.label}
        >
          <span className="theme-label">{compact ? option.short : option.label}</span>
          <span className="theme-short">{option.short}</span>
        </button>
      ))}
    </div>
  );
}
