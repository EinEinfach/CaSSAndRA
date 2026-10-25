import { describe, expect, it, vi } from 'vitest';
import {
	fetchBrokerStatus,
	fetchSettings,
	saveSettings,
	sendTestMessage
} from '#features/settings/api.ts';
import { view } from './fixtures.ts';

const respond = (status: number, body: unknown) =>
	vi.fn(async () => new Response(JSON.stringify(body), { status }));

describe('settings api', () => {
	it('loads the settings', async () => {
		const fetchFn = respond(200, view());
		await expect(fetchSettings(fetchFn)).resolves.toEqual(view());
		expect(fetchFn).toHaveBeenCalledWith('/api/settings', expect.anything());
	});

	it('asks how the built-in broker is doing', async () => {
		const status = { enabled: true, running: true, port: 1883, clients: 1, error: '' };
		const fetchFn = respond(200, status);
		await expect(fetchBrokerStatus(fetchFn)).resolves.toEqual(status);
		expect(fetchFn).toHaveBeenCalledWith('/api/broker', expect.anything());
	});

	it('sends a test message', async () => {
		const fetchFn = respond(200, { telegramChatId: '4242' });
		await expect(sendTestMessage(fetchFn)).resolves.toBe('4242');
		expect(fetchFn).toHaveBeenCalledWith(
			'/api/notify/test',
			expect.objectContaining({ method: 'POST' })
		);
		await expect(
			sendTestMessage(respond(502, { error: 'telegram: chat not found' }))
		).rejects.toThrow('chat not found');
	});

	it('saves with PUT and returns the new view', async () => {
		const fetchFn = respond(200, view());
		const update = { settings: view().settings, passwords: { mqttPassword: 'x' } };
		await expect(saveSettings(update, fetchFn)).resolves.toEqual(view());
		expect(fetchFn).toHaveBeenCalledWith(
			'/api/settings',
			expect.objectContaining({ method: 'PUT', body: JSON.stringify(update) })
		);
	});

	it('reports validation errors', async () => {
		const fetchFn = respond(400, { error: 'invalid settings: rover.mowSpeedMps' });
		await expect(
			saveSettings({ settings: view().settings, passwords: {} }, fetchFn)
		).rejects.toThrow('rover.mowSpeedMps');
	});
});
