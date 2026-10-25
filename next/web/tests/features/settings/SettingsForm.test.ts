import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import SettingsForm from '#features/settings/SettingsForm.svelte';
import type { BrokerStatus, SettingsUpdate, SettingsView } from '#features/settings/types.ts';
import { view } from './fixtures.ts';

function setup(
	save = vi.fn(async (u: SettingsUpdate): Promise<SettingsView> => ({
		...view(),
		settings: u.settings
	}))
) {
	render(SettingsForm, {
		load: async () => view(),
		save,
		loadBroker: async () => stopped,
		brokerRefreshMs: 0
	});
	return save;
}

const stopped: BrokerStatus = { enabled: false, running: false, port: 1883, clients: 0, error: '' };

describe('SettingsForm', () => {
	it('shows the loaded settings and the fields of the connection', async () => {
		setup();
		expect(((await screen.findByLabelText('Robot URL')) as HTMLInputElement).value).toBe(
			'http://192.168.1.50'
		);
		expect((screen.getByRole('radio', { name: /WiFi/ }) as HTMLInputElement).checked).toBe(true);
		expect(screen.queryByLabelText('Broker')).toBeNull();
	});

	it('switches the connection fields', async () => {
		setup();
		await userEvent.click(await screen.findByRole('radio', { name: /MQTT/ }));
		expect(screen.getByLabelText('Broker')).toBeTruthy();
		expect(screen.queryByLabelText('Robot URL')).toBeNull();
	});

	it('offers to save only after a change and sends it', async () => {
		const save = setup();
		const speed = (await screen.findByLabelText(/Mow speed/)) as HTMLInputElement;
		expect(screen.queryByRole('button', { name: 'Save' })).toBeNull();

		await userEvent.clear(speed);
		await userEvent.type(speed, '0.4');
		await userEvent.click(screen.getByRole('button', { name: 'Save' }));

		expect(save).toHaveBeenCalledOnce();
		expect(save.mock.calls[0][0].settings.rover.mowSpeedMps).toBe(0.4);
		expect(save.mock.calls[0][0].passwords).toEqual({});
		expect((await screen.findByRole('status')).textContent).toBe('Saved');
		expect(screen.queryByRole('button', { name: 'Save' })).toBeNull();
	});

	it('chooses the robot picture and its size', async () => {
		const save = setup();
		await userEvent.click(await screen.findByRole('radio', { name: 'Alfred' }));
		const size = screen.getByLabelText(/Size/) as HTMLInputElement;
		await userEvent.clear(size);
		await userEvent.type(size, '130');
		await userEvent.click(screen.getByRole('button', { name: 'Save' }));

		expect(save.mock.calls[0][0].settings.appearance).toEqual({
			robotPicture: 'alfred',
			robotSizeCm: 130
		});
	});

	it('keeps a set password unless one is typed or removed', async () => {
		const save = setup();
		const pw = (await screen.findByLabelText('Robot password')) as HTMLInputElement;
		expect(pw.value).toBe('');
		expect(pw.placeholder).toContain('unchanged');

		await userEvent.click(screen.getByLabelText('Remove robot password'));
		expect(pw.disabled).toBe(true);
		await userEvent.click(screen.getByRole('button', { name: 'Save' }));
		expect(save.mock.calls[0][0].passwords).toEqual({ httpPassword: 0 });
	});

	it('discards changes', async () => {
		setup();
		const url = (await screen.findByLabelText('Robot URL')) as HTMLInputElement;
		await userEvent.type(url, '1');
		await userEvent.click(screen.getByRole('button', { name: 'Discard' }));
		expect(url.value).toBe('http://192.168.1.50');
		expect(screen.queryByRole('button', { name: 'Save' })).toBeNull();
	});

	it('shows save errors and keeps the changes', async () => {
		setup(
			vi.fn().mockRejectedValue(new Error('/api/settings: invalid settings: rover.mowSpeedMps'))
		);
		const speed = (await screen.findByLabelText(/Mow speed/)) as HTMLInputElement;
		await userEvent.clear(speed);
		await userEvent.type(speed, '5');
		await userEvent.click(screen.getByRole('button', { name: 'Save' }));
		expect((await screen.findByRole('alert')).textContent).toContain('rover.mowSpeedMps');
		expect(speed.value).toBe('5');
	});

	it('shows load errors', async () => {
		render(SettingsForm, {
			load: () => Promise.reject(new Error('offline')),
			loadBroker: async () => stopped,
			brokerRefreshMs: 0
		});
		expect((await screen.findByRole('alert')).textContent).toBe('offline');
	});

	it('shows coordinates only for absolute positioning and API fields only when enabled', async () => {
		setup();
		await screen.findByLabelText(/Mow speed/);
		expect(screen.queryByLabelText('Longitude')).toBeNull();
		await userEvent.click(screen.getByLabelText(/Absolute position/));
		expect(screen.getByLabelText('Longitude')).toBeTruthy();

		expect(screen.queryByLabelText(/Server name/)).toBeNull();
		await userEvent.click(screen.getByLabelText('MQTT API enabled'));
		expect(screen.getByLabelText(/Server name/)).toBeTruthy();
	});

	it('runs the built-in broker and lets the API use it', async () => {
		const save = setup();
		await userEvent.click(await screen.findByLabelText('Broker enabled'));
		await userEvent.clear(screen.getByLabelText('Port'));
		await userEvent.type(screen.getByLabelText('Port'), '1884');
		await userEvent.type(screen.getByLabelText('Broker password'), 'mow-the-lawn');
		await userEvent.click(screen.getByLabelText('MQTT API enabled'));
		await userEvent.click(screen.getByLabelText('Built-in broker'));
		expect(screen.queryByLabelText('Broker')).toBeNull(); // the URL of another broker
		await userEvent.click(screen.getByRole('button', { name: 'Save' }));

		const u = save.mock.calls[0][0];
		expect(u.settings.broker).toEqual({
			enabled: true,
			port: 1884,
			user: 'cassandra',
			password: ''
		});
		expect(u.settings.api).toMatchObject({ enabled: true, useBuiltinBroker: true });
		expect(u.passwords.brokerPassword).toBe('mow-the-lawn');
	});

	it('shows whether the broker runs', async () => {
		const status = (b: Partial<BrokerStatus>) => async () => ({ ...stopped, enabled: true, ...b });
		render(SettingsForm, {
			load: async () => view(),
			loadBroker: status({ running: true, clients: 2 }),
			brokerRefreshMs: 0
		});
		expect(
			(await screen.findByTestId('broker-status')).textContent?.replace(/\s+/g, ' ').trim()
		).toBe('Running on port 1883 · 2 clients connected');
	});

	it('says why the broker does not run', async () => {
		render(SettingsForm, {
			load: async () => view(),
			loadBroker: async () => ({
				...stopped,
				enabled: true,
				error: 'broker: port 1883: address already in use'
			}),
			brokerRefreshMs: 0
		});
		expect((await screen.findByTestId('broker-status')).textContent).toContain(
			'Not running: broker: port 1883: address already in use'
		);
	});
});
