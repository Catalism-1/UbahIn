import type { EngineHealth } from '../types/engine';
import './pages.css';

type EnginePageStatus = 'idle' | 'checking' | 'ready' | 'failed';

interface EngineCheckPageProps {
  status: EnginePageStatus;
  health: EngineHealth | null;
  message: string;
  onCheck: () => void;
  onOpenLogFolder: () => void;
}

function statusText(status: EnginePageStatus): string {
  if (status === 'checking') return 'Engine sedang diperiksa';
  if (status === 'ready') return 'Engine siap';
  if (status === 'failed') return 'Engine bermasalah';
  return 'Engine belum diperiksa';
}

function available(value: boolean | undefined): string {
  if (value === undefined) return '-';
  return value ? 'Tersedia' : 'Tidak tersedia';
}

export function EngineCheckPage({ status, health, message, onCheck, onOpenLogFolder }: EngineCheckPageProps) {
  return (
    <div className="page">
      <section className="panel-card" aria-labelledby="engine-title">
        <div className="panel-head">
          <div>
            <h2 id="engine-title">Pemeriksaan Engine</h2>
            <p>Pastikan Python engine lokal siap sebelum fitur converter dipindahkan ke React.</p>
          </div>
          <span className={`status-pill ${status === 'ready' ? 'ready' : status === 'failed' ? 'failed' : ''}`}>{statusText(status)}</span>
        </div>

        {message ? <div className="notice">{message}</div> : null}

        <div className="button-row">
          <button type="button" className="primary-button" onClick={onCheck} disabled={status === 'checking'}>
            {status === 'checking' ? 'Memeriksa...' : 'Cek Engine'}
          </button>
          <button type="button" className="secondary-button" onClick={onOpenLogFolder}>
            Buka Folder Log
          </button>
        </div>

        <dl className="detail-grid">
          <div>
            <dt>Versi engine</dt>
            <dd>{health?.engine_version ?? '-'}</dd>
          </div>
          <div>
            <dt>PyMuPDF</dt>
            <dd>{available(health?.pymupdf_available)}</dd>
          </div>
          <div>
            <dt>Pillow</dt>
            <dd>{available(health?.pillow_available)}</dd>
          </div>
          <div>
            <dt>pypdf</dt>
            <dd>{available(health?.pypdf_available)}</dd>
          </div>
          <div>
            <dt>Native acceleration</dt>
            <dd>{health?.native_acceleration ?? '-'}</dd>
          </div>
          <div>
            <dt>Platform</dt>
            <dd>{health?.platform ?? '-'}</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
