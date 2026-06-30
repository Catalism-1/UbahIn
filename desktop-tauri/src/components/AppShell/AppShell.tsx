import { useState, useEffect, type ReactNode } from 'react';
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
  const [isWidthCompact, setIsWidthCompact] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth < 1280 : false
  );

  const [isCollapsed, setIsCollapsed] = useState(() => {
    try {
      const item = localStorage.getItem('ubahin-sidebar-collapsed');
      return item ? JSON.parse(item) === true : false;
    } catch {
      return false;
    }
  });

  useEffect(() => {
    const handleResize = () => {
      setIsWidthCompact(window.innerWidth < 1280);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isCompact = isWidthCompact || isCollapsed;

  const handleToggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('ubahin-sidebar-collapsed', JSON.stringify(next));
      } catch (e) {
        console.error(e);
      }
      return next;
    });
  };

  return (
    <div className={`${styles.shell} ${isCompact ? styles.compact : ''}`}>
      <Sidebar
        items={navigationItems}
        activePage={activePage}
        engineStatus={engineStatus}
        theme={theme}
        onThemeChange={onThemeChange}
        onNavigate={onNavigate}
        isCompact={isCompact}
        isWidthCompact={isWidthCompact}
        onToggleCollapse={handleToggleCollapse}
      />
      <section className={styles.workspace}>
        <Topbar title={title} eyebrow={eyebrow} engineStatus={engineStatus} onOpenEngineCheck={() => onNavigate('engine')} />
        <main className={styles.content}>{children}</main>
      </section>
    </div>
  );
}
