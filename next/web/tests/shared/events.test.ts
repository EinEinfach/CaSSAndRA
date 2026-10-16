import { describe, expect, it, vi } from 'vitest';
import { EventStream, type EventSourceLike } from '#shared/events.ts';

class FakeSource implements EventSourceLike {
	onopen: ((ev: Event) => unknown) | null = null;
	onerror: ((ev: Event) => unknown) | null = null;
	closed = false;
	listeners = new Map<string, Set<(ev: Event) => void>>();

	addEventListener(type: string, fn: (ev: Event) => void) {
		if (!this.listeners.has(type)) this.listeners.set(type, new Set());
		this.listeners.get(type)!.add(fn);
	}
	removeEventListener(type: string, fn: (ev: Event) => void) {
		this.listeners.get(type)?.delete(fn);
	}
	close() {
		this.closed = true;
	}
	emit(type: string, data: string) {
		for (const fn of this.listeners.get(type) ?? []) fn(new MessageEvent(type, { data }));
	}
}

function setup() {
	const source = new FakeSource();
	const urls: string[] = [];
	const stream = new EventStream('/api/events', (url) => {
		urls.push(url);
		return source;
	});
	return { source, stream, urls };
}

describe('EventStream', () => {
	it('connects to the given URL', () => {
		expect(setup().urls).toEqual(['/api/events']);
	});

	it('delivers parsed events by name', () => {
		const { source, stream } = setup();
		const robot = vi.fn();
		const other = vi.fn();
		stream.on('robot', robot);
		stream.on('map', other);

		source.emit('robot', '{"status":"idle"}');

		expect(robot).toHaveBeenCalledWith({ status: 'idle' });
		expect(other).not.toHaveBeenCalled();
	});

	it('stops delivering after unsubscribe', () => {
		const { source, stream } = setup();
		const fn = vi.fn();
		const off = stream.on('robot', fn);
		off();
		source.emit('robot', '{}');
		expect(fn).not.toHaveBeenCalled();
	});

	it('skips invalid JSON instead of throwing', () => {
		const { source, stream } = setup();
		const fn = vi.fn();
		const log = vi.spyOn(console, 'error').mockImplementation(() => {});
		stream.on('robot', fn);

		expect(() => source.emit('robot', '{broken')).not.toThrow();
		expect(fn).not.toHaveBeenCalled();
		expect(log).toHaveBeenCalled();
		log.mockRestore();
	});

	it('reports connection status and closes', () => {
		const { source, stream } = setup();
		const status = vi.fn();
		const off = stream.onStatus(status);

		source.onopen!(new Event('open'));
		source.onerror!(new Event('error'));
		source.onopen!(new Event('open'));
		stream.close();
		expect(status.mock.calls.map((c) => c[0])).toEqual([false, true, false, true, false]);
		expect(source.closed).toBe(true);

		off();
		source.onopen!(new Event('open'));
		expect(status).toHaveBeenCalledTimes(5);
	});

	it('tells a late status listener that the stream is connected', () => {
		const { source, stream } = setup();
		source.onopen!(new Event('open'));
		const status = vi.fn();
		stream.onStatus(status);
		expect(status).toHaveBeenCalledWith(true);
	});

	// A page opened again subscribes after the server sent its (only-on-change) events.
	it('gives a new listener the latest event of its type right away', () => {
		const { source, stream } = setup();
		const off = stream.on('robot', () => {});
		source.emit('robot', '{"n":1}');
		source.emit('robot', '{"n":2}');
		off();

		const late = vi.fn();
		stream.on('robot', late);
		expect(late).toHaveBeenCalledExactlyOnceWith({ n: 2 });

		source.emit('robot', '{"n":3}');
		expect(late).toHaveBeenLastCalledWith({ n: 3 });
		expect(late).toHaveBeenCalledTimes(2);
	});

	it('replays nothing before the first event', () => {
		const { stream } = setup();
		const fn = vi.fn();
		stream.on('maps', fn);
		stream.on('maps', fn);
		expect(fn).not.toHaveBeenCalled();
	});
});
