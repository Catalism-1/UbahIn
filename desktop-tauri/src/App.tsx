import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AppShell } from './components/AppShell/AppShell';
import { useAppSettings } from './hooks/useAppSettings';
import { ComingSoonPage } from './pages/ComingSoonPage';
import { EngineCheckPage } from './pages/EngineCheckPage';
import { HistoryPage } from './pages/HistoryPage';
import { PdfToJpgPage } from './pages/PdfToJpgPage/PdfToJpgPage';
import { HomePage } from './pages/HomePage';
import { ImageToPdfPage } from './pages/ImageToPdfPage/ImageToPdfPage';
import { ImageConversionPage } from './pages/ImageConversionPage';
import { SettingsPage } from './pages/SettingsPage';
import { useTauriEvent } from './hooks/useTauriEvent';
import { cancelActiveJobAndClose, checkEngine, logWindowEvent, openLogFolder } from './services/engine';
import type { EngineHealth } from './types/engine';
import type { EngineStatus, NavigationItem, PageId } from './types/navigation';

type EnginePageStatus = 'idle' | 'checking' | 'ready' | 'failed';

interface RuntimeState {
  isEngineCheckRunning: boolean;
  activeJobId: string | null;
  isConversionRunning: boolean;
}

type CloseActiveJobPayload = {
  active_job_id?: string | null;
};

const navigationItems: NavigationItem[] = [
  { id: 'home', label: 'Beranda', icon: 'home' },
  { id: 'pdf', label: 'Ubah PDF', icon: 'pdf' },
  { id: 'image', label: 'Gambar ke PDF', icon: 'image' },
  { id: 'image-conv', label: 'Ubah Format Gambar', icon: 'image' },
  { id: 'history', label: 'Riwayat', icon: 'history' },
  { id: 'engine', label: 'Diagnostik', icon: 'settings' },
  { id: 'settings', label: 'Pengaturan', icon: 'settings' },
];

const pageMeta: Record<PageId, { title: string; eyebrow: string; description: string }> = {
  home: { title: 'Beranda', eyebrow: 'Ringkasan', description: 'Pilih alat yang kamu butuhkan.' },
  pdf: { title: 'PDF ke JPG', eyebrow: 'Alat PDF', description: 'Ubah halaman PDF menjadi gambar JPG.' },
  image: { title: 'Gambar ke PDF', eyebrow: 'Alat Gambar', description: 'Gabungkan beberapa gambar menjadi satu file PDF.' },
  'image-conv': { title: 'Ubah Format Gambar', eyebrow: 'Alat Gambar', description: 'Ubah format gambar antara JPG, PNG, WEBP, dan HEIC.' },
  history: { title: 'Riwayat', eyebrow: 'Aktivitas', description: 'Riwayat konversi lokal.' },
  settings: { title: 'Pengaturan', eyebrow: 'Preferensi', description: 'Pengaturan frontend sementara.' },
  engine: { title: 'Diagnostik Sistem', eyebrow: 'Diagnostik', description: 'Informasi status engine dan log.' },
  'merge-pdf': { title: 'Gabungkan PDF', eyebrow: 'Segera hadir', description: 'Fitur gabung PDF belum dipindahkan ke React.' },
  'compress-pdf': { title: 'Kompres PDF', eyebrow: 'Segera hadir', description: 'Fitur kompres PDF belum dipindahkan ke React.' },
  'resize-image': { title: 'Ubah Ukuran Gambar', eyebrow: 'Segera hadir', description: 'Fitur resize gambar belum dipindahkan ke React.' },
  'pdf-word': { title: 'PDF ke Word', eyebrow: 'Segera hadir', description: 'Fitur PDF ke Word belum dipindahkan ke React.' },
};

function shellEngineStatus(status: EnginePageStatus): EngineStatus {
  if (status === 'ready') return 'ready';
  if (status === 'failed') return 'error';
  if (status === 'checking') return 'checking';
  return 'unchecked';
}

