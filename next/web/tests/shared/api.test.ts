import { describe, expect, it, vi } from 'vitest';
import { ApiError, fetchHealth, getJSON, post } from '#shared/api.ts';

function respond(status: number, body?: unknown): typeof fetch {
	return vi.fn(
		async () => new Response(body === undefined ? null : JSON.stringify(body), { status })
	);
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

describe('getJSON', () => {
	it('uses the error message from the backend', async () => {
		const err = await getJSON('/api/x', respond(502, { error: 'robot offline' })).catch(
			(e: unknown) => e
		);
		expect((err as Error).message).toBe('/api/x: robot offline');
	});

	it('falls back to the status when the body is not JSON', async () => {
		const fetchFn = vi.fn(async () => new Response('<html>proxy error</html>', { status: 502 }));
		const err = await getJSON('/api/x', fetchFn).catch((e: unknown) => e);
		expect((err as Error).message).toBe('/api/x failed with status 502');
	});
});

describe('post', () => {
	it('sends JSON bodies', async () => {
		const fetchFn = respond(204);
		await post('/api/robot/move', { linear: 0.2, angular: 0 }, fetchFn);

		expect(fetchFn).toHaveBeenCalledWith('/api/robot/move', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: '{"linear":0.2,"angular":0}'
		});
	});

	it('sends no body and no content type without payload', async () => {
		const fetchFn = respond(204);
		await post('/api/robot/stop', undefined, fetchFn);

		expect(fetchFn).toHaveBeenCalledWith('/api/robot/stop', {
			method: 'POST',
			headers: {},
			body: undefined
		});
	});

	it('throws the backend error', async () => {
		await expect(
			post('/api/robot/dock', undefined, respond(503, { error: 'robot offline' }))
		).rejects.toThrow('/api/robot/dock: robot offline');
	});
});
