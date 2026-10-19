import { describe, expect, it } from 'vitest';
import { PlanStore, TaskStore } from '#features/tasks/store.svelte.ts';
import { EventStream, type EventSourceLike } from '#shared/events.ts';
import { plan, task } from './fixtures.ts';

function fakeStream() {
	const listeners = new Map<string, (ev: Event) => void>();
	const source: EventSourceLike = {
		onopen: null,
		onerror: null,
		addEventListener: (type, l) => listeners.set(type, l),
		removeEventListener: (type) => listeners.delete(type),
		close() {}
	};
	const stream = new EventStream('/x', () => source);
	const emit = (type: string, data: unknown) =>
		listeners.get(type)?.(new MessageEvent(type, { data: JSON.stringify(data) }));
	return { stream, emit, listeners };
}

describe('PlanStore', () => {
	it('follows the plan event', () => {
		const { stream, emit, listeners } = fakeStream();
		const store = new PlanStore();
		const stop = store.connect(stream);
		expect(store.loaded).toBe(false);

		emit('plan', { plan: plan() });
		expect(store.loaded).toBe(true);
		expect(store.plan?.route).toHaveLength(4);

		emit('plan', { plan: null });
		expect(store.plan).toBeNull();

		stop();
		expect(listeners.has('plan')).toBe(false);
	});

	it('TaskStore follows the tasks event and filters by map', () => {
		const { stream, emit } = fakeStream();
		const store = new TaskStore();
		const stop = store.connect(stream);
		emit('tasks', { tasks: [task('a', 'A'), task('b', 'B', { mapId: 'm2' })] });
		expect(store.loaded).toBe(true);
		expect(store.forMap('m1').map((t) => t.name)).toEqual(['A']);
		expect(store.forMap(undefined)).toEqual([]);
		stop();
	});
});
