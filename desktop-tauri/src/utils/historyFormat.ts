import type { HistoryStatus } from '../types/history';

const TOOL_LABELS: Record<string, string> = {
  pdf_to_jpg: 'PDF ke JPG',
  image_to_pdf: 'Gambar ke PDF',
  heic_to_image: 'HEIC ke JPG / PNG',
  merge_pdf: 'Gabungkan PDF',
  split_pdf: 'Pisahkan PDF',
  compress_pdf: 'Kompres PDF',
  image_convert: 'Konversi Gambar',
  image_resize: 'Ubah Ukuran Gambar',
  image_compress: 'Kompres Gambar',
};

export function toolLabel(toolType: string): string {
  return TOOL_LABELS[toolType] ?? toolType;
}

export type StatusTone = 'success' | 'warning' | 'error' | 'muted';

interface StatusMeta {
  label: string;
  tone: StatusTone;
}

const STATUS_META: Record<HistoryStatus, StatusMeta> = {
  completed: { label: 'Berhasil', tone: 'success' },
  completed_with_warnings: { label: 'Selesai dengan peringatan', tone: 'warning' },
  failed: { label: 'Gagal', tone: 'error' },
  cancelled: { label: 'Dibatalkan', tone: 'muted' },
};

export function statusMeta(status: HistoryStatus): StatusMeta {
  return STATUS_META[status] ?? { label: status, tone: 'muted' };
}

const dateFormatter = new Intl.DateTimeFormat('id-ID', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

export function formatDateTime(iso: string | null): string {
  if (!iso) return '-';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '-';
  return dateFormatter.format(date);
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds) || seconds < 0) return '-';
  if (seconds < 60) {
    return `${seconds.toFixed(seconds < 10 ? 1 : 0)} detik`;
  }
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return rest > 0 ? `${minutes} mnt ${rest} dtk` : `${minutes} mnt`;
}

export function formatOutputCount(count: number): string {
  return `${count} hasil`;
}
