import { describe, expect, it, vi } from 'vitest';
import { ApiError, fetchHealth } from '#shared/api.ts';

function respond(status: number, body: unknown): typeof fetch {
	return vi.fn(async () => new Response(JSON.stringify(body), { status }));
}

describe('fetchHealth', () => {
	it('returns the parsed health response', async () => {
		const fetchFn = respond(200, { status: 'ok', version: '1.2.3' });

		await expect(fetchHealth(fetchFn)).resolves.toEqual({ status: 'ok', version: '1.2.3' });
		expect(fetchFn).toHaveBeenCalledWith('/api/health', expect.anything());
	});

	it('throws ApiError with path and status on HTTP errors', async () => {
		const err = await fetchHealth(respond(503, {})).catch((e: unknown) => e);

		expect(err).toBeInstanceOf(ApiError);
		expect(err).toMatchObject({ path: '/api/health', status: 503 });
	});

	it('passes network errors through', async () => {
		const fetchFn = vi.fn(async () => {
			throw new TypeError('network down');
		});

		await expect(fetchHealth(fetchFn)).rejects.toThrow('network down');
	});
});
