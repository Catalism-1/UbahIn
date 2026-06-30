import { useCallback, useEffect, useState } from 'react';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { EmptyState } from '../components/common/EmptyState';
import { Toast } from '../components/common/Toast';
import { useToasts } from '../hooks/useToasts';
import { clearHistory, deleteHistoryItem, listHistory, openHistoryOutputDirectory } from '../services/history';
import type { HistoryFilter, HistoryItem } from '../types/history';
import { formatDateTime, formatDuration, statusMeta, toolLabel } from '../utils/historyFormat';
import './pages.css';

const PAGE_SIZE = 50;

const filters: Array<{ value: HistoryFilter; label: string }> = [
  { value: 'all', label: 'Semua' },
  { value: 'completed', label: 'Berhasil' },
  { value: 'failed', label: 'Gagal' },
  { value: 'cancelled', label: 'Dibatalkan' },
];

export function HistoryPage() {
  const [filter, setFilter] = useState<HistoryFilter>('all');
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const { toasts, addToast } = useToasts();

  const load = useCallback(
    async (nextFilter: HistoryFilter, offset: number) => {
      const append = offset > 0;
      if (append) setLoadingMore(true);
      else setLoading(true);
      try {
        const response = await listHistory({ limit: PAGE_SIZE, offset, status: nextFilter });
        setItems((current) => (append ? [...current, ...response.items] : response.items));
        setTotal(response.total);
        setHasMore(response.has_more);
      } catch (error) {
        addToast('Riwayat gagal dimuat.', 'error', error instanceof Error ? error.message : 'Silakan coba lagi.');
        if (!append) {
          setItems([]);
          setTotal(0);
          setHasMore(false);
        }
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [addToast],
  );

  useEffect(() => {
    void load(filter, 0);
  }, [filter, load]);

  function handleFilterChange(next: HistoryFilter) {
    if (next === filter) return;
    setLoading(true);
    setItems([]);
    setFilter(next);
  }

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

  async function handleDelete(item: HistoryItem) {
    try {
      await deleteHistoryItem(item.id);
      setItems((current) => current.filter((entry) => entry.id !== item.id));
      setTotal((current) => Math.max(0, current - 1));
      addToast('Riwayat dihapus.', 'success', 'File hasil tetap tersimpan di foldernya.');
    } catch (error) {
      addToast('Riwayat gagal dihapus.', 'error', error instanceof Error ? error.message : 'Silakan coba lagi.');
    }
  }

  async function handleClearAll() {
    setShowClearConfirm(false);
    try {
      await clearHistory();
      setItems([]);
      setTotal(0);
      setHasMore(false);
      addToast('Semua riwayat dihapus.', 'success', 'File hasil pengguna tidak ikut terhapus.');
    } catch (error) {
      addToast('Riwayat gagal dihapus.', 'error', error instanceof Error ? error.message : 'Silakan coba lagi.');
    }
  }

  const isEmpty = !loading && items.length === 0;

  return (
    <div className="page">
      <div className="section-title">
        <div className="history-filters">
          {filters.map((item) => (
            <button
              key={item.value}
              type="button"
              className={filter === item.value ? 'filter-chip active' : 'filter-chip'}
              onClick={() => handleFilterChange(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>
        {items.length > 0 ? (
          <button type="button" className="secondary-button" onClick={() => setShowClearConfirm(true)}>
            Hapus Riwayat
          </button>
        ) : null}
      </div>

      {loading ? (
        <div className="notice">Memuat riwayat…</div>
      ) : isEmpty ? (
        <EmptyState
          icon="H"
          title="Belum ada aktivitas."
          description="Riwayat konversi akan muncul di sini setelah kamu menggunakan Ubahin."
        />
      ) : (
        <>
          <div className="history-list">
            {items.map((item) => {
              const status = statusMeta(item.status);
              return (
                <article key={item.id} className="history-item">
                  <div className="history-main">
                    <div className="history-heading">
                      <strong>{toolLabel(item.tool_type)}</strong>
                      <span className={`history-badge ${status.tone}`}>{status.label}</span>
                    </div>
                    <span className="history-file" title={item.primary_filename}>
                      {item.primary_filename || 'Tanpa nama file'}
                    </span>
                    <div className="history-meta">
                      <span>{formatDateTime(item.created_at)}</span>
                      <span aria-hidden="true">•</span>
                      <span>{item.output_count} hasil</span>
                      <span aria-hidden="true">•</span>
                      <span>{formatDuration(item.duration_seconds)}</span>
                    </div>
                  </div>
                  <div className="history-actions">
                    <button type="button" className="secondary-button" onClick={() => handleOpenFolder(item)}>
                      Buka Folder
                    </button>
                    <button type="button" className="ghost-button" onClick={() => handleDelete(item)}>
                      Hapus
                    </button>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="history-footer">
            <span className="history-count">
              Menampilkan {items.length} dari {total} riwayat
            </span>
            {hasMore ? (
              <button
                type="button"
                className="secondary-button"
                disabled={loadingMore}
                onClick={() => load(filter, items.length)}
              >
                {loadingMore ? 'Memuat…' : 'Muat Lebih Banyak'}
              </button>
            ) : null}
          </div>
        </>
      )}

      <ConfirmDialog
        open={showClearConfirm}
        title="Hapus semua riwayat?"
        description="Seluruh catatan riwayat akan dihapus. File hasil konversi di foldermu tidak ikut terhapus."
        confirmLabel="Ya, hapus semua"
        cancelLabel="Batal"
        onCancel={() => setShowClearConfirm(false)}
        onConfirm={handleClearAll}
      />

      <Toast messages={toasts} />
    </div>
  );
}
