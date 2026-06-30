import type { EngineResponse } from '../types/engine';
import type { HistoryFilter, HistoryItem, HistoryListResponse } from '../types/history';
import { parseHistoryList, parseRecentItems } from '../types/history';
import { invokeWithTimeout, unwrapEngineResponse } from './transport';

export interface ListHistoryParams {
  limit?: number;
  offset?: number;
  status?: HistoryFilter;
  toolType?: string;
}

export async function listHistory(params: ListHistoryParams = {}): Promise<HistoryListResponse> {
  const payload = {
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
    status: params.status ?? 'all',
    tool_type: params.toolType ?? 'all',
  };
  const response = await invokeWithTimeout<EngineResponse<unknown>>('list_history', { payload }, 12000);
  return parseHistoryList(unwrapEngineResponse(response));
}

export async function getRecentHistory(limit = 5): Promise<HistoryItem[]> {
  const response = await invokeWithTimeout<EngineResponse<unknown>>('get_recent_history', { payload: { limit } }, 10000);
  return parseRecentItems(unwrapEngineResponse(response));
}

export async function deleteHistoryItem(historyId: string): Promise<void> {
  const response = await invokeWithTimeout<EngineResponse<unknown>>(
    'delete_history_item',
    { payload: { history_id: historyId } },
    10000,
  );
  unwrapEngineResponse(response);
}

export async function clearHistory(): Promise<void> {
  const response = await invokeWithTimeout<EngineResponse<unknown>>(
    'clear_history',
    { payload: { scope: 'all' } },
    10000,
  );
  unwrapEngineResponse(response);
}

/** Membuka folder hasil sebuah record. Rust melempar pesan bila folder hilang. */
export async function openHistoryOutputDirectory(historyId: string): Promise<void> {
  await invokeWithTimeout<void>('open_history_output_directory', { payload: { history_id: historyId } }, 10000);
}
