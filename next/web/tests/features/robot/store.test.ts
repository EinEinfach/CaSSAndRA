import { describe, expect, it, vi } from 'vitest';
import { RobotStore, type TrailApi } from '#features/robot/store.svelte.ts';
import type { RobotMap, Trail } from '#features/robot/types.ts';
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

/** The backend's trail; load answers when the test resolves it. */
function fakeTrail(initial: Trail = { id: 1, points: [] }) {
	let backend = initial;
	const waiting: (() => void)[] = [];
	const api = {
		load: vi.fn(() => new Promise<Trail>((resolve) => waiting.push(() => resolve(backend)))),
		clear: vi.fn(async () => {})
	} satisfies TrailApi;
	return {
		api,
		set: (t: Trail) => (backend = t),
		/** Answers all pending loads. */
		answer: async () => {
			waiting.splice(0).forEach((fn) => fn());
			await Promise.resolve();
			await Promise.resolve();
		}
	};
}

const p = (x: number) => ({ x, y: 0 });

describe('RobotStore', () => {
	it('follows state and connection from the stream', () => {
		const store = new RobotStore(async () => map, fakeTrail().api);
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
		const store = new RobotStore(load, fakeTrail().api);

		store.apply(robotState({ mapCrc: 1 }));
		store.apply(robotState({ mapCrc: 1 }));
		await vi.waitFor(() => expect(store.map).toEqual(map));
		store.apply(robotState({ mapCrc: 2 }));

		expect(load).toHaveBeenCalledTimes(2);
	});

	it('retries the map after a failed load', async () => {
		const log = vi.spyOn(console, 'error').mockImplementation(() => {});
		const load = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue(map);
		const store = new RobotStore(load, fakeTrail().api);

		store.apply(robotState({ mapCrc: 1 }));
		await vi.waitFor(() => expect(log).toHaveBeenCalled());
		store.apply(robotState({ mapCrc: 1 }));
		await vi.waitFor(() => expect(store.map).toEqual(map));
		expect(load).toHaveBeenCalledTimes(2);
		log.mockRestore();
	});

	it('takes the trail from the backend and extends it with new states', async () => {
		const t = fakeTrail({ id: 1, points: [p(0), p(1)] });
		const store = new RobotStore(async () => map, t.api);

		store.apply(robotState({ trailId: 1, position: p(1) }));
		store.apply(robotState({ trailId: 1, position: p(2) })); // arrives while loading
		await t.answer();
		expect(store.trail).toEqual([p(0), p(1), p(2)]);

		store.apply(robotState({ trailId: 1, position: p(3) }));
		store.apply(robotState({ trailId: 1, status: 'offline', position: p(4) }));
		expect(store.trail).toEqual([p(0), p(1), p(2), p(3)]);
		expect(t.api.load).toHaveBeenCalledTimes(1);
	});

	it('fetches the trail again when it starts anew (docked or cleared elsewhere)', async () => {
		const t = fakeTrail({ id: 1, points: [p(0), p(1)] });
		const store = new RobotStore(async () => map, t.api);
		store.apply(robotState({ trailId: 1, position: p(1) }));
		await t.answer();

		t.set({ id: 2, points: [p(5)] });
		store.apply(robotState({ trailId: 2, status: 'charging', position: p(5) }));
		expect(store.trail).toEqual([]);
		await t.answer();
		expect(store.trail).toEqual([p(5)]);
	});

	it('ignores a loaded trail that is already outdated', async () => {
		const t = fakeTrail({ id: 1, points: [p(0)] });
		const store = new RobotStore(async () => map, t.api);
		store.apply(robotState({ trailId: 1, position: p(0) }));
		t.set({ id: 2, points: [p(9)] }); // the backend moved on before answering
		await t.answer();
		expect(store.trail).toEqual([]);

		store.apply(robotState({ trailId: 2, position: p(9) }));
		await t.answer();
		expect(store.trail).toEqual([p(9)]);
	});

	it('retries loading the trail with the next state', async () => {
		const log = vi.spyOn(console, 'error').mockImplementation(() => {});
		const api: TrailApi = {
			load: vi
				.fn()
				.mockRejectedValueOnce(new Error('offline'))
				.mockResolvedValue({ id: 1, points: [p(7)] }),
			clear: vi.fn()
		};
		const store = new RobotStore(async () => map, api);
		store.apply(robotState({ trailId: 1, position: p(7) }));
		await vi.waitFor(() => expect(log).toHaveBeenCalled());
		store.apply(robotState({ trailId: 1, position: p(7) }));
		await vi.waitFor(() => expect(store.trail).toEqual([p(7)]));
		log.mockRestore();
	});

	it('clears the trail at once and in the backend', async () => {
		const t = fakeTrail({ id: 1, points: [p(0), p(1)] });
		const store = new RobotStore(async () => map, t.api);
		store.apply(robotState({ trailId: 1, position: p(1) }));
		await t.answer();

		await store.clearTrail();
		expect(store.trail).toEqual([]);
		expect(t.api.clear).toHaveBeenCalledOnce();
	});
});
