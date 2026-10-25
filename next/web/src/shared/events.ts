// Live updates from the backend (Server-Sent Events on /api/events).

/** The part of the browser's EventSource that EventStream uses. */
export interface EventSourceLike {
	onopen: ((ev: Event) => unknown) | null;
	onerror: ((ev: Event) => unknown) | null;
	addEventListener(type: string, listener: (ev: Event) => void): void;
	removeEventListener(type: string, listener: (ev: Event) => void): void;
	close(): void;
}

export type EventSourceFactory = (url: string) => EventSourceLike;

/** The events the backend sends (app/app.go). They are kept from the start. */
export const eventNames = ['robot', 'settings', 'maps', 'tasks', 'plan', 'schedule'] as const;

/**
 * One connection to /api/events, shared by all pages. The browser reconnects
 * by itself; listeners see `connected` change and receive the latest state
 * again after reconnecting. The server sends most events only on change, so
 * the stream keeps the latest event of each type and the connection status
 * and hands them to every new listener right away (e.g. a page opened again).
 * It keeps the events in `names` from the start, so a page opened later gets
 * the ones sent before it subscribed; other names from their first listener.
 */
export class EventStream {
	private source: EventSourceLike;
	private statusListeners = new Set<(connected: boolean) => void>();
	private connected = false;
	private latest = new Map<string, string>();

	constructor(
		url = '/api/events',
		factory: EventSourceFactory = (u) => new EventSource(u),
		names: readonly string[] = eventNames
	) {
		this.source = factory(url);
		this.source.onopen = () => this.setStatus(true);
		this.source.onerror = () => this.setStatus(false);
		for (const name of names) this.keep(name);
	}

	/** Remembers the latest `name` event for listeners that come later. */
	private keep(name: string) {
		if (this.latest.has(name)) return;
		this.latest.set(name, '');
		this.source.addEventListener(name, (ev) => {
			this.latest.set(name, (ev as MessageEvent<string>).data);
		});
	}

	/**
	 * Calls fn with the parsed JSON of every `name` event, starting with the
	 * latest one if there was one. Returns an unsubscribe function.
	 */
	on<T>(name: string, fn: (data: T) => void): () => void {
		this.keep(name); // registered before fn, so the cache is current when fn runs
		const deliver = (data: string) => {
			try {
				fn(JSON.parse(data) as T);
			} catch (err) {
				console.error(`invalid ${name} event`, err);
			}
		};
		const listener = (ev: Event) => deliver((ev as MessageEvent<string>).data);
		const last = this.latest.get(name);
		if (last) deliver(last);
		this.source.addEventListener(name, listener);
		return () => this.source.removeEventListener(name, listener);
	}

	/** Calls fn with the current status and every change. Returns an unsubscribe function. */
	onStatus(fn: (connected: boolean) => void): () => void {
		this.statusListeners.add(fn);
		fn(this.connected);
		return () => this.statusListeners.delete(fn);
	}

	close(): void {
		this.source.close();
		this.setStatus(false);
	}

	private setStatus(connected: boolean) {
		this.connected = connected;
		for (const fn of this.statusListeners) fn(connected);
	}
}
