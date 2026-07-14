import type { PageId } from '../types/navigation';
import './pages.css';

interface ComingSoonPageProps {
  title: string;
  description: string;
  onNavigate: (page: PageId) => void;
}

export function ComingSoonPage({ title, description, onNavigate }: ComingSoonPageProps) {
  return (
    <div className="page">
      <section className="empty-card">
        <span className="badge">Segera hadir</span>
        <span className="empty-icon" aria-hidden="true">
          U
        </span>
        <h2>{title}</h2>
        <p>{description}</p>
        <div className="button-row" style={{ marginTop: 20 }}>
          <button type="button" className="primary-button" onClick={() => onNavigate('home')}>
            Kembali ke Beranda
          </button>
        </div>
      </section>
    </div>
  );
}
