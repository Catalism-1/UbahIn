import { useState } from 'react';
import { checkEngine, openLogFolder } from './services/engine';
import type { EngineHealth } from './types/engine';

type Status = 'idle' | 'checking' | 'ready' | 'failed';

function statusText(status: Status): string {
  if (status === 'checking') return 'Engine sedang diperiksa';
  if (status === 'ready') return 'Engine siap';
  if (status === 'failed') return 'Engine gagal';
  return 'Engine belum diperiksa';
}

export default function App() {
  const [status, setStatus] = useState<Status>('idle');
  const [health, setHealth] = useState<EngineHealth | null>(null);
  const [message, setMessage] = useState<string>('');

  async function handleCheckEngine() {
    setStatus('checking');
    setMessage('');
    setHealth(null);
    try {
      const response = await checkEngine();
      if (response.ok && response.data) {
        setHealth(response.data);
        setStatus('ready');
        return;
      }
      setMessage(response.error?.message ?? 'Engine tidak siap.');
      setStatus('failed');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Engine tidak dapat dijalankan.');
      setStatus('failed');
    }
  }

  async function handleOpenLogFolder() {
    try {
      await openLogFolder();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Folder log tidak dapat dibuka.');
      setStatus('failed');
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">Ubahin</p>
        <h1>Ubah file jadi lebih mudah.</h1>
        <p className="lead">Bukti arsitektur Tauri + React + Python engine.</p>
      </section>

      <section className="panel" aria-labelledby="engine-title">
        <div className="panel-head">
          <div>
            <h2 id="engine-title">Pemeriksaan Engine</h2>
            <p>{statusText(status)}</p>
          </div>
          <span className={`status ${status}`}>{statusText(status)}</span>
        </div>

        {message ? <div className="notice">{message}</div> : null}

        <div className="actions">
          <button type="button" onClick={handleCheckEngine} disabled={status === 'checking'}>
            {status === 'checking' ? 'Memeriksa...' : 'Cek Engine'}
          </button>
          <button type="button" className="secondary" onClick={handleOpenLogFolder}>
            Buka Folder Log
          </button>
        </div>

        <dl className="details">
          <div>
            <dt>Versi engine</dt>
            <dd>{health?.engine_version ?? '-'}</dd>
          </div>
          <div>
            <dt>PyMuPDF</dt>
            <dd>{health ? (health.pymupdf_available ? 'Tersedia' : 'Tidak tersedia') : '-'}</dd>
          </div>
          <div>
            <dt>Pillow</dt>
            <dd>{health ? (health.pillow_available ? 'Tersedia' : 'Tidak tersedia') : '-'}</dd>
          </div>
          <div>
            <dt>pypdf</dt>
            <dd>{health ? (health.pypdf_available ? 'Tersedia' : 'Tidak tersedia') : '-'}</dd>
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
    </main>
  );
}
