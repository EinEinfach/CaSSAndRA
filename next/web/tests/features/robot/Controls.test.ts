import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import Controls from '#features/robot/Controls.svelte';

const button = (name: string) => screen.getByRole('button', { name }) as HTMLButtonElement;

describe('Controls', () => {
	it('sends the clicked command', async () => {
		const send = vi.fn<(name: string) => Promise<void>>(async () => {});
		render(Controls, { status: 'idle', send });

		await userEvent.click(button('Mow'));
		await userEvent.click(button('Dock'));
		await userEvent.click(button('Stop'));

		expect(send.mock.calls.map((c) => c[0])).toEqual(['mow', 'dock', 'stop']);
	});

	it.each([
		['idle', false, false, false],
		['mow', true, false, false],
		['charging', false, false, true],
		['offline', true, true, true]
	] as const)('in status %s disables mow %s, stop %s, dock %s', (status, mow, stop, dock) => {
		render(Controls, { status, send: vi.fn() });
		expect(button('Mow').disabled).toBe(mow);
		expect(button('Stop').disabled).toBe(stop);
		expect(button('Dock').disabled).toBe(dock);
	});

	it('keeps Stop available while another command runs', async () => {
		let finish: () => void = () => {};
		const send = vi.fn((name: string) =>
			name === 'mow' ? new Promise<void>((resolve) => (finish = resolve)) : Promise.resolve()
		);
		render(Controls, { status: 'idle', send });

		await userEvent.click(button('Mow'));
		expect(button('Mow').disabled).toBe(true);
		expect(button('Dock').disabled).toBe(true);
		expect(button('Stop').disabled).toBe(false);

		await userEvent.click(button('Stop'));
		expect(send).toHaveBeenLastCalledWith('stop');
		finish();
	});

	it('shows errors and clears them on the next command', async () => {
		const send = vi
			.fn()
			.mockRejectedValueOnce(new Error('/api/robot/dock: robot offline'))
			.mockResolvedValue(undefined);
		render(Controls, { status: 'idle', send });

		await userEvent.click(button('Dock'));
		expect((await screen.findByRole('alert')).textContent).toBe('/api/robot/dock: robot offline');

		await userEvent.click(button('Stop'));
		expect(screen.queryByRole('alert')).toBeNull();
	});
});
