import { describe, expect, it, vi } from 'vitest';
import { clearPreview, previewRoute, startMowing } from '#features/tasks/api.ts';
import { parameters, plan } from './fixtures.ts';

const respond = (status: number, body?: unknown) =>
	vi.fn(async () => new Response(body === undefined ? null : JSON.stringify(body), { status }));

describe('tasks api', () => {
	it('asks for a preview and returns the plan', async () => {
		const fetchFn = respond(200, plan());
		const req = { selection: [], parameters: parameters() };
		await expect(previewRoute(req, fetchFn)).resolves.toEqual(plan());
		expect(fetchFn).toHaveBeenLastCalledWith(
			'/api/tasks/preview',
			expect.objectContaining({ method: 'POST', body: JSON.stringify(req) })
		);
	});

	it('reports the reason of a failed preview', async () => {
		const fetchFn = respond(409, { error: 'no active map' });
		await expect(
			previewRoute({ selection: [], parameters: parameters() }, fetchFn)
		).rejects.toThrow('no active map');
	});

	it('discards the preview', async () => {
		const fetchFn = respond(204);
		await clearPreview(fetchFn);
		expect(fetchFn).toHaveBeenLastCalledWith(
			'/api/tasks/preview',
			expect.objectContaining({ method: 'DELETE' })
		);
	});

	it('starts mowing', async () => {
		const fetchFn = respond(204);
		await startMowing(fetchFn);
		expect(fetchFn).toHaveBeenLastCalledWith(
			'/api/tasks/start',
			expect.objectContaining({ method: 'POST' })
		);
	});
});
