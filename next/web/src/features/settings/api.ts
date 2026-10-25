// Settings API (settings/api.go).
import { getJSON, sendJSON } from '#shared/api.ts';
import type { BrokerStatus, SettingsUpdate, SettingsView } from './types.ts';

export const fetchSettings = (fetchFn: typeof fetch = fetch) =>
	getJSON<SettingsView>('/api/settings', fetchFn);

export async function saveSettings(
	update: SettingsUpdate,
	fetchFn: typeof fetch = fetch
): Promise<SettingsView> {
	return (await sendJSON<SettingsView>('PUT', '/api/settings', update, fetchFn))!;
}

export const fetchBrokerStatus = (fetchFn: typeof fetch = fetch) =>
	getJSON<BrokerStatus>('/api/broker', fetchFn);

/** Sends a test message with the saved settings; returns the Telegram chat id found on the way. */
export async function sendTestMessage(fetchFn: typeof fetch = fetch): Promise<string> {
	const res = await sendJSON<{ telegramChatId: string }>(
		'POST',
		'/api/notify/test',
		undefined,
		fetchFn
	);
	return res?.telegramChatId ?? '';
}
