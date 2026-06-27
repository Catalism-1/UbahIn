import { useEffect, useRef, useState } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { cancelEngineJob, checkEngine, logWindowEvent, openLogFolder } from './services/engine';
import type { EngineHealth } from './types/engine';

type Status = 'idle' | 'checking' | 'ready' | 'failed';

interface RuntimeState {
  isEngineCheckRunning: boolean;
  activeJobId: string | null;
  isConversionRunning: boolean;
}

const navigationItems = ['Engine', 'PDF', 'Gambar', 'Riwayat', 'Pengaturan'];

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
  const [isEngineCheckRunning, setIsEngineCheckRunning] = useState(false);
  const [activeJobId] = useState<string | null>(null);
  const [isConversionRunning] = useState(false);
  const [showCloseDialog, setShowCloseDialog] = useState(false);
  const runtimeRef = useRef<RuntimeState>({
    isEngineCheckRunning: false,
    activeJobId: null,
    isConversionRunning: false,
  });
  const forceClosingRef = useRef(false);

  useEffect(() => {
    runtimeRef.current = {
      isEngineCheckRunning,
      activeJobId,
      isConversionRunning,
    };
  }, [activeJobId, isConversionRunning, isEngineCheckRunning]);

  useEffect(() => {
    let disposed = false;
    let unlisten: (() => void) | undefined;

    getCurrentWindow()
      .onCloseRequested(async (event) => {
        const runtime = runtimeRef.current;
        void logWindowEvent(
          `close_requested engineCheck=${runtime.isEngineCheckRunning} conversion=${runtime.isConversionRunning} job=${runtime.activeJobId ?? 'none'}`,
        );

        if (forceClosingRef.current) {
          return;
        }

        if (runtime.isConversionRunning) {
          event.preventDefault();
          setShowCloseDialog(true);
          return;
        }

        if (runtime.isEngineCheckRunning) {
          void cancelEngineJob(runtime.activeJobId);
        }
      })
      .then((handler) => {
        if (disposed) {
          handler();
          return;
        }
        unlisten = handler;
      })
      .catch((error) => {
        console.error('Gagal memasang listener close request:', error);
        void logWindowEvent(`close_listener_error ${String(error)}`);
      });

    return () => {
      disposed = true;
      unlisten?.();
    };
  }, []);

  async function handleCheckEngine() {
    setIsEngineCheckRunning(true);
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
    } finally {
      setIsEngineCheckRunning(false);
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

  async function handleCancelAndClose() {
    setShowCloseDialog(false);
    try {
      await cancelEngineJob(activeJobId);
    } finally {
      forceClosingRef.current = true;
      await getCurrentWindow().close();
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Navigasi utama">
        <div className="brand">
          <span className="brand-mark">U</span>
          <div className="brand-copy">
            <strong>Ubahin</strong>
            <span>Desktop</span>
          </div>
        </div>
        <nav className="nav-list" aria-label="Bagian aplikasi">
          {navigationItems.map((item) => (
            <button
              key={item}
              type="button"
              className={item === 'Engine' ? 'nav-item active' : 'nav-item'}
              aria-current={item === 'Engine' ? 'page' : undefined}
            >
              <span aria-hidden="true">{item.charAt(0)}</span>
              <strong>{item}</strong>
            </button>
          ))}
        </nav>
      </aside>

      <section className="workspace">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">Ubahin</p>
            <h1>Ubah file jadi lebih mudah.</h1>
          </div>
          <p>Bukti arsitektur Tauri + React + Python engine.</p>
        </header>

        <div className="content-scroll">
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
        </div>
      </section>

      {showCloseDialog ? (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="close-dialog-title">
            <h2 id="close-dialog-title">Konversi masih berjalan</h2>
            <p>Menutup aplikasi akan membatalkan proses yang sedang berjalan. File yang sudah selesai tetap tersimpan.</p>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setShowCloseDialog(false)}>
                Lanjutkan Konversi
              </button>
              <button type="button" onClick={handleCancelAndClose}>
                Batalkan dan Tutup
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
