import { describe, expect, it, vi } from 'vitest';
import {
	activateMap,
	createMap,
	deleteMap,
	fetchMaps,
	updateMap,
	uploadMap
} from '#features/maps/api.ts';
import { garden } from './fixtures.ts';

const respond = (status: number, body?: unknown) =>
	vi.fn(async () => new Response(body === undefined ? null : JSON.stringify(body), { status }));

describe('maps api', () => {
	it('lists maps', async () => {
		const list = { activeId: 'm1', maps: [garden()] };
		await expect(fetchMaps(respond(200, list))).resolves.toEqual(list);
	});

	it('creates, updates and deletes', async () => {
		const fetchFn = respond(201, garden());
		await expect(createMap(garden(), fetchFn)).resolves.toEqual(garden());
		expect(fetchFn).toHaveBeenLastCalledWith(
			'/api/maps',
			expect.objectContaining({ method: 'POST' })
		);

		const put = respond(200, garden());
		await updateMap('a b', garden(), put);
		expect(put).toHaveBeenLastCalledWith(
			'/api/maps/a%20b',
			expect.objectContaining({ method: 'PUT' })
		);

		const del = respond(204);
		await deleteMap('m1', del);
		expect(del).toHaveBeenLastCalledWith(
			'/api/maps/m1',
			expect.objectContaining({ method: 'DELETE' })
		);
	});

	it('activates and uploads', async () => {
		const fetchFn = respond(204);
		await activateMap('m1', fetchFn);
		expect(fetchFn).toHaveBeenLastCalledWith(
			'/api/maps/active',
			expect.objectContaining({ method: 'PUT', body: '{"id":"m1"}' })
		);
		await uploadMap('m1', fetchFn);
		expect(fetchFn).toHaveBeenLastCalledWith(
			'/api/maps/m1/upload',
			expect.objectContaining({ method: 'POST' })
		);
	});

	it('passes errors on', async () => {
		await expect(
			uploadMap('m1', respond(409, { error: 'robot is driving, stop it first' }))
		).rejects.toThrow('robot is driving');
	});
});
