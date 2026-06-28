export type HistoryStatus = 'completed' | 'completed_with_warnings' | 'failed' | 'cancelled';

/** Filter UI Riwayat: "completed" mencakup juga selesai dengan peringatan. */
export type HistoryFilter = 'all' | 'completed' | 'failed' | 'cancelled';

export interface HistoryItem {
  id: string;
  tool_type: string;
  status: HistoryStatus;
  created_at: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  primary_filename: string;
  input_count: number;
  output_count: number;
  output_directory: string;
  input_size_bytes: number;
  output_size_bytes: number;
  error_summary: string;
  warning_count: number;
}

export interface HistoryListResponse {
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

const STATUS_VALUES: readonly HistoryStatus[] = ['completed', 'completed_with_warnings', 'failed', 'cancelled'];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function asNullableString(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function asNullableNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function asStatus(value: unknown): HistoryStatus {
  return typeof value === 'string' && (STATUS_VALUES as readonly string[]).includes(value)
    ? (value as HistoryStatus)
    : 'completed';
}

/** Type guard + parser untuk satu item riwayat. Mengembalikan null jika tak valid. */
export function parseHistoryItem(raw: unknown): HistoryItem | null {
  if (!isRecord(raw)) return null;
  if (typeof raw.id !== 'string' || raw.id.length === 0) return null;
  return {
    id: raw.id,
    tool_type: asString(raw.tool_type, 'unknown'),
    status: asStatus(raw.status),
    created_at: asNullableString(raw.created_at),
    started_at: asNullableString(raw.started_at),
    ended_at: asNullableString(raw.ended_at),
    duration_seconds: asNullableNumber(raw.duration_seconds),
    primary_filename: asString(raw.primary_filename),
    input_count: asNumber(raw.input_count),
    output_count: asNumber(raw.output_count),
    output_directory: asString(raw.output_directory),
    input_size_bytes: asNumber(raw.input_size_bytes),
    output_size_bytes: asNumber(raw.output_size_bytes),
    error_summary: asString(raw.error_summary),
    warning_count: asNumber(raw.warning_count),
  };
}

function parseItems(value: unknown): HistoryItem[] {
  if (!Array.isArray(value)) return [];
  const result: HistoryItem[] = [];
  for (const entry of value) {
    const item = parseHistoryItem(entry);
    if (item) result.push(item);
  }
  return result;
}

export function parseHistoryList(raw: unknown): HistoryListResponse {
  if (!isRecord(raw)) {
    return { items: [], total: 0, limit: 50, offset: 0, has_more: false };
  }
  const items = parseItems(raw.items);
  return {
    items,
    total: asNumber(raw.total, items.length),
    limit: asNumber(raw.limit, 50),
    offset: asNumber(raw.offset, 0),
    has_more: typeof raw.has_more === 'boolean' ? raw.has_more : false,
  };
}

export function parseRecentItems(raw: unknown): HistoryItem[] {
  if (isRecord(raw)) return parseItems(raw.items);
  return [];
}
