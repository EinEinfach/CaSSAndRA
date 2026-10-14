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

/**
 * One connection to /api/events. The browser reconnects by itself; listeners
 * see `connected` change and receive the latest state again after reconnecting.
 */
export class EventStream {
	private source: EventSourceLike;
	private statusListeners = new Set<(connected: boolean) => void>();

	constructor(url = '/api/events', factory: EventSourceFactory = (u) => new EventSource(u)) {
		this.source = factory(url);
		this.source.onopen = () => this.setStatus(true);
		this.source.onerror = () => this.setStatus(false);
	}

	/** Calls fn with the parsed JSON of every `name` event. Returns an unsubscribe function. */
	on<T>(name: string, fn: (data: T) => void): () => void {
		const listener = (ev: Event) => {
			try {
				fn(JSON.parse((ev as MessageEvent<string>).data) as T);
			} catch (err) {
				console.error(`invalid ${name} event`, err);
			}
		};
		this.source.addEventListener(name, listener);
		return () => this.source.removeEventListener(name, listener);
	}

	onStatus(fn: (connected: boolean) => void): () => void {
		this.statusListeners.add(fn);
		return () => this.statusListeners.delete(fn);
	}

	close(): void {
		this.source.close();
		this.setStatus(false);
	}

	private setStatus(connected: boolean) {
		for (const fn of this.statusListeners) fn(connected);
	}
}
