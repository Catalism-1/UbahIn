import { useEffect, useState } from 'react';
import { Toast } from '../components/common/Toast';
import { useToasts } from '../hooks/useToasts';
import { getRecentHistory, openHistoryOutputDirectory } from '../services/history';
import type { HistoryItem } from '../types/history';
import type { PageId } from '../types/navigation';
import { formatDateTime, statusMeta, toolLabel } from '../utils/historyFormat';
import './pages.css';

interface HomePageProps {
  onNavigate: (page: PageId) => void;
}

const tools: Array<{
  id: PageId;
  title: string;
  description: string;
  tint: string;
  icon: string;
  badge: string;
  muted?: boolean;
}> = [
  { id: 'pdf', title: 'PDF ke JPG', description: 'Ubah setiap halaman PDF menjadi gambar JPG.', tint: 'var(--blue)', icon: 'PDF', badge: 'Siap dipakai' },
  { id: 'image', title: 'Gambar ke PDF', description: 'Gabungkan gambar menjadi dokumen PDF.', tint: 'var(--sage)', icon: 'IMG', badge: 'Siap dipakai' },
  { id: 'heic', title: 'HEIC ke JPG / PNG', description: 'Ubah foto HEIC menjadi JPG atau PNG secara offline.', tint: 'var(--peach)', icon: 'HEIC', badge: 'Siap dipakai' },
  { id: 'merge-pdf', title: 'Gabungkan PDF', description: 'Satukan beberapa PDF dalam satu file.', tint: 'var(--lavender)', icon: 'PDF', badge: 'Segera hadir', muted: true },
  { id: 'compress-pdf', title: 'Kompres PDF', description: 'Kecilkan ukuran PDF untuk dibagikan.', tint: 'var(--peach)', icon: 'ZIP', badge: 'Segera hadir', muted: true },
  { id: 'resize-image', title: 'Ubah Ukuran Gambar', description: 'Atur ulang dimensi gambar lokal.', tint: 'var(--pink)', icon: 'PX', badge: 'Segera hadir', muted: true },
  { id: 'pdf-word', title: 'PDF ke Word', description: 'Ekspor konten PDF ke dokumen Word.', tint: 'var(--blue)', icon: 'DOC', badge: 'Segera hadir', muted: true },
];

export function HomePage({ onNavigate }: HomePageProps) {
  const [recents, setRecents] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const { toasts, addToast } = useToasts();

  useEffect(() => {
    let active = true;
    getRecentHistory(5)
      .then((items) => {
        if (active) setRecents(items);
      })
      .catch((error) => {
        // Beranda tidak boleh crash bila engine belum siap.
        console.error('Gagal memuat riwayat terbaru:', error);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleOpenFolder(item: HistoryItem) {
    try {
      await openHistoryOutputDirectory(item.id);
    } catch (error) {
      addToast(
        'Tidak dapat membuka folder.',
        'warning',
        error instanceof Error ? error.message : 'Folder hasil tidak ditemukan.',
      );
    }
  }

  return (
    <div className="page">
      <section className="hero-panel">
        <h2>Halo, mau ubah file apa hari ini?</h2>
        <p>Pilih alat yang kamu butuhkan. Semua proses dilakukan langsung di laptopmu.</p>
      </section>

      <section className="page">
        <div className="section-title">
          <div>
            <h3>Alat</h3>
            <p>Pilih alat untuk mulai mengubah file.</p>
          </div>
        </div>
        <div className="tool-grid">
          {tools.map((tool) => (
            <button key={tool.id} type="button" className="tool-card" onClick={() => onNavigate(tool.id)}>
              <span className="tool-icon" style={{ background: tool.tint }}>
                {tool.icon}
              </span>
              <div>
                <h3>{tool.title}</h3>
                <p>{tool.description}</p>
              </div>
              <span className={tool.muted ? 'badge muted' : 'badge'}>{tool.badge}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="page">
        <div className="section-title">
          <div>
            <h3>Terakhir digunakan</h3>
            <p>Aktivitas konversi terbaru kamu.</p>
          </div>
          {recents.length > 0 ? (
            <button type="button" className="secondary-button" onClick={() => onNavigate('history')}>
              Lihat Semua
            </button>
          ) : null}
        </div>

        {loading ? (
          <div className="notice">Memuat aktivitas…</div>
        ) : recents.length === 0 ? (
          <div className="recent-empty">
            <p>Belum ada aktivitas. Riwayat konversi akan muncul di sini setelah kamu menggunakan Ubahin.</p>
          </div>
        ) : (
          <div className="recent-list">
            {recents.map((recent) => {
              const status = statusMeta(recent.status);
              return (
                <div key={recent.id} className="recent-item">
                  <span className={`recent-mark ${status.tone}`} aria-hidden="true" />
                  <div>
                    <strong>{toolLabel(recent.tool_type)}</strong>
                    <span title={recent.primary_filename}>
                      {recent.primary_filename || 'Tanpa nama file'} · {status.label}
                    </span>
                  </div>
                  <div className="recent-trailing">
                    <time>{formatDateTime(recent.created_at)}</time>
                    {recent.output_count > 0 ? (
                      <button type="button" className="ghost-button" onClick={() => handleOpenFolder(recent)}>
                        Buka
                      </button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <Toast messages={toasts} />
    </div>
  );
}
