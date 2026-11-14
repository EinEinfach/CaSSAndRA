// Follows the app's log by asking for newer records at an interval.
import type { Level, LogEntry } from './types.ts';

export interface Scheduler {
	setInterval(fn: () => void, ms: number): unknown;
	clearInterval(handle: unknown): void;
}

export const browserScheduler: Scheduler = {
	setInterval: (fn, ms) => setInterval(fn, ms),
	clearInterval: (h) => clearInterval(h as ReturnType<typeof setInterval>)
};

const levels: Level[] = ['DEBUG', 'INFO', 'WARN', 'ERROR'];

/** The entries at minLevel or above whose text contains query (any case). */
export function filterEntries(entries: LogEntry[], query: string, minLevel: Level): LogEntry[] {
	const q = query.trim().toLowerCase();
	const min = levels.indexOf(minLevel);
	return entries.filter(
		(e) => levels.indexOf(e.level) >= min && (q === '' || e.message.toLowerCase().includes(q))
	);
}

/** "14:03:07" in local time. */
export function formatTime(iso: string): string {
	// eslint-disable-next-line svelte/prefer-svelte-reactivity -- read once, never changed
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return '';
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export class LogFeed {
	entries = $state<LogEntry[]>([]);
	paused = $state(false);
	error = $state('');
	private handle: unknown = null;
	private loading = false;
	/** Seq of the last cleared line, so cleared lines do not come back. */
	private clearedAt = 0;

	constructor(
		private load: (after: number) => Promise<LogEntry[]>,
		private scheduler: Scheduler = browserScheduler,
		private intervalMs = 2000,
		/** As many as the backend keeps. */
		private max = 1000
	) {}

	get lastSeq(): number {
		return this.entries.at(-1)?.seq ?? 0;
	}

	start(): void {
		if (this.handle !== null) return;
		void this.poll();
		this.handle = this.scheduler.setInterval(() => void this.poll(), this.intervalMs);
	}

	stop(): void {
		if (this.handle === null) return;
		this.scheduler.clearInterval(this.handle);
		this.handle = null;
	}

	/** Pausing keeps the lines still for reading; resuming fetches what came meanwhile. */
	togglePause(): void {
		this.paused = !this.paused;
		if (!this.paused) void this.poll();
	}

	clear(): void {
		const last = this.entries.at(-1);
		this.entries = [];
		this.clearedAt = last?.seq ?? this.clearedAt;
	}

	async poll(): Promise<void> {
		if (this.paused || this.loading) return;
		this.loading = true;
		try {
			const after = Math.max(this.lastSeq, this.clearedAt);
			const fresh = (await this.load(after)).filter((e) => e.seq > after);
			this.error = '';
			if (fresh.length > 0) this.entries = [...this.entries, ...fresh].slice(-this.max);
		} catch (err) {
			this.error = err instanceof Error ? err.message : String(err);
		} finally {
			this.loading = false;
		}
	}
}
