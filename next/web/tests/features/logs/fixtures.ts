import type { Level, LogEntry } from '#features/logs/types.ts';

export const entry = (seq: number, message = `line ${seq}`, level: Level = 'INFO'): LogEntry => ({
	seq,
	time: `2026-11-14T10:00:${String(seq % 60).padStart(2, '0')}Z`,
	level,
	message
});

/** A Scheduler whose ticks the test runs by hand. */
export function manualScheduler() {
	const timers = new Map<number, () => void>();
	let next = 1;
	return {
		setInterval: (fn: () => void) => {
			timers.set(next, fn);
			return next++;
		},
		clearInterval: (h: unknown) => void timers.delete(h as number),
		tick: () => timers.forEach((fn) => fn()),
		get active() {
			return timers.size;
		}
	};
}
