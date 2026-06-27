import type { EngineStatus } from '../../types/navigation';
import styles from './AppShell.module.css';

interface TopbarProps {
  title: string;
  eyebrow: string;
  engineStatus: EngineStatus;
  onOpenEngineCheck: () => void;
}

function engineLabel(status: EngineStatus): string {
  if (status === 'ready') return 'Engine siap';
  if (status === 'error') return 'Engine bermasalah';
  if (status === 'checking') return 'Memeriksa engine';
  return 'Belum diperiksa';
}

export function Topbar({ title, eyebrow, engineStatus, onOpenEngineCheck }: TopbarProps) {
  return (
    <header className={styles.topbar}>
      <div className={styles.titleBlock}>
        <span className={styles.breadcrumb}>{eyebrow}</span>
        <h1 className={styles.pageTitle}>{title}</h1>
      </div>
      <div className={styles.topbarActions}>
        <span className={`${styles.engineStatus} ${styles[engineStatus]}`}>
          <span className={styles.statusDot} aria-hidden="true" />
          {engineLabel(engineStatus)}
        </span>
        <button type="button" className={styles.engineButton} onClick={onOpenEngineCheck}>
          Pemeriksaan Engine
        </button>
      </div>
    </header>
  );
}
