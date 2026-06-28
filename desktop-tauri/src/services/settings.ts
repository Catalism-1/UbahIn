import type { EngineResponse } from '../types/engine';
import type { AppSettings, SaveSettingsPayload } from '../types/settings';
import { parseAppSettings } from '../types/settings';
import { invokeWithTimeout, unwrapEngineResponse } from './transport';

export async function getSettings(): Promise<AppSettings> {
  const response = await invokeWithTimeout<EngineResponse<unknown>>('get_settings', undefined, 10000);
  return parseAppSettings(unwrapEngineResponse(response));
}

export async function saveSettings(payload: SaveSettingsPayload): Promise<AppSettings> {
  const response = await invokeWithTimeout<EngineResponse<unknown>>('save_settings', { payload }, 10000);
  return parseAppSettings(unwrapEngineResponse(response));
}

export async function selectDefaultOutputDirectory(): Promise<string | null> {
  return invokeWithTimeout<string | null>('select_default_output_directory', undefined, 60000);
}
