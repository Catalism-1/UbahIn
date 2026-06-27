import type { PageId } from '../types/navigation';
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
  { id: 'pdf', title: 'PDF ke JPG', description: 'Siapkan alur konversi PDF menjadi gambar.', tint: 'var(--blue)', icon: 'PDF', badge: 'Segera disiapkan' },
  { id: 'image', title: 'Gambar ke PDF', description: 'Gabungkan gambar menjadi dokumen PDF.', tint: 'var(--sage)', icon: 'IMG', badge: 'Segera hadir', muted: true },
  { id: 'merge-pdf', title: 'Gabungkan PDF', description: 'Satukan beberapa PDF dalam satu file.', tint: 'var(--lavender)', icon: 'PDF', badge: 'Segera hadir', muted: true },
  { id: 'compress-pdf', title: 'Kompres PDF', description: 'Kecilkan ukuran PDF untuk dibagikan.', tint: 'var(--peach)', icon: 'ZIP', badge: 'Segera hadir', muted: true },
  { id: 'resize-image', title: 'Ubah Ukuran Gambar', description: 'Atur ulang dimensi gambar lokal.', tint: 'var(--pink)', icon: 'PX', badge: 'Segera hadir', muted: true },
  { id: 'pdf-word', title: 'PDF ke Word', description: 'Ekspor konten PDF ke dokumen Word.', tint: 'var(--blue)', icon: 'DOC', badge: 'Segera hadir', muted: true },
];

const recents = [
  { name: 'Contoh_Laporan.pdf', meta: 'Pemeriksaan engine lokal', when: 'Tahap 2A', tint: 'var(--blue)' },
  { name: 'Folder hasil default', meta: 'Belum dihubungkan ke settings backend', when: 'Placeholder', tint: 'var(--sage)' },
  { name: 'Riwayat konversi', meta: 'Akan muncul setelah converter dipindahkan', when: 'Nanti', tint: 'var(--lavender)' },
];

export function HomePage({ onNavigate }: HomePageProps) {
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
            <p>Fondasi app shell sudah siap, fitur converter menyusul per halaman.</p>
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
            <p>Data sementara sampai history backend dipasang ke React.</p>
          </div>
        </div>
        <div className="recent-list">
          {recents.map((recent) => (
            <div key={recent.name} className="recent-item">
              <span className="recent-mark" style={{ background: recent.tint }} />
              <div>
                <strong>{recent.name}</strong>
                <span>{recent.meta}</span>
              </div>
              <time>{recent.when}</time>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
