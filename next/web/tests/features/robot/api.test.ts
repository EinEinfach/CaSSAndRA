import { describe, expect, it, vi } from 'vitest';
import {
	command,
	fetchMap,
	fetchState,
	move,
	setMowMotor,
	skipToProgress
} from '#features/robot/api.ts';

const ok = () => vi.fn(async () => new Response(null, { status: 204 }));

describe('robot api', () => {
	it.each([
		'stop',
		'dock',
		'mow',
		'goto',
		'skip-next-point',
		'reboot',
		'reboot-gps',
		'shutdown'
	] as const)('posts %s without body', async (name) => {
		const fetchFn = ok();
		await command(name, fetchFn);
		expect(fetchFn).toHaveBeenCalledWith(
			`/api/robot/${name}`,
			expect.objectContaining({ method: 'POST', body: undefined })
		);
	});

	it('posts move and mow motor with JSON', async () => {
		const fetchFn = ok();
		await move(0.3, -0.5, fetchFn);
		await setMowMotor(true, fetchFn);
		expect(fetchFn).toHaveBeenNthCalledWith(
			1,
			'/api/robot/move',
			expect.objectContaining({ body: '{"linear":0.3,"angular":-0.5}' })
		);
		expect(fetchFn).toHaveBeenNthCalledWith(
			2,
			'/api/robot/mow-motor',
			expect.objectContaining({ body: '{"on":true}' })
		);
	});

	it('jumps to a fraction of the route', async () => {
		const fetchFn = ok();
		await skipToProgress(0.7, fetchFn);
		expect(fetchFn).toHaveBeenCalledWith(
			'/api/robot/skip-to-progress',
			expect.objectContaining({ body: '{"fraction":0.7}' })
		);
	});

	it('reads state and map', async () => {
		const fetchFn = vi.fn(
			async (url: string) => new Response(JSON.stringify({ url }), { status: 200 })
		);
		await expect(fetchState(fetchFn as typeof fetch)).resolves.toEqual({ url: '/api/robot/state' });
		await expect(fetchMap(fetchFn as typeof fetch)).resolves.toEqual({ url: '/api/robot/map' });
	});
});
