import { describe, expect, it, vi } from 'vitest';
import { saveSchedule } from '#features/schedule/api.ts';
import { schedule, view } from './fixtures.ts';

const respond = (status: number, body?: unknown) =>
	vi.fn(async () => new Response(body === undefined ? null : JSON.stringify(body), { status }));

describe('schedule api', () => {
	it('saves the schedule wrapped and returns the view', async () => {
		const fetchFn = respond(200, view());
		await expect(saveSchedule(schedule(), fetchFn)).resolves.toEqual(view());
		expect(fetchFn).toHaveBeenLastCalledWith(
			'/api/schedule',
			expect.objectContaining({ method: 'PUT', body: JSON.stringify({ schedule: schedule() }) })
		);
	});

	it('reports why saving failed', async () => {
		const fetchFn = respond(400, { error: 'invalid schedule: monday: task "x" not found' });
		await expect(saveSchedule(schedule(), fetchFn)).rejects.toThrow('task "x" not found');
	});
});
