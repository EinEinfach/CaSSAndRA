import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { RobotStatus } from '#features/robot/types.ts';
import { LivePlan } from '#features/tasks/livePlan.svelte.ts';
import MowPlanner from '#features/tasks/MowPlanner.svelte';
import type { Plan } from '#features/tasks/types.ts';
import { parameters, plan, task } from './fixtures.ts';

function setup(
	opts: { plan?: Plan | null; status?: RobotStatus; open?: boolean; hasMap?: boolean } = {}
) {
	const live = new LivePlan();
	live.session.useDefaults(parameters());
	if (opts.open ?? true) live.start();
	const actions = {
		preview: vi.fn(async () => {}),
		start: vi.fn(async () => {}),
		discard: vi.fn(async () => {})
	};
	render(MowPlanner, {
		live,
		plan: opts.plan ?? null,
		tasks: [task('t1', 'Front'), task('t2', 'Back')],
		mowSpeedMps: 0.25,
		status: opts.status ?? 'docked',
		hasMap: opts.hasMap ?? true,
		...actions
	});
	return { live, ...actions };
}

const button = (name: string) => screen.getByRole('button', { name }) as HTMLButtonElement;

describe('MowPlanner', () => {
	it('opens only with an active map', async () => {
		const { live } = setup({ open: false, hasMap: false });
		expect(button('Plan mowing').disabled).toBe(true);
		expect(screen.getByText(/under Maps/)).toBeTruthy();
		expect(live.open).toBe(false);
	});

	it('calculates the whole garden with the changed mow settings', async () => {
		const { preview } = setup();
		await userEvent.click(screen.getByText('Mow settings'));
		await userEvent.click(screen.getByRole('radio', { name: 'Squares' }));
		await userEvent.click(button('Calculate route'));
		expect(preview).toHaveBeenCalledWith({
			parts: [{ selection: [], parameters: parameters({ pattern: 'squares' }) }]
		});
	});

	it('waits for an area to be drawn', async () => {
		const { preview } = setup();
		await userEvent.click(screen.getByRole('radio', { name: 'Rectangle' }));
		expect(button('Calculate route').disabled).toBe(true);
		expect(screen.getByText(/Draw the area/)).toBeTruthy();
		expect(preview).not.toHaveBeenCalled();
	});

	it('plans saved tasks in the chosen order', async () => {
		const { preview } = setup();
		await userEvent.click(screen.getByRole('radio', { name: 'Saved tasks' }));
		expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull();
		await userEvent.click(screen.getByLabelText('Mow Back'));
		await userEvent.click(screen.getByLabelText('Mow Front'));
		await userEvent.click(button('Calculate route'));
		expect(preview).toHaveBeenCalledWith({ taskIds: ['t2', 't1'] });
	});

	it('starts the calculated route and closes', async () => {
		const { start, live } = setup({ plan: plan() });
		expect(screen.getByLabelText('Planned route').textContent).toContain('1.4 km');
		await userEvent.click(button('Start mowing'));
		expect(start).toHaveBeenCalledOnce();
		expect(live.open).toBe(false);
	});

	it('does not start a route for another choice', async () => {
		setup({ plan: plan({ taskIds: ['t1'] }) });
		expect(button('Start mowing').disabled).toBe(true);
		expect(screen.getByText(/changed since/)).toBeTruthy();
	});

	it('starts only while the robot stands still', () => {
		setup({ plan: plan(), status: 'mow' });
		expect(button('Start mowing').disabled).toBe(true);
		expect(screen.getByText(/idle or in the dock/)).toBeTruthy();
	});

	it('shows why the start failed and stays open', async () => {
		const { start, live } = setup({ plan: plan() });
		start.mockRejectedValueOnce(new Error('map changed'));
		await userEvent.click(button('Start mowing'));
		expect((await screen.findByRole('alert')).textContent).toBe('map changed');
		expect(live.open).toBe(true);
	});

	it('discards the route', async () => {
		const { discard } = setup({ plan: plan() });
		await userEvent.click(button('Discard'));
		expect(discard).toHaveBeenCalledOnce();
	});
});
