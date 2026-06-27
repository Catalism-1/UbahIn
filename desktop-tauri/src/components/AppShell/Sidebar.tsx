import { ThemeToggle } from '../ThemeToggle/ThemeToggle';
import { Tooltip } from '../common/Tooltip';
import type { ThemePreference } from '../../hooks/useTheme';
import type { EngineStatus, NavigationItem, PageId } from '../../types/navigation';
import styles from './AppShell.module.css';

interface SidebarProps {
  items: NavigationItem[];
  activePage: PageId;
  engineStatus: EngineStatus;
  theme: ThemePreference;
  onThemeChange: (theme: ThemePreference) => void;
  onNavigate: (page: PageId) => void;
}

function engineLabel(status: EngineStatus): string {
  if (status === 'ready') return 'Engine siap';
  if (status === 'error') return 'Engine bermasalah';
  if (status === 'checking') return 'Memeriksa engine';
  return 'Belum diperiksa';
}

function Icon({ name }: { name: string }) {
  const common = { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.9 };
  if (name === 'home') return <svg {...common}><path d="M4 11.5 12 5l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z" /></svg>;
  if (name === 'pdf') return <svg {...common}><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v5h4" /><path d="M9 13h6M9 17h4" /></svg>;
  if (name === 'image') return <svg {...common}><rect x="4" y="5" width="16" height="14" rx="2" /><path d="m7 16 3-3 3 3 2-2 2 2" /><circle cx="9" cy="9" r="1.2" /></svg>;
  if (name === 'history') return <svg {...common}><path d="M4 12a8 8 0 1 0 2.2-5.5" /><path d="M4 5v4h4M12 8v5l3 2" /></svg>;
  return <svg {...common}><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1" /></svg>;
}

export function Sidebar({ items, activePage, engineStatus, theme, onThemeChange, onNavigate }: SidebarProps) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <span className={styles.brandMark} aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
            <path d="M4 7h5M4 7l3-3M4 7l3 3M20 17h-5M20 17l-3-3M20 17l-3 3" />
          </svg>
        </span>
        <span className={styles.brandText}>
          <strong>Ubahin</strong>
          <span>Ubah file jadi lebih mudah.</span>
        </span>
      </div>

      <nav className={styles.nav} aria-label="Navigasi utama">
        {items.map((item) => {
          const button = (
            <button
              key={item.id}
              type="button"
              className={`${styles.navItem} ${activePage === item.id ? styles.active : ''}`}
              onClick={() => onNavigate(item.id)}
              aria-current={activePage === item.id ? 'page' : undefined}
            >
              <span className={styles.navIcon} aria-hidden="true">
                <Icon name={item.icon} />
              </span>
              <span className={styles.navLabel}>{item.label}</span>
            </button>
          );
          return (
            <Tooltip key={item.id} label={item.label}>
              {button}
            </Tooltip>
          );
        })}
      </nav>

      <div className={styles.sidebarFooter}>
        <ThemeToggle value={theme} onChange={onThemeChange} />
        <div className={styles.engineMini}>
          <strong>{engineLabel(engineStatus)}</strong>
          <span>Status engine lokal</span>
        </div>
        <span className={styles.version}>Ubahin 0.1.1</span>
      </div>
    </aside>
  );
}