export default function App() {
  const { settings, theme, usingFallback, previewTheme, persistTheme, saveSettings } = useAppSettings();
  const [activePage, setActivePage] = useState<PageId>('home');
  const [engineStatus, setEngineStatus] = useState<EnginePageStatus>('idle');
  const [health, setHealth] = useState<EngineHealth | null>(null);
  const [message, setMessage] = useState('');
  const [isEngineCheckRunning, setIsEngineCheckRunning] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [isConversionRunning, setIsConversionRunning] = useState(false);
  const [showCloseDialog, setShowCloseDialog] = useState(false);
  const runtimeRef = useRef<RuntimeState>({
    isEngineCheckRunning: false,
    activeJobId: null,
    isConversionRunning: false,
  });

  useEffect(() => {
    runtimeRef.current = {
      isEngineCheckRunning,
      activeJobId,
      isConversionRunning,
    };
  }, [activeJobId, isConversionRunning, isEngineCheckRunning]);

  const handleNativeCloseActiveJob = useCallback((payload: CloseActiveJobPayload) => {
    void logWindowEvent(`close_blocked_active_job job=${payload.active_job_id ?? runtimeRef.current.activeJobId ?? 'none'}`);
    setShowCloseDialog(true);
  }, []);

  useTauriEvent<CloseActiveJobPayload>('app://close-active-job', handleNativeCloseActiveJob, true);

  const meta = pageMeta[activePage];
  const statusForShell = useMemo(() => shellEngineStatus(engineStatus), [engineStatus]);

  async function handleCheckEngine() {
    setActivePage('engine');
    setIsEngineCheckRunning(true);
    setEngineStatus('checking');
    setMessage('');
    setHealth(null);
    try {
      const response = await checkEngine();
      if (response.ok && response.data) {
        setHealth(response.data);
        setEngineStatus('ready');
        return;
      }
      setMessage(response.error?.message ?? 'Engine tidak siap.');
      setEngineStatus('failed');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Engine tidak dapat dijalankan.');
      setEngineStatus('failed');
    } finally {
      setIsEngineCheckRunning(false);
    }
  }

  async function handleOpenLogFolder() {
    try {
      await openLogFolder();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Folder log tidak dapat dibuka.');
      setEngineStatus('failed');
    }
  }

  async function handleCancelAndClose() {
    setShowCloseDialog(false);
    try {
      await cancelActiveJobAndClose(activeJobId);
    } catch (error) {
      console.error('Gagal membatalkan dan menutup aplikasi:', error);
      void logWindowEvent(`cancel_and_close_error ${String(error)}`);
      setShowCloseDialog(true);
    }
  }

  const handlePdfJobStateChange = useCallback((state: { activeJobId: string | null; isConversionRunning: boolean }) => {
    setActiveJobId(state.activeJobId);
    setIsConversionRunning(state.isConversionRunning);
  }, []);

  function renderPage() {
    if (activePage === 'home') return <HomePage onNavigate={setActivePage} />;
    if (activePage === 'pdf') {
      return (
        <PdfToJpgPage
          isEngineReady={engineStatus === 'ready'}
          settings={settings}
          onJobStateChange={handlePdfJobStateChange}
        />
      );
    }
    if (activePage === 'image') {
      return (
        <ImageToPdfPage
          isEngineReady={engineStatus === 'ready'}
          settings={settings}
          onJobStateChange={handlePdfJobStateChange}
        />
      );
    }
    if (activePage === 'image-conv') {
      return (
        <ImageConversionPage />
      );
    }
    if (activePage === 'engine') {
      return (
        <EngineCheckPage
          status={engineStatus}
          health={health}
          message={message}
          onCheck={handleCheckEngine}
          onOpenLogFolder={handleOpenLogFolder}
        />
      );
    }
    if (activePage === 'history') return <HistoryPage />;
    if (activePage === 'settings') {
      return (
        <SettingsPage
          settings={settings}
          usingFallback={usingFallback}
          onPreviewTheme={previewTheme}
          onSave={saveSettings}
        />
      );
    }
    return <ComingSoonPage title={meta.title} description={meta.description} onNavigate={setActivePage} />;
  }

  return (
    <>
      <AppShell
        activePage={activePage}
        title={meta.title}
        eyebrow={meta.eyebrow}
        engineStatus={statusForShell}
        theme={theme}
        navigationItems={navigationItems}
        onThemeChange={(next) => void persistTheme(next)}
        onNavigate={setActivePage}
      >
        {renderPage()}
      </AppShell>

      {showCloseDialog ? (
        <div className="app-modal-root" role="presentation">
          <section className="app-modal" role="dialog" aria-modal="true" aria-labelledby="close-dialog-title">
            <h2 id="close-dialog-title">Konversi masih berjalan</h2>
            <p>Menutup aplikasi akan membatalkan proses yang sedang berjalan. File yang sudah selesai tetap tersimpan.</p>
            <div className="button-row" style={{ justifyContent: 'flex-end', marginTop: 24 }}>
              <button type="button" className="secondary-button" onClick={() => setShowCloseDialog(false)}>
                Lanjutkan Konversi
              </button>
              <button type="button" className="primary-button" onClick={handleCancelAndClose}>
                Batalkan dan Tutup
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </>
  );
}
