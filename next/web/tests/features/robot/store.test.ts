import { describe, expect, it, vi } from 'vitest';
import { RobotStore } from '#features/robot/store.svelte.ts';
import type { RobotMap } from '#features/robot/types.ts';
import { EventStream, type EventSourceLike } from '#shared/events.ts';
import { robotState } from './fixtures.ts';

const map: RobotMap = { perimeter: [{ x: 0, y: 0 }], exclusions: [], dock: [], way: [] };

function fakeStream() {
	const listeners = new Map<string, (ev: Event) => void>();
	const source: EventSourceLike = {
		onopen: null,
		onerror: null,
		addEventListener: (t, fn) => listeners.set(t, fn),
		removeEventListener: (t) => listeners.delete(t),
		close: () => {}
	};
	const stream = new EventStream('/x', () => source);
	return {
		stream,
		source,
		emit: (data: unknown) =>
			listeners.get('robot')?.(new MessageEvent('robot', { data: JSON.stringify(data) })),
		listening: () => listeners.has('robot')
	};
}

describe('RobotStore', () => {
	it('follows state and connection from the stream', () => {
		const store = new RobotStore(async () => map);
		const s = fakeStream();
		const stop = store.connect(s.stream);

		s.source.onopen!(new Event('open'));
		s.emit(robotState({ status: 'mow' }));
		expect(store.connected).toBe(true);
		expect(store.state?.status).toBe('mow');

		stop();
		expect(s.listening()).toBe(false);
	});

	it('loads the map once per map checksum', async () => {
		const load = vi.fn(async () => map);
		const store = new RobotStore(load);

		store.apply(robotState({ mapCrc: 1 }));
		store.apply(robotState({ mapCrc: 1 }));
		await vi.waitFor(() => expect(store.map).toEqual(map));
		store.apply(robotState({ mapCrc: 2 }));

		expect(load).toHaveBeenCalledTimes(2);
	});

	it('retries the map after a failed load', async () => {
		const log = vi.spyOn(console, 'error').mockImplementation(() => {});
		const load = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue(map);
		const store = new RobotStore(load);

		store.apply(robotState({ mapCrc: 1 }));
		await vi.waitFor(() => expect(log).toHaveBeenCalled());
		store.apply(robotState({ mapCrc: 1 }));
		await vi.waitFor(() => expect(store.map).toEqual(map));
		expect(load).toHaveBeenCalledTimes(2);
		log.mockRestore();
	});

	it('builds a trail while online and keeps it when offline', () => {
		const store = new RobotStore(async () => map);
		store.apply(robotState({ position: { x: 0, y: 0 } }));
		store.apply(robotState({ position: { x: 1, y: 0 } }));
		store.apply(robotState({ status: 'offline', position: { x: 2, y: 0 } }));
		expect(store.trail).toEqual([
			{ x: 0, y: 0 },
			{ x: 1, y: 0 }
		]);

		store.clearTrail();
		expect(store.trail).toEqual([]);
	});
});
