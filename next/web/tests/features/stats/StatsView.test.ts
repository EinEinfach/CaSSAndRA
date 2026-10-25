import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StatsView from '#features/stats/StatsView.svelte';
import type { StatsResponse } from '#features/stats/types.ts';
import { response } from './fixtures.ts';

const now = new Date('2026-10-26T09:00:00Z');

function setup(load = vi.fn(async (): Promise<StatsResponse> => response())) {
	render(StatsView, { load, now: () => now, refreshMs: 0 });
	return load;
}

const section = (name: string) => screen.getByRole('heading', { name }).closest('section')!;

beforeEach(() => {
	vi.stubGlobal(
		'ResizeObserver',
		class {
			observe() {}
			unobserve() {}
			disconnect() {}
		}
	);
});
afterEach(() => {
	vi.useRealTimers();
	vi.unstubAllGlobals();
});

describe('StatsView', () => {
	it('loads the last day and shows shares, numbers and charts', async () => {
		const load = setup();
		await screen.findByText('History');
		expect(load).toHaveBeenCalledWith(new Date('2026-10-25T09:00:00Z'), now);

		const time = section('Time');
		expect(within(time).getByText('Mowing').closest('div')!.textContent).toContain('2 h · 67 %');
		expect(within(time).getByText('Charging').closest('div')!.textContent).toContain('1 h · 33 %');
		const gps = section('GPS while mowing');
		expect(within(gps).getByText('Float').closest('div')!.textContent).toContain('10 min · 8 %');
		expect(within(section('Mowing')).getByText('2.5 km')).toBeTruthy();
		expect(within(section('Events')).getByText('Obstacles').closest('div')!.textContent).toContain(
			'3'
		);
		expect(screen.getAllByRole('img').map((e) => e.getAttribute('aria-label'))).toEqual([
			'Battery over time',
			'Current over time',
			'Satellites over time',
			'GPS accuracy over time',
			'Lateral error over time'
		]);
		expect(screen.getByText('26.50 V')).toBeTruthy(); // the latest battery value
	});

	it('loads another time span when chosen', async () => {
		const load = setup();
		await screen.findByText('History');
		await userEvent.click(screen.getByLabelText('7 days'));
		expect(load).toHaveBeenLastCalledWith(new Date('2026-10-19T09:00:00Z'), now);
	});

	it('says when nothing was recorded', async () => {
		setup(vi.fn(async () => response({ samples: [], totals: {} })));
		await screen.findByText('History');
		expect(screen.getAllByText('Nothing recorded in this time span.')).toHaveLength(2);
		expect(screen.getAllByText('No data in this time span.')).toHaveLength(5);
	});

	it('shows why loading failed', async () => {
		setup(vi.fn(async () => Promise.reject(new Error('stats unavailable'))));
		expect((await screen.findByRole('alert')).textContent).toBe('stats unavailable');
	});

	it('keeps the answer of the latest request', async () => {
		let release!: (r: StatsResponse) => void;
		const slow = new Promise<StatsResponse>((r) => (release = r));
		const load = vi
			.fn<() => Promise<StatsResponse>>()
			.mockReturnValueOnce(slow)
			.mockResolvedValueOnce(response({ totals: { mowSec: 60 } }));
		setup(load);
		await userEvent.click(screen.getByLabelText('30 days'));
		await screen.findByText('History');
		release(response({ totals: { mowSec: 999_999 } }));
		await Promise.resolve();
		expect(within(section('Time')).getByText('Mowing').closest('div')!.textContent).toContain(
			'1 min'
		);
	});

	it('moves on and reloads every refreshMs', async () => {
		vi.useFakeTimers();
		const load = vi.fn(async () => response());
		render(StatsView, { load, now: () => now, refreshMs: 60_000 });
		expect(load).toHaveBeenCalledTimes(1);
		await vi.advanceTimersByTimeAsync(60_000);
		expect(load).toHaveBeenCalledTimes(2);
	});
});
