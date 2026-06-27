import { useState, useEffect } from 'react';
import { getVersion } from '@tauri-apps/api/app';
import { appDataDir } from '@tauri-apps/api/path';
import { getCurrentWindow, LogicalSize } from '@tauri-apps/api/window';
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
  if (status === 'checking') return 'Sedang diperiksa...';
  if (status === 'ready') return 'Berjalan lancar';
  if (status === 'failed') return 'Bermasalah';
  return 'Belum diperiksa';
}

function available(value: boolean | undefined): string {
  if (value === undefined) return '-';
  return value ? 'Tersedia' : 'Tidak tersedia';
}

export function EngineCheckPage({ status, health, message, onCheck, onOpenLogFolder }: EngineCheckPageProps) {
  const [appVersion, setAppVersion] = useState<string>('-');
  const [appDataPath, setAppDataPath] = useState<string>('-');

  useEffect(() => {
    async function fetchInfo() {
      try {
        const v = await getVersion();
        setAppVersion(v);
      } catch (e) {
        setAppVersion('Tidak diketahui');
      }
      try {
        const d = await appDataDir();
        setAppDataPath(d);
      } catch (e) {
        setAppDataPath('Tidak diketahui');
      }
    }
    void fetchInfo();
  }, []);

  async function handleResetWindow() {
    try {
      const win = getCurrentWindow();
      await win.setSize(new LogicalSize(1440, 900));
      await win.center();
    } catch (error) {
      console.error('Gagal reset ukuran jendela', error);
    }
  }

  async function handleCopyDiagnostics() {
    const info = `Status: ${statusText(status)}
Pesan: ${message}
Versi Aplikasi: ${appVersion}
Versi Engine: ${health?.engine_version ?? '-'}
Platform: ${health?.platform ?? '-'}
PyMuPDF: ${available(health?.pymupdf_available)}
Pillow: ${available(health?.pillow_available)}
PyPDF: ${available(health?.pypdf_available)}
Native Accel: ${health?.native_acceleration ?? '-'}
Lokasi App Data: ${appDataPath}`;
    try {
      await navigator.clipboard.writeText(info);
      alert('Informasi diagnostik berhasil disalin ke clipboard.');
    } catch (e) {
      alert('Gagal menyalin informasi diagnostik.');
    }
  }

  return (
    <div className="page">
      <section className="panel-card" aria-labelledby="engine-title">
        <div className="panel-head">
          <div>
            <h2 id="engine-title">Diagnostik Sistem</h2>
            <p>Informasi status engine Python dan path aplikasi lokal.</p>
          </div>
          <span className={`status-pill ${status === 'ready' ? 'ready' : status === 'failed' ? 'failed' : ''}`}>{statusText(status)}</span>
        </div>

        {message ? <div className="notice">{message}</div> : null}

        <div className="button-row">
          <button type="button" className="primary-button" onClick={onCheck} disabled={status === 'checking'}>
            {status === 'checking' ? 'Memeriksa...' : 'Cek Status Engine'}
          </button>
          <button type="button" className="secondary-button" onClick={handleCopyDiagnostics}>
            Salin Informasi Diagnostik
          </button>
          <button type="button" className="secondary-button" onClick={onOpenLogFolder}>
            Buka Folder Log
          </button>
          <button type="button" className="secondary-button" onClick={handleResetWindow}>
            Reset Ukuran Jendela
          </button>
        </div>

        <dl className="detail-grid" style={{ marginTop: '2rem' }}>
          <div>
            <dt>Versi Aplikasi</dt>
            <dd>{appVersion}</dd>
          </div>
          <div>
            <dt>Versi Engine</dt>
            <dd>{health?.engine_version ?? '-'}</dd>
          </div>
          <div>
            <dt>Status Sidecar</dt>
            <dd>{statusText(status)}</dd>
          </div>
          <div>
            <dt>Lokasi App Data / Log</dt>
            <dd style={{ wordBreak: 'break-all' }}>{appDataPath}</dd>
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
