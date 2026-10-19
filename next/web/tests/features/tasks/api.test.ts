import { describe, expect, it, vi } from 'vitest';
import {
	clearPreview,
	createTask,
	deleteTask,
	previewRoute,
	startMowing,
	updateTask
} from '#features/tasks/api.ts';
import { parameters, plan, task } from './fixtures.ts';

const respond = (status: number, body?: unknown) =>
	vi.fn(async () => new Response(body === undefined ? null : JSON.stringify(body), { status }));

describe('tasks api', () => {
	it('asks for a preview and returns the plan', async () => {
		const fetchFn = respond(200, plan());
		const req = { parts: [{ selection: [], parameters: parameters() }] };
		await expect(previewRoute(req, fetchFn)).resolves.toEqual(plan());
		expect(fetchFn).toHaveBeenLastCalledWith(
			'/api/tasks/preview',
			expect.objectContaining({ method: 'POST', body: JSON.stringify(req) })
		);
	});

	it('reports the reason of a failed preview', async () => {
		const fetchFn = respond(409, { error: 'no active map' });
		await expect(previewRoute({ taskIds: ['a'] }, fetchFn)).rejects.toThrow('no active map');
	});

	it('discards the preview and starts mowing', async () => {
		const fetchFn = respond(204);
		await clearPreview(fetchFn);
		expect(fetchFn).toHaveBeenLastCalledWith(
			'/api/tasks/preview',
			expect.objectContaining({ method: 'DELETE' })
		);
		await startMowing(fetchFn);
		expect(fetchFn).toHaveBeenLastCalledWith(
			'/api/tasks/start',
			expect.objectContaining({ method: 'POST' })
		);
	});

	it('creates, updates and deletes tasks', async () => {
		const t = task('a b', 'Front');
		const post = respond(201, t);
		await expect(createTask(t, post)).resolves.toEqual(t);
		expect(post).toHaveBeenLastCalledWith(
			'/api/tasks',
			expect.objectContaining({ method: 'POST' })
		);
		const put = respond(200, t);
		await updateTask('a b', t, put);
		expect(put).toHaveBeenLastCalledWith(
			'/api/tasks/a%20b',
			expect.objectContaining({ method: 'PUT' })
		);
		const del = respond(204);
		await deleteTask('a b', del);
		expect(del).toHaveBeenLastCalledWith(
			'/api/tasks/a%20b',
			expect.objectContaining({ method: 'DELETE' })
		);
	});
});
