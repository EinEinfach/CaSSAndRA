import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { LivePlan } from '#features/tasks/livePlan.svelte.ts';
import MowPlanner from '#features/tasks/MowPlanner.svelte';
import type { Plan } from '#features/tasks/types.ts';
import { parameters, plan, task } from './fixtures.ts';

function setup(opts: { plan?: Plan | null; open?: boolean; hasMap?: boolean } = {}) {
	const live = new LivePlan();
	live.session.useDefaults(parameters());
	if (opts.open ?? true) live.start();
	const actions = {
		preview: vi.fn(async () => {}),
		discard: vi.fn(async () => {})
	};
	render(MowPlanner, {
		live,
		plan: opts.plan ?? null,
		tasks: [task('t1', 'Front'), task('t2', 'Back')],
		mowSpeedMps: 0.25,
		playLabel: 'Mow: the drawn area',
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

	it('tells what the play button does', () => {
		setup();
		expect(screen.getByRole('status').textContent).toBe('▶ mows the drawn area');
	});

	it('shows the calculated route and whether it fits the choice', async () => {
		setup({ plan: plan({ taskIds: ['t1'] }) });
		expect(screen.getByLabelText('Planned route').textContent).toContain('1.4 km');
		expect(screen.getByText(/changed since/)).toBeTruthy();
	});

	it('shows why the calculation failed', async () => {
		const { preview } = setup();
		preview.mockRejectedValueOnce(new Error('no active map'));
		await userEvent.click(button('Calculate route'));
		expect((await screen.findByRole('alert')).textContent).toBe('no active map');
	});

	it('discards the route', async () => {
		const { discard } = setup({ plan: plan() });
		await userEvent.click(button('Discard route'));
		expect(discard).toHaveBeenCalledOnce();
	});
});
