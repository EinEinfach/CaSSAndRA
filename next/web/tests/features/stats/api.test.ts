import { describe, expect, it, vi } from 'vitest';
import { fetchStats } from '#features/stats/api.ts';
import { response } from './fixtures.ts';

describe('stats api', () => {
	it('asks for a time span in RFC 3339 without milliseconds', async () => {
		const fetchFn = vi.fn(async () => new Response(JSON.stringify(response()), { status: 200 }));
		const got = await fetchStats(
			new Date('2026-10-25T09:00:00.250Z'),
			new Date('2026-10-26T09:00:00Z'),
			300,
			fetchFn
		);
		expect(got.totals.mowSec).toBe(7200);
		expect(fetchFn).toHaveBeenCalledWith(
			'/api/stats?from=2026-10-25T09%3A00%3A00Z&to=2026-10-26T09%3A00%3A00Z&points=300',
			expect.anything()
		);
	});

	it('reports why loading failed', async () => {
		const fetchFn = vi.fn(
			async () => new Response(JSON.stringify({ error: 'points: want 1 to 2000' }), { status: 400 })
		);
		await expect(fetchStats(new Date(0), new Date(1000), 0, fetchFn)).rejects.toThrow('points');
	});
});
