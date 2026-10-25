import { describe, expect, it } from 'vitest';
import { ScheduleStore } from '#features/schedule/store.svelte.ts';
import { EventStream, type EventSourceLike } from '#shared/events.ts';
import { view } from './fixtures.ts';

describe('ScheduleStore', () => {
	it('follows the schedule event', () => {
		const listeners = new Map<string, (ev: Event) => void>();
		const source: EventSourceLike = {
			onopen: null,
			onerror: null,
			addEventListener: (type, l) => listeners.set(type, l),
			removeEventListener: (type) => listeners.delete(type),
			close() {}
		};
		const store = new ScheduleStore();
		const stop = store.connect(new EventStream('/x', () => source));
		expect(store.view).toBeNull();
		listeners.get('schedule')?.(new MessageEvent('schedule', { data: JSON.stringify(view()) }));
		expect(store.view?.schedule.days[0].taskIds).toEqual(['t1', 't2']);
		stop();
		expect(listeners.has('schedule')).toBe(false);
	});
});
