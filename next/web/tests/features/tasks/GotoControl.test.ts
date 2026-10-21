import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import GotoControl from '#features/tasks/GotoControl.svelte';
import { GotoPicker } from '#features/tasks/goto.svelte.ts';
import type { RobotStatus } from '#features/robot/types.ts';

function setup(status: RobotStatus = 'idle') {
	const picker = new GotoPicker();
	const send = vi.fn(async () => {});
	const result = render(GotoControl, { picker, status, send });
	return { picker, send, ...result };
}

const button = (name: string) => screen.getByRole('button', { name }) as HTMLButtonElement;

describe('GotoControl', () => {
	it('drives only after a goal is picked and confirmed', async () => {
		const { picker, send } = setup();
		await userEvent.click(button('Go to a point'));
		expect(screen.getByRole('status').textContent).toContain('Tap the map');
		expect(button('Drive there').disabled).toBe(true);

		picker.interact.tap!({ x: 4, y: 2.5 }, 0.01);
		await vi.waitFor(() => expect(screen.getByRole('status').textContent).toContain('4.00, 2.50'));
		expect(send).not.toHaveBeenCalled();
		await userEvent.click(button('Drive there'));
		expect(send).toHaveBeenCalledWith({ x: 4, y: 2.5 });
		expect(picker.picking).toBe(false);
	});

	it('cancels without sending', async () => {
		const { picker, send } = setup();
		await userEvent.click(button('Go to a point'));
		picker.interact.tap!({ x: 4, y: 2 }, 0.01);
		await userEvent.click(button('Cancel'));
		expect(send).not.toHaveBeenCalled();
		expect(picker.goal).toBeNull();
	});

	it('is not offered while the robot is busy', async () => {
		const { rerender } = setup('mow');
		expect(button('Go to a point').disabled).toBe(true);
		await rerender({ status: 'docked' });
		expect(button('Go to a point').disabled).toBe(false);
	});

	it('keeps the goal and shows why the robot did not drive', async () => {
		const { picker } = setup();
		const send = vi.fn(async () => Promise.reject(new Error('the robot cannot drive there')));
		render(GotoControl, { picker, status: 'idle', send });
		picker.start();
		picker.interact.tap!({ x: 1, y: 1 }, 0.01);
		await vi.waitFor(() =>
			expect(screen.getAllByRole('button', { name: 'Drive there' })).toHaveLength(2)
		);
		await userEvent.click(screen.getAllByRole('button', { name: 'Drive there' })[1]);
		expect(screen.getByRole('alert').textContent).toBe('the robot cannot drive there');
		expect(picker.goal).toEqual({ x: 1, y: 1 });
	});
});
