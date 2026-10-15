import { describe, expect, it } from 'vitest';
import { MapsStore } from '#features/maps/store.svelte.ts';
import { EventStream, type EventSourceLike } from '#shared/events.ts';
import { garden } from './fixtures.ts';

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

describe('MapsStore', () => {
	it('follows the maps event', () => {
		const { stream, emit, listeners } = fakeStream();
		const store = new MapsStore();
		expect(store.loaded).toBe(false);
		const stop = store.connect(stream);

		emit('maps', { activeId: 'm2', maps: [garden('m1'), garden('m2', 'Yard')] });
		expect(store.loaded).toBe(true);
		expect(store.maps).toHaveLength(2);
		expect(store.active?.name).toBe('Yard');
		expect(store.byId('m1')?.name).toBe('Garden');
		expect(store.byId('nope')).toBeNull();

		stop();
		expect(listeners.has('maps')).toBe(false);
	});

	it('has no active map without activeId', () => {
		const store = new MapsStore();
		store.apply({ activeId: '', maps: [garden()] });
		expect(store.active).toBeNull();
	});
});
