import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import CommandInput from '#features/logs/CommandInput.svelte';

function setup(send = vi.fn(async (line: string) => `reply to ${line}`)) {
	render(CommandInput, { send });
	return { send, user: userEvent.setup(), input: screen.getByLabelText('AT command') };
}

const sent = () => within(screen.getByRole('list', { name: 'Sent commands' }));

describe('CommandInput', () => {
	it('sends a command once and shows the reply', async () => {
		const { send, user, input } = setup();
		await user.type(input, 'at+V{Enter}');
		expect(send).toHaveBeenCalledTimes(1);
		expect(send).toHaveBeenCalledWith('AT+V');
		expect(sent().getByText('reply to AT+V')).toBeTruthy();
		expect((input as HTMLInputElement).value).toBe('');
	});

	it('does not send what is not an AT+ command', async () => {
		const { send, user, input } = setup();
		const button = screen.getByRole('button', { name: 'Send' });
		expect((button as HTMLButtonElement).disabled).toBe(true);
		await user.type(input, 'reboot{Enter}');
		expect(send).not.toHaveBeenCalled();
		expect((button as HTMLButtonElement).disabled).toBe(true);
		expect(screen.getByText('Commands start with AT+, e.g. AT+V.')).toBeTruthy();
	});

	it('keeps the line and shows the error when sending fails', async () => {
		const { user, input } = setup(vi.fn(async () => Promise.reject(new Error('robot is offline'))));
		await user.type(input, 'AT+S{Enter}');
		expect(sent().getByText('robot is offline')).toBeTruthy();
		expect((input as HTMLInputElement).value).toBe('AT+S');
	});

	it('shows newest first and an empty reply as such', async () => {
		const { user, input } = setup(vi.fn(async (line: string) => (line === 'AT+Y' ? '' : 'ok')));
		await user.type(input, 'AT+V{Enter}');
		await user.type(input, 'AT+Y{Enter}');
		const items = sent().getAllByRole('listitem');
		expect(items[0].textContent).toContain('AT+Y (no reply)');
		expect(items[1].textContent).toContain('AT+V ok');
	});
});
