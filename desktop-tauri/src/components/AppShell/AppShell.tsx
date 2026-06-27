import type { ReactNode } from 'react';
import type { ThemePreference } from '../../hooks/useTheme';
import type { EngineStatus, NavigationItem, PageId } from '../../types/navigation';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import styles from './AppShell.module.css';

interface AppShellProps {
  activePage: PageId;
  title: string;
  eyebrow: string;
  engineStatus: EngineStatus;
  theme: ThemePreference;
  navigationItems: NavigationItem[];
  children: ReactNode;
  onThemeChange: (theme: ThemePreference) => void;
  onNavigate: (page: PageId) => void;
}

export function AppShell({
  activePage,
  title,
  eyebrow,
  engineStatus,
  theme,
  navigationItems,
  children,
  onThemeChange,
  onNavigate,
}: AppShellProps) {
  return (
    <div className={styles.shell}>
      <Sidebar
        items={navigationItems}
        activePage={activePage}
        engineStatus={engineStatus}
        theme={theme}
        onThemeChange={onThemeChange}
        onNavigate={onNavigate}
      />
      <section className={styles.workspace}>
        <Topbar title={title} eyebrow={eyebrow} engineStatus={engineStatus} onOpenEngineCheck={() => onNavigate('engine')} />
        <main className={styles.content}>{children}</main>
      </section>
    </div>
  );
}
