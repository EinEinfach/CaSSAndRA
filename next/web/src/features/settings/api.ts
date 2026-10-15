// Settings API (settings/api.go).
import { getJSON, sendJSON } from '#shared/api.ts';
import type { SettingsUpdate, SettingsView } from './types.ts';

export const fetchSettings = (fetchFn: typeof fetch = fetch) =>
	getJSON<SettingsView>('/api/settings', fetchFn);

export async function saveSettings(
	update: SettingsUpdate,
	fetchFn: typeof fetch = fetch
): Promise<SettingsView> {
	return (await sendJSON<SettingsView>('PUT', '/api/settings', update, fetchFn))!;
}
